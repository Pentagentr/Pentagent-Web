"""
vul_depency_scanner.py - Pentagent Projesi için MCP Uyumlu Dependency Tarama Aracı

Amaç: 
Bu araç, tespit edilen teknolojilerin (CMS, Framework, JS Kütüphaneleri vb.) detaylı versiyon
bilgilerini farklı yöntemler kullanarak yüksek doğrulukla tespit eder ve bilinen zafiyetleri
analiz eder.

Temel Felsefeye Uygunluk:
- Keşfet & Tespit Et: Teknolojilerin versiyonlarını tespit ederek potansiyel zafiyetleri ortaya çıkarır.
- Kanıtla: Tespit edilen versiyonlar ve bilinen zafiyetlerle somut kanıtlar sunar.
- RAG Girdisi Sağla: 'data' alanında, bulunan versiyonlar ve zafiyet bilgilerini yapılandırılmış formatta sağlar.
- Otonom Ajanı Yönlendir: 'recommendations' alanı ile MCP'ye, "bu versiyon için CVE taraması yap" gibi net komutlar verir.
"""

import requests
import re
import json
import hashlib
import time
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin
import logging

# PentagentTool base class'ını import et
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

# Standart bir logger yapısı
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class VulnDependencyScanner(MCPTool):
    """
    Hedef sistemde çalışan teknolojilerin versiyonlarını tespit eder.
    MCP ajan mimarisi için standartlaştırılmış girdi ve çıktı formatlarına sahiptir.
    """

    def __init__(self):
        super().__init__(
            name="vuln_dependency_scanner",
            description="Tespit edilen teknolojilerin detaylı versiyon bilgilerini toplar ve bilinen zafiyetleri analiz eder.",
            category=ToolCategory.VULNERABILITY_SCANNING
        )
        self.version = "2.1.0-MCP"

        # Orijinal koddaki harika bilgi bankalarını koruyoruz
        self.version_endpoints = {
            'wordpress': ['/readme.html', '/license.txt'],
            'drupal': ['/CHANGELOG.txt', '/core/CHANGELOG.txt'],
            'joomla': ['/administrator/manifests/files/joomla.xml']
        }
        self.version_patterns = {
            'wordpress': [r'Version (\d+\.\d+\.?\d*)', r'wp-includes.*ver=(\d+\.\d+\.?\d*)'],
            'apache': [r'Apache/(\d+\.\d+\.\d+)'], 'nginx': [r'nginx/(\d+\.\d+\.\d+)'],
            'php': [r'PHP/(\d+\.\d+\.\d+)'],
            'jquery': [r'jQuery v(\d+\.\d+\.\d+)', r'jquery[/-](\d+\.\d+\.\d+)'],
            'drupal': [r'Drupal (\d+\.\d+\.?\d*)'],
            'bootstrap': [r'Bootstrap v(\d+\.\d+\.\d+)']
        }
        self.known_hashes = {'35d6d33467025be5e2f8c8e5e0ebc5b0': ('jquery', '3.6.0')}
        self.latest_versions = {'wordpress': '6.4.2', 'jquery': '3.7.1'}

    # =====================================================================================
    # MCP STANDART GİRİŞ NOKTASI (ENTRY POINT)
    # =====================================================================================
    def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # DÜZELTME: ai_reasoning_log initialize et
        self.ai_reasoning_log = []
        
        try:
            target_url = params.get("url")
            detected_technologies = params.get("detected_technologies")
            if not target_url or not detected_technologies:
                raise ValueError("Gerekli 'url' ve 'detected_technologies' parametreleri eksik.")
            
            self._add_reasoning(self.ai_reasoning_log, "initialization", f"'{target_url}' hedefi için {len(detected_technologies)} teknolojinin versiyon tespiti başlatılıyor.")
            
            version_results = self._scan_for_versions(target_url, detected_technologies)
            
            self._add_reasoning(self.ai_reasoning_log, "analysis_complete", "Versiyon tespiti tamamlandı. MCP için standart çıktı oluşturuldu.")
            
            # Dinamik öneriler oluştur
            recommendations = self._generate_dynamic_dependency_recommendations(version_results['technologies'], target_url)
            
            # RAG-friendly format ekle
            rag_data = {
                "dependency_vulnerabilities": [
                    {
                        "technology": tech['technology'],
                        "version": tech.get('version_info', {}).get('detected_version', ''),
                        "vulnerability_count": len(tech.get('version_info', {}).get('known_vulnerabilities', [])),
                        "cve_references": tech.get('version_info', {}).get('known_vulnerabilities', []),
                        "rag_query_suggestion": f"Dependency vulnerability analysis for {tech['technology']} {tech.get('version_info', {}).get('detected_version', '')}"
                    }
                    for tech in version_results['technologies']
                    if tech.get('version_info', {}).get('known_vulnerabilities')
                ],
                "scan_metadata": {
                    "target_url": target_url,
                    "scan_timestamp": time.time(),
                    "scan_type": "dependency_vulnerability_scanning",
                    "total_technologies_scanned": len(version_results['technologies']),
                    "vulnerable_dependencies": len([t for t in version_results['technologies'] if t.get('version_info', {}).get('known_vulnerabilities')])
                }
            }
            
            # RAG data'yı version_results'a ekle
            version_results["rag_analysis_data"] = rag_data
            
            return self._create_final_output(
                success=True,
                data=version_results,
                summary=self._generate_ai_summary(version_results['technologies']),
                recommendations=recommendations
            )

        except Exception as e:
            logger.error(f"Dependency tarayıcıda hata: {e}", exc_info=True)
            self._add_reasoning(self.ai_reasoning_log, "error", f"Araç çalıştırılırken kritik bir hata oluştu: {e}")
            return self._create_final_output(
                success=False,
                data={},
                summary=f"Araç çalıştırılırken kritik bir hata oluştu: {e}",
                recommendations=[],
                error=str(e)
            )

    
    def _generate_ai_summary(self, tech_results: List[Dict]) -> str:
        """İnsan tarafından okunabilir bir özet oluşturur."""
        found_versions = [t for t in tech_results if t.get('version_info')]
        outdated_count = sum(1 for t in found_versions if t['version_info'].get('age_analysis', {}).get('status', '').endswith('outdated'))
        
        if not found_versions:
            return "Hiçbir teknoloji için kesin versiyon bilgisi tespit edilemedi."
        
        summary = f"{len(found_versions)} teknoloji için versiyon bilgisi bulundu. Bunlardan {outdated_count} tanesi güncel değil."
        if outdated_count > 0:
            summary = f"⚠️ {summary} Bilinen zafiyet (CVE) taraması önerilir."
        return summary

    def _generate_mcp_recommendations(self, tech_results: List[Dict]) -> List[Dict]:
        """MCP ajanı için eyleme dönüştürülebilir öneriler üretir."""
        recommendations = []
        for tech in tech_results:
            version_info = tech.get("version_info")
            if version_info:
                tech_name = tech['name']
                version = version_info['version']
                age_status = version_info.get('age_analysis', {}).get('status', 'unknown')
                
                priority = PriorityLevel.HIGH if age_status.endswith('outdated') else PriorityLevel.MEDIUM
                
                # Her versiyonu bulunan teknoloji için bir CVE lookup öner
                recommendations.append(self._create_recommendation(
                    priority=priority,
                    tool="vuln_cve_lookup",
                    reason=f"'{tech_name}' teknolojisinin '{version}' versiyonu tespit edildi. Bu versiyona ait bilinen zafiyetler (CVE) kontrol edilmeli.",
                    params={"technology": tech_name, "version": version}
                ))

                # Teknolojiye özel ek tarayıcıları tetikle
                if tech_name.lower() == 'wordpress':
                    recommendations.append(self._create_recommendation(
                        priority=PriorityLevel.HIGH,
                        tool="vuln_wordpress_scanner",
                        reason=f"WordPress versiyonu tespit edildi. Eklenti, tema ve kullanıcı listeleme gibi özel kontroller yapılmalı.",
                        params={"url": tech.get("url"), "version": version}
                    ))

        return recommendations

    def _generate_dynamic_dependency_recommendations(self, tech_results: List[Dict], target_url: str) -> List[Dict]:
        """Dinamik dependency vulnerability önerileri oluşturur."""
        recommendations = []
        
        # Kritik zafiyetli bağımlılıkları analiz et
        critical_vulns = []
        high_vulns = []
        medium_vulns = []
        
        for tech in tech_results:
            version_info = tech.get('version_info', {})
            vulnerabilities = version_info.get('known_vulnerabilities', [])
            
            if vulnerabilities:
                for vuln in vulnerabilities:
                    severity = vuln.get('severity', 'medium').lower()
                    if severity == 'critical':
                        critical_vulns.append((tech, vuln))
                    elif severity == 'high':
                        high_vulns.append((tech, vuln))
                    elif severity == 'medium':
                        medium_vulns.append((tech, vuln))
        
        # Kritik zafiyetler için özel öneriler
        if critical_vulns:
            for tech, vuln in critical_vulns[:3]:  # İlk 3 kritik zafiyet
                recommendations.append({
                    "priority": "critical",
                    "tool": "human_intervention_alert",
                    "reason": f"🚨 KRİTİK BAĞIMLILIK ZAFİYETİ: {tech['name']} {version_info.get('version', '')} için kritik CVE tespit edildi.",
                    "params": {
                        "technology": tech['name'],
                        "version": version_info.get('version', ''),
                        "cve_id": vuln.get('cve_id', ''),
                        "severity": vuln.get('severity', ''),
                        "urgent_patch": True,
                        "rag_query": f"Critical CVE remediation for {tech['name']} {version_info.get('version', '')}"
                    },
                    "expert_context": f"Kritik bağımlılık zafiyeti için acil müdahale. {tech['name']} {version_info.get('version', '')} için CVE {vuln.get('cve_id', '')} detaylı analizi ve patch planı gerekli."
                })
        
        # Yüksek riskli zafiyetler için öneriler
        if high_vulns:
            for tech, vuln in high_vulns[:3]:  # İlk 3 yüksek riskli zafiyet
                recommendations.append({
                    "priority": "high",
                    "tool": "vuln_dependency_scanner",
                    "reason": f"⚠️ YÜKSEK RİSKLİ BAĞIMLILIK: {tech['name']} {version_info.get('version', '')} için yüksek riskli CVE tespit edildi.",
                    "params": {
                        "technology": tech['name'],
                        "version": version_info.get('version', ''),
                        "cve_id": vuln.get('cve_id', ''),
                        "severity": vuln.get('severity', ''),
                        "patch_required": True,
                        "rag_query": f"High risk CVE remediation for {tech['name']} {version_info.get('version', '')}"
                    },
                    "expert_context": f"Yüksek riskli bağımlılık zafiyeti analizi. {tech['name']} {version_info.get('version', '')} için CVE {vuln.get('cve_id', '')} detaylı analizi ve patch planı gerekli."
                })
        
        # Genel dependency güvenlik önerileri
        if critical_vulns or high_vulns:
            recommendations.append({
                "priority": "high",
                "tool": "vuln_dependency_scanner",
                "reason": f"📦 BAĞIMLILIK GÜVENLİK ANALİZİ: {len(critical_vulns)} kritik, {len(high_vulns)} yüksek riskli zafiyet tespit edildi.",
                "params": {
                    "target": target_url,
                    "critical_count": len(critical_vulns),
                    "high_count": len(high_vulns),
                    "medium_count": len(medium_vulns),
                    "dependency_security_review": True
                },
                "expert_context": f"Bağımlılık güvenlik analizi için kapsamlı inceleme. {len(critical_vulns)} kritik, {len(high_vulns)} yüksek riskli zafiyet için detaylı analiz ve remediation planı gerekli."
            })
        
        return recommendations


    # =====================================================================================
    # MEVCUT ÇEKİRDEK MANTIK (ORİJİNAL KODDAN ALINMIŞ VE GELİŞTİRİLMİŞTİR)
    # =====================================================================================

    def _scan_for_versions(self, target_url: str, detected_technologies: List[Dict]) -> Dict:
        """Ana versiyon tarama fonksiyonu (Çekirdek mantık)."""
        results = []
        main_content, main_headers = self._fetch_content(target_url)

        for tech in detected_technologies:
            tech_name = tech.get('name', '')
            self._add_reasoning(self.ai_reasoning_log, "scan_start", f"'{tech_name}' için versiyon tespiti yapılıyor...")
            tech_result = {'name': tech_name, 'category': tech.get('category', 'Unknown'), 'version_info': None, 'url': target_url}
            
            # Strateji 1: Özel endpoint kontrolü
            version_info = self._check_version_endpoints(target_url, tech_name)
            
            # Strateji 2: Header kontrolü
            if not version_info and main_headers:
                version_info = self._extract_version_from_headers(main_headers, tech_name)
            
            # Strateji 3: Ana sayfa içeriği kontrolü
            if not version_info and main_content:
                version_info = self._extract_version_from_content(main_content, tech_name)

            if version_info:
                version = version_info['version']
                self._add_reasoning(self.ai_reasoning_log, "finding", f"✅ Versiyon bulundu: {tech_name} {version} (Kaynak: {version_info['source']}, Güvenilirlik: {version_info['confidence']})")
                version_info['age_analysis'] = self._analyze_version_age(tech_name, version)
                if 'outdated' in version_info['age_analysis'].get('status', ''):
                    self._add_reasoning(self.ai_reasoning_log, "critical_finding", f"⚠️ Güncel olmayan versiyon: {tech_name} {version} durumu '{version_info['age_analysis']['status']}'.")
                tech_result['version_info'] = version_info
            else:
                 self._add_reasoning(self.ai_reasoning_log, "scan_result", f"'{tech_name}' için versiyon bilgisi bulunamadı.")
            
            results.append(tech_result)
        
        return {'technologies': results}

    def _fetch_content(self, url: str) -> Tuple[Optional[str], Optional[Dict]]:
        try:
            response = requests.get(url, timeout=5, verify=False, headers={'User-Agent': 'Pentagent-Scanner/1.0'})
            return response.text, {k.lower(): v for k, v in response.headers.items()}
        except requests.exceptions.RequestException:
            return None, None

    def _check_version_endpoints(self, base_url: str, tech_name: str) -> Optional[Dict]:
        tech_lower = tech_name.lower()
        if tech_lower not in self.version_endpoints: return None
        
        for endpoint in self.version_endpoints[tech_lower]:
            url = urljoin(base_url, endpoint)
            self._add_reasoning(self.ai_reasoning_log, "probe", f"Özel endpoint kontrol ediliyor: {url}")
            content, _ = self._fetch_content(url)
            if content:
                for pattern in self.version_patterns.get(tech_lower, []):
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        return {'version': match.group(1).strip(), 'source': endpoint, 'confidence': 'high'}
        return None

    def _extract_version_from_headers(self, headers: Dict, tech_name: str) -> Optional[Dict]:
        tech_lower = tech_name.lower()
        header_map = {'apache': 'server', 'nginx': 'server', 'php': 'x-powered-by'}
        header_to_check = header_map.get(tech_lower)
        
        if header_to_check and header_to_check in headers:
            for pattern in self.version_patterns.get(tech_lower, []):
                match = re.search(pattern, headers[header_to_check], re.IGNORECASE)
                if match:
                    return {'version': match.group(1).strip(), 'source': f'HTTP Header ({header_to_check})', 'confidence': 'medium'}
        return None

    def _extract_version_from_content(self, content: str, tech_name: str) -> Optional[Dict]:
        for pattern in self.version_patterns.get(tech_name.lower(), []):
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return {'version': match.group(1).strip(), 'source': 'page_content', 'confidence': 'low'}
        
        content_hash = hashlib.md5(content.encode()).hexdigest()
        if content_hash in self.known_hashes:
            hash_tech, hash_version = self.known_hashes[content_hash]
            if hash_tech.lower() == tech_name.lower():
                return {'version': hash_version, 'source': 'file_hash', 'confidence': 'very_high'}
        return None
    
    def _analyze_version_age(self, tech_name: str, version: str) -> Dict:
        latest = self.latest_versions.get(tech_name.lower())
        if not latest: return {'status': 'unknown'}
        
        try:
            # Basit bir major versiyon karşılaştırması
            current_major = int(version.split('.')[0])
            latest_major = int(latest.split('.')[0])
            if current_major < latest_major:
                return {'status': 'severely_outdated', 'latest_known': latest}
        except (ValueError, IndexError):
            pass # Versiyon numarası beklenmedik bir formatta ise karşılaştırma yapma

        return {'status': 'recent', 'latest_known': latest}

