#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pentagent - Infrastructure Reconnaissance Scanner
Görev: Shodan ve Censys API'lerini kullanarak hedefin internete açık servislerini,
yönetim panellerini ve altyapı bileşenlerini pasif olarak keşfeder.
MCP ajanına, hedefin saldırı yüzeyini haritalandırmak için temel kanıtları sunar.
"""

import shodan
import requests
import json
import logging
import os
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import base64
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

# Logging yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)
# Shodan ve requests kütüphanelerinden gelen gürültülü logları bastır
logging.getLogger("shodan").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

@dataclass
class ExposedServiceFinding:
    """Tek bir açık servis için toplanan ham teknik kanıtları temsil eder."""
    ip: str
    port: int
    transport: str  # 'tcp' veya 'udp'
    service_name: str
    product: Optional[str] = None
    version: Optional[str] = None
    hostname: Optional[str] = None
    banner: Optional[str] = None
    # YENİ: Servis tipini kategorize etmek için. MCP'nin analizini kolaylaştırır.
    service_category: str = 'unknown' # örn: database, remote_access, web_panel
    source: str = 'shodan' # Verinin nereden geldiği (shodan/censys)

class InfraReconScanner(MCPTool):
    """
    Shodan/Censys kullanarak hedefin saldırı yüzeyini keşfeden, MCP ile entegre profesyonel araç.
    """

    def __init__(self):
        super().__init__(
            name="infra_exposed_panels_finder",
            description="Shodan/Censys kullanarak hedefin internete açık altyapısını ve servislerini pasif olarak keşfeder.",
            category=ToolCategory.RECONNAISSANCE
        )

        # REFAKTÖR EDİLDİ: Servis imzaları sadeleştirildi. Risk ve istismar notları kaldırıldı.
        # Bu bilgiler artık merkezi RAG/MCP sisteminde olacak.
        self.service_signatures = {
            # Yönetim Panelleri
            'cpanel': {'category': 'web_panel', 'patterns': ['cpanel', 'WHM']},
            'plesk': {'category': 'web_panel', 'patterns': ['plesk']},
            'webmin': {'category': 'web_panel', 'patterns': ['webmin']},
            'phpmyadmin': {'category': 'web_panel', 'patterns': ['phpmyadmin']},
            'jenkins': {'category': 'ci_cd', 'patterns': ['jenkins', 'x-jenkins']},
            # Veritabanları
            'mysql': {'category': 'database', 'patterns': ['mysql']},
            'mongodb': {'category': 'database', 'patterns': ['mongodb buildinfo', 'mongodb server information']},
            'elasticsearch': {'category': 'database', 'patterns': ['elasticsearch']},
            'redis': {'category': 'database', 'patterns': ['redis_version']},
            'postgresql': {'category': 'database', 'patterns': ['postgresql']},
            # Uzaktan Erişim
            'ssh': {'category': 'remote_access', 'patterns': ['openssh']},
            'rdp': {'category': 'remote_access', 'patterns': ['remote desktop']},
            'vnc': {'category': 'remote_access', 'patterns': ['rfb ']},
            'telnet': {'category': 'remote_access', 'patterns': ['telnet']},
        }

    def _get_shodan_api(self, api_keys: Dict) -> Optional[shodan.Shodan]:
        """Verilen API anahtarı ile Shodan API nesnesini başlatır."""
        shodan_key = api_keys.get("shodan")
        if not shodan_key:
            logger.warning("Shodan API anahtarı sağlanmadı. Shodan taraması atlanıyor.")
            return None
        try:
            return shodan.Shodan(shodan_key)
        except Exception as e:
            logger.error(f"Shodan API başlatılamadı: {e}")
            return None

    def _search_shodan(self, api: shodan.Shodan, query: str, ai_reasoning_log: List[Dict]) -> List[Dict]:
        """Shodan'da belirli bir sorgu için arama yapar."""
        try:
            ai_reasoning_log.append({"phase": "recon", "thought": f"Shodan'da sorgu çalıştırılıyor: '{query}'"})
            results = api.search(query, limit=100)
            return results.get('matches', [])
        except shodan.APIError as e:
            ai_reasoning_log.append({"phase": "error", "thought": f"Shodan API hatası: {e}"})
            logger.error(f"Shodan API hatası: {e}")
            return []

    def _process_shodan_result(self, result: Dict) -> ExposedServiceFinding:
        """Shodan'dan gelen tek bir sonucu standart bulgu formatımıza dönüştürür."""
        banner = result.get('data', '')
        # Servis kategorisini belirle
        category = 'unknown'
        service_name = result.get('product', 'unknown').lower()
        
        # İmza tabanlı kategori tespiti
        full_data_string = json.dumps(result).lower()
        for name, sig in self.service_signatures.items():
            for pattern in sig['patterns']:
                if pattern in full_data_string:
                    service_name = name
                    category = sig['category']
                    break
            if category != 'unknown':
                            break
                
        return ExposedServiceFinding(
            ip=result.get('ip_str'),
            port=result.get('port'),
            transport=result.get('transport', 'tcp'),
            service_name=service_name,
            product=result.get('product'),
            version=result.get('version'),
            hostname=result.get('hostnames')[0] if result.get('hostnames') else None,
            banner=banner.strip(),
            service_category=category,
            source='shodan'
        )

    def _get_censys_auth(self, api_keys: Dict) -> Optional[str]:
        """Censys API için authentication header oluşturur."""
        censys_token = api_keys.get("censys_token")
        if not censys_token:
            logger.warning("Censys API token'ı sağlanmadı. Censys taraması atlanıyor.")
            return None
        try:
            return f"Bearer {censys_token}"
        except Exception as e:
            logger.error(f"Censys authentication oluşturulamadı: {e}")
            return None

    def _search_censys(self, auth_header: str, query: str, ai_reasoning_log: List[Dict]) -> List[Dict]:
        """Censys'de belirli bir sorgu için arama yapar."""
        try:
            ai_reasoning_log.append({"phase": "recon", "thought": f"Censys'de sorgu çalıştırılıyor: '{query}'"})
            headers = {
                'Authorization': auth_header,
                'Content-Type': 'application/json'
            }
            data = {
                'q': query,
                'per_page': 100
            }
            response = requests.post('https://search.censys.io/api/v2/hosts/search', 
                                   headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result.get('result', {}).get('hits', [])
        except requests.exceptions.RequestException as e:
            ai_reasoning_log.append({"phase": "error", "thought": f"Censys API hatası: {e}"})
            logger.error(f"Censys API hatası: {e}")
            return []

    def _process_censys_result(self, result: Dict) -> ExposedServiceFinding:
        """Censys'den gelen tek bir sonucu standart bulgu formatımıza dönüştürür."""
        services = result.get('services', [])
        if not services:
            return None
        # İlk servisi al
        service = services[0]
        banner = service.get('banner', '')
        
        # Servis kategorisini belirle
        category = 'unknown'
        service_name = service.get('service_name', 'unknown').lower()
        
        # İmza tabanlı kategori tespiti
        full_data_string = json.dumps(result).lower()
        for name, sig in self.service_signatures.items():
            for pattern in sig['patterns']:
                if pattern in full_data_string:
                    service_name = name
                    category = sig['category']
                    break
            if category != 'unknown':
                break

        return ExposedServiceFinding(
            ip=result.get('ip'),
            port=service.get('port'),
            transport=service.get('transport_protocol', 'tcp'),
            service_name=service_name,
            product=service.get('software', [{}])[0].get('product') if service.get('software') else None,
            version=service.get('software', [{}])[0].get('version') if service.get('software') else None,
            hostname=result.get('dns', {}).get('reverse_dns', {}).get('names', [None])[0] if result.get('dns', {}).get('reverse_dns') else None,
            banner=banner.strip(),
            service_category=category,
            source='censys'
        )

    async def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aracın ana giriş noktası. Verilen hedefe göre altyapı keşfi yapar
        ve sonucu standart MCP JSON formatında döndürür.
        """
        target = params.get("target")
        api_keys = params.get("api_keys", {})

        if not target:
            return self._create_final_output(
                success=False,
                ai_summary="Hedef parametresi eksik.",
                error="Hedef 'target' parametresi eksik."
            )
        # API anahtarları olmadan da çalışabilir - HTTP-based discovery
        shodan_api = self._get_shodan_api(api_keys) if api_keys.get("shodan") else None
        censys_auth = self._get_censys_auth(api_keys) if api_keys.get("censys_token") else None
        
        # API anahtarları yoksa HTTP-based discovery yap
        if not shodan_api and not censys_auth:
            return await self._run_http_based_discovery(target)

        ai_reasoning_log = []
        self._add_reasoning(ai_reasoning_log, "initialization", f"infra_recon_scanner aracı '{target}' hedefi için başlatıldı.")
        
        shodan_api = self._get_shodan_api(api_keys)
        censys_auth = self._get_censys_auth(api_keys)
        
        if not shodan_api and not censys_auth:
            return self._create_final_output(
                success=False,
                ai_summary="Hiçbir API başlatılamadı.",
                ai_reasoning=ai_reasoning_log,
                error="Hiçbir API başlatılamadı."
            )
        
        findings: List[ExposedServiceFinding] = []
        
        try:
            # Farklı sorgu tipleriyle hedefin altyapısını haritalandır
            queries = [
                f'hostname:{target}',
                f'ssl:"{target}"',
                f'org:"{target}"' # Şirket adına göre arama (daha gürültülü olabilir ama kapsamlıdır)
            ]
            
            all_results = []
            
            # Shodan sorguları
            if shodan_api:
                all_shodan_results = []
                for q in queries:
                    all_shodan_results.extend(self._search_shodan(shodan_api, q, ai_reasoning_log))
                all_results.extend(all_shodan_results)
            
            # Censys sorguları
            if censys_auth:
                censys_queries = [
                    f'hosts.names: {target}',
                    f'services.tls.certificates.leaf_data.subject.common_name: {target}',
                    f'hosts.names: *{target}*'
                ]
                all_censys_results = []
                for q in censys_queries:
                    all_censys_results.extend(self._search_censys(censys_auth, q, ai_reasoning_log))
                all_results.extend(all_censys_results)
            
            # Tekilleştirme
            unique_results = {}
            for res in all_results:
                if 'ip_str' in res:  # Shodan result
                    key = f"{res['ip_str']}:{res['port']}"
                    unique_results[key] = res
                elif 'ip' in res:  # Censys result
                    services = res.get('services', [])
                    if services:
                        key = f"{res['ip']}:{services[0]['port']}"
                        unique_results[key] = res
            
            ai_reasoning_log.append({"phase": "analysis", "thought": f"Toplam {len(unique_results)} adet benzersiz servis bulundu."})

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for res in unique_results.values():
                    if 'ip_str' in res:  # Shodan result
                        futures.append(executor.submit(self._process_shodan_result, res))
                    elif 'ip' in res:  # Censys result
                        futures.append(executor.submit(self._process_censys_result, res))
                
            for future in as_completed(futures):
                result = future.result()
                if result:  # None olabilir
                    findings.append(result)

            # Dinamik öneriler oluştur
            recommendations = self._generate_dynamic_infra_recommendations(findings, target)
            
            # RAG-friendly format ekle
            rag_data = {
                "exposed_services": [
                    {
                        "ip": finding.ip,
                        "port": finding.port,
                        "service": finding.service,
                        "service_category": finding.service_category,
                        "banner": finding.banner,
                        "risk_level": finding.risk_level,
                        "rag_query_suggestion": f"Exposed service analysis for {finding.service} on {finding.ip}:{finding.port}"
                    }
                    for finding in findings
                ],
                "scan_metadata": {
                    "target": target,
                    "scan_timestamp": time.time(),
                    "scan_type": "infrastructure_reconnaissance",
                    "total_services_found": len(findings),
                    "high_risk_services": len([f for f in findings if f.risk_level == 'high']),
                    "critical_services": len([f for f in findings if f.risk_level == 'critical'])
                }
            }
            
            self._add_reasoning(ai_reasoning_log, "analysis_complete", f"Analiz tamamlandı. Bulgular MCP formatına dönüştürülüyor.")
            return self._create_final_output(
                success=True,
                data={
                    "target": target,
                    "findings": [asdict(f) for f in findings],
                    "rag_analysis_data": rag_data
                },
                ai_summary=self._generate_ai_summary(target, findings),
                ai_reasoning=ai_reasoning_log,
                recommendations=recommendations
            )

        except Exception as e:
            logger.critical(f"Altyapı keşif aracında kritik hata: {e}", exc_info=True)
            return self._create_final_output(
                success=False,
                ai_summary="Altyapı keşfi sırasında kritik bir hata oluştu.",
                ai_reasoning=ai_reasoning_log,
                error=f"Beklenmedik bir hata oluştu: {str(e)}"
            )

    def _generate_ai_summary(self, target: str, findings: List[ExposedServiceFinding]) -> str:
        """AI summary oluşturur."""
        if not findings:
            return f"'{target}' için yapılan pasif taramada internete açık herhangi bir servis bulunamadı."
        
        db_count = sum(1 for f in findings if f.service_category == 'database')
        panel_count = sum(1 for f in findings if f.service_category == 'web_panel')
        remote_count = sum(1 for f in findings if f.service_category == 'remote_access')
        summary_parts = [f"'{target}' hedefiyle ilişkili {len(findings)} adet açık servis tespit ettim."]
        if db_count > 0: summary_parts.append(f"Bunların {db_count} tanesi veritabanı.")
        if panel_count > 0: summary_parts.append(f"{panel_count} tanesi yönetim paneli.")
        if remote_count > 0: summary_parts.append(f"{remote_count} tanesi uzaktan erişim servisi.")
        return " ".join(summary_parts)

    def _generate_recommendations(self, findings: List[ExposedServiceFinding]) -> List[Dict]:
        """Öneriler oluşturur."""
        recommendations = []
        for f in findings:
            if f.service_category == 'database':
                recommendations.append(
                    self._create_recommendation(
                        priority=PriorityLevel.CRITICAL,
                        tool_name="database_conn_tester",
                        reason=f"'{f.ip}:{f.port}' adresinde bir '{f.service_name}' veritabanı tespit edildi. Anonim erişim ve zayıf parola denemeleri yapılmalı.",
                        params={"host": f.ip, "port": f.port, "type": f.service_name}
                    )
                )
            if f.service_category in ['web_panel', 'ci_cd']:
                 recommendations.append(
                    self._create_recommendation(
                        priority=PriorityLevel.HIGH,
                        tool_name="credential_bruteforcer",
                        reason=f"'{f.ip}:{f.port}' adresinde bir '{f.service_name}' yönetim paneli bulundu. Yaygın ve varsayılan parolalar denenmeli.",
                        params={"url": f"http://{f.ip}:{f.port}", "service": f.service_name}
                    )
                )
            if f.product:
                recommendations.append(
                    self._create_recommendation(
                        priority=PriorityLevel.MEDIUM,
                        tool_name="exploit_suggester",
                        reason=f"'{f.product} {f.version}' servisi tespit edildi. Bu yazılım için bilinen zafiyetler (CVE) araştırılmalı.",
                        params={"product": f.product, "version": f.version}
                    )
                )
        return recommendations

    def _generate_dynamic_infra_recommendations(self, findings: List[ExposedServiceFinding], target: str) -> List[Dict]:
        """Dinamik infrastructure reconnaissance önerileri oluşturur."""
        recommendations = []
        
        if not findings:
            return recommendations
        
        # Servis kategorilerini analiz et
        database_services = [f for f in findings if f.service_category == 'database']
        web_panels = [f for f in findings if f.service_category == 'web_panel']
        remote_access = [f for f in findings if f.service_category == 'remote_access']
        critical_services = [f for f in findings if f.risk_level == 'critical']
        high_risk_services = [f for f in findings if f.risk_level == 'high']
        
        # Kritik servisler için özel öneriler
        if critical_services:
            for service in critical_services[:2]:  # İlk 2 kritik servis
                recommendations.append({
                    "priority": "critical",
                    "tool": "human_intervention_alert",
                    "reason": f"🚨 KRİTİK: {service.service} servisi {service.ip}:{service.port} adresinde açık. Acil güvenlik kontrolü gerekli.",
                    "params": {
                        "ip": service.ip,
                        "port": service.port,
                        "service": service.service,
                        "service_category": service.service_category,
                        "risk_level": service.risk_level,
                        "urgent_review": True,
                        "rag_query": f"Critical service security analysis for {service.service} on {service.ip}:{service.port}"
                    },
                    "expert_context": f"Kritik servis için acil müdahale. {service.service} servisi {service.ip}:{service.port} adresinde açık ve kritik güvenlik riski oluşturuyor. Detaylı güvenlik analizi ve remediation planı gerekli."
                })
        
        # Veritabanı servisleri için özel öneriler
        if database_services:
            for service in database_services[:2]:  # İlk 2 veritabanı servisi
                recommendations.append({
                    "priority": "high",
                    "tool": "vuln_dependency_scanner",
                    "reason": f"⚠️ YÜKSEK RİSK: {service.service} veritabanı {service.ip}:{service.port} adresinde açık. Veritabanı güvenlik kontrolleri kontrol edilmeli.",
                    "params": {
                        "ip": service.ip,
                        "port": service.port,
                        "service": service.service,
                        "service_category": "database",
                        "database_security_scan": True,
                        "rag_query": f"Database security analysis for {service.service} on {service.ip}:{service.port}"
                    },
                    "expert_context": f"Veritabanı servisi için kritik analiz. {service.service} veritabanı {service.ip}:{service.port} adresinde açık ve veri güvenliği riski oluşturuyor. Veritabanı güvenlik kontrolleri ve access control mekanizmaları analiz edilmeli."
                })
        
        # Web panelleri için özel öneriler
        if web_panels:
            for service in web_panels[:2]:  # İlk 2 web paneli
                recommendations.append({
                    "priority": "high",
                    "tool": "vuln_dependency_scanner",
                    "reason": f"⚠️ YÜKSEK RİSK: {service.service} web paneli {service.ip}:{service.port} adresinde açık. Panel güvenlik kontrolleri kontrol edilmeli.",
                    "params": {
                        "ip": service.ip,
                        "port": service.port,
                        "service": service.service,
                        "service_category": "web_panel",
                        "panel_security_scan": True,
                        "rag_query": f"Web panel security analysis for {service.service} on {service.ip}:{service.port}"
                    },
                    "expert_context": f"Web paneli için kritik analiz. {service.service} web paneli {service.ip}:{service.port} adresinde açık ve yetkilendirme riski oluşturuyor. Panel güvenlik kontrolleri ve access control mekanizmaları analiz edilmeli."
                })
        
        # Remote access servisleri için özel öneriler
        if remote_access:
            for service in remote_access[:2]:  # İlk 2 remote access servisi
                recommendations.append({
                    "priority": "high",
                    "tool": "vuln_dependency_scanner",
                    "reason": f"⚠️ YÜKSEK RİSK: {service.service} remote access servisi {service.ip}:{service.port} adresinde açık. Remote access güvenlik kontrolleri kontrol edilmeli.",
                    "params": {
                        "ip": service.ip,
                        "port": service.port,
                        "service": service.service,
                        "service_category": "remote_access",
                        "remote_access_security_scan": True,
                        "rag_query": f"Remote access security analysis for {service.service} on {service.ip}:{service.port}"
                    },
                    "expert_context": f"Remote access servisi için kritik analiz. {service.service} remote access servisi {service.ip}:{service.port} adresinde açık ve yetkilendirme riski oluşturuyor. Remote access güvenlik kontrolleri ve access control mekanizmaları analiz edilmeli."
                })
        
        # Genel infrastructure güvenlik önerileri
        if findings:
            recommendations.append({
                "priority": "high",
                "tool": "vuln_dependency_scanner",
                "reason": f"🔍 ALTYAPI GÜVENLİK ANALİZİ: {len(findings)} açık servis bulundu. Infrastructure güvenlik kontrolleri gözden geçirilmeli.",
                "params": {
                    "target": target,
                    "total_services": len(findings),
                    "database_services": len(database_services),
                    "web_panels": len(web_panels),
                    "remote_access": len(remote_access),
                    "critical_services": len(critical_services),
                    "high_risk_services": len(high_risk_services),
                    "infrastructure_security_review": True
                },
                "expert_context": f"Altyapı güvenlik analizi için kapsamlı inceleme. {len(findings)} açık servis için detaylı güvenlik kontrolleri ve access control mekanizmaları analiz edilmeli."
            })
        
        return recommendations
    
    async def _run_http_based_discovery(self, target: str) -> Dict[str, Any]:
        """
        API anahtarları olmadan HTTP-based discovery yapar.
        Yaygın admin panel, management interface'leri tarar.
        """
        import aiohttp
        import asyncio
        
        ai_reasoning_log = []
        self._add_reasoning(ai_reasoning_log, "initialization", f"HTTP-based discovery '{target}' için başlatıldı (API anahtarı yok)")
        
        # Yaygın admin panel ve management interface'leri
        common_panels = [
            "/admin", "/admin/", "/administrator", "/admin.php", "/admin/login",
            "/wp-admin", "/phpmyadmin", "/pma", "/phpmyadmin/", "/phpmyadmin/index.php",
            "/cpanel", "/cpanel/", "/webmail", "/webmail/", "/mail/",
            "/manager", "/manager/", "/tomcat/manager", "/jenkins", "/jenkins/",
            "/grafana", "/grafana/", "/kibana", "/kibana/", "/elasticsearch",
            "/swagger", "/swagger-ui", "/swagger-ui/", "/api/docs", "/docs",
            "/redmine", "/redmine/", "/jira", "/jira/", "/confluence",
            "/sonar", "/sonar/", "/nexus", "/nexus/", "/artifactory",
            "/gitlab", "/gitlab/", "/gitea", "/gitea/", "/bitbucket",
            "/drupal/admin", "/drupal/admin/", "/joomla/administrator",
            "/magento/admin", "/prestashop/admin", "/opencart/admin"
        ]
        
        findings = []
        discovered_panels = []
        
        # HTTP ve HTTPS protokollerini dene
        protocols = ["http", "https"]
        
        for protocol in protocols:
            base_url = f"{protocol}://{target}"
            
            # Her panel için kontrol et
            for panel_path in common_panels:
                url = base_url + panel_path
                
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                        async with session.get(url, allow_redirects=True) as response:
                            if response.status == 200:
                                content = await response.text()
                                
                                # Panel türünü tespit et
                                panel_type = self._identify_panel_type(panel_path, content)
                                
                                finding = ExposedServiceFinding(
                                    service_name=panel_type,
                                    port=None,
                                    url=url,
                                    description=f"{panel_type} admin panel discovered",
                                    severity="medium",
                                    confidence="high",
                                    source='http_discovery'
                                )
                                findings.append(finding)
                                discovered_panels.append(url)
                                
                                self._add_reasoning(ai_reasoning_log, "panel_discovered", 
                                                  f"{panel_type} panel bulundu: {url}")
                
                except Exception as e:
                    # Timeout veya bağlantı hatası - sessizce devam et
                    continue
        
        # Sonuçları hazırla
        if discovered_panels:
            ai_summary = f"{len(discovered_panels)} admin panel ve management interface keşfedildi (HTTP-based discovery)"
            
            recommendations = [
                {
                    "tool": "verify_xss",
                    "reason": f"Keşfedilen panellere XSS testi uygula: {', '.join(discovered_panels[:3])}"
                },
                {
                    "tool": "verify_sqli", 
                    "reason": f"Admin panellerinde SQL injection testi yap"
                },
                {
                    "tool": "vuln_http_header_analyzer",
                    "reason": "Güvenlik header'larını kontrol et"
                }
            ]
            
            return self._create_final_output(
                success=True,
                data={
                    "discovered_panels": discovered_panels,
                    "panel_count": len(discovered_panels),
                    "discovery_method": "http_based",
                    "findings": [f.to_dict() for f in findings]
                },
                ai_summary=ai_summary,
                ai_reasoning=ai_reasoning_log,
                recommendations=recommendations
            )
        else:
            return self._create_final_output(
                success=True,
                data={
                    "discovered_panels": [],
                    "panel_count": 0,
                    "discovery_method": "http_based"
                },
                ai_summary="HTTP-based discovery tamamlandı, admin panel bulunamadı",
                ai_reasoning=ai_reasoning_log,
                recommendations=[
                    {
                        "tool": "enum_directory_bruteforce",
                        "reason": "Gizli admin panelleri için directory bruteforce yap"
                    }
                ]
            )
    
    def _identify_panel_type(self, path: str, content: str) -> str:
        """Panel türünü path ve content'e göre tespit et"""
        path_lower = path.lower()
        content_lower = content.lower()
        
        if "wp-admin" in path_lower or "wordpress" in content_lower:
            return "WordPress Admin"
        elif "phpmyadmin" in path_lower or "phpmyadmin" in content_lower:
            return "phpMyAdmin"
        elif "cpanel" in path_lower or "cpanel" in content_lower:
            return "cPanel"
        elif "jenkins" in path_lower or "jenkins" in content_lower:
            return "Jenkins"
        elif "grafana" in path_lower or "grafana" in content_lower:
            return "Grafana"
        elif "swagger" in path_lower or "swagger" in content_lower:
            return "Swagger UI"
        elif "gitlab" in path_lower or "gitlab" in content_lower:
            return "GitLab"
        elif "admin" in path_lower:
            return "Admin Panel"
        else:
            return "Management Interface"

# --- Test Amaçlı Çalıştırma Bloğu ---
if __name__ == "__main__":
    # Güvenlik notu: API anahtarınızı asla koda doğrudan yazmayın.
    # Ortam değişkenlerinden (environment variables) okumak en iyi pratiktir.
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import config
    
    SHODAN_API_KEY = config.SHODAN_API_KEY
    if not SHODAN_API_KEY:
        print("Lütfen 'SHODAN_API_KEY' ortam değişkenini ayarlayın.")
        exit(1)

    test_params = {
        # KENDİ TESTİN İÇİN 'target' DEĞERİNİ DEĞİŞTİR!
        "target": "renicames.com",
        "api_keys": {
            "shodan": SHODAN_API_KEY,
            "censys_token": config.CENSYS_API_TOKEN
        }
    }

    print(f"--- [TEST BAŞLANGICI] ---")
    print(f"Hedef: {test_params['target']}")
    print("-" * 25)

    scanner = InfraReconScanner()
    import asyncio
    result = asyncio.run(scanner.run_tool(test_params))

    print("\n--- [TEST SONUCU] ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("-" * 25)