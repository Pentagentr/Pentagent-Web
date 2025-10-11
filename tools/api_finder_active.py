"""
recon_api_finder_active.py (MCP Refactored)
Görevi: Belgelenmemiş veya gizli API endpoint'lerini kelime listesi, Swagger tespiti ve akıllı
        base path analizi gibi yöntemlerle aktif olarak keşfeder.
Bu araç, Pentagent projesinin standartlarına uygun olarak yeniden düzenlenmiştir.
"""

import requests
import json
import re
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Set, Tuple
import logging

# PentagentTool base class'ını import et
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

# Standart bir logger yapısı
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ReconApiFinderActive(MCPTool):
    """
    Kelime listesi ve akıllı detection yöntemleriyle API endpoint'lerini aktif olarak tarar.
    MCP ajan mimarisi için standartlaştırılmış girdi ve çıktı formatlarına sahiptir.
    """

    def __init__(self):
        super().__init__(
            name="recon_api_finder_active",
            description="Kelime listesi ve Swagger tespiti ile API endpoint'lerini aktif olarak keşfeder.",
            category=ToolCategory.RECONNAISSANCE
        )
        self.version = "2.0.0-MCP"
        self.ai_reasoning_log = []

        # Orijinal koddaki harika bilgi bankalarını ve metodları koruyoruz
        self.default_wordlist = [
            'api/v1', 'api/v2', 'api', 'v1', 'users', 'login', 'auth', 'token',
            'admin', 'config', 'status', 'version', 'docs', 'swagger', 'graphql',
            'data', 'search', 'upload', 'download', 'profile', 'password/reset',
            'swagger.json', 'openapi.json', 'swagger-ui.html'
        ]
        self.methods_to_test = ['GET', 'POST'] # Hızlı tarama için GET ve POST yeterli
        self.api_base_patterns = [r'/api/v\d+', r'/v\d+', r'/api', r'/rest']
        
    def _log_thought(self, phase: str, thought: str):
        """Düşünce sürecini logla - DÜZELTME: reasoning_log parametresi eklendi"""
        self._add_reasoning(self.ai_reasoning_log, phase, thought)
        logger.info(f"[{self.name} - {phase}] {thought}")

    # =====================================================================================
    # MCP STANDART GİRİŞ NOKTASI (ENTRY POINT)
    # =====================================================================================
    def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        self.ai_reasoning_log = []
        try:
            base_url = params.get("url")
            if not base_url:
                raise ValueError("Gerekli 'url' parametresi eksik.")
            
            threads = params.get("threads", 20)
            wordlist = params.get("wordlist", self.default_wordlist)
            
            self._log_thought("initialization", f"Aktif API endpoint keşfi '{base_url}' için başlatılıyor.")
            
            # Ana tarama iş akışını başlat
            discovered_endpoints = self._scan(base_url, wordlist, threads)
            
            mcp_output = self._format_mcp_output(discovered_endpoints, base_url)
            self._log_thought("analysis_complete", "Aktif keşif tamamlandı. MCP için standart çıktı oluşturuldu.")
            return mcp_output

        except Exception as e:
            logger.error(f"API endpoint bulucuda hata: {e}", exc_info=True)
            self._log_thought("error", f"Araç çalıştırılırken kritik bir hata oluştu: {e}")
            return {
                "success": False, "data": {},
                "ai_summary": f"Araç çalıştırılırken kritik bir hata oluştu: {e}",
                "ai_reasoning": self.ai_reasoning_log, "recommendations": [],
                "error": str(e)
            }

    def _format_mcp_output(self, discovered_endpoints: List[Dict], base_url: str) -> Dict[str, Any]:
        high_risk_endpoints = [e for e in discovered_endpoints if e.get('ai_risk_score', 0) > 6]
        summary = f"{len(discovered_endpoints)} adet potansiyel API endpoint'i keşfedildi. Bunlardan {len(high_risk_endpoints)} tanesi yüksek riskli olarak işaretlendi."
        if not discovered_endpoints:
            summary = "Aktif tarama sonucunda herhangi bir API endpoint'i veya Swagger dokümanı bulunamadı."

        return self._create_final_output(
            success=True,
            data={"base_url": base_url, "discovered_endpoints": discovered_endpoints},
            ai_summary=summary,
            ai_reasoning=self.ai_reasoning_log,
            recommendations=self._generate_mcp_recommendations(discovered_endpoints)
        )

    def _generate_mcp_recommendations(self, discovered_endpoints: List[Dict]) -> List[Dict]:
        """MCP ajanı için eyleme dönüştürülebilir öneriler üretir."""
        recommendations = []
        unique_recommendations: Set[str] = set()

        for endpoint in discovered_endpoints:
            # IDOR Testi Önerisi
            if "IDOR" in endpoint.get("ai_exploitation_hint", ""):
                rec_key = f"idor_{endpoint['method']}"
                if rec_key not in unique_recommendations:
                    recommendations.append(
                        self._create_recommendation(
                            priority=PriorityLevel.HIGH,
                            tool_name="vuln_idor_tester",
                            reason=f"Keşfedilen '{endpoint['url']}' endpoint'i IDOR zafiyetleri için potansiyel taşıyor.",
                            params={"url": endpoint['url'], "method": endpoint['method']}
                        )
                    )
                    unique_recommendations.add(rec_key)

            # JWT Analizi Önerisi
            if "JWT" in endpoint.get("ai_exploitation_hint", ""):
                rec_key = "jwt_analyzer"
                if rec_key not in unique_recommendations:
                    recommendations.append(
                        self._create_recommendation(
                            priority=PriorityLevel.HIGH,
                            tool_name="vuln_jwt_analyzer",
                            reason="Bearer Token (JWT) kimlik doğrulaması tespit edildi. Token zafiyetleri için derinlemesine analiz yapılmalı.",
                            params={"url": endpoint['url']}
                        )
                    )
                    unique_recommendations.add(rec_key)

        # Genel Fuzzing Önerisi
        if discovered_endpoints:
             recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.MEDIUM,
                    tool_name="fuzzer_api_general",
                    reason=f"{len(discovered_endpoints)} endpoint bulundu. Bu endpoint'ler genel API zafiyetleri (SQLi, Command Injection vb.) için fuzz edilmeli.",
                    params={"endpoints": [e['url'] for e in discovered_endpoints]}
                )
            )
        
        return recommendations

    # =====================================================================================
    # MEVCUT ÇEKİRDEK MANTIK (ORİJİNAL KODDAN ALINMIŞ VE UYARLANMIŞTIR)
    # =====================================================================================

    def _scan(self, base_url: str, wordlist: List[str], threads: int) -> List[Dict]:
        """Ana tarama iş akışı: base path tespiti, swagger ve kaba kuvvet taraması."""
        session = requests.Session()
        session.headers.update({'User-Agent': 'Pentagent-Scanner/1.0'})
        
        # 1. Akıllı Base Path Tespiti
        base_paths = self._detect_api_base_paths(base_url, session)
        
        # 2. Swagger/OpenAPI Doküman Taraması
        discovered_from_docs: List[Dict] = []
        for doc_url, swagger_data in self._discover_swagger_docs(base_url, session):
            paths = self._extract_endpoints_from_swagger(swagger_data)
            for path, method in paths:
                full_url = urljoin(doc_url, path)
                # Swagger'dan gelenleri direkt ekleyelim, çünkü zaten var oldukları biliniyor.
                discovered_from_docs.append({
                    "url": full_url, "method": method.upper(), "status_code": 200, "source": "swagger",
                    "ai_risk_score": 5.0, "ai_exploitation_hint": "Endpoint documented in Swagger. Check for business logic flaws."
                })
        
        # 3. Kaba Kuvvet Taraması
        all_paths_to_scan = set(wordlist)
        for bp in base_paths:
            for word in wordlist:
                all_paths_to_scan.add(f"{bp.strip('/')}/{word.strip('/')}")

        discovered_from_bruteforce: List[Dict] = []
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(self._test_endpoint, base_url, path, method, session) 
                       for path in all_paths_to_scan for method in self.methods_to_test]
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    discovered_from_bruteforce.append(result)
                    self._log_thought("finding", f"✅ Endpoint bulundu: {result['method']} {result['url']} (Status: {result['status_code']}, Risk: {result['ai_risk_score']:.1f})")

        # Sonuçları birleştir ve tekilleştir
        final_endpoints = {ep['url'] + ep['method']: ep for ep in discovered_from_docs}
        for ep in discovered_from_bruteforce:
            key = ep['url'] + ep['method']
            if key not in final_endpoints:
                final_endpoints[key] = ep
        
        return sorted(final_endpoints.values(), key=lambda x: x.get('ai_risk_score', 0), reverse=True)

    def _detect_api_base_paths(self, base_url: str, session: requests.Session) -> Set[str]:
        """Potansiyel API base path'lerini test eder."""
        base_paths: Set[str] = {''} # Root her zaman bir base path'tir
        self._log_thought("discovery", "Potansiyel API base path'leri taranıyor...")
        for pattern in self.api_base_patterns:
            try:
                # regex'i basit bir path'e dönüştür
                test_path = pattern.replace(r'/v\d+', '/v1')
                url = urljoin(base_url, test_path)
                resp = session.get(url, timeout=3, verify=False, allow_redirects=False)
                if 400 <= resp.status_code < 500: # 401, 403 gibi yanıtlar base path'in varlığına işarettir
                    base_paths.add(test_path)
                    self._log_thought("finding", f"Potansiyel API base path bulundu: {test_path}")
            except requests.exceptions.RequestException:
                pass
        return base_paths

    def _discover_swagger_docs(self, base_url: str, session: requests.Session) -> List[Tuple[str, Dict]]:
        """Swagger/OpenAPI dokümantasyonunu bulur."""
        swagger_paths = ['/swagger.json', '/openapi.json', '/v1/swagger.json', '/api/docs']
        self._log_thought("discovery", "Swagger/OpenAPI dokümanları aranıyor...")
        docs = []
        for path in swagger_paths:
            url = urljoin(base_url, path)
            try:
                resp = session.get(url, timeout=3, verify=False)
                if resp.status_code == 200 and 'json' in resp.headers.get('Content-Type', ''):
                    data = resp.json()
                    if 'paths' in data or 'swagger' in data or 'openapi' in data:
                        self._log_thought("critical_finding", f"⚠️ Swagger dokümanı bulundu: {url}")
                        docs.append((url, data))
            except (requests.exceptions.RequestException, json.JSONDecodeError):
                pass
        return docs

    def _extract_endpoints_from_swagger(self, swagger_data: Dict) -> List[Tuple[str, str]]:
        """Swagger verisinden (path, method) ikililerini çıkarır."""
        endpoints = []
        if 'paths' in swagger_data:
            for path, methods in swagger_data['paths'].items():
                endpoints.extend((path, method.upper()) for method in methods if method.upper() in self.methods_to_test)
        return endpoints

    def _test_endpoint(self, base_url: str, endpoint: str, method: str, session: requests.Session) -> Optional[Dict]:
        url = urljoin(base_url, endpoint)
        try:
            response = session.request(method, url, timeout=5, verify=False, allow_redirects=False, json={})
            if response.status_code != 404:
                return self._analyze_response(response, method, url)
        except requests.exceptions.RequestException:
            pass
        return None

    def _analyze_response(self, response: requests.Response, method: str, url: str) -> Dict:
        """Bir HTTP yanıtını analiz eder ve MCP formatına uygun bir sözlük döndürür."""
        status_code = response.status_code
        auth_required = status_code in [401, 403]
        
        hint = "Standard endpoint. Check for common vulnerabilities (e.g., input validation, logic flaws)."
        if any(p in url for p in ['user', 'account', 'profile', 'id']):
            hint = "ID-like parameters in URL suggest potential for IDOR."
        if 'Bearer' in response.headers.get('WWW-Authenticate', ''):
            hint = "JWT authentication detected. Check for token weaknesses (e.g., weak secrets, alg confusion)."
        
        risk_score = 1.0 # Temel skor
        if not auth_required and method in ['POST', 'PUT', 'DELETE'] and status_code < 400:
            risk_score += 5.0
            hint += " CRITICAL: Unauthenticated data modification method!"
        if status_code == 500:
            risk_score += 3.0
            hint += " Server error might leak sensitive info."
        
        return {
            "url": url, "method": method, "status_code": status_code, "source": "brute-force",
            "ai_risk_score": min(risk_score, 10.0), "ai_exploitation_hint": hint
        }
        
# =====================================================================================
# ÖRNEK KULLANIM VE TEST
# =====================================================================================
if __name__ == '__main__':
    active_finder = ReconApiFinderActive()
    
    # Gerçekçi bir test için zafiyetli bir API (örn: crAPI, vAPI) üzerinde denenmelidir.
    test_params = {
        "url": "https://jsonplaceholder.typicode.com/",
        "wordlist": ["posts", "comments", "users", "todos", "photos", "admin", "config", "swagger.json"]
    }
    
    print(f"--- {test_params['url']} için aktif API endpoint keşfi başlatılıyor ---")
    result = active_finder.run_tool(test_params)
    print(json.dumps(result, indent=4, ensure_ascii=True))