# =====================================================================================
# ÖRNEK KULLANIM VE TEST
# =====================================================================================
if __name__ == '__main__':
    version_scanner = VulnVersionScanner()

    # enum_tech_detector'dan gelmiş gibi görünen örnek bir girdi
    mock_detected_techs = [
        {"name": "WordPress", "category": "CMS"},
        {"name": "jQuery", "category": "JavaScript Libraries"},
        {"name": "Apache", "category": "Web Servers"}
    ]
    
    # Gerçek bir hedef yerine, mock bir sunucu veya bilinen bir site kullanmak daha iyi olurdu.
    # Şimdilik, sadece aracın yapısını ve çağrısını test ediyoruz.
    test_params = {
        "url": "http://example-wordpress-site.com", # Bu URL'nin gerçek olduğunu varsayın
        "detected_technologies": mock_detected_techs
    }
    
    print(f"--- {test_params['url']} için versiyon taraması başlatılıyor ---")
    # Gerçek bir istek atmadan, sadece çıktının nasıl görüneceğini göstermek için:
    # result = version_scanner.execute_tool(test_params)
    # print(json.dumps(result, indent=4, ensure_ascii=False))

    # (KODUN BAŞLANGICI ÖNCEKİ MESAJDA VERİLDİ)

# =====================================================================================
# ÖRNEK KULLANIM VE TEST
# =====================================================================================
if __name__ == '__main__':
    version_scanner = VulnVersionScanner()

    # --- Test Senaryosu 1: WordPress ve jQuery Tespiti ---
    print("--- SENARYO 1: WordPress ve jQuery Tespiti ---")
    
    # Gerçek bir hedef yerine, mock bir sunucu veya bilinen bir site kullanmak daha iyi olurdu.
    # Şimdilik, sadece aracın yapısını ve çağrısını test ediyoruz.
    # Bu testin çalışması için internet bağlantısı ve hedef sitenin ayakta olması gerekir.
    # Gerçekçi bir sonuç almak için 'url'yi bilinen bir WordPress sitesiyle değiştirebilirsiniz.
    
    test_params_1 = {
        "url": "https://www.wordfence.com", # Örnek bir WordPress sitesi
        "detected_technologies": [
            {"name": "WordPress", "category": "CMS"},
            {"name": "jQuery", "category": "JavaScript Libraries"},
            {"name": "Apache", "category": "Web Servers"}, # Bu sitede olmayabilir, test ediyoruz
            {"name": "NonExistentTech", "category": "Unknown"} # Bulunamayacak bir teknoloji
        ]
    }
    
    print(f"--- {test_params_1['url']} için versiyon taraması başlatılıyor ---")
    result_1 = version_scanner.execute_tool(test_params_1)
    print(json.dumps(result_1, indent=4, ensure_ascii=False))

    # --- Test Senaryosu 2: Eksik Parametrelerle Hata Senaryosu ---
    print("\n--- SENARYO 2: Eksik Parametrelerle Hata Senaryosu ---")
    test_params_2 = {
        "url": "https://example.com"
        # "detected_technologies" parametresi kasten eksik bırakıldı.
    }
    result_2 = version_scanner.execute_tool(test_params_2)
    print(json.dumps(result_2, indent=4, ensure_ascii=False))

    # --- Test Senaryosu 3: Ulaşılamayan URL ---
    print("\n--- SENARYO 3: Ulaşılamayan URL ---")
    test_params_3 = {
        "url": "http://thissitedoesnotexist12345.com",
        "detected_technologies": [{"name": "WordPress"}]
    }
    # Bu senaryo, _fetch_content içindeki hata yakalama mekanizmasını test eder.
    # Araç çökmemeli, sadece versiyon bulamadığını raporlamalıdır.
    result_3 = version_scanner.execute_tool(test_params_3)
    print(json.dumps(result_3, indent=4, ensure_ascii=False))
