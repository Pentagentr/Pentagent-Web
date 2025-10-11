"""
vuln_http_header_analyzer.py (MCP Refactored)
Görevi: HTTP güvenlik başlıklarını ve SSL/TLS yapılandırmasını derinlemesine analiz etmek.
Bu araç, Pentagent projesinin standartlarına uygun olarak yeniden düzenlenmiştir.
"""

import requests
import ssl
import socket
import re
import json
import time
from urllib.parse import urlparse
from typing import Dict, List, Optional, Any
from datetime import datetime
import warnings
import logging

# PentagentTool base class'ını import et
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

# InsecureRequestWarning'ü bastırıyoruz, çünkü bu araç kendi SSL/TLS analizini yapıyor.
warnings.filterwarnings('ignore', category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

# Standart bir logger yapısı kuralım
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class VulnHttpHeaderAnalyzer(MCPTool):
    """
    HTTP güvenlik başlıklarını ve SSL/TLS yapılandırmasını derinlemesine analiz eder.
    MCP ajan mimarisi için standartlaştırılmış girdi ve çıktı formatlarına sahiptir.
    """

    def __init__(self):
        super().__init__(
            name="vuln_http_header_analyzer",
            description="HTTP güvenlik başlıklarını ve SSL/TLS yapılandırmasını derinlemesine analiz eder.",
            category=ToolCategory.VULNERABILITY_SCANNING
        )

        # Analiz edilecek başlıklar ve yapılandırmaları (Bu yapı çok iyi, koruyoruz)
        self.security_headers_config = {
            'Strict-Transport-Security': {'risk_if_missing': 'high', 'check': self._analyze_hsts},
            'Content-Security-Policy': {'risk_if_missing': 'high', 'check': self._analyze_csp},
            'X-Frame-Options': {'risk_if_missing': 'medium', 'check': self._analyze_xframe},
            'X-Content-Type-Options': {'risk_if_missing': 'medium', 'check': self._analyze_xcontent},
            'Referrer-Policy': {'risk_if_missing': 'low', 'check': self._analyze_referrer},
            'Permissions-Policy': {'risk_if_missing': 'low', 'check': self._analyze_permissions}
        }
        self.information_headers = ['Server', 'X-Powered-By', 'X-AspNet-Version']

    def _log_thought(self, phase: str, thought: str):
        """AI'ın düşünce sürecini standart bir formatta loglar."""
        self._add_reasoning(self.ai_reasoning_log, phase, thought)
        logger.info(f"[{self.name} - {phase}] {thought}")

    # =====================================================================================
    # MCP STANDART GİRİŞ NOKTASI (ENTRY POINT)
    # =====================================================================================
    def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP Ajanı tarafından çağrılacak ana fonksiyon.
        Standart MCP JSON formatında çıktı üretir.
        """
        self.ai_reasoning_log = []
        try:
            target_url = params.get("url")
            if not target_url or not isinstance(target_url, str):
                return self._create_final_output(
                    success=False,
                    ai_summary="Gerekli 'url' parametresi eksik veya geçersiz.",
                    error="Gerekli 'url' parametresi eksik veya geçersiz."
                )
            
            self._log_thought("initialization", f"HTTP güvenlik analizi '{target_url}' hedefi için başlatılıyor.")

            analysis_result = self._analyze(target_url)

            if "error" in analysis_result:
                 return self._create_final_output(
                     success=False,
                     ai_summary=f"Analiz başarısız oldu: {analysis_result['error']}",
                     ai_reasoning=self.ai_reasoning_log,
                     error=analysis_result["error"]
                 )

            mcp_output = self._format_mcp_output(analysis_result, target_url)
            self._log_thought("analysis_complete", "Analiz tamamlandı. MCP için standart çıktı oluşturuldu.")
            return mcp_output

        except requests.exceptions.RequestException as e:
            error_msg = f"Hedefe ulaşılamadı: {e}"
            return self._create_final_output(
                success=False,
                ai_summary=f"Analiz başarısız oldu: {error_msg}",
                ai_reasoning=self.ai_reasoning_log,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Beklenmedik bir hata oluştu: {e}"
            logger.error(error_msg, exc_info=True)
            return self._create_final_output(
                success=False,
                ai_summary=f"Analiz başarısız oldu: {error_msg}",
                ai_reasoning=self.ai_reasoning_log,
                error=error_msg
            )
    
    def _format_mcp_output_error(self, error_msg: str) -> Dict[str, Any]:
        """Hata durumunda standart MCP çıktısı oluşturur."""
        self._log_thought("error", error_msg)
        return {
            "success": False, "data": {},
            "ai_summary": f"Analiz başarısız oldu: {error_msg}",
            "ai_reasoning": self.ai_reasoning_log, "recommendations": [],
            "error": error_msg
        }

    def _format_mcp_output(self, analysis_result: Dict, target_url: str) -> Dict[str, Any]:
        """Dahili analiz sonucunu standart MCP JSON formatına dönüştürür."""
        overall_score = analysis_result.get('overall_score', 0)  # DÜZELTME: score → overall_score
        posture = analysis_result.get('risk_summary', {}).get('security_posture', 'bilinmiyor')
        
        summary = f"Güvenlik analizi tamamlandı. Puan: {overall_score}/100. Genel güvenlik duruşu: '{posture.upper()}'."
        if posture in ['poor', 'moderate']:
            critical_risks = len(analysis_result['risk_summary']['critical_risks'])
            high_risks = len(analysis_result['risk_summary']['high_risks'])
            summary = f"⚠️ Düşük Güvenlik Puanı: {overall_score}/100. Güvenlik duruşu: '{posture.upper()}'. {critical_risks} kritik, {high_risks} yüksek riskli bulgu tespit edildi."

        # RAG-friendly format ekle
        analysis_result["rag_analysis_data"] = {
            "security_headers_for_analysis": [
                {
                    "header_name": header_name,
                    "present": analysis.get('present', False),
                    "value": analysis.get('value', ''),
                    "risk_level": analysis.get('risk_level', 'unknown'),
                    "rag_query_suggestion": f"Security header analysis for {header_name} - {analysis.get('risk_level', 'unknown')} risk"
                }
                for header_name, analysis in analysis_result.get('security_headers', {}).items()
            ],
            "server_info_for_cve_lookup": [
                {
                    "server_banner": info['value'],
                    "header_type": info['header'],
                    "cve_reference": self._get_server_cve_reference(info['value']),
                    "rag_query_suggestion": f"CVE analysis for {info['value']}"
                }
                for info in analysis_result.get('information_disclosure', [])
                if info['header'].lower() == 'server'
            ],
            "scan_metadata": {
                "target_url": target_url,
                "scan_timestamp": time.time(),
                "scan_type": "http_header_analysis",
                "overall_security_score": overall_score,
                "critical_risks_count": len(analysis_result.get('risk_summary', {}).get('critical_risks', [])),
                "high_risks_count": len(analysis_result.get('risk_summary', {}).get('high_risks', []))
            }
        }

        return self._create_final_output(
            success=True,
            data=analysis_result,
            ai_summary=summary,
            ai_reasoning=self.ai_reasoning_log,
            recommendations=self._generate_mcp_recommendations(analysis_result, target_url)
        )

    def _generate_mcp_recommendations(self, analysis_result: Dict, target_url: str) -> List[Dict]:
        """Dinamik uzman önerileri oluşturur."""
        recommendations = []
        headers_analysis = analysis_result.get('security_headers', {})
        risk_summary = analysis_result.get('risk_summary', {})
        overall_score = analysis_result.get('overall_score', 0)
        
        # Dinamik güvenlik başlığı analizi ve öneriler
        header_recommendations = self._generate_header_expert_recommendations(headers_analysis, target_url, overall_score)
        recommendations.extend(header_recommendations)
        
        # SSL/TLS analizi önerileri
        ssl_recommendations = self._generate_ssl_expert_recommendations(analysis_result, target_url)
        recommendations.extend(ssl_recommendations)
        
        # Bilgi ifşası önerileri
        info_recommendations = self._generate_info_disclosure_recommendations(analysis_result, target_url)
        recommendations.extend(info_recommendations)
        
        return recommendations

    def _generate_header_expert_recommendations(self, headers_analysis: Dict, target_url: str, overall_score: int) -> List[Dict]:
        """Güvenlik başlıklarına özel dinamik uzman önerileri oluşturur."""
        recommendations = []
        
        # Kritik eksik başlıklar için özel öneriler
        if not headers_analysis.get('X-Frame-Options', {}).get('present'):
            recommendations.append({
                "priority": "critical",
                "tool": "poc_clickjacking_tester",
                "reason": f"🚨 CLICKJACKING RİSKİ: X-Frame-Options başlığı eksik. Clickjacking saldırıları ve iframe injection testleri yapılmalı.",
                "params": {"url": target_url, "clickjacking_test": True, "iframe_injection": True},
                "expert_context": f"Clickjacking riski için kritik test. {target_url} için iframe injection ve clickjacking teknikleri test edilmeli."
            })
        
        csp = headers_analysis.get('Content-Security-Policy', {})
        if not csp.get('present') or csp.get('strength') == 'weak':
            recommendations.append({
                "priority": "critical",
                "tool": "verify_xss",
                "reason": f"🚨 CSP ZAFİYETİ: Content Security Policy eksik veya zayıf. XSS zafiyetleri ve script injection testleri yapılmalı.",
                "params": {"url": target_url, "csp_bypass": True, "xss_payloads": ["advanced"]},
                "expert_context": f"CSP zafiyeti için kritik XSS testi. {target_url} için CSP bypass teknikleri ve advanced XSS payload'ları test edilmeli."
            })
        
        if not headers_analysis.get('Strict-Transport-Security', {}).get('present'):
            recommendations.append({
                "priority": "critical",
                "tool": "ssl_security_scanner",
                "reason": f"🚨 HSTS EKSİK: Strict-Transport-Security başlığı eksik. SSL/TLS downgrade saldırıları ve man-in-the-middle testleri yapılmalı.",
                "params": {"url": target_url, "hsts_test": True, "ssl_downgrade": True},
                "expert_context": f"HSTS eksikliği için kritik SSL güvenlik testi. {target_url} için SSL downgrade ve MITM saldırıları test edilmeli."
            })
        
        if not headers_analysis.get('X-Content-Type-Options', {}).get('present'):
            recommendations.append({
                "priority": "high",
                "tool": "verify_lfi",
                "reason": f"⚠️ MIME SNIFFING RİSKİ: X-Content-Type-Options başlığı eksik. MIME sniffing ve file upload zafiyetleri test edilmeli.",
                "params": {"url": target_url, "mime_sniffing": True, "file_upload": True},
                "expert_context": f"MIME sniffing riski için kritik test. {target_url} için file upload zafiyetleri ve MIME sniffing teknikleri test edilmeli."
            })
        
        if not headers_analysis.get('Referrer-Policy', {}).get('present'):
            recommendations.append({
                "priority": "high",
                "tool": "enum_web_crawler",
                "reason": f"⚠️ REFERRER LEAKAGE: Referrer-Policy başlığı eksik. Sensitive bilgi sızıntısı ve referrer leakage testleri yapılmalı.",
                "params": {"url": target_url, "referrer_test": True, "sensitive_info": True},
                "expert_context": f"Referrer leakage riski için kritik test. {target_url} için sensitive bilgi sızıntısı ve referrer leakage teknikleri test edilmeli."
            })
        
        # Genel güvenlik skoru düşükse kapsamlı test
        if overall_score < 50:
            recommendations.append({
                "priority": "critical",
                "tool": "vuln_dependency_scanner",
                "reason": f"🚨 DÜŞÜK GÜVENLİK SKORU: Genel güvenlik skoru {overall_score}/100. Kapsamlı güvenlik analizi ve dependency zafiyetleri kontrol edilmeli.",
                "params": {"url": target_url, "comprehensive": True, "dependency_check": True},
                "expert_context": f"Düşük güvenlik skoru için kritik analiz. {target_url} için kapsamlı güvenlik analizi ve dependency zafiyetleri kontrol edilmeli."
            })
        
        return recommendations

    def _generate_ssl_expert_recommendations(self, analysis_result: Dict, target_url: str) -> List[Dict]:
        """SSL/TLS analizine özel dinamik uzman önerileri oluşturur."""
        recommendations = []
        
        ssl_issues = analysis_result.get('ssl_tls_analysis', {}).get('issues', [])
        if not ssl_issues:
            return recommendations
        
        # SSL/TLS zafiyetleri için özel testler
        if any(issue['type'] == 'weak_protocol' for issue in ssl_issues):
            from urllib.parse import urlparse
            hostname = urlparse(target_url).hostname
            recommendations.append({
                "priority": "high",
                "tool": "ssl_security_scanner",
                "reason": f"🔒 ZAYIF TLS PROTOKOLÜ: Zayıf TLS protokolleri (TLS 1.0/1.1) tespit edildi. Cipher suite analizi ve SSL downgrade testleri yapılmalı.",
                "params": {"host": hostname, "cipher_analysis": True, "ssl_downgrade": True},
                "expert_context": f"Zayıf TLS protokolü için kritik SSL analizi. {hostname} için cipher suite analizi ve SSL downgrade testleri yapılmalı."
            })
        
        return recommendations

    def _generate_info_disclosure_recommendations(self, analysis_result: Dict, target_url: str) -> List[Dict]:
        """Bilgi ifşasına özel dinamik uzman önerileri oluşturur."""
        recommendations = []
        
        info_disclosure = analysis_result.get('information_disclosure', [])
        if not info_disclosure:
            return recommendations
        
        # Server bilgisi ifşası için özel testler
        server_info = next((h['value'] for h in info_disclosure if h['header'].lower() == 'server'), None)
        if server_info:
            # Temel CVE referansı + RAG yönlendirmesi
            cve_info = self._get_server_cve_reference(server_info)
            
            recommendations.append({
                "priority": "high",
                "tool": "vuln_dependency_scanner",
                "reason": f"🔍 SERVER BİLGİSİ İFŞASI: Sunucu versiyon bilgisi sızdırılıyor ({server_info}). {cve_info['summary']} Detaylı CVE analizi için RAG sorgusu yapın.",
                "params": {
                    "service_banner": server_info, 
                    "cve_check": True, 
                    "version_analysis": True,
                    "rag_query": f"CVE analysis for {server_info}"
                },
                "expert_context": f"Server bilgisi ifşası için kritik CVE analizi. {server_info} için bilinen CVE'ler: {cve_info['cve_ids']}. Detaylı analiz için RAG sistemi kullanın."
            })
        
        return recommendations

    def _get_server_cve_reference(self, server_info: str) -> Dict[str, str]:
        """
        Server bilgisi için temel CVE referansları döndürür.
        Detaylı analiz RAG sistemi ile yapılacak.
        """
        server_lower = server_info.lower()
        
        # Temel server CVE referansları
        server_cve_references = {
            'apache': {
                'cve_ids': 'CVE-2021-41773, CVE-2021-44224',
                'summary': 'Apache web sunucusu için bilinen kritik CVE\'ler mevcut.',
                'risk_level': 'Critical'
            },
            'nginx': {
                'cve_ids': 'CVE-2021-23017, CVE-2022-41741',
                'summary': 'Nginx için yüksek riskli CVE\'ler tespit edildi.',
                'risk_level': 'High'
            },
            'iis': {
                'cve_ids': 'CVE-2017-7269, CVE-2021-31166',
                'summary': 'Microsoft IIS için kritik güvenlik zafiyetleri bulundu.',
                'risk_level': 'Critical'
            },
            'tomcat': {
                'cve_ids': 'CVE-2020-1938, CVE-2021-25329',
                'summary': 'Apache Tomcat için bilinen CVE\'ler mevcut.',
                'risk_level': 'High'
            }
        }
        
        # Server için CVE referansı bul
        for server_key, cve_info in server_cve_references.items():
            if server_key in server_lower:
                return cve_info
        
        # Varsayılan (bilinmeyen server)
        return {
            'cve_ids': 'CVE-UNKNOWN',
            'summary': 'Bu server versiyonu için CVE analizi RAG sistemi ile yapılmalı.',
            'risk_level': 'Unknown'
        }


    # =====================================================================================
    # MEVCUT ÇEKİRDEK MANTIK (ORİJİNAL KODDAN ALINMIŞ VE GELİŞTİRİLMİŞTİR)
    # =====================================================================================

    def _analyze(self, target_url: str) -> Dict[str, Any]:
        """Ana analiz fonksiyonu (Çekirdek mantık)."""
        results = {'security_headers': {}, 'information_disclosure': [], 'ssl_tls_analysis': {},
                   'cookie_security': {}, 'cors_configuration': {}}
        
        self._log_thought("request", f"Hedefe GET isteği gönderiliyor: {target_url}")
        response = requests.get(target_url, verify=False, timeout=10, headers={'User-Agent': 'Pentagent-Scanner/1.0'})
        headers = {k.lower(): v for k, v in response.headers.items()}

        self._log_thought("analysis", "Güvenlik başlıkları analiz ediliyor...")
        for name, config in self.security_headers_config.items():
            value = headers.get(name.lower())
            analysis = {'present': value is not None, 'value': value}
            if value:
                analysis.update(config['check'](value))
            else:
                analysis['risk_level'] = config['risk_if_missing']
                analysis['issue'] = f"{name} başlığı eksik."
                self._log_thought("finding", f"⚠️ Eksik başlık: {name} (Risk: {analysis['risk_level']})")
            results['security_headers'][name] = analysis

        for name in self.information_headers:
            if name.lower() in headers:
                value = headers[name.lower()]
                results['information_disclosure'].append({'header': name, 'value': value})
                self._log_thought("finding", f"Bilgi ifşası: {name}: {value}")
        
        if target_url.startswith('https://'):
            self._log_thought("analysis", "SSL/TLS yapılandırması analiz ediliyor...")
            results['ssl_tls_analysis'] = self._analyze_ssl_tls(target_url)

        self._log_thought("analysis", "Çerez (cookie) güvenliği analiz ediliyor...")
        results['cookie_security'] = self._analyze_cookies(response)
        
        self._log_thought("analysis", "CORS yapılandırması analiz ediliyor...")
        results['cors_configuration'] = self._analyze_cors(headers)

        results['risk_summary'] = self._generate_risk_summary(results)
        results['overall_score'] = self._calculate_score(results)
        
        return results

    # ... [ Orijinal kodunuzdaki tüm _analyze_... yardımcı fonksiyonları buraya gelecek ]
    # ... [ Bu fonksiyonlar zaten çok iyi yazılmış ve modüler, bu yüzden onları değiştirmeden aynen kopyalıyoruz. ]
    # ... [ Sadece header isimlerini küçük harfe çevirerek daha tutarlı hale getirdim. ]

    def _analyze_hsts(self, value: str) -> Dict:
        analysis = {'risk_level': 'none'}
        if 'max-age' not in value or int(re.search(r'max-age=(\d+)', value).group(1)) < 31536000:
            analysis['risk_level'] = 'medium'
            analysis['issue'] = 'HSTS max-age 1 yıldan az veya tanımsız.'
        if 'includeSubDomains' not in value:
            analysis['warning'] = 'includeSubDomains direktifi eksik.'
        return analysis

    def _analyze_csp(self, value: str) -> Dict:
        analysis = {'strength': 'strong', 'risk_level': 'none', 'issues': []}
        unsafe_keywords = ["'unsafe-inline'", "'unsafe-eval'", "http:", "*"]
        if any(k in value for k in unsafe_keywords):
            analysis['strength'] = 'weak'
            analysis['risk_level'] = 'high'
            analysis['issues'].append("CSP, 'unsafe-inline', 'unsafe-eval' veya wildcard gibi güvensiz direktifler içeriyor.")
        if 'default-src' not in value and 'script-src' not in value:
            analysis['strength'] = 'minimal'
            analysis['risk_level'] = 'medium'
            analysis['issues'].append("Kritik 'default-src' veya 'script-src' direktifleri eksik.")
        return analysis
    
    # ... DİĞER YARDIMCI FONKSİYONLAR BURADA YER ALACAKTIR (_analyze_xframe, _analyze_ssl_tls, vb.)
    # Örnek olarak:
    def _analyze_xframe(self, value: str) -> Dict:
        return {'risk_level': 'none'} if value.upper() in ['DENY', 'SAMEORIGIN'] else {'risk_level': 'medium', 'issue': 'Zayıf X-Frame-Options değeri.'}

    def _analyze_xcontent(self, value: str) -> Dict:
        return {'risk_level': 'none'} if value.lower() == 'nosniff' else {'risk_level': 'medium', 'issue': 'Geçersiz değer, "nosniff" olmalı.'}

    def _analyze_referrer(self, value: str) -> Dict:
        secure = ['no-referrer', 'same-origin', 'strict-origin']
        return {'risk_level': 'none'} if any(s in value for s in secure) else {'risk_level': 'low', 'issue': 'Daha güvenli bir Referrer-Policy kullanılabilir.'}

    def _analyze_permissions(self, value: str) -> Dict:
        return {'risk_level': 'none', 'note': 'Tarayıcı özelliklerine erişim kısıtlanmış.'}

    def _analyze_ssl_tls(self, url: str) -> Dict:
        analysis = {'issues': []}
        try:
            hostname = urlparse(url).hostname
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    protocol_version = ssock.version()
                    if protocol_version in ['TLSv1', 'TLSv1.1', 'SSLv3']:
                        analysis['issues'].append({
                            'type': 'weak_protocol', 'risk': 'medium',
                            'detail': f'Eski ve güvensiz protokol kullanılıyor: {protocol_version}'
                        })
                        self._log_thought("finding", f"Zayıf TLS protokolü tespit edildi: {protocol_version}")
        except Exception as e:
            analysis['issues'].append({'type': 'ssl_error', 'risk': 'unknown', 'detail': str(e)})
        return analysis

    def _analyze_cookies(self, response) -> Dict:
        analysis = {'issues': []}
        for cookie in response.cookies:
            if not cookie.secure:
                analysis['issues'].append({'type': 'cookie_not_secure', 'risk': 'medium', 'name': cookie.name})
            if not cookie.has_nonstandard_attr('HttpOnly'):
                analysis['issues'].append({'type': 'cookie_not_httponly', 'risk': 'medium', 'name': cookie.name})
        return analysis

    def _analyze_cors(self, headers: Dict) -> Dict:
        analysis = {'issues': []}
        # (KODUN BAŞLANGICI ÖNCEKİ MESAJDA VERİLDİ)

        origin = headers.get('access-control-allow-origin')
        if origin == '*':
            analysis['issues'].append({'type': 'cors_wildcard', 'risk': 'high', 'detail': 'Access-Control-Allow-Origin wildcard (*) kullanıyor.'})
            if headers.get('access-control-allow-credentials') == 'true':
                analysis['issues'].append({'type': 'cors_wildcard_with_credentials', 'risk': 'critical', 'detail': 'Wildcard origin ile kimlik bilgilerine izin verilmesi son derece tehlikelidir.'})
        return analysis

    def _calculate_score(self, results: Dict) -> int:
        """Genel güvenlik skoru hesaplar (0-100)."""
        score = 100
        penalties = {'critical': 25, 'high': 15, 'medium': 10, 'low': 5}
        
        # Risk özetindeki bulgulara göre puan düşür
        summary = self._generate_risk_summary(results) # Riskleri tek bir yerden alalım
        for risk_level, items in summary.items():
            if isinstance(items, list):
                score -= len(items) * penalties.get(risk_level.replace('_risks', ''), 0)

        return max(0, score)

    def _generate_risk_summary(self, results: Dict) -> Dict:
        """Tüm bulguları toplayarak bir risk özeti oluşturur."""
        summary = {'critical_risks': [], 'high_risks': [], 'medium_risks': [], 'low_risks': []}
        
        def add_risk(level, type, detail):
            summary[f"{level}_risks"].append({'type': type, 'detail': detail})

        # Güvenlik başlıkları
        for name, analysis in results.get('security_headers', {}).items():
            if analysis.get('risk_level') and analysis['risk_level'] != 'none':
                add_risk(analysis['risk_level'], f"header_{name.lower()}", analysis.get('issue', f"{name} başlığı zayıf yapılandırılmış."))
        
        # Bilgi ifşası
        for info in results.get('information_disclosure', []):
            add_risk('low', 'info_disclosure', f"{info['header']} başlığı bilgi sızdırıyor: {info['value']}")

        # SSL/TLS
        for issue in results.get('ssl_tls_analysis', {}).get('issues', []):
            add_risk(issue.get('risk', 'low'), 'ssl_tls_issue', issue.get('detail'))
            
        # Çerezler
        for issue in results.get('cookie_security', {}).get('issues', []):
            add_risk(issue.get('risk', 'medium'), 'cookie_issue', f"'{issue['name']}' çerezi güvensiz: {issue['type']}")

        # CORS
        for issue in results.get('cors_configuration', {}).get('issues', []):
             add_risk(issue.get('risk', 'high'), 'cors_issue', issue.get('detail'))

        # Genel Güvenlik Duruşu
        if summary['critical_risks'] or len(summary['high_risks']) > 2:
            summary['security_posture'] = 'poor'
        elif summary['high_risks'] or len(summary['medium_risks']) > 3:
            summary['security_posture'] = 'moderate'
        elif summary['medium_risks'] or summary['low_risks']:
            summary['security_posture'] = 'good'
        else:
            summary['security_posture'] = 'excellent'

        return summary


# =====================================================================================
# ÖRNEK KULLANIM VE TEST
# =====================================================================================
if __name__ == '__main__':
    # Bu blok, aracı doğrudan çalıştırarak test etmemizi sağlar.
    # MCP ajanı bu kısmı kullanmayacak, sadece `execute_tool` metodunu çağıracaktır.
    
    header_analyzer = VulnHttpHeaderAnalyzer()
    
    # --- Test Senaryosu 1: Güvenliği Zayıf Bir Site ---
    # `http` kullanıyoruz ki HSTS eksikliğini görebilelim.
    print("--- SENARYO 1: Güvenliği Zayıf Bir Site (http://httpbin.org) ---")
    test_params_1 = {"url": "http://httpbin.org/response-headers?Content-Type=text/html"}
    result_1 = header_analyzer.run_tool(test_params_1)
    print(json.dumps(result_1, indent=4, ensure_ascii=True))
    
    # --- Test Senaryosu 2: Güvenliği İyi Bir Site ---
    print("\n--- SENARYO 2: Güvenliği İyi Bir Site (https://github.com) ---")
    test_params_2 = {"url": "https://github.com"}
    result_2 = header_analyzer.run_tool(test_params_2)
    print(json.dumps(result_2, indent=4, ensure_ascii=True))

    # --- Test Senaryosu 3: Ulaşılamayan Site ---
    print("\n--- SENARYO 3: Ulaşılamayan Site ---")
    test_params_3 = {"url": "https://thissitedoesnotexist12345.com"}
    result_3 = header_analyzer.run_tool(test_params_3)
    print(json.dumps(result_3, indent=4, ensure_ascii=True))
    
    # --- Test Senaryosu 4: Geçersiz URL ---
    print("\n--- SENARYO 4: Geçersiz URL ---")
    test_params_4 = {"url": "bu-bir-url-degil"}
    result_4 = header_analyzer.run_tool(test_params_4)
    print(json.dumps(result_4, indent=4, ensure_ascii=True))
