#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pentagent - Cross-Site Scripting (XSS) Verifier (Selenium Edition)
Görev: Zararsız, benzersiz bir metnin (marker) hedef sayfaya yansıtılıp
yansıtılmadığını kontrol ederek XSS zafiyetinin varlığını kanıtlar.
Bu sürüm, geniş Python uyumluluğu için Selenium kullanır.
"""

import json
import logging
import uuid
import time
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

# SELENIUM ENTEGRASYONU
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

# Logging yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class XssFinding:
    """Tek bir XSS zafiyet kanıtını temsil eder."""
    injection_context: str
    vulnerable_parameter: str
    poc_payload: str
    proof: Dict[str, Any]

class XssVerifier(MCPTool):
    """
    Selenium kullanarak XSS zafiyetini doğrulayan, MCP ile entegre profesyonel araç.
    """
    
    def __init__(self):
        super().__init__(
            name="verify_xss",
            description="Zararsız yansıtma tekniği ile XSS zafiyetini doğrular.",
            category=ToolCategory.VULNERABILITY_SCANNING
        )
        self.unique_marker = f"pentagentproof{uuid.uuid4().hex[:12]}"

    def _generate_payloads(self) -> List[Dict[str, str]]:
        """Farklı XSS bağlamları için zararsız kanıt payload'ları oluşturur."""
        return [
            {"context": "html_tag", "payload": f'<pentagent_proof_tag id="{self.unique_marker}"></pentagent_proof_tag>'},
            {"context": "html_tag_breaker", "payload": f'"><div data-proof="{self.unique_marker}"></div>'},
            {"context": "html_attribute", "payload": f'" autofocus data-pentagent="{self.unique_marker}'},
            {"context": "html_attribute_breaker", "payload": f'\' autofocus data-pentagent=\'{self.unique_marker}\''},
            {"context": "script_context_breaker", "payload": f'</script><div id="{self.unique_marker}"></div><script>'},
            {"context": "script_string_breaker", "payload": f"';document.body.setAttribute('data-proof','{self.unique_marker}');//"},
        ]

    def _get_driver(self) -> Optional[webdriver.Chrome]:
        """Otomatik olarak indirilen sürücü ile bir Chrome WebDriver nesnesi oluşturur."""
        try:
            options = ChromeOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--log-level=3") # Sadece ciddi hataları göster
            options.add_argument(f"user-agent=Pentagent/{self.name}/1.0 (Selenium)")
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(15)
            return driver
        except Exception as e:
            logger.error(f"Chrome WebDriver başlatılamadı. Hata: {e}")
            logger.error("Lütfen sisteminizde Google Chrome'un kurulu olduğundan emin olun.")
            return None

    def _test_payload(self, driver: webdriver.Chrome, url: str, method: str, parameter: str, payload_info: Dict[str, str], ai_reasoning_log: List[Dict]) -> Optional[XssFinding]:
        """Tek bir payload'u hedefe gönderir ve marker'ın yansıtılıp yansıtılmadığını kontrol eder."""
        payload = payload_info["payload"]
        ai_reasoning_log.append({"phase": "verification_attempt", "thought": f"'{payload_info['context']}' bağlamı için payload test ediliyor: {payload[:50]}..."})
        
        try:
            url_parts = list(urlparse(url))
            query = parse_qs(url_parts[4], keep_blank_values=True)
            query[parameter] = [payload]
            url_with_payload = urlunparse(url_parts[:4] + [urlencode(query, doseq=True)] + url_parts[5:])

            if method.upper() == "GET":
                driver.get(url_with_payload)
            else: # POST
                driver.get(url)
                # Formu bul, doldur ve gönder
                input_element = driver.find_element(By.NAME, parameter)
                input_element.send_keys(payload)
                input_element.submit()
            
            time.sleep(1) # Sayfanın oturması için kısa bir bekleme

            # SAYFANIN İŞLENMİŞ DOM'UNDA KANIT ARA
            selector = f'//*[(@id="{self.unique_marker}") or (@data-proof="{self.unique_marker}") or (@data-pentagent="{self.unique_marker}")]'
            proof_element = driver.find_elements(By.XPATH, selector)

            if proof_element:
                ai_reasoning_log.append({"phase": "critical_finding", "thought": f"⚠️ XSS KANITLANDI! Marker, DOM içinde bir element olarak bulundu. Bağlam: {payload_info['context']}"})
                return XssFinding(
                    injection_context=payload_info["context"],
                    vulnerable_parameter=parameter,
                    poc_payload=payload,
                    proof={
                        "reflected_in_dom": True,
                        "marker_string": self.unique_marker,
                        "proof_method": "Selenium XPath query"
                    }
                )
        except TimeoutException:
            logger.warning(f"Sayfa yüklenirken zaman aşımı: {url_with_payload[:80]}")
        except WebDriverException as e:
            logger.debug(f"Selenium payload testi sırasında hata: {e.msg}")
        except Exception as e:
            logger.debug(f"Payload testi sırasında genel hata: {e}")
            
        return None

    async def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Aracın ana giriş noktası. XSS doğrulama testi yapar."""
        url = params.get("url")
        parameter = params.get("parameter")
        method = params.get("method", "GET")

        if not all([url, parameter]):
            return self._create_mcp_output(success=False, error="'url' ve 'parameter' parametreleri gereklidir.")
        
        ai_reasoning_log = [{"phase": "initialization", "thought": f"XSS Verifier (Selenium) aracı '{url}' hedefi ve '{parameter}' parametresi için başlatıldı."}]
        
        driver = self._get_driver()
        if not driver:
            error_msg = "Selenium WebDriver başlatılamadığı için testler çalıştırılamadı."
            ai_reasoning_log.append({"phase": "error", "thought": error_msg})
            return self._create_mcp_output(success=False, error=error_msg, ai_reasoning_log=ai_reasoning_log)

        findings: List[XssFinding] = []
        try:
            payloads = self._generate_payloads()
            for payload_info in payloads:
                result = self._test_payload(driver, url, method, parameter, payload_info, ai_reasoning_log)
                if result:
                    findings.append(result)
                    ai_reasoning_log.append({"phase": "confirmation", "thought": "Zafiyet kanıtlandığı için testler durduruldu."})
                    break
            
            ai_reasoning_log.append({"phase": "analysis_complete", "thought": "Tüm XSS doğrulama testleri tamamlandı."})
            return self._create_mcp_output(target_url=url, findings=findings, ai_reasoning_log=ai_reasoning_log)
        finally:
            if driver:
                driver.quit()

    def _create_mcp_output(self,
                           target_url: str = None,
                           findings: List[XssFinding] = None,
                           ai_reasoning_log: List[Dict] = None,
                           success: bool = True,
                           error: str = None) -> Dict[str, Any]:
        """Toplanan kanıtları standart MCP JSON formatına dönüştürür."""
        if findings is None: findings = []
        if ai_reasoning_log is None: ai_reasoning_log = []

        if not success:
            ai_summary = "XSS doğrulama testi bir hata nedeniyle başarısız oldu."
        elif not findings:
            ai_summary = f"Hedefte yapılan testlerde yansıtmalı XSS zafiyeti kanıtlanamadı."
        else:
            context = findings[0].injection_context
            param = findings[0].vulnerable_parameter
            ai_summary = f"YÜKSEK RİSK! Hedefte '{param}' parametresinde, '{context}' bağlamında bir XSS zafiyeti kanıtlandı."
            
        # Dinamik öneriler oluştur
        recommendations = self._generate_dynamic_xss_recommendations(findings, target_url)
        
        # RAG-friendly format ekle
        rag_data = {
            "xss_findings": [
                {
                    "injection_context": finding.injection_context,
                    "vulnerable_parameter": finding.vulnerable_parameter,
                    "payload": finding.payload,
                    "evidence": finding.evidence,
                    "confidence": finding.confidence,
                    "rag_query_suggestion": f"XSS remediation for {finding.injection_context} on parameter {finding.vulnerable_parameter}"
                }
                for finding in findings
            ],
            "scan_metadata": {
                "target_url": target_url,
                "scan_timestamp": time.time(),
                "scan_type": "xss_verification",
                "total_findings": len(findings),
                "high_risk_vulnerabilities": len([f for f in findings if f.confidence == "high"])
            }
        }

        data = {
            "target_url": target_url, 
            "vulnerability_proofs": [asdict(f) for f in findings],
            "rag_analysis_data": rag_data
        } if success else {}

        return {
            "success": success,
            "data": data,
            "ai_summary": ai_summary,
            "ai_reasoning": ai_reasoning_log,
            "recommendations": recommendations,
            "error": error
        }

    def _generate_dynamic_xss_recommendations(self, findings: List[XssFinding], target_url: str) -> List[Dict]:
        """Dinamik XSS önerileri oluşturur."""
        recommendations = []
        
        if not findings:
            return recommendations
        
        # XSS context'lerini analiz et
        reflected_xss = [f for f in findings if f.injection_context == "Reflected"]
        stored_xss = [f for f in findings if f.injection_context == "Stored"]
        dom_xss = [f for f in findings if f.injection_context == "DOM"]
        
        # Reflected XSS için özel öneriler
        if reflected_xss:
            for finding in reflected_xss[:2]:  # İlk 2 reflected XSS finding
                recommendations.append({
                    "priority": "high",
                    "tool": "vuln_dependency_scanner",
                    "reason": f"🎭 REFLECTED XSS: {finding.vulnerable_parameter} parametresinde reflected XSS tespit edildi. Session hijacking riski var.",
                    "params": {
                        "vulnerability": "XSS - Reflected",
                        "parameter": finding.vulnerable_parameter,
                        "payload": finding.payload,
                        "session_hijacking": True,
                        "rag_query": f"Reflected XSS remediation for {finding.vulnerable_parameter}"
                    },
                    "expert_context": f"Reflected XSS için kritik analiz. {finding.vulnerable_parameter} parametresi için session hijacking teknikleri ve remediation analiz edilmeli."
                })
        
        # Stored XSS için özel öneriler
        if stored_xss:
            for finding in stored_xss[:2]:  # İlk 2 stored XSS finding
                recommendations.append({
                    "priority": "critical",
                    "tool": "vuln_dependency_scanner",
                    "reason": f"🎭 STORED XSS: {finding.vulnerable_parameter} parametresinde stored XSS tespit edildi. Persistent attack riski var.",
                    "params": {
                        "vulnerability": "XSS - Stored",
                        "parameter": finding.vulnerable_parameter,
                        "payload": finding.payload,
                        "persistent_attack": True,
                        "rag_query": f"Stored XSS remediation for {finding.vulnerable_parameter}"
                    },
                    "expert_context": f"Stored XSS için kritik analiz. {finding.vulnerable_parameter} parametresi için persistent attack teknikleri ve remediation analiz edilmeli."
                })
        
        # DOM XSS için özel öneriler
        if dom_xss:
            for finding in dom_xss[:2]:  # İlk 2 DOM XSS finding
                recommendations.append({
                    "priority": "high",
                    "tool": "vuln_dependency_scanner",
                    "reason": f"🎭 DOM XSS: {finding.vulnerable_parameter} parametresinde DOM XSS tespit edildi. Client-side manipulation riski var.",
                    "params": {
                        "vulnerability": "XSS - DOM",
                        "parameter": finding.vulnerable_parameter,
                        "payload": finding.payload,
                        "client_side": True,
                        "rag_query": f"DOM XSS remediation for {finding.vulnerable_parameter}"
                    },
                    "expert_context": f"DOM XSS için kritik analiz. {finding.vulnerable_parameter} parametresi için client-side manipulation teknikleri ve remediation analiz edilmeli."
                })
        
        # Genel XSS önerileri
        if findings:
            recommendations.append({
                "priority": "high",
                "tool": "human_intervention_alert",
                "reason": f"🎭 XSS ZAFİYETİ TESPİT EDİLDİ: {len(findings)} farklı XSS context'i tespit edildi. Güvenlik analizi gerekiyor.",
                "params": {
                    "target": target_url,
                    "vulnerability_count": len(findings),
                    "xss_contexts": list(set(f.injection_context for f in findings)),
                    "security_review": True
                },
                "expert_context": f"XSS zafiyeti için güvenlik analizi. {len(findings)} farklı XSS context'i için detaylı analiz ve remediation planı gerekli."
            })
        
        return recommendations

# --- Test Amaçlı Çalıştırma Bloğu ---
if __name__ == "__main__":
    import asyncio
    
    # Test için Google'ın XSS oyunu kullanılıyor.
    test_params = {
        "url": "https://xss-game.appspot.com/level1/frame",
        "parameter": "query",
        "method": "GET"
    }

    async def main():
        print(f"--- [TEST BAŞLANGICI] ---")
        print(f"Hedef URL: {test_params['url']}")
        print(f"Parametre: {test_params['parameter']}")
        print("-" * 25)

        verifier = XssVerifier()
        result = await verifier.run_tool(test_params)

        print("\n--- [TEST SONUCU] ---")
        print(json.dumps(result, indent=2, ensure_ascii=True))
        print("-" * 25)
    
    asyncio.run(main())