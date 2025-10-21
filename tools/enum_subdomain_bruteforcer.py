#!/usr/bin/env python3
"""
Subdomain Bruteforce Tool - Subdomain'leri bruteforce ile bulma
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

class SubdomainBruteforceModule(MCPTool):
    """Subdomain bruteforce modülü"""
    
    def __init__(self):
        super().__init__(
            name="enum_subdomain_bruteforcer",
            description="Subdomain'leri bruteforce teknikleri ile bulur. Yaygın kelimeler, sayılar ve kombinasyonlar kullanır.",
            category=ToolCategory.RECONNAISSANCE
        )
        self.version = "1.0.0-MCP"
        self.reasoning_log = []
    
    async def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """MCP ajanı tarafından çağrılacak ana fonksiyon - OPTIMIZE EDİLMİŞ."""
        try:
            # Hem 'domain' hem de 'target' parametresini kabul et
            domain = params.get("domain") or params.get("target")
            if not domain:
                raise ValueError("Gerekli 'domain' veya 'target' parametresi eksik.")
            
            # URL'den domain çıkar
            if domain.startswith("http"):
                from urllib.parse import urlparse
                domain = urlparse(domain).netloc
            
            scan_type = params.get("scan_type", "fast")  # Default'u "fast" yap
            timeout = params.get("timeout", 3)  # 5'ten 3'e düşürüldü
            threads = params.get("threads", 3)  # 5'ten 3'e düşürüldü
            
            self._add_reasoning(self.reasoning_log, "initialization", f"Subdomain bruteforce '{domain}' için başlatılıyor (OPTIMIZE EDİLMİŞ).")
            
            # Ana tarama mantığını çalıştır
            scan_result = await self._bruteforce_subdomains(domain, scan_type, timeout, threads)
            
            self._add_reasoning(self.reasoning_log, "analysis_complete", "Subdomain bruteforce tamamlandı.")
            
            return self._create_final_output(
                success=True,
                data=scan_result,
                ai_summary=self._generate_ai_summary(scan_result),
                recommendations=self._generate_mcp_recommendations(scan_result)
            )
            
        except Exception as e:
            logger.error(f"Subdomain bruteforce'da hata: {e}", exc_info=True)
            self._add_reasoning(self.reasoning_log, "error", f"Araç çalıştırılırken kritik bir hata oluştu: {e}")
            return self._create_final_output(
                success=False,
                data={},
                ai_summary=f"Araç çalıştırılırken kritik bir hata oluştu: {e}",
                recommendations=[],
                error=str(e)
            )
    
    async def _bruteforce_subdomains(self, domain: str, scan_type: str, timeout: int, threads: int) -> Dict[str, Any]:
        """Ana subdomain bruteforce fonksiyonu - OPTIMIZE EDİLMİŞ"""
        found_subdomains = set()
        techniques_used = []
        
        # Wordlist oluştur
        wordlist = self._generate_wordlist(domain, scan_type)
        
        self._add_reasoning(self.reasoning_log, "wordlist_generation", f"{len(wordlist)} kelime ile wordlist oluşturuldu.")
        
        # Bruteforce işlemini başlat - BATCH PROCESSING ile
        # DNS çözümleme için optimize edilmiş connector
        connector = aiohttp.TCPConnector(
            limit=threads, 
            limit_per_host=threads,
            ttl_dns_cache=300,
            force_close=False,
            enable_cleanup_closed=True
        )
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout, connect=30, sock_connect=30),
            connector=connector
        ) as session:
            # Batch processing - küçük gruplar halinde işle
            batch_size = min(threads * 2, 10)  # Maksimum 10 subdomain per batch
            total_batches = (len(wordlist) + batch_size - 1) // batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(wordlist))
                batch_wordlist = wordlist[start_idx:end_idx]
                
                self._add_reasoning(
                    self.reasoning_log, 
                    "batch_progress", 
                    f"Batch {batch_num + 1}/{total_batches}: {len(batch_wordlist)} subdomain kontrol ediliyor..."
                )
                
                # Paralel bruteforce - sadece bu batch için
                semaphore = asyncio.Semaphore(threads)
                tasks = []
                
                for subdomain in batch_wordlist:
                    task = self._check_subdomain(session, subdomain, domain, semaphore, timeout)
                    tasks.append(task)
                
                # Bu batch'i çalıştır
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Sonuçları topla
                batch_found = 0
                for result in results:
                    if isinstance(result, dict) and result.get("found"):
                        found_subdomains.add(result["subdomain"])
                        techniques_used.append(result.get("method", "HTTP_BRUTEFORCE"))
                        batch_found += 1
                
                self._add_reasoning(
                    self.reasoning_log, 
                    "batch_complete", 
                    f"Batch {batch_num + 1} tamamlandı: {batch_found} subdomain bulundu"
                )
                
                # Kısa bir bekleme (rate limiting)
                await asyncio.sleep(0.1)
        
        # Subdomain'leri analiz et
        analyzed_subdomains = self._analyze_subdomains(found_subdomains, domain)
        
        return {
            "subdomains": analyzed_subdomains,
            "total_found": len(analyzed_subdomains),
            "wordlist_size": len(wordlist),
            "techniques_used": list(set(techniques_used)),
            "ai_reasoning": self.reasoning_log
        }

    def _generate_wordlist(self, domain: str, scan_type: str) -> List[str]:
        """Domain'e özel wordlist oluştur - OPTIMIZE EDİLMİŞ"""
        # Temel yaygın subdomain'ler (en kritik olanlar)
        base_words = [
            "www", "mail", "ftp", "admin", "api", "dev", "test", "staging", "prod",
            "blog", "shop", "store", "app", "mobile", "cdn", "static", "assets",
            "docs", "help", "support", "status", "monitor", "stats", "analytics",
            "backup", "db", "database", "mysql", "redis", "cache", "search",
            "jenkins", "ci", "git", "gitlab", "github", "docker", "k8s",
            "nginx", "apache", "tomcat", "php", "python", "node", "java",
            "wordpress", "drupal", "laravel", "django", "rails", "express",
            "aws", "azure", "gcp", "cloudflare", "stripe", "paypal",
            "google", "facebook", "twitter", "slack", "discord", "zoom",
            "salesforce", "hubspot", "zendesk", "sentry", "datadog", "newrelic"
        ]
        
        # Domain'e özel kelimeler ekle (sadece ana domain)
        domain_words = domain.split('.')[0]
        if len(domain_words) > 3:
            base_words.extend([
                domain_words,
                domain_words + "api",
                domain_words + "app",
                domain_words + "dev",
                domain_words + "test"
            ])
        
        # Sayılar ekle (sadece 0-20 arası)
        numbers = [str(i) for i in range(0, 21)]
        
        # Kombinasyonlar oluştur
        wordlist = set(base_words)
        
        if scan_type == "fast":
            # Hızlı tarama - sadece en kritik kelimeler
            wordlist.update(numbers[:10])  # Sadece 0-9
            # Maksimum 50 kelime
            return list(wordlist)[:50]
        elif scan_type == "comprehensive":
            # Daha kapsamlı ama hala sınırlı wordlist
            wordlist.update(numbers)
            # Sadece en önemli 20 kelime ile kombinasyon yap
            wordlist.update([f"{word}{num}" for word in base_words[:20] for num in numbers[:5]])
            wordlist.update([f"{num}{word}" for word in base_words[:20] for num in numbers[:5]])
            # Maksimum 200 kelime ile sınırla
            return list(wordlist)[:200]
        else:
            # Default: balanced scan
            wordlist.update(numbers[:20])  # 0-19
            # Maksimum 100 kelime
            return list(wordlist)[:100]

    async def _check_subdomain(self, session: aiohttp.ClientSession, subdomain: str, domain: str, semaphore: asyncio.Semaphore, timeout: int) -> Dict[str, Any]:
        """Tek bir subdomain'i kontrol et - HTTP-based OPTIMIZE EDİLMİŞ"""
        async with semaphore:
            full_domain = f"{subdomain}.{domain}"
            
            # HTTP/HTTPS kontrolü (daha hızlı)
            for protocol in ["https", "http"]:
                try:
                    url = f"{protocol}://{full_domain}"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                        if response.status < 500:  # 4xx ve 2xx/3xx kodları kabul et
                            return {
                                "found": True,
                                "subdomain": full_domain,
                                "url": url,
                                "status_code": response.status,
                                "method": f"HTTP_{protocol.upper()}"
                            }
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    continue
            
            # DNS kontrolü sadece HTTP başarısız olursa (fallback)
            try:
                import socket
                ip = socket.gethostbyname(full_domain)
                if ip:
                    return {
                        "found": True,
                        "subdomain": full_domain,
                        "ip": ip,
                        "method": "DNS_FALLBACK"
                    }
            except:
                pass
            
            return {"found": False, "subdomain": full_domain}

    def _analyze_subdomains(self, subdomains: Set[str], domain: str) -> List[Dict[str, Any]]:
        """Subdomain'leri analiz et ve risk seviyesi belirle"""
        analyzed_subdomains = []
        for subdomain in subdomains:
            risk_level = self._determine_risk_level(subdomain, domain)
            analyzed_subdomains.append({
                "subdomain": subdomain,
                "risk_level": risk_level,
                "confidence": "high",
                "method": "bruteforce"
            })
        return analyzed_subdomains

    def _determine_risk_level(self, subdomain: str, domain: str) -> str:
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
            return "Hiçbir subdomain bruteforce ile tespit edilemedi."
        
        high_risk_count = len([s for s in subdomains if s.get('risk_level') == 'high'])
        medium_risk_count = len([s for s in subdomains if s.get('risk_level') == 'medium'])
        wordlist_size = scan_result.get('wordlist_size', 0)
        
        summary = f"{len(subdomains)} subdomain bruteforce ile tespit edildi. "
        summary += f"{high_risk_count} tanesi yüksek risk, {medium_risk_count} tanesi orta risk seviyesinde. "
        summary += f"{wordlist_size} kelime ile tarama yapıldı."
        
        return summary

    def _generate_mcp_recommendations(self, scan_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """MCP formatında öneriler oluşturur."""
        recommendations = []
        
        subdomains = scan_result.get('subdomains', [])
        if subdomains:
            recommendations.append({
                "title": "Subdomain Port Taraması",
                "description": f"Tespit edilen {len(subdomains)} subdomain üzerinde port taraması yapın",
                "priority": "high"
            })
            
            high_risk = [s for s in subdomains if s.get('risk_level') == 'high']
            if high_risk:
                recommendations.append({
                    "title": "Yüksek Riskli Subdomain'ler",
                    "description": f"{len(high_risk)} yüksek riskli subdomain'i öncelikle test edin",
                    "priority": "critical"
                })
            
            recommendations.append({
                "title": "Web Uygulama Testi",
                "description": "Tespit edilen subdomain'lerde web uygulama güvenlik testleri yapın",
                "priority": "high"
            })
            
            recommendations.append({
                "title": "Teknoloji Tespiti",
                "description": "Her subdomain için teknoloji tespiti yapın",
                "priority": "medium"
            })
        else:
            recommendations.append({
                "title": "Alternatif Teknikler",
                "description": "Pasif subdomain enumeration tekniklerini deneyin",
                "priority": "medium"
            })
        
        return recommendations

# MCP Tool instance
enum_subdomain_bruteforcer = SubdomainBruteforceModule()
