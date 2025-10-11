#!/usr/bin/env python3
"""
Origin IP Finder Tool - Cloudflare arkasındaki gerçek IP'yi bulma
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

class OriginIPFinderModule(MCPTool):
    """Cloudflare arkasındaki gerçek IP'yi bulma modülü"""
    
    def __init__(self):
        super().__init__(
            name="recon_origin_ip_finder",
            description="Cloudflare arkasındaki gerçek IP adresini bulur. SPF kayıtları, DNS geçmişi, SSL sertifikaları ve diğer teknikler kullanır.",
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
            
            self._add_reasoning(self.reasoning_log, "initialization", f"Origin IP keşfi '{domain}' için başlatılıyor.")
            
            # Ana tarama mantığını çalıştır
            scan_result = await self._find_origin_ip(domain)
            
            self._add_reasoning(self.reasoning_log, "analysis_complete", "Origin IP keşfi tamamlandı.")
            
            return self._create_final_output(
                success=True,
                data=scan_result,
                ai_summary=self._generate_ai_summary(scan_result),
                recommendations=self._generate_mcp_recommendations(scan_result)
            )
            
        except Exception as e:
            logger.error(f"Origin IP finder'da hata: {e}", exc_info=True)
            self._add_reasoning(self.reasoning_log, "error", f"Araç çalıştırılırken kritik bir hata oluştu: {e}")
            return self._create_final_output(
                success=False,
                data={},
                ai_summary=f"Araç çalıştırılırken kritik bir hata oluştu: {e}",
                recommendations=[],
                error=str(e)
            )
    
    async def _find_origin_ip(self, domain: str) -> Dict[str, Any]:
        """Ana origin IP bulma fonksiyonu."""
        found_ips = set()
        techniques_used = []
        
        async with aiohttp.ClientSession() as session:
            # Farklı tekniklerle origin IP'yi bul
            await self._check_spf_records(session, domain, found_ips, techniques_used)
            await self._check_mx_records(session, domain, found_ips, techniques_used)
            await self._check_ssl_certificates(session, domain, found_ips, techniques_used)
            await self._check_dns_history(session, domain, found_ips, techniques_used)
            await self._check_subdomain_ip(session, domain, found_ips, techniques_used)
            await self._check_common_subdomains(session, domain, found_ips, techniques_used)
        
        # IP'leri analiz et ve temizle
        analyzed_ips = self._analyze_ips(found_ips, domain)
        
        return {
            "potential_origin_ips": analyzed_ips,
            "total_found": len(analyzed_ips),
            "techniques_used": techniques_used,
            "ai_reasoning": self.reasoning_log
        }

    async def _check_spf_records(self, session: aiohttp.ClientSession, domain: str, found_ips: Set[str], techniques: List[str]):
        """SPF kayıtlarından IP'leri çıkar"""
        self.reasoning_log.append({"phase": "technique", "thought": "SPF kayıtları kontrol ediliyor..."})
        try:
            import dns.resolver
            txt_records = dns.resolver.resolve(domain, 'TXT')
            for record in txt_records:
                txt_data = str(record).strip('"')
                if txt_data.startswith('v=spf1'):
                    # SPF kaydından IP'leri çıkar
                    ip_matches = re.findall(r'ip4:(\d+\.\d+\.\d+\.\d+)', txt_data)
                    for ip in ip_matches:
                        found_ips.add(ip)
                    if ip_matches:
                        techniques.append("SPF Records")
                        self.reasoning_log.append({"phase": "result", "thought": f"SPF kayıtlarından {len(ip_matches)} IP bulundu."})
        except Exception as e:
            self.reasoning_log.append({"phase": "error", "thought": f"SPF kayıt kontrolü hatası: {str(e)}"})

    async def _check_mx_records(self, session: aiohttp.ClientSession, domain: str, found_ips: Set[str], techniques: List[str]):
        """MX kayıtlarından IP'leri çıkar"""
        self.reasoning_log.append({"phase": "technique", "thought": "MX kayıtları kontrol ediliyor..."})
        try:
            import dns.resolver
            mx_records = dns.resolver.resolve(domain, 'MX')
            for record in mx_records:
                mx_host = str(record).split()[1].rstrip('.')
                # MX host'unun IP'sini al
                try:
                    a_records = dns.resolver.resolve(mx_host, 'A')
                    for a_record in a_records:
                        found_ips.add(str(a_record))
                    if a_records:
                        techniques.append("MX Records")
                        self.reasoning_log.append({"phase": "result", "thought": f"MX kayıtlarından IP bulundu: {mx_host}"})
                except:
                    pass
        except Exception as e:
            self.reasoning_log.append({"phase": "error", "thought": f"MX kayıt kontrolü hatası: {str(e)}"})

    async def _check_ssl_certificates(self, session: aiohttp.ClientSession, domain: str, found_ips: Set[str], techniques: List[str]):
        """SSL sertifikalarından IP'leri çıkar"""
        self.reasoning_log.append({"phase": "technique", "thought": "SSL sertifikaları kontrol ediliyor..."})
        try:
            # Censys benzeri SSL sertifika arama
            url = f"https://crt.sh/?q={domain}&output=json"
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    for cert in data:
                        if 'common_name' in cert and domain in cert['common_name']:
                            # Sertifika IP'sini al
                            if 'name_value' in cert:
                                names = cert['name_value'].split('\n')
                                for name in names:
                                    if re.match(r'^\d+\.\d+\.\d+\.\d+$', name.strip()):
                                        found_ips.add(name.strip())
                    if data:
                        techniques.append("SSL Certificates")
                        self.reasoning_log.append({"phase": "result", "thought": f"SSL sertifikalarından IP'ler bulundu."})
        except Exception as e:
            self.reasoning_log.append({"phase": "error", "thought": f"SSL sertifika kontrolü hatası: {str(e)}"})

    async def _check_dns_history(self, session: aiohttp.ClientSession, domain: str, found_ips: Set[str], techniques: List[str]):
        """DNS geçmişinden IP'leri çıkar"""
        self.reasoning_log.append({"phase": "technique", "thought": "DNS geçmişi kontrol ediliyor..."})
        try:
            # SecurityTrails benzeri DNS geçmişi
            url = f"https://securitytrails.com/domain/{domain}/dns"
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    html_content = await response.text()
                    # HTML'den IP'leri çıkar
                    ip_matches = re.findall(r'(\d+\.\d+\.\d+\.\d+)', html_content)
                    for ip in ip_matches:
                        if self._is_valid_ip(ip):
                            found_ips.add(ip)
                    if ip_matches:
                        techniques.append("DNS History")
                        self.reasoning_log.append({"phase": "result", "thought": f"DNS geçmişinden {len(ip_matches)} IP bulundu."})
        except Exception as e:
            self.reasoning_log.append({"phase": "error", "thought": f"DNS geçmişi kontrolü hatası: {str(e)}"})

    async def _check_subdomain_ip(self, session: aiohttp.ClientSession, domain: str, found_ips: Set[str], techniques: List[str]):
        """Subdomain'lerin IP'lerini kontrol et"""
        self.reasoning_log.append({"phase": "technique", "thought": "Subdomain IP'leri kontrol ediliyor..."})
        try:
            # Yaygın subdomain'leri kontrol et
            common_subdomains = ['www', 'mail', 'ftp', 'admin', 'api', 'dev', 'test', 'staging']
            for subdomain in common_subdomains:
                full_domain = f"{subdomain}.{domain}"
                try:
                    import dns.resolver
                    a_records = dns.resolver.resolve(full_domain, 'A')
                    for record in a_records:
                        ip = str(record)
                        # Cloudflare IP'leri değilse ekle
                        if not self._is_cloudflare_ip(ip):
                            found_ips.add(ip)
                    if a_records:
                        techniques.append("Subdomain IPs")
                        self.reasoning_log.append({"phase": "result", "thought": f"{full_domain} için non-Cloudflare IP bulundu."})
                except:
                    pass
        except Exception as e:
            self.reasoning_log.append({"phase": "error", "thought": f"Subdomain IP kontrolü hatası: {str(e)}"})

    async def _check_common_subdomains(self, session: aiohttp.ClientSession, domain: str, found_ips: Set[str], techniques: List[str]):
        """Yaygın subdomain'leri kontrol et"""
        self.reasoning_log.append({"phase": "technique", "thought": "Yaygın subdomain'ler kontrol ediliyor..."})
        try:
            # Daha fazla subdomain kontrol et
            extended_subdomains = ['cpanel', 'webmail', 'whm', 'direct', 'direct-connect', 'blog', 'forums', 'shop', 'store']
            for subdomain in extended_subdomains:
                full_domain = f"{subdomain}.{domain}"
                try:
                    import dns.resolver
                    a_records = dns.resolver.resolve(full_domain, 'A')
                    for record in a_records:
                        ip = str(record)
                        if not self._is_cloudflare_ip(ip):
                            found_ips.add(ip)
                except:
                    pass
        except Exception as e:
            self.reasoning_log.append({"phase": "error", "thought": f"Yaygın subdomain kontrolü hatası: {str(e)}"})

    def _is_cloudflare_ip(self, ip: str) -> bool:
        """IP'nin Cloudflare IP'si olup olmadığını kontrol et"""
        cloudflare_ranges = [
            "104.16.0.0/12", "104.24.0.0/14", "104.28.0.0/16", "104.29.0.0/16",
            "104.30.0.0/15", "104.31.0.0/16", "108.162.192.0/18", "141.101.64.0/18",
            "162.158.0.0/15", "172.64.0.0/13", "173.245.48.0/20", "188.114.96.0/20",
            "190.93.240.0/20", "197.234.240.0/22", "198.41.128.0/17"
        ]
        # Basit kontrol - gerçek implementasyonda IP range kontrolü yapılmalı
        return any(ip.startswith(range.split('/')[0].rsplit('.', 1)[0]) for range in cloudflare_ranges)

    def _is_valid_ip(self, ip: str) -> bool:
        """IP'nin geçerli olup olmadığını kontrol et"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False
            return True
        except:
            return False

    def _analyze_ips(self, ips: Set[str], domain: str) -> List[Dict[str, Any]]:
        """IP'leri analiz et ve risk seviyesi belirle"""
        analyzed_ips = []
        for ip in ips:
            if self._is_valid_ip(ip) and not self._is_cloudflare_ip(ip):
                risk_level = self._determine_risk_level(ip, domain)
                analyzed_ips.append({
                    "ip": ip,
                    "risk_level": risk_level,
                    "confidence": "medium",
                    "technique": "origin_ip_discovery"
                })
        return analyzed_ips

    def _determine_risk_level(self, ip: str, domain: str) -> str:
        """IP'nin risk seviyesini belirle"""
        # Basit risk analizi
        if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
            return "low"  # Private IP
        elif ip.startswith("127."):
            return "low"  # Localhost
        else:
            return "high"  # Public IP - potansiyel origin

    def _generate_ai_summary(self, scan_result: Dict[str, Any]) -> str:
        """İnsan tarafından okunabilir bir özet oluşturur."""
        ips = scan_result.get('potential_origin_ips', [])
        if not ips:
            return "Hiçbir origin IP tespit edilemedi. Hedef tamamen Cloudflare arkasında olabilir."
        
        high_risk_count = len([ip for ip in ips if ip.get('risk_level') == 'high'])
        techniques = scan_result.get('techniques_used', [])
        
        summary = f"{len(ips)} potansiyel origin IP tespit edildi. "
        summary += f"{high_risk_count} tanesi yüksek risk seviyesinde. "
        summary += f"Kullanılan teknikler: {', '.join(techniques)}."
        
        return summary

    def _generate_mcp_recommendations(self, scan_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """MCP formatında öneriler oluşturur."""
        recommendations = []
        
        ips = scan_result.get('potential_origin_ips', [])
        if ips:
            recommendations.append({
                "title": "Origin IP Port Taraması",
                "description": f"Tespit edilen {len(ips)} origin IP üzerinde port taraması yapın",
                "priority": "high"
            })
            
            recommendations.append({
                "title": "Direct IP Erişim Testi",
                "description": "Origin IP'ler üzerinden doğrudan web servisine erişim test edin",
                "priority": "high"
            })
            
            recommendations.append({
                "title": "Cloudflare Bypass",
                "description": "Origin IP'ler ile Cloudflare korumasını bypass etmeyi deneyin",
                "priority": "critical"
            })
        else:
            recommendations.append({
                "title": "Alternatif Teknikler",
                "description": "Subdomain enumeration ve DNS bruteforce tekniklerini deneyin",
                "priority": "medium"
            })
        
        return recommendations

# MCP Tool instance
recon_origin_ip_finder = OriginIPFinderModule()
