"""
api_vuln_idor_scanner.py - Pentagent Projesi için MCP Uyumlu IDOR/BOLA Tarama Aracı

Amaç: 
Bu araç, API endpoint'lerinde Insecure Direct Object Reference (IDOR) ve Broken Object
Level Authorization (BOLA) zafiyetlerini tespit etmek için tasarlanmıştır. Verilen
endpoint'lerdeki ID'leri akıllıca tespit eder, bunları değiştirerek yetkisiz veri
erişimi olup olmadığını test eder ve bulguları kanıtlarıyla birlikte sunar.

Temel Felsefeye Uygunluk:
- Keşfet & Tespit Et: API endpoint'lerini tarayarak, en yaygın ve kritik API
  zafiyetlerinden biri olan yetkilendirme eksikliklerini tespit eder.
- Kanıtla: Bir zafiyet bulduğunda, "orijinal ID", "test edilen ID", "başarılı yanıt kodu"
  ve "sızdırılan hassas veri türleri" gibi somut kanıtları sunar. Sömürü yapmaz.
- RAG Girdisi Sağla: 'data' alanında, bulunan her IDOR/BOLA zafiyetini, etkilenen
  endpoint, sızan veri türleri ve kanıtlarıyla birlikte yapılandırılmış bir formatta sağlar.
- Otonom Ajanı Yönlendir: 'recommendations' alanı ile MCP'ye, "bu IDOR zafiyetini
  kullanarak sızan token'ı 'vuln_credential_tester' ile doğrula" veya "sızan PII
  verisini 'intel_data_exfiltrator' ile analiz et" gibi, saldırı zincirinin bir
  sonraki halkasını oluşturan net komutlar verir.
"""
import asyncio
import re
import json
import logging
import time
from typing import Dict, Any, List, Optional
import aiohttp
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import uuid

# PentagentTool base class'ını import et
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Aranacak ID parametre isimleri
ID_PARAM_NAMES = ['id', 'user_id', 'userId', 'account_id', 'accountId', 'profileId', 'orderId']
# Sızdırılan veride aranacak hassas anahtar kelimeler
SENSITIVE_KEYWORDS = ['email', 'phone', 'ssn', 'password', 'secret', 'token', 'apiKey', 'address', 'creditCard']

