#!/usr/bin/env python3
"""
Passive Subdomain Finder Tool - Pasif yöntemlerle subdomain keşfi
Gerçek penetrasyon test uzmanları için kritik araç
"""

import asyncio
import aiohttp
import re
import json
import logging
from typing import Dict, Any, Set, List, Optional
from datetime import datetime
from tools.base_mcp_tool import MCPTool, ToolCategory

logger = logging.getLogger(__name__)

class SubdomainFinderModule(MCPTool):
    """Pasif subdomain keşif modülü"""
    
    def __init__(self):
        super().__init__(
            name="recon_passive_subfinder",
            description="Pasif yöntemlerle subdomain'leri keşfeder. Certificate Transparency, DNS kayıtları ve açık kaynaklar kullanır.",
            category=ToolCategory.RECONNAISSANCE
        )
        self.version = "1.0.0-MCP"
        self.reasoning_log = []
    
    async def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """MCP ajanı tarafından çağrılacak ana fonksiyon."""
        try:
            # Hem 'domain' hem de 'target' parametresini kabul et
            domain = params.get("domain") or params.get("target")
            if not domain:
                raise ValueError("Gerekli 'domain' veya 'target' parametresi eksik.")
            
            # URL'den domain çıkar
            if domain.startswith("http"):
                from urllib.parse import urlparse
                domain = urlparse(domain).netloc
            
            self._add_reasoning(self.reasoning_log, "initialization", f"Pasif subdomain keşfi '{domain}' için başlatılıyor.")
            
            # Ana tarama mantığını çalıştır
            scan_result = await self._scan_subdomains(domain)
            
            self._add_reasoning(self.reasoning_log, "analysis_complete", "Pasif subdomain keşfi tamamlandı.")
            
            return self._create_final_output(
                success=True,
                data=scan_result,
                ai_summary=self._generate_ai_summary(scan_result),
                recommendations=self._generate_mcp_recommendations(scan_result)
            )
            
        except Exception as e:
            logger.error(f"Subdomain finder'da hata: {e}", exc_info=True)
            self._add_reasoning(self.reasoning_log, "error", f"Araç çalıştırılırken kritik bir hata oluştu: {e}")
            return self._create_final_output(
                success=False,
                data={},
                ai_summary=f"Araç çalıştırılırken kritik bir hata oluştu: {e}",
                recommendations=[],
                error=str(e)
            )
    
    async def _scan_subdomains(self, domain: str) -> Dict[str, Any]:
        """Ana subdomain tarama fonksiyonu."""
        found_subdomains = set()
        
        async with aiohttp.ClientSession() as session:
            # ÜCRETSİZ kaliteli kaynaklardan subdomain'leri topla
            await self._get_crtsh(session, domain, found_subdomains)
            await self._get_censys_ct(session, domain, found_subdomains)
            await self._get_crato_ct(session, domain, found_subdomains)
            await self._get_hackertarget(session, domain, found_subdomains)
            await self._get_threatcrowd(session, domain, found_subdomains)
            await self._get_dnsdumpster(session, domain, found_subdomains)
            await self._get_securitytrails(session, domain, found_subdomains)
            await self._get_rapiddns(session, domain, found_subdomains)
            await self._get_wayback_machine(session, domain, found_subdomains)
            await self._get_github_leaks(session, domain, found_subdomains)
            await self._get_gitlab_leaks(session, domain, found_subdomains)
        
        # Subdomain'leri temizle ve analiz et
        clean_subdomains = self._clean_subdomains(found_subdomains, domain)
        analyzed_subdomains = self._analyze_subdomains(clean_subdomains)
        
        return {
            "subdomains": analyzed_subdomains,
            "total_found": len(clean_subdomains),
            "ai_reasoning": self.reasoning_log
        }

    async def _fetch_from_source(self, session: aiohttp.ClientSession, url: str, headers: Optional[Dict] = None) -> Any:
        source_name = url.split('/')[2]
        try:
            async with session.get(url, headers=headers, timeout=25, ssl=False) as response:
                if response.status == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        return await response.json()
                    else:
                        return await response.text()
                elif response.status == 502:
                    logger.warning(f"Kaynak {source_name} 502 durum kodu döndürdü.")
                    return None
                else:
                    logger.warning(f"Kaynak {source_name} {response.status} durum kodu döndürdü.")
                    return None
        except Exception as e:
            logger.warning(f"Kaynak {source_name} erişim hatası: {e}")
            return None

    async def _get_crtsh(self, session: aiohttp.ClientSession, domain: str, found_subdomains: Set[str]):
        """crt.sh'den subdomain'leri al - İyileştirilmiş parsing"""
        self._add_reasoning(self.reasoning_log, "crtsh_lookup", f"crt.sh'den '{domain}' için sertifika kayıtları aranıyor...")
        try:
            # JSON API'yi dene
            url = f"https://crt.sh/?q=%25.{domain}&output=json"
            data = await self._fetch_from_source(session, url)
            if data and isinstance(data, list):
                for cert in data:
                    # name_value alanından subdomain'leri çıkar
                    if 'name_value' in cert:
                        names = cert['name_value'].split('\n')
                        for name in names:
                            name = name.strip()
                            if name.endswith(f'.{domain}') and '*' not in name and name != domain:
                                found_subdomains.add(name)
                                self._add_reasoning(self.reasoning_log, "crtsh_found", f"crt.sh JSON'den subdomain bulundu: {name}")
                    
                    # common_name alanından da kontrol et
                    if 'common_name' in cert:
                        cn = cert['common_name'].strip()
                        if cn.endswith(f'.{domain}') and '*' not in cn and cn != domain:
                            found_subdomains.add(cn)
                            self._add_reasoning(self.reasoning_log, "crtsh_cn_found", f"crt.sh Common Name'den subdomain bulundu: {cn}")
            
            # HTML fallback - daha kapsamlı parsing
            html_url = f"https://crt.sh/?q=%25.{domain}"
            html_data = await self._fetch_from_source(session, html_url)
            if html_data and isinstance(html_data, str):
                # Daha kapsamlı regex pattern'leri
                patterns = [
                    rf'([a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]\.{re.escape(domain)})',  # Normal subdomain
                    rf'([a-zA-Z0-9]+\.{re.escape(domain)})',  # Basit subdomain
                    rf'([a-zA-Z0-9-]+\.{re.escape(domain)})'   # Tire içeren subdomain
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, html_data, re.IGNORECASE)
                    for match in matches:
                        match = match.lower().strip()
                        if match != domain and '*' not in match and len(match) > len(domain) + 1:
                            found_subdomains.add(match)
                            self._add_reasoning(self.reasoning_log, "crtsh_html_found", f"crt.sh HTML'den subdomain bulundu: {match}")
                
                # Tablo içindeki subdomain'leri de bul
                table_pattern = rf'<td[^>]*>([a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]\.{re.escape(domain)})</td>'
                table_matches = re.findall(table_pattern, html_data, re.IGNORECASE)
                for match in table_matches:
                    match = match.lower().strip()
                    if match != domain and '*' not in match:
                        found_subdomains.add(match)
                        self._add_reasoning(self.reasoning_log, "crtsh_table_found", f"crt.sh tablosundan subdomain bulundu: {match}")
                        
        except Exception as e:
            self._add_reasoning(self.reasoning_log, "crtsh_error", f"crt.sh aranırken hata: {e}")

    async def _get_hackertarget(self, session: aiohttp.ClientSession, domain: str, found_subdomains: Set[str]):
        """HackerTarget'den subdomain'leri al - İyileştirilmiş parsing"""
        self._add_reasoning(self.reasoning_log, "hackertarget_lookup", f"HackerTarget'den '{domain}' için DNS kayıtları aranıyor...")
        try:
            url = f"https://api.hackertarget.com/hostsearch/?q={domain}"
            data = await self._fetch_from_source(session, url)
            if data and isinstance(data, str):
                lines = data.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line and ',' in line:
                        parts = line.split(',')
                        if len(parts) >= 2:
                            subdomain = parts[0].strip()
                            ip = parts[1].strip()
                            
                            # Subdomain kontrolü
                            if subdomain.endswith(f'.{domain}') and subdomain != domain:
                                found_subdomains.add(subdomain)
                                self._add_reasoning(self.reasoning_log, "hackertarget_found", f"HackerTarget'den subdomain bulundu: {subdomain} -> {ip}")
                    
                    # Virgül olmayan satırları da kontrol et (bazen farklı format)
                    elif line and '.' in line and domain in line:
                        # Basit regex ile subdomain kontrolü
                        subdomain_pattern = rf'([a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]\.{re.escape(domain)})'
                        matches = re.findall(subdomain_pattern, line)
                        for match in matches:
                            if match != domain:
                                found_subdomains.add(match)
                                self._add_reasoning(self.reasoning_log, "hackertarget_regex_found", f"HackerTarget regex'den subdomain bulundu: {match}")
                                
        except Exception as e:
            self._add_reasoning(self.reasoning_log, "hackertarget_error", f"HackerTarget aranırken hata: {e}")

    async def _get_threatcrowd(self, session: aiohttp.ClientSession, domain: str, found_subdomains: Set[str]):
        """ThreatCrowd'den subdomain'leri al - İyileştirilmiş parsing"""
        self._add_reasoning(self.reasoning_log, "threatcrowd_lookup", f"ThreatCrowd'den '{domain}' için subdomain'ler aranıyor...")
        try:
            url = f"https://www.threatcrowd.org/searchApi/v2/domain/report/?domain={domain}"
            data = await self._fetch_from_source(session, url)
            if data and isinstance(data, dict):
                # subdomains alanından subdomain'leri al
                if 'subdomains' in data and isinstance(data['subdomains'], list):
                    for subdomain in data['subdomains']:
                        if subdomain.endswith(f'.{domain}') and subdomain != domain:
                            found_subdomains.add(subdomain)
                            self._add_reasoning(self.reasoning_log, "threatcrowd_found", f"ThreatCrowd'den subdomain bulundu: {subdomain}")
                
                # resolutions alanından da subdomain'leri kontrol et
                if 'resolutions' in data and isinstance(data['resolutions'], list):
                    for resolution in data['resolutions']:
                        if isinstance(resolution, dict) and 'domain' in resolution:
                            domain_name = resolution['domain']
                            if domain_name.endswith(f'.{domain}') and domain_name != domain:
                                found_subdomains.add(domain_name)
                                self._add_reasoning(self.reasoning_log, "threatcrowd_resolution_found", f"ThreatCrowd resolution'den subdomain bulundu: {domain_name}")
                                
        except Exception as e:
            self._add_reasoning(self.reasoning_log, "threatcrowd_error", f"ThreatCrowd aranırken hata: {e}")

    async def _get_dnsdumpster(self, session: aiohttp.ClientSession, domain: str, found_subdomains: Set[str]):
        """DNSdumpster'den subdomain'leri al"""
        self._add_reasoning(self.reasoning_log, "dnsdumpster_lookup", "DNSdumpster'den DNS kayıtları aranıyor...")
        try:
            # DNSdumpster için CSRF token al
            csrf_url = "https://dnsdumpster.com/"
            csrf_data = await self._fetch_from_source(session, csrf_url)
            if csrf_data and isinstance(csrf_data, str):
                # CSRF token'ı bul
                csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', csrf_data)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
                    
                    # POST request ile subdomain'leri al
                    post_url = "https://dnsdumpster.com/"
                    headers = {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'Referer': 'https://dnsdumpster.com/',
                        'X-CSRFToken': csrf_token
                    }
                    post_data = f"csrfmiddlewaretoken={csrf_token}&targetip={domain}"
                    
                    async with session.post(post_url, data=post_data, headers=headers, timeout=30) as response:
                        if response.status == 200:
                            html_content = await response.text()
                            # Subdomain'leri bul
                            subdomain_pattern = rf'([a-zA-Z0-9-]+\.{re.escape(domain)})'
                            matches = re.findall(subdomain_pattern, html_content)
                            for match in matches:
                                if match != domain and '*' not in match:
                                    found_subdomains.add(match)
                                    self._add_reasoning(self.reasoning_log, "dnsdumpster_found", f"DNSdumpster'den subdomain bulundu: {match}")
                else:
                    self._add_reasoning(self.reasoning_log, "dnsdumpster_csrf_error", "DNSdumpster CSRF token bulunamadı.")
        except Exception as e:
            self._add_reasoning(self.reasoning_log, "dnsdumpster_error", f"DNSdumpster aranırken hata: {e}")

    async def _get_securitytrails(self, session: aiohttp.ClientSession, domain: str, found_subdomains: Set[str]):
        """SecurityTrails'den subdomain'leri al"""
        self._add_reasoning(self.reasoning_log, "securitytrails_lookup", "SecurityTrails'den subdomain'ler aranıyor...")
        try:
            # SecurityTrails API key gerektirir
            self._add_reasoning(self.reasoning_log, "securitytrails_skipped", "SecurityTrails için API key gerekli, atlandı.")
        except Exception as e:
            self._add_reasoning(self.reasoning_log, "securitytrails_error", f"SecurityTrails aranırken hata: {e}")

    async def _get_rapiddns(self, session: aiohttp.ClientSession, domain: str, found_subdomains: Set[str]):
        """RapidDNS'den subdomain'leri al - İyileştirilmiş parsing"""
        self._add_reasoning(self.reasoning_log, "rapiddns_lookup", f"RapidDNS'den '{domain}' için DNS kayıtları aranıyor...")
        try:
            url = f"https://rapiddns.io/subdomain/{domain}?full=1"
            data = await self._fetch_from_source(session, url)
            if data and isinstance(data, str):
                # Daha kapsamlı regex pattern'leri
                patterns = [
                    rf'([a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]\.{re.escape(domain)})',  # Normal subdomain
                    rf'([a-zA-Z0-9]+\.{re.escape(domain)})',  # Basit subdomain
                    rf'([a-zA-Z0-9-]+\.{re.escape(domain)})'   # Tire içeren subdomain
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, data, re.IGNORECASE)
                    for match in matches:
                        match = match.lower().strip()
                        if match != domain and '*' not in match and len(match) > len(domain) + 1:
                            found_subdomains.add(match)
                            self._add_reasoning(self.reasoning_log, "rapiddns_found", f"RapidDNS'den subdomain bulundu: {match}")
                
                # Tablo içindeki DNS kayıtlarından subdomain'leri bul
                table_patterns = [
                    rf'<td[^>]*>([a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]\.{re.escape(domain)})</td>',
                    rf'<td[^>]*>([a-zA-Z0-9]+\.{re.escape(domain)})</td>',
                    rf'<td[^>]*>([a-zA-Z0-9-]+\.{re.escape(domain)})</td>'
                ]
                
                for pattern in table_patterns:
                    table_matches = re.findall(pattern, data, re.IGNORECASE)
                    for match in table_matches:
                        match = match.lower().strip()
                        if match != domain and '*' not in match:
                            found_subdomains.add(match)
                            self._add_reasoning(self.reasoning_log, "rapiddns_table_found", f"RapidDNS tablosundan subdomain bulundu: {match}")
                
                # DNS kayıt formatından subdomain'leri bul
                dns_patterns = [
                    rf'([a-zA-Z0-9-]+)\.{re.escape(domain)}\s+[A-Z]+\s+',
                    rf'([a-zA-Z0-9-]+)\.{re.escape(domain)}\s+IN\s+',
                    rf'([a-zA-Z0-9-]+)\.{re.escape(domain)}\s+\d+\s+'
                ]
                
                for pattern in dns_patterns:
                    dns_matches = re.findall(pattern, data, re.IGNORECASE)
                    for match in dns_matches:
                        full_subdomain = f"{match.lower()}.{domain}"
                        if full_subdomain != domain:
                            found_subdomains.add(full_subdomain)
                            self._add_reasoning(self.reasoning_log, "rapiddns_dns_found", f"RapidDNS DNS'den subdomain bulundu: {full_subdomain}")
                            
        except Exception as e:
            self._add_reasoning(self.reasoning_log, "rapiddns_error", f"RapidDNS aranırken hata: {e}")

    def _clean_subdomains(self, subdomains: Set[str], domain: str) -> List[str]:
        """Subdomain'leri temizle ve filtrele"""
        clean_subdomains = []
        for subdomain in subdomains:
            # Temizleme işlemleri
            subdomain = subdomain.strip().lower()
            if (subdomain.endswith(f'.{domain}') and 
                subdomain != domain and 
                len(subdomain) > len(domain) + 2 and
                not subdomain.startswith('*')):
                clean_subdomains.append(subdomain)
        
        return sorted(list(set(clean_subdomains)))

    def _analyze_subdomains(self, subdomains: List[str]) -> List[Dict[str, Any]]:
        """Subdomain'leri analiz et ve risk seviyesi belirle"""
        analyzed_subdomains = []
        for subdomain in subdomains:
            risk_level = self._determine_risk_level(subdomain)
            analyzed_subdomains.append({
                "subdomain": subdomain,
                "risk_level": risk_level,
                "confidence": "high",
                "method": "passive_discovery"
            })
        return analyzed_subdomains

    def _determine_risk_level(self, subdomain: str) -> str:
        """Subdomain'in risk seviyesini belirle"""
        high_risk_keywords = ["admin", "api", "dev", "test", "staging", "backup", "db", "database", "mail", "ftp"]
        medium_risk_keywords = ["www", "blog", "shop", "store", "app", "mobile", "cdn", "static"]
        
        subdomain_lower = subdomain.lower()
        
        for keyword in high_risk_keywords:
            if keyword in subdomain_lower:
                return "high"
        
        for keyword in medium_risk_keywords:
            if keyword in subdomain_lower:
                return "medium"
        
        return "low"

    def _generate_ai_summary(self, scan_result: Dict[str, Any]) -> str:
        """İnsan tarafından okunabilir bir özet oluşturur."""
        subdomains = scan_result.get('subdomains', [])
        if not subdomains:
            return "Hiçbir subdomain pasif yöntemlerle tespit edilemedi."
        
        high_risk_count = len([s for s in subdomains if s.get('risk_level') == 'high'])
        medium_risk_count = len([s for s in subdomains if s.get('risk_level') == 'medium'])
        
        summary = f"{len(subdomains)} subdomain pasif yöntemlerle tespit edildi. "
        summary += f"{high_risk_count} tanesi yüksek risk, {medium_risk_count} tanesi orta risk seviyesinde."
        
        return summary

    def _generate_mcp_recommendations(self, scan_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """Dinamik uzman önerileri oluşturur."""
        recommendations = []
        
        subdomains = scan_result.get('subdomains', [])
        domain = scan_result.get('domain', '')
        
        if subdomains:
            # Dinamik subdomain analizi ve öneriler
            subdomain_recommendations = self._generate_subdomain_expert_recommendations(subdomains, domain)
            recommendations.extend(subdomain_recommendations)
        else:
            # Subdomain bulunamadığında alternatif stratejiler
            recommendations.extend(self._generate_fallback_recommendations(domain))
        
        return recommendations

    def _generate_subdomain_expert_recommendations(self, subdomains: List[Dict], domain: str) -> List[Dict]:
        """Subdomain'lere özel dinamik uzman önerileri oluşturur."""
        recommendations = []
        
        # Subdomain kategorilerini analiz et
        admin_subdomains = [s for s in subdomains if any(keyword in s['subdomain'].lower() for keyword in ['admin', 'panel', 'dashboard', 'control'])]
        api_subdomains = [s for s in subdomains if any(keyword in s['subdomain'].lower() for keyword in ['api', 'rest', 'graphql', 'v1', 'v2'])]
        dev_subdomains = [s for s in subdomains if any(keyword in s['subdomain'].lower() for keyword in ['dev', 'test', 'staging', 'beta', 'alpha'])]
        mail_subdomains = [s for s in subdomains if any(keyword in s['subdomain'].lower() for keyword in ['mail', 'smtp', 'pop', 'imap', 'mx'])]
        cdn_subdomains = [s for s in subdomains if any(keyword in s['subdomain'].lower() for keyword in ['cdn', 'static', 'assets', 'media'])]
        
        # Admin subdomain'leri için kritik öneriler
        if admin_subdomains:
            for admin_sub in admin_subdomains[:3]:  # İlk 3 admin subdomain
                recommendations.append({
                    "priority": "critical",
                    "tool": "enum_tech_detector",
                    "reason": f"🚨 ADMIN PANEL KEŞFİ: {admin_sub['subdomain']} admin paneli tespit edildi. Kritik güvenlik analizi ve authentication bypass testleri yapılmalı.",
                    "params": {"url": f"https://{admin_sub['subdomain']}", "admin_panel": True},
                    "expert_context": f"Admin panelleri için kritik güvenlik analizi. {admin_sub['subdomain']} için bilinen admin panel zafiyetleri ve authentication bypass teknikleri test edilmeli."
                })
        
        # API subdomain'leri için özel öneriler
        if api_subdomains:
            for api_sub in api_subdomains[:2]:  # İlk 2 API subdomain
                recommendations.append({
                    "priority": "high",
                    "tool": "api_vuln_idor_scanner",
                    "reason": f"🔌 API GÜVENLİK ANALİZİ: {api_sub['subdomain']} API endpoint'i tespit edildi. IDOR, authentication bypass ve API güvenlik zafiyetleri analiz edilmeli.",
                    "params": {"url": f"https://{api_sub['subdomain']}", "api_analysis": True},
                    "expert_context": f"API güvenliği için kritik analiz. {api_sub['subdomain']} için API-specific zafiyetler ve authentication bypass teknikleri test edilmeli."
                })
        
        # Genel subdomain'ler için port taraması
        if len(subdomains) > 0:
            recommendations.append({
                "priority": "high",
                "tool": "enum_port_scanner",
                "reason": f"🔍 SUBDOMAIN PORT TARAMASI: {len(subdomains)} subdomain tespit edildi. Her subdomain için port taraması ve servis keşfi yapılmalı.",
                "params": {"target": ",".join([s['subdomain'] for s in subdomains[:10]]), "scan_type": "comprehensive"},
                "expert_context": f"Subdomain port taraması için kritik analiz. {len(subdomains)} subdomain için port taraması ve servis keşfi yapılmalı."
            })
        
        return recommendations

    def _generate_fallback_recommendations(self, domain: str) -> List[Dict]:
        """Subdomain bulunamadığında alternatif stratejiler önerir."""
        recommendations = []
        
        recommendations.append({
            "priority": "high",
            "tool": "enum_subdomain_bruteforcer",
            "reason": f"🔨 DNS BRUTE FORCE: {domain} için pasif subdomain keşfi başarısız. DNS brute force ile yaygın subdomain'ler test edilmeli.",
            "params": {"domain": domain, "wordlist": "common_subdomains", "threads": 50},
            "expert_context": f"DNS brute force için kritik analiz. {domain} için yaygın subdomain'ler ve wordlist-based enumeration yapılmalı."
        })
        
        recommendations.append({
            "priority": "medium",
            "tool": "enum_tech_detector",
            "reason": f"🔍 ANA DOMAIN ANALİZİ: {domain} ana domain'i için teknoloji tespiti ve güvenlik analizi yapılmalı.",
            "params": {"url": f"https://{domain}", "comprehensive": True},
            "expert_context": f"Ana domain analizi için kritik bilgi toplama. {domain} için teknoloji stack'i ve güvenlik konfigürasyonları kontrol edilmeli."
        })
        
        return recommendations

    def _add_reasoning(self, log: List[Dict[str, str]], phase: str, thought: str):
        """Muhakeme adımlarını log'a ekler."""
        log.append({"phase": phase, "thought": thought})

    async def _get_censys_ct(self, session: aiohttp.ClientSession, domain: str, found_subdomains: Set[str]):
        """Censys.io Certificate Transparency logs (ücretsiz tier)"""
        try:
            self.reasoning_log.append({"phase": "censys_start", "thought": f"Censys CT logs '{domain}' için taranıyor."})
            
            # Censys ücretsiz arama endpoint'i
            search_url = f"https://search.censys.io/certificates?q={domain}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            async with session.get(search_url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # HTML içinden subdomain'leri çıkar
                    subdomain_pattern = rf'([a-zA-Z0-9][a-zA-Z0-9\-]*\.)*{re.escape(domain)}'
                    matches = re.findall(subdomain_pattern, content, re.IGNORECASE)
                    
                    for match in matches:
                        if isinstance(match, tuple):
                            subdomain = ''.join(match)
                        else:
                            subdomain = match
                        
                        if subdomain and subdomain.endswith(domain) and subdomain != domain:
                            found_subdomains.add(subdomain.lower())
                    
                    self.reasoning_log.append({"phase": "censys_found", "thought": f"Censys'ten {len(matches)} potansiyel subdomain bulundu."})
                else:
                    self.reasoning_log.append({"phase": "censys_error", "thought": f"Censys CT logs erişim hatası: {response.status}"})
                    
        except Exception as e:
            self.reasoning_log.append({"phase": "censys_error", "thought": f"Censys CT taramasında hata: {e}"})

    async def _get_crato_ct(self, session: aiohttp.ClientSession, domain: str, found_subdomains: Set[str]):
        """Crato.sh Certificate Transparency logs (ücretsiz)"""
        try:
            self.reasoning_log.append({"phase": "crato_start", "thought": f"Crato.sh CT logs '{domain}' için taranıyor."})
            
            url = f"https://crt.sh/?q=%.{domain}&output=json"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        if isinstance(data, list):
                            for cert in data:
                                name_value = cert.get('name_value', '')
                                if name_value:
                                    # Çoklu subdomain'leri ayır
                                    subdomains = name_value.split('\n')
                                    for subdomain in subdomains:
                                        subdomain = subdomain.strip().lower()
                                        if subdomain.endswith(domain) and subdomain != domain:
                                            found_subdomains.add(subdomain)
                                    
                            self.reasoning_log.append({"phase": "crato_found", "thought": f"Crato.sh'ten {len(data)} sertifika kaydı bulundu."})
                    except json.JSONDecodeError:
                        # JSON değilse HTML parse et
                        content = await response.text()
                        subdomain_pattern = rf'([a-zA-Z0-9][a-zA-Z0-9\-]*\.)*{re.escape(domain)}'
                        matches = re.findall(subdomain_pattern, content, re.IGNORECASE)
                        
                        for match in matches:
                            if isinstance(match, tuple):
                                subdomain = ''.join(match)
                            else:
                                subdomain = match
                            
                            if subdomain and subdomain.endswith(domain) and subdomain != domain:
                                found_subdomains.add(subdomain.lower())
                        
                        self.reasoning_log.append({"phase": "crato_html_found", "thought": f"Crato.sh HTML'den {len(matches)} subdomain bulundu."})
                else:
                    self.reasoning_log.append({"phase": "crato_error", "thought": f"Crato.sh erişim hatası: {response.status}"})
                    
        except Exception as e:
            self.reasoning_log.append({"phase": "crato_error", "thought": f"Crato.sh taramasında hata: {e}"})

    async def _get_wayback_machine(self, session: aiohttp.ClientSession, domain: str, found_subdomains: Set[str]):
        """Wayback Machine DNS history (ücretsiz)"""
        try:
            self.reasoning_log.append({"phase": "wayback_start", "thought": f"Wayback Machine '{domain}' için DNS geçmişi taranıyor."})
            
            url = f"https://web.archive.org/cdx/search/cdx?url=*.{domain}/*&output=json&collapse=urlkey"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        if isinstance(data, list) and len(data) > 1:  # İlk satır header
                            for row in data[1:]:  # Header'ı atla
                                if len(row) > 2:
                                    url_key = row[2]  # URL key
                                    # URL'den subdomain çıkar
                                    if url_key.startswith('http://') or url_key.startswith('https://'):
                                        try:
                                            from urllib.parse import urlparse
                                            parsed = urlparse(url_key)
                                            hostname = parsed.hostname
                                            if hostname and hostname.endswith(domain) and hostname != domain:
                                                found_subdomains.add(hostname.lower())
                                        except:
                                            continue
                            
                            self.reasoning_log.append({"phase": "wayback_found", "thought": f"Wayback Machine'den {len(data)-1} URL kaydı bulundu."})
                    except json.JSONDecodeError:
                        self.reasoning_log.append({"phase": "wayback_error", "thought": "Wayback Machine JSON parse hatası."})
                else:
                    self.reasoning_log.append({"phase": "wayback_error", "thought": f"Wayback Machine erişim hatası: {response.status}"})
                    
        except Exception as e:
            self.reasoning_log.append({"phase": "wayback_error", "thought": f"Wayback Machine taramasında hata: {e}"})

    async def _get_github_leaks(self, session: aiohttp.ClientSession, domain: str, found_subdomains: Set[str]):
        """GitHub code leak scanning (ücretsiz API)"""
        try:
            self.reasoning_log.append({"phase": "github_start", "thought": f"GitHub '{domain}' için kod sızıntısı taranıyor."})
            
            # GitHub API ücretsiz endpoint'leri
            search_queries = [
                f'"{domain}"',
                f'site:github.com "{domain}"',
                f'"{domain}" filename:config',
                f'"{domain}" filename:env',
                f'"{domain}" filename:dockerfile'
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            for query in search_queries:
                try:
                    url = f"https://api.github.com/search/code?q={query}"
                    async with session.get(url, headers=headers, timeout=30) as response:
                        if response.status == 200:
                            data = await response.json()
                            items = data.get('items', [])
                            
                            for item in items:
                                # Repository content'ini kontrol et
                                content_url = item.get('html_url', '')
                                if content_url:
                                    # URL'den subdomain çıkar
                                    subdomain_pattern = rf'([a-zA-Z0-9][a-zA-Z0-9\-]*\.)*{re.escape(domain)}'
                                    matches = re.findall(subdomain_pattern, content_url, re.IGNORECASE)
                                    
                                    for match in matches:
                                        if isinstance(match, tuple):
                                            subdomain = ''.join(match)
                                        else:
                                            subdomain = match
                                        
                                        if subdomain and subdomain.endswith(domain) and subdomain != domain:
                                            found_subdomains.add(subdomain.lower())
                            
                            self.reasoning_log.append({"phase": "github_found", "thought": f"GitHub'dan '{query}' için {len(items)} kod parçası bulundu."})
                        else:
                            self.reasoning_log.append({"phase": "github_error", "thought": f"GitHub API hatası: {response.status}"})
                            
                        # Rate limiting için bekle
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    self.reasoning_log.append({"phase": "github_query_error", "thought": f"GitHub query '{query}' hatası: {e}"})
                    continue
                    
        except Exception as e:
            self.reasoning_log.append({"phase": "github_error", "thought": f"GitHub taramasında hata: {e}"})

    async def _get_gitlab_leaks(self, session: aiohttp.ClientSession, domain: str, found_subdomains: Set[str]):
        """GitLab code leak scanning (ücretsiz)"""
        try:
            self.reasoning_log.append({"phase": "gitlab_start", "thought": f"GitLab '{domain}' için kod sızıntısı taranıyor."})
            
            # GitLab ücretsiz arama
            search_url = f"https://gitlab.com/search?search={domain}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            async with session.get(search_url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # HTML içinden subdomain'leri çıkar
                    subdomain_pattern = rf'([a-zA-Z0-9][a-zA-Z0-9\-]*\.)*{re.escape(domain)}'
                    matches = re.findall(subdomain_pattern, content, re.IGNORECASE)
                    
                    for match in matches:
                        if isinstance(match, tuple):
                            subdomain = ''.join(match)
                        else:
                            subdomain = match
                        
                        if subdomain and subdomain.endswith(domain) and subdomain != domain:
                            found_subdomains.add(subdomain.lower())
                    
                    self.reasoning_log.append({"phase": "gitlab_found", "thought": f"GitLab'dan {len(matches)} potansiyel subdomain bulundu."})
                else:
                    self.reasoning_log.append({"phase": "gitlab_error", "thought": f"GitLab erişim hatası: {response.status}"})
                    
        except Exception as e:
            self.reasoning_log.append({"phase": "gitlab_error", "thought": f"GitLab taramasında hata: {e}"})

# MCP Tool instance
recon_passive_subfinder = SubdomainFinderModule()