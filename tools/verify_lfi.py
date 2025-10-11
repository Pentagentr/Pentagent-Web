#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pentagent - Local File Inclusion (LFI) Verifier
Görev: Sunucu yanıtlarındaki anormallikleri analiz ederek, zararsız bir şekilde
LFI zafiyetinin var olma potansiyelini kanıtlar.
Bu araç, "Sömürü Yok, Kanıt Var" prensibine sıkı sıkıya bağlıdır ve ASLA dosya okumaz.
"""

import requests
import json
import logging
import uuid
import time
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

# Logging yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class LfiFinding:
    """Tek bir LFI zafiyet kanıtını temsil eder."""
    vulnerable_parameter: str
    poc_payload: str
    proof_method: str  # 'response_anomaly'
    proof_details: Dict[str, Any]

@dataclass
class BaselineResponse:
    """Karşılaştırma için bir baseline yanıtını temsil eder."""
    status_code: int
    content_length: int

class LfiVerifier(MCPTool):
    """
    Zararsız davranış analizi ile LFI potansiyelini doğrulayan, MCP ile entegre profesyonel araç.
    """
    
    def __init__(self):
        super().__init__(
            name="verify_lfi",
            description="Zararsız davranış analizi ile LFI zafiyetinin potansiyelini doğrular.",
            category=ToolCategory.VULNERABILITY_SCANNING
        )
        
        # REFAKTÖR EDİLDİ: Sadece traversal desenleri kaldı, hassas dosya listeleri kaldırıldı.
        self.traversal_sequences = [
            "../", "..\\", "..%2f", "..%5c", "%2e%2e/", ".\\./"
        ]
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"Pentagent/{self.name}/1.0"
        })
        self.timeout = 30  # Timeout süresini artırdık

    def _make_request(self, url: str, method: str, parameter: str, value: str, timeout: int = None) -> Optional[requests.Response]:
        """Verilen payload ile hedefe bir HTTP isteği gönderir."""
        if timeout is None:
            timeout = self.timeout
        try:
            url_parts = list(urlparse(url))
            query_params = parse_qs(url_parts[4], keep_blank_values=True)
            query_params[parameter] = [value]
            
            if method.upper() == "GET":
                url_parts[4] = urlencode(query_params, doseq=True)
                final_url = urlunparse(url_parts)
                return self.session.get(final_url, timeout=timeout)
            else: # POST
                post_data = {k: v[0] for k, v in query_params.items()}
                return self.session.post(urlunparse(url_parts[:3] + ('', '', '')), data=post_data, timeout=timeout)

        except requests.exceptions.RequestException as e:
            logger.warning(f"İstek gönderilirken hata oluştu: {e}")
            return None

    def _establish_baseline(self, url: str, method: str, parameter: str, ai_reasoning_log: List[Dict]) -> Optional[BaselineResponse]:
        """Sunucunun "dosya bulunamadı" hatası için bir baseline oluşturur."""
        ai_reasoning_log.append({"phase": "preparation", "thought": "Normal 'dosya bulunamadı' davranışı için baseline oluşturuluyor."})
        # Benzersiz ve var olması imkansız bir dosya adı
        non_existent_file = f"{uuid.uuid4().hex}.tmp"
        
        response = self._make_request(url, method, parameter, non_existent_file)
        
        if response:
            baseline = BaselineResponse(
                status_code=response.status_code,
                content_length=len(response.text)
            )
            ai_reasoning_log.append({"phase": "preparation", "thought": f"Baseline oluşturuldu: Status={baseline.status_code}, Length={baseline.content_length}"})
            return baseline
        
        ai_reasoning_log.append({"phase": "error", "thought": "Baseline yanıtı alınamadı, test devam edemiyor."})
        return None

    async def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Aracın ana giriş noktası. LFI potansiyelini doğrular."""
        url = params.get("url")
        parameter = params.get("parameter")
        method = params.get("method", "GET")

        if not all([url, parameter]):
            return self._create_mcp_output(success=False, error="'url' ve 'parameter' parametreleri gereklidir.")
        
        ai_reasoning_log = [{"phase": "initialization", "thought": f"LFI Verifier aracı '{url}' hedefi ve '{parameter}' parametresi için başlatıldı."}]
        
        baseline = self._establish_baseline(url, method, parameter, ai_reasoning_log)
        if not baseline:
            return self._create_mcp_output(success=False, error="Hedefin baseline davranışı belirlenemedi.", ai_reasoning_log=ai_reasoning_log)
        
        findings: List[LfiFinding] = []
        try:
            # Farklı derinliklerde traversal dene
            for depth in range(1, 12):
                for traversal_char in self.traversal_sequences:
                    # Var olmayan dosyanın aynısını kullanarak payload oluştur
                    payload = (traversal_char * depth) + f"{uuid.uuid4().hex}.tmp"
                    
                    response = self._make_request(url, method, parameter, payload)
                    if not response:
                        continue

                    # ANOMALİ KONTROLÜ: Yanıt, baseline'dan farklı mı?
                    if response.status_code != baseline.status_code or len(response.text) != baseline.content_length:
                        ai_reasoning_log.append({"phase": "critical_finding", "thought": f"⚠️ LFI POTANSİYELİ DOĞRULANDI! Yanıt baseline'dan farklı. Payload: {payload}"})
                        finding = LfiFinding(
                            vulnerable_parameter=parameter,
                            poc_payload=payload,
                            proof_method='response_anomaly',
                            proof_details={
                                'baseline_status': baseline.status_code,
                                'traversal_status': response.status_code,
                                'baseline_length': baseline.content_length,
                                'traversal_length': len(response.text)
                            }
                        )
                        findings.append(finding)
                        # İlk kanıt yeterlidir, döngüyü sonlandır.
                        return self._create_mcp_output(target_url=url, findings=findings, ai_reasoning_log=ai_reasoning_log)

            ai_reasoning_log.append({"phase": "analysis_complete", "thought": "Tüm traversal testleri denendi, anormal bir yanıt bulunamadı."})
            return self._create_mcp_output(target_url=url, findings=findings, ai_reasoning_log=ai_reasoning_log)

        except Exception as e:
            logger.critical(f"LFI Verifier aracında kritik hata: {e}", exc_info=True)
            return self._create_mcp_output(success=False, error=f"Beklenmedik bir hata oluştu: {str(e)}", ai_reasoning_log=ai_reasoning_log)

    def _create_mcp_output(self,
                           target_url: str = None,
                           findings: List[LfiFinding] = None,
                           ai_reasoning_log: List[Dict] = None,
                           success: bool = True,
                           error: str = None) -> Dict[str, Any]:
        """Toplanan kanıtları standart MCP JSON formatına dönüştürür."""
        if findings is None: findings = []
        if ai_reasoning_log is None: ai_reasoning_log = []

        if not success:
            ai_summary = "LFI doğrulama testi bir hata nedeniyle başarısız oldu."
        elif not findings:
            ai_summary = f"Hedefte yapılan testlerde LFI zafiyeti potansiyeli kanıtlanamadı."
        else:
            param = findings[0].vulnerable_parameter
            ai_summary = f"YÜKSEK RİSK! Hedefte '{param}' parametresinde, sunucu yanıtlarındaki anormalliklere dayanarak LFI zafiyeti potansiyeli kanıtlandı."
            
        # Dinamik öneriler oluştur
        recommendations = self._generate_dynamic_lfi_recommendations(findings, target_url)
        
        # RAG-friendly format ekle
        rag_data = {
            "lfi_findings": [
                {
                    "vulnerable_parameter": finding.vulnerable_parameter,
                    "poc_payload": finding.poc_payload,
                    "proof_method": finding.proof_method,
                    "proof_details": finding.proof_details,
                    "rag_query_suggestion": f"LFI remediation for parameter {finding.vulnerable_parameter}"
                }
                for finding in findings
            ],
            "scan_metadata": {
                "target_url": target_url,
                "scan_timestamp": time.time(),
                "scan_type": "lfi_verification",
                "total_findings": len(findings),
                "high_risk_vulnerabilities": len(findings)
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

    def _generate_dynamic_lfi_recommendations(self, findings: List[LfiFinding], target_url: str) -> List[Dict]:
        """Dinamik LFI önerileri oluşturur."""
        recommendations = []
        
        if not findings:
            return recommendations
        
        # LFI türlerini analiz et
        traversal_findings = [f for f in findings if f.proof_method == "response_anomaly"]
        
        # Path traversal için özel öneriler
        if traversal_findings:
            for finding in traversal_findings[:2]:  # İlk 2 traversal finding
                recommendations.append({
                    "priority": "high",
                    "tool": "vuln_dependency_scanner",
                    "reason": f"📁 PATH TRAVERSAL: {finding.vulnerable_parameter} parametresinde path traversal tespit edildi. Dosya sistemine erişim riski var.",
                    "params": {
                        "vulnerability": "LFI - Path Traversal",
                        "parameter": finding.vulnerable_parameter,
                        "payload": finding.poc_payload,
                        "file_access": True,
                        "rag_query": f"Path traversal remediation for {finding.vulnerable_parameter}"
                    },
                    "expert_context": f"Path traversal için kritik analiz. {finding.vulnerable_parameter} parametresi için dosya sistemine erişim teknikleri ve remediation analiz edilmeli."
                })
        
        # Genel LFI önerileri
        if findings:
            recommendations.append({
                "priority": "high",
                "tool": "human_intervention_alert",
                "reason": f"📁 LFI ZAFİYETİ TESPİT EDİLDİ: {len(findings)} LFI zafiyeti tespit edildi. Dosya sistem güvenliği analizi gerekiyor.",
                "params": {
                    "target": target_url,
                    "vulnerability_count": len(findings),
                    "lfi_types": list(set(f.proof_method for f in findings)),
                    "file_system_review": True
                },
                "expert_context": f"LFI zafiyeti için dosya sistem güvenliği analizi. {len(findings)} LFI zafiyeti için detaylı analiz ve remediation planı gerekli."
            })
        
        return recommendations

# --- Test Amaçlı Çalıştırma Bloğu ---
if __name__ == "__main__":
    # Test için DVWA (Damn Vulnerable Web Application) gibi bir ortam varsayılmıştır.
    # Bu URL'in yerel ağınızda çalışan bir DVWA örneği olması gerekir.
    # ÖNEMLİ: Bu testi çalıştırmadan önce DVWA'yı kurup giriş yapmanız ve
    # URL'i kendi IP adresinize göre düzenlemeniz gerekir.
    test_params = {
        # Test için erişilebilir bir hedef kullanıyoruz
        "url": "https://httpbin.org/get?file=test.txt",
        "parameter": "file",
        "method": "GET"
    }

    print(f"--- [TEST BAŞLANGICI] ---")
    print(f"Hedef URL: {test_params['url']}")
    print(f"Parametre: {test_params['parameter']}")
    print("-" * 25)

    verifier = LfiVerifier()
    # DVWA testi için session cookie'si gerekebilir.
    # verifier.session.cookies.set("security", "low", domain="127.0.0.1")
    # verifier.session.cookies.set("PHPSESSID", "YOUR_SESSION_ID_HERE", domain="127.0.0.1")
    
    result = verifier.execute(test_params)

    print("\n--- [TEST SONUCU] ---")
    print(json.dumps(result, indent=2, ensure_ascii=True))
    print("-" * 25)