class ApiVulnIdorScannerTool(MCPTool):
    """API endpoint'lerinde IDOR ve BOLA zafiyetlerini tespit eder."""
    def __init__(self):
        super().__init__(
            name="api_vuln_idor_scanner",
            description="API endpoint'lerinde yetkisiz veri erişimi (IDOR/BOLA) zafiyetlerini arar.",
            category=ToolCategory.API_SECURITY
        )

    def _identify_and_extract_ids(self, url: str) -> List[Dict]:
        """Bir URL'den potansiyel ID'leri ve konumlarını çıkarır."""
        ids = []
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        
        # Path içindeki ID'ler (örn: /users/123/profile)
        for part in path_parts:
            if part.isdigit() and len(part) < 10: # Çok uzun sayıları ID varsayma
                ids.append({"value": part, "type": "numeric", "location": "path"})
            elif re.match(r'^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$', part):
                ids.append({"value": part, "type": "uuid", "location": "path"})

        # Query parametrelerindeki ID'ler (örn: ?user_id=123)
        query_params = parse_qs(parsed.query)
        for param, values in query_params.items():
            if any(p_name.lower() in param.lower() for p_name in ID_PARAM_NAMES) and values:
                value = values[0]
                id_type = "uuid" if re.match(r'^[0-9a-fA-F-]{36}$', value) else "numeric" if value.isdigit() else "alphanumeric"
                ids.append({"value": value, "type": id_type, "location": "query", "param_name": param})
        return ids
        
    def _generate_test_ids(self, original_id: str, id_type: str, count: int = 5) -> List[str]:
        """Test için değiştirilmiş ID'ler üretir."""
        if id_type == "numeric":
            try:
                base_id = int(original_id)
                return [str(base_id + i) for i in range(-2, 3) if i != 0 and base_id + i > 0]
            except ValueError:
                return []
        if id_type == "uuid":
            return [str(uuid.uuid4()) for _ in range(count)]
        return []

    async def _test_single_endpoint(self, session: aiohttp.ClientSession, endpoint: Dict) -> Optional[Dict]:
        """Tek bir endpoint ve ID kombinasyonunu IDOR için test eder."""
        method = endpoint.get("method", "GET").upper()
        url = endpoint.get("url")
        
        try:
            async with session.request(method, url) as original_response:
                if original_response.status not in [200, 201]: return None
                original_content = await original_response.text()
            
            ids_to_test = self._identify_and_extract_ids(url)
            if not ids_to_test: return None
            
            for discovered_id in ids_to_test:
                original_id_val = discovered_id["value"]
                test_ids = self._generate_test_ids(original_id_val, discovered_id["type"])

                for test_id in test_ids:
                    if discovered_id["location"] == "path":
                        test_url = url.replace(original_id_val, test_id)
                    else:
                        parsed = urlparse(url); query = parse_qs(parsed.query)
                        query[discovered_id["param_name"]] = [test_id]
                        test_url = urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
                    
                    async with session.request(method, test_url) as test_response:
                        if test_response.status == original_response.status:
                            test_content = await test_response.text()
                            if test_content != original_content and len(test_content) > 20:
                                leaked_data_types = [kw for kw in SENSITIVE_KEYWORDS if kw in test_content.lower()]
                                return {
                                    "endpoint": url, "method": method, "parameter": discovered_id.get("param_name", "path-based"),
                                    "original_id": original_id_val, "tested_id": test_id, "status_code": test_response.status,
                                    "leaked_data_types": leaked_data_types,
                                    "evidence_snippet": test_content[:250]
                                }
        except Exception as e:
            logger.warning(f"Error testing endpoint {url}: {e}")
        return None

    def _generate_mcp_recommendations(self, findings: List[Dict]) -> List[Dict]:
        """Bulgulara göre MCP için eyleme geçirilebilir öneriler üretir."""
        recommendations = []
        for vuln in findings:
            if "token" in vuln["leaked_data_types"] or "apiKey" in vuln["leaked_data_types"]:
                recommendations.append(
                    self._create_recommendation(
                        priority=PriorityLevel.CRITICAL,
                        tool_name="vuln_credential_tester",
                        reason=f"IDOR zafiyeti ile potansiyel bir token/API anahtarı sızdırıldı. Geçerliliği acilen test edilmeli.",
                        params={"credential": "EXTRACT_FROM_EVIDENCE", "type": "token"}
                    )
                )
            elif vuln["leaked_data_types"]:
                recommendations.append(
                    self._create_recommendation(
                        priority=PriorityLevel.HIGH,
                        tool_name="intel_data_exfiltrator",
                        reason=f"IDOR zafiyeti ile PII verisi sızdırılıyor. Sızıntının boyutunu anlamak için veri çekilmeli.",
                        params={"endpoint": vuln["endpoint"], "vulnerability": "IDOR"}
                    )
                )
        return recommendations

    def _generate_dynamic_idor_recommendations(self, findings: List[Dict]) -> List[Dict]:
        """Dinamik IDOR/BOLA önerileri oluşturur."""
        recommendations = []
        
        if not findings:
            return recommendations
        
        # IDOR türlerini analiz et
        idor_findings = [f for f in findings if f.get('vulnerability_type') == 'IDOR']
        bola_findings = [f for f in findings if f.get('vulnerability_type') == 'BOLA']
        high_severity = [f for f in findings if f.get('severity') == 'high']
        
        # IDOR zafiyetleri için özel öneriler
        if idor_findings:
            for finding in idor_findings[:2]:  # İlk 2 IDOR finding
                recommendations.append({
                    "priority": "high",
                    "tool": "vuln_dependency_scanner",
                    "reason": f"🔓 IDOR ZAFİYETİ: {finding['endpoint']} endpoint'inde IDOR tespit edildi. Yetkisiz veri erişimi mümkün.",
                    "params": {
                        "endpoint": finding['endpoint'],
                        "method": finding['method'],
                        "vulnerability_type": "IDOR",
                        "leaked_data_types": finding['leaked_data_types'],
                        "rag_query": f"IDOR remediation for {finding['endpoint']}"
                    },
                    "expert_context": f"IDOR zafiyeti için kritik analiz. {finding['endpoint']} endpoint'i için yetkilendirme kontrolleri ve access control mekanizmaları analiz edilmeli."
                })
        
        # BOLA zafiyetleri için özel öneriler
        if bola_findings:
            for finding in bola_findings[:2]:  # İlk 2 BOLA finding
                recommendations.append({
                    "priority": "high",
                    "tool": "vuln_dependency_scanner",
                    "reason": f"🔓 BOLA ZAFİYETİ: {finding['endpoint']} endpoint'inde BOLA tespit edildi. Object-level authorization eksik.",
                    "params": {
                        "endpoint": finding['endpoint'],
                        "method": finding['method'],
                        "vulnerability_type": "BOLA",
                        "leaked_data_types": finding['leaked_data_types'],
                        "rag_query": f"BOLA remediation for {finding['endpoint']}"
                    },
                    "expert_context": f"BOLA zafiyeti için kritik analiz. {finding['endpoint']} endpoint'i için object-level authorization kontrolleri ve access control mekanizmaları analiz edilmeli."
                })
        
        # Yüksek riskli zafiyetler için özel öneriler
        if high_severity:
            for finding in high_severity[:2]:  # İlk 2 yüksek riskli finding
                recommendations.append({
                    "priority": "critical",
                    "tool": "human_intervention_alert",
                    "reason": f"🚨 YÜKSEK RİSKLİ API ZAFİYETİ: {finding['endpoint']} endpoint'inde yüksek riskli {finding['vulnerability_type']} tespit edildi.",
                    "params": {
                        "endpoint": finding['endpoint'],
                        "vulnerability_type": finding['vulnerability_type'],
                        "severity": finding['severity'],
                        "urgent_review": True,
                        "rag_query": f"High risk API vulnerability remediation for {finding['endpoint']}"
                    },
                    "expert_context": f"Yüksek riskli API zafiyeti için acil müdahale. {finding['endpoint']} endpoint'i için detaylı güvenlik analizi ve remediation planı gerekli."
                })
        
        # Genel API güvenlik önerileri
        if findings:
            recommendations.append({
                "priority": "high",
                "tool": "vuln_dependency_scanner",
                "reason": f"🔓 API GÜVENLİK ANALİZİ: {len(findings)} API zafiyeti tespit edildi. Authorization kontrolleri gözden geçirilmeli.",
                "params": {
                    "total_vulnerabilities": len(findings),
                    "idor_count": len(idor_findings),
                    "bola_count": len(bola_findings),
                    "high_severity_count": len(high_severity),
                    "api_security_review": True
                },
                "expert_context": f"API güvenlik analizi için kapsamlı inceleme. {len(findings)} API zafiyeti için detaylı authorization kontrolleri ve access control mekanizmaları analiz edilmeli."
            })
        
        return recommendations

    def _create_final_output(self, findings: List[Dict], recommendations: List[Dict], reasoning_log: List[Dict], rag_data: Dict = None) -> Dict:
        """Tüm verileri standart MCP JSON formatında birleştirir."""
        summary = f"API IDOR/BOLA taraması tamamlandı. {len(findings)} adet potansiyel zafiyet bulundu. "
        if not findings:
            summary = "API IDOR/BOLA taraması tamamlandı. Test edilen endpointlerde bariz bir zafiyet bulunamadı."
        else:
            summary += f"MCP ajanı için {len(recommendations)} adet bir sonraki adım önerisi oluşturuldu."

        data = {"vulnerabilities": findings}
        if rag_data:
            data["rag_analysis_data"] = rag_data

        return {
            "success": True, 
            "data": data, 
            "ai_summary": summary,
            "ai_reasoning": reasoning_log, 
            "recommendations": recommendations, 
            "error": None
        }

    async def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Aracın ana giriş noktası."""
        endpoints = params.get("endpoints")
        auth_token = params.get("auth_token")
        reasoning_log = []
        
        try:
            self._add_reasoning(reasoning_log, "initialization", f"{len(endpoints)} API endpoint'i için IDOR/BOLA taraması başlatılıyor.")
            
            if not endpoints or not isinstance(endpoints, list):
                raise ValueError("`endpoints` parametresi bir liste olmalı ve boş olmamalıdır.")

            headers = {'Accept': 'application/json', 'User-Agent': 'Pentagent-Scanner/1.0'}
            if auth_token:
                headers['Authorization'] = f'Bearer {auth_token}'

            findings = []
            async with aiohttp.ClientSession(headers=headers) as session:
                tasks = [self._test_single_endpoint(session, ep) for ep in endpoints]
                results = await asyncio.gather(*tasks)
                findings = sorted([res for res in results if res is not None], key=lambda x: len(x['leaked_data_types']), reverse=True)

            if findings:
                self._add_reasoning(reasoning_log, "critical_finding", f"⚠️ {len(findings)} adet potansiyel IDOR/BOLA zafiyeti tespit edildi.")
            else:
                self._add_reasoning(reasoning_log, "analysis_complete", "Analiz tamamlandı. Kritik bir IDOR/BOLA zafiyetine rastlanmadı.")

            recommendations = self._generate_mcp_recommendations(findings)
            self._add_reasoning(reasoning_log, "recommendation", f"Bulgulara dayanarak {len(recommendations)} adet bir sonraki adım önerisi oluşturuldu.")
            
            self._add_reasoning(reasoning_log, "completion", "Tarama başarıyla tamamlandı, sonuçlar formatlanıyor.")
            
            # Dinamik öneriler oluştur
            recommendations = self._generate_dynamic_idor_recommendations(findings)
            
            # RAG-friendly format ekle
            rag_data = {
                "idor_vulnerabilities": [
                    {
                        "endpoint": finding['endpoint'],
                        "method": finding['method'],
                        "vulnerability_type": finding['vulnerability_type'],
                        "leaked_data_types": finding['leaked_data_types'],
                        "severity": finding['severity'],
                        "rag_query_suggestion": f"IDOR remediation for {finding['endpoint']} - {finding['vulnerability_type']}"
                    }
                    for finding in findings
                ],
                "scan_metadata": {
                    "scan_timestamp": time.time(),
                    "scan_type": "idor_bola_scanning",
                    "total_endpoints_tested": len(endpoints),
                    "total_vulnerabilities_found": len(findings),
                    "high_severity_count": len([f for f in findings if f.get('severity') == 'high'])
                }
            }
            
            self._add_reasoning(reasoning_log, "completion", "Tarama başarıyla tamamlandı, sonuçlar formatlanıyor.")
            
            return self._create_final_output(findings, recommendations, reasoning_log, rag_data)

        except Exception as e:
            error_message = f"IDOR tarayıcısı çalıştırılırken hata oluştu: {str(e)}"
            logger.error(error_message, exc_info=True)
            self._add_reasoning(reasoning_log, "error", error_message)
            
            return self._create_final_output([], [], reasoning_log)

async def main():
    """Aracın komut satırından test edilmesi için ana fonksiyon."""
    print("--- IDOR/BOLA Tarayıcı Test Modu ---")
    
    # Gerçekçi bir senaryo için, bu endpoint listesinin bir önceki
    # `enum_api_endpoints` aracı tarafından üretildiğini varsayalım.
    test_endpoints = [
        {"url": "https://jsonplaceholder.typicode.com/users/1", "method": "GET"}, # Potansiyel IDOR'u test etmek için iyi bir aday
        {"url": "https://jsonplaceholder.typicode.com/posts/1", "method": "GET"},
        {"url": "https://jsonplaceholder.typicode.com/photos?albumId=1", "method": "GET"},
        {"url": "https://api.github.com/users/octocat", "method": "GET"} # IDOR olmaması beklenen bir endpoint
    ]
    
    # Örnek bir auth token (gerçek senaryoda gerekli olabilir)
    # test_auth_token = "ey..." 
    
    tool = ApiVulnIdorScannerTool()
    
    # Aracı çalıştır
    result = await tool.run_tool({
        "endpoints": test_endpoints,
        "auth_token": None # Public API için token gerekmiyor
    })
    
    print(json.dumps(result, indent=4, ensure_ascii=True))

if __name__ == "__main__":
    asyncio.run(main())