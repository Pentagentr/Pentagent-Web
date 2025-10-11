#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pentagent - SQL Injection Verifier
Görev: Zararsız, kanıt odaklı payload'lar (zaman, boolean, hata tabanlı)
kullanarak SQL enjeksiyonu zafiyetinin varlığını doğrular.
Bu araç, "Sömürü Yok, Kanıt Var" prensibine sıkı sıkıya bağlıdır ve ASLA veri çekmez.
"""

import requests
import json
import logging
import time
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Dict, Any, List, Optional, Tuple
import re
from dataclasses import dataclass, asdict
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

# Logging yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SqliFinding:
    """Tek bir SQLi zafiyet kanıtını temsil eder."""
    injection_type: str  # 'time_based', 'boolean_based', 'error_based'
    vulnerable_parameter: str
    poc_payload: str
    proof: Dict[str, Any]
    dbms_identified: Optional[str] = None

class SqliVerifier(MCPTool):
    """
    Zararsız yöntemlerle SQL Injection zafiyetini doğrulayan, MCP ile entegre profesyonel araç.
    """
    
    def __init__(self):
        super().__init__(
            name="verify_sqli",
            description="Zararsız yöntemlerle SQL enjeksiyon zafiyetinin varlığını kanıtlar.",
            category=ToolCategory.VULNERABILITY_SCANNING
        )
        
        self.dbms_signatures = {
            "mysql": {"sleep": "SLEEP(5)", "comment": "-- -", "error": "SQL syntax.*MySQL"},
            "postgresql": {"sleep": "PG_SLEEP(5)", "comment": "--", "error": "PostgreSQL.*ERROR"},
            "mssql": {"sleep": "WAITFOR DELAY '00:00:05'", "comment": "--", "error": "Microsoft.*ODBC.*SQL"},
            "oracle": {"sleep": "DBMS_PIPE.RECEIVE_MESSAGE('a',5)", "comment": "--", "error": "ORA-[0-9]{5}"}
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"Pentagent/{self.name}/1.0"
        })

    def _make_request(self, url: str, method: str, parameter: str, value: str, timeout: int = 15) -> Optional[requests.Response]:
        """Verilen payload ile hedefe bir HTTP isteği gönderir."""
        try:
            url_parts = list(urlparse(url))
            query_params = parse_qs(url_parts[4], keep_blank_values=True)
            # Parametrenin değerini payload olarak ayarla
            query_params[parameter] = [value]
            
            if method.upper() == "GET":
                url_parts[4] = urlencode(query_params, doseq=True)
                final_url = urlunparse(url_parts)
                return self.session.get(final_url, timeout=timeout)
            else: # POST
                # POST verisi, query string'den veya body'den gelebilir. Şimdilik query string varsayıyoruz.
                post_data = {k: v[0] for k, v in query_params.items()}
                return self.session.post(url_parts[0], data=post_data, timeout=timeout)

        except requests.exceptions.RequestException as e:
            logger.warning(f"İstek gönderilirken hata oluştu: {e}")
            return None

    def _test_time_based(self, url: str, method: str, parameter: str, original_value: str, ai_reasoning_log: List[Dict]) -> Optional[SqliFinding]:
        """Zaman tabanlı SQLi zafiyetini test eder."""
        ai_reasoning_log.append({"phase": "verification", "thought": f"'{parameter}' parametresi için zaman tabanlı SQLi testi başlatıldı."})
        for dbms, sig in self.dbms_signatures.items():
            payload = f"{original_value}' AND {sig['sleep']} {sig['comment']}"
            start_time = time.time()
            self._make_request(url, method, parameter, payload, timeout=10)
            duration = time.time() - start_time

            if duration > 4.5 and duration < 10: # 5 saniyelik gecikme için
                ai_reasoning_log.append({"phase": "critical_finding", "thought": f"⚠️ Zaman tabanlı SQLi doğrulandı! Gecikme: {duration:.2f}s, DBMS: {dbms}"})
                return SqliFinding(
                    injection_type='time_based',
                    vulnerable_parameter=parameter,
                    poc_payload=payload,
                    proof={'observed_delay_seconds': round(duration, 2)},
                    dbms_identified=dbms
                )
        return None

    def _test_boolean_based(self, url: str, method: str, parameter: str, original_value: str, ai_reasoning_log: List[Dict]) -> Optional[SqliFinding]:
        """Boolean tabanlı SQLi zafiyetini test eder."""
        ai_reasoning_log.append({"phase": "verification", "thought": f"'{parameter}' parametresi için boolean tabanlı SQLi testi başlatıldı."})
        
        payload_true = f"{original_value}' AND 1=1 -- -"
        payload_false = f"{original_value}' AND 1=2 -- -"

        resp_true = self._make_request(url, method, parameter, payload_true)
        resp_false = self._make_request(url, method, parameter, payload_false)

        if resp_true and resp_false and resp_true.status_code == 200 and resp_false.status_code == 200:
            if resp_true.text != resp_false.text:
                 # Farkın anlamlı olduğundan emin olalım (örn: 10 karakterden fazla)
                if abs(len(resp_true.text) - len(resp_false.text)) > 10:
                    ai_reasoning_log.append({"phase": "critical_finding", "thought": "⚠️ Boolean tabanlı SQLi doğrulandı! 'true' ve 'false' yanıtları farklı."})
                    return SqliFinding(
                        injection_type='boolean_based',
                        vulnerable_parameter=parameter,
                        poc_payload=payload_true,
                        proof={
                            'true_response_length': len(resp_true.text),
                            'false_response_length': len(resp_false.text)
                        }
                    )
        return None
    
    def _test_error_based(self, url: str, method: str, parameter: str, original_value: str, ai_reasoning_log: List[Dict]) -> Optional[SqliFinding]:
        """Hata tabanlı SQLi zafiyetini test eder."""
        ai_reasoning_log.append({"phase": "verification", "thought": f"'{parameter}' parametresi için hata tabanlı SQLi testi başlatıldı."})
        payload = f"{original_value}'" # Basit bir tırnak işareti genellikle yeterlidir
        
        response = self._make_request(url, method, parameter, payload)
        if response:
            for dbms, sig in self.dbms_signatures.items():
                if re.search(sig['error'], response.text, re.IGNORECASE):
                    ai_reasoning_log.append({"phase": "critical_finding", "thought": f"⚠️ Hata tabanlı SQLi doğrulandı! Hata mesajı DBMS ile eşleşiyor: {dbms}"})
                    return SqliFinding(
                        injection_type='error_based',
                        vulnerable_parameter=parameter,
                        poc_payload=payload,
                        proof={'error_pattern_matched': sig['error']},
                        dbms_identified=dbms
                    )
        return None

    async def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Aracın ana giriş noktası. SQLi doğrulama testi yapar."""
        url = params.get("url")
        parameter = params.get("parameter")
        method = params.get("method", "GET")

        if not all([url, parameter, method]):
            return self._create_mcp_output(success=False, error="'url', 'parameter' ve 'method' parametreleri gereklidir.")
        
        ai_reasoning_log = [{"phase": "initialization", "thought": f"SQLi Verifier aracı '{url}' hedefi ve '{parameter}' parametresi için başlatıldı."}]
        
        # Orijinal parametre değerini al (varsa)
        parsed_url = urlparse(url)
        original_value = parse_qs(parsed_url.query).get(parameter, ['1'])[0]
        
        findings: List[SqliFinding] = []
        try:
            # Her bir kanıt yöntemini sırayla dene
            finding_error = self._test_error_based(url, method, parameter, original_value, ai_reasoning_log)
            if finding_error: findings.append(finding_error)

            finding_boolean = self._test_boolean_based(url, method, parameter, original_value, ai_reasoning_log)
            if finding_boolean: findings.append(finding_boolean)
            
            # Zaman tabanlıyı en son dene çünkü yavaştır
            finding_time = self._test_time_based(url, method, parameter, original_value, ai_reasoning_log)
            if finding_time: findings.append(finding_time)
            
            ai_reasoning_log.append({"phase": "analysis_complete", "thought": "Tüm SQLi doğrulama testleri tamamlandı."})
            return self._create_mcp_output(target_url=url, findings=findings, ai_reasoning_log=ai_reasoning_log)

        except Exception as e:
            logger.critical(f"SQLi Verifier aracında kritik hata: {e}", exc_info=True)
            return self._create_mcp_output(success=False, error=f"Beklenmedik bir hata oluştu: {str(e)}", ai_reasoning_log=ai_reasoning_log)

    def _create_mcp_output(self,
                           target_url: str = None,
                           findings: List[SqliFinding] = None,
                           ai_reasoning_log: List[Dict] = None,
                           success: bool = True,
                           error: str = None) -> Dict[str, Any]:
        """Toplanan kanıtları standart MCP JSON formatına dönüştürür."""
        if findings is None: findings = []
        if ai_reasoning_log is None: ai_reasoning_log = []

        if not success:
            ai_summary = "SQLi doğrulama testi bir hata nedeniyle başarısız oldu."
        elif not findings:
            ai_summary = f"Hedefte yapılan testlerde SQL enjeksiyonu zafiyeti kanıtlanamadı."
        else:
            types_found = list(set(f.injection_type for f in findings))
            param = findings[0].vulnerable_parameter
            ai_summary = f"KRİTİK! Hedefte '{param}' parametresinde {', '.join(types_found)} tipi SQL enjeksiyonu zafiyeti doğrulandı."
            
        # Dinamik öneriler oluştur
        recommendations = self._generate_dynamic_sqli_recommendations(findings, target_url)
        
        # RAG-friendly format ekle
        rag_data = {
            "sql_injection_findings": [
                {
                    "injection_type": finding.injection_type,
                    "vulnerable_parameter": finding.vulnerable_parameter,
                    "payload": finding.payload,
                    "evidence": finding.evidence,
                    "confidence": finding.confidence,
                    "rag_query_suggestion": f"SQL injection remediation for {finding.injection_type} on parameter {finding.vulnerable_parameter}"
                }
                for finding in findings
            ],
            "scan_metadata": {
                "target_url": target_url,
                "scan_timestamp": time.time(),
                "scan_type": "sql_injection_verification",
                "total_findings": len(findings),
                "critical_vulnerabilities": len([f for f in findings if f.confidence == "high"])
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

    def _generate_dynamic_sqli_recommendations(self, findings: List[SqliFinding], target_url: str) -> List[Dict]:
        """Dinamik SQL injection önerileri oluşturur."""
        recommendations = []
        
        if not findings:
            return recommendations
        
        # SQL injection türlerini analiz et
        error_based = [f for f in findings if f.injection_type == "Error-based"]
        boolean_based = [f for f in findings if f.injection_type == "Boolean-based"]
        time_based = [f for f in findings if f.injection_type == "Time-based"]
        
        # Error-based SQL injection için özel öneriler
        if error_based:
            for finding in error_based[:2]:  # İlk 2 error-based finding
                recommendations.append({
                    "priority": "critical",
                    "tool": "vuln_dependency_scanner",
                    "reason": f"🚨 ERROR-BASED SQL INJECTION: {finding.vulnerable_parameter} parametresinde error-based SQL injection tespit edildi. Database bilgileri sızabilir.",
                    "params": {
                        "vulnerability": "SQL Injection - Error-based",
                        "parameter": finding.vulnerable_parameter,
                        "payload": finding.payload,
                        "cve_check": True,
                        "rag_query": f"Error-based SQL injection remediation for {finding.vulnerable_parameter}"
                    },
                    "expert_context": f"Error-based SQL injection için kritik analiz. {finding.vulnerable_parameter} parametresi için database bilgi sızıntısı ve remediation teknikleri analiz edilmeli."
                })
        
        # Boolean-based SQL injection için özel öneriler
        if boolean_based:
            for finding in boolean_based[:2]:  # İlk 2 boolean-based finding
                recommendations.append({
                    "priority": "critical",
                    "tool": "vuln_dependency_scanner",
                    "reason": f"🚨 BOOLEAN-BASED SQL INJECTION: {finding.vulnerable_parameter} parametresinde boolean-based SQL injection tespit edildi. Blind SQL injection riski var.",
                    "params": {
                        "vulnerability": "SQL Injection - Boolean-based",
                        "parameter": finding.vulnerable_parameter,
                        "payload": finding.payload,
                        "blind_sqli": True,
                        "rag_query": f"Boolean-based SQL injection remediation for {finding.vulnerable_parameter}"
                    },
                    "expert_context": f"Boolean-based SQL injection için kritik analiz. {finding.vulnerable_parameter} parametresi için blind SQL injection teknikleri ve remediation analiz edilmeli."
                })
        
        # Time-based SQL injection için özel öneriler
        if time_based:
            for finding in time_based[:2]:  # İlk 2 time-based finding
                recommendations.append({
                    "priority": "critical",
                    "tool": "vuln_dependency_scanner",
                    "reason": f"🚨 TIME-BASED SQL INJECTION: {finding.vulnerable_parameter} parametresinde time-based SQL injection tespit edildi. Database kontrolü mümkün olabilir.",
                    "params": {
                        "vulnerability": "SQL Injection - Time-based",
                        "parameter": finding.vulnerable_parameter,
                        "payload": finding.payload,
                        "time_delay": True,
                        "rag_query": f"Time-based SQL injection remediation for {finding.vulnerable_parameter}"
                    },
                    "expert_context": f"Time-based SQL injection için kritik analiz. {finding.vulnerable_parameter} parametresi için time delay teknikleri ve remediation analiz edilmeli."
                })
        
        # Genel SQL injection önerileri
        if findings:
            recommendations.append({
                "priority": "critical",
                "tool": "human_intervention_alert",
                "reason": f"🚨 KRİTİK SQL INJECTION ZAFİYETİ: {len(findings)} farklı SQL injection türü tespit edildi. Uzman müdahalesi gerekiyor.",
                "params": {
                    "target": target_url,
                    "vulnerability_count": len(findings),
                    "injection_types": list(set(f.injection_type for f in findings)),
                    "urgent_review": True
                },
                "expert_context": f"Kritik SQL injection zafiyeti için acil uzman müdahalesi. {len(findings)} farklı injection türü için detaylı analiz ve remediation planı gerekli."
            })
        
        return recommendations

# --- Test Amaçlı Çalıştırma Bloğu ---
if __name__ == "__main__":
    import asyncio
    
    # Test için halka açık, bilinen zafiyetli bir site kullanılıyor.
    # Bu site, eğitim amaçlıdır ve bu tür testlere izin verir.
    test_params = {
        "url": "http://testphp.vulnweb.com/listproducts.php?cat=1",
        "parameter": "cat",
        "method": "GET"
    }

    async def main():
        print(f"--- [TEST BAŞLANGICI] ---")
        print(f"Hedef URL: {test_params['url']}")
        print(f"Parametre: {test_params['parameter']}")
        print("-" * 25)

        verifier = SqliVerifier()
        result = await verifier.run_tool(test_params)

        print("\n--- [TEST SONUCU] ---")
        print(json.dumps(result, indent=2, ensure_ascii=True))
        print("-" * 25)
    
    asyncio.run(main())