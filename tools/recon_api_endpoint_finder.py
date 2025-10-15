"""
recon_api_endpoint_finder.py - Pentagent Projesi için MCP Uyumlu API Endpoint Keşif Aracı

Amaç: 
Bu araç, Selenium kullanarak web uygulamalarında gizli API endpoint'lerini keşfeder.
Tarayıcının ağ trafiğini dinleyerek, JavaScript tarafından yapılan API çağrılarını
yakalar ve analiz eder.

Temel Felsefeye Uygunluk:
- Keşfet & Tespit Et: Web uygulamasının JavaScript kodunu çalıştırarak gizli API endpoint'lerini tespit eder.
- Kanıtla: Her endpoint için HTTP metodu, URL, status code ve POST verisi gibi somut kanıtlar sunar.
- RAG Girdisi Sağla: 'data' alanında, bulunan tüm endpoint'leri yapılandırılmış formatta sağlar.
- Otonom Ajanı Yönlendir: 'recommendations' alanı ile MCP'ye, "bu endpoint'leri IDOR testi ile kontrol et" gibi komutlar verir.
"""
import asyncio
import logging
import json
import argparse
import sys
import time
from typing import Dict, Any, List
from urllib.parse import urlparse
from dataclasses import dataclass, field
import concurrent.futures

# PentagentTool base class'ını import et
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
    from selenium.common.exceptions import WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# ... (Logger ve statik veri tanımlamaları önceki gibi) ...
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
logger = logging.getLogger(__name__)

IGNORED_EXTENSIONS = ('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.woff', '.woff2', '.ttf', '.eot', '.ico', '.map')
IGNORED_CONTENT_TYPES = ('text/css', 'image/', 'font/', 'javascript')

@dataclass
class ApiFinderContext:
    target_url: str; target_domain: str; wait_time: int
    endpoints: List[Dict[str, Any]] = field(default_factory=list)
    ai_reasoning_log: List[Dict[str, str]] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)

class ReconApiEndpointFinderTool(MCPTool):
    def __init__(self):
        super().__init__(
            name="recon_api_endpoint_finder",
            description="Selenium kullanarak web uygulamalarında gizli API endpoint'lerini keşfeder.",
            category=ToolCategory.RECONNAISSANCE
        )
        self.version = "3.0.0-MCP"
    
    def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """MCP ajanı tarafından çağrılacak ana fonksiyon."""
        try:
            target_url = params.get("url")
            wait_time = params.get("wait_time", 10)
            
            if not target_url:
                raise ValueError("Gerekli 'url' parametresi eksik.")
            
            self._add_reasoning("initialization", f"API endpoint keşfi '{target_url}' hedefi için başlatılıyor.")
            
            # Ana tarama mantığını çalıştır
            scan_result = self._scan_for_endpoints(target_url, wait_time)
            
            self._add_reasoning("analysis_complete", "API endpoint keşfi tamamlandı.")
            
            return self._create_final_output(
                success=True,
                data=scan_result,
                summary=self._generate_ai_summary(scan_result),
                recommendations=self._generate_mcp_recommendations(scan_result)
            )
            
        except Exception as e:
            logger.error(f"API endpoint finder'da hata: {e}", exc_info=True)
            self._add_reasoning("error", f"Araç çalıştırılırken kritik bir hata oluştu: {e}")
            return self._create_final_output(
                success=False,
                data={},
                summary=f"Araç çalıştırılırken kritik bir hata oluştu: {e}",
                recommendations=[],
                error=str(e)
            )
    
    def _generate_ai_summary(self, scan_result: Dict[str, Any]) -> str:
        """İnsan tarafından okunabilir bir özet oluşturur."""
        endpoints = scan_result.get('endpoints', [])
        if not endpoints:
            return "Hiçbir API endpoint'i tespit edilemedi."
        
        unique_methods = set(endpoint.get('method', 'UNKNOWN') for endpoint in endpoints)
        return f"{len(endpoints)} adet API endpoint tespit edildi. HTTP metodları: {', '.join(unique_methods)}"
    
    def _generate_mcp_recommendations(self, scan_result: Dict[str, Any]) -> List[Dict]:
        """MCP ajanı için eyleme dönüştürülebilir öneriler üretir."""
        recommendations = []
        endpoints = scan_result.get('endpoints', [])
        
        if not endpoints:
            return recommendations
        
        # API endpoint'leri için IDOR testi öner
        api_endpoints = [ep for ep in endpoints if ep.get('method') in ['GET', 'POST', 'PUT', 'DELETE']]
        if api_endpoints:
            recommendations.append(self._create_recommendation(
                priority=PriorityLevel.HIGH,
                tool="api_vuln_idor_scanner",
                reason="Tespit edilen API endpoint'lerinde IDOR/BOLA zafiyetleri kontrol edilmeli.",
                params={"endpoints": api_endpoints}
            ))
        
        # POST endpoint'leri için JWT testi öner
        post_endpoints = [ep for ep in endpoints if ep.get('method') == 'POST']
        if post_endpoints:
            recommendations.append(self._create_recommendation(
                priority=PriorityLevel.MEDIUM,
                tool="api_vuln_jwt_tester",
                reason="POST endpoint'lerinde JWT token zafiyetleri kontrol edilmeli.",
                params={"endpoints": post_endpoints}
            ))
        
        return recommendations
    
    def _scan_for_endpoints(self, target_url: str, wait_time: int) -> Dict[str, Any]:
        """Ana endpoint tarama fonksiyonu."""
        if not SELENIUM_AVAILABLE:
            self._add_reasoning("fallback", "Selenium kullanılamıyor, HTTP tabanlı endpoint keşfi kullanılıyor.")
            return self._http_based_endpoint_discovery(target_url)
        
        context = ApiFinderContext(
            target_url=target_url,
            target_domain=urlparse(target_url).netloc,
            wait_time=wait_time
        )
        
        try:
            # Selenium ile tarama yap
            context = self._intercept_with_logs_sync(context)
            
            return {
                "endpoints": context.endpoints,
                "scan_duration": time.time() - context.start_time,
                "ai_reasoning": context.ai_reasoning_log
            }
        except Exception as e:
            logger.error(f"Selenium taraması başarısız: {e}")
            self._add_reasoning("fallback", f"Selenium hatası ({str(e)}), HTTP tabanlı endpoint keşfi kullanılıyor.")
            return self._http_based_endpoint_discovery(target_url)
    
    def _http_based_endpoint_discovery(self, target_url: str) -> Dict[str, Any]:
        """HTTP-only endpoint keşfi (Render gibi Selenium olmayan ortamlar için)"""
        import requests
        from bs4 import BeautifulSoup
        
        endpoints = []
        start_time = time.time()
        
        try:
            # Ana sayfayı indir
            response = requests.get(target_url, timeout=10, headers={'User-Agent': 'PentagentBot/1.0'})
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # JavaScript dosyalarındaki API endpoint'lerini ara
            script_tags = soup.find_all('script', src=True)
            for script in script_tags:
                script_url = script.get('src')
                if script_url and not script_url.startswith('http'):
                    script_url = urlparse(target_url)._replace(path=script_url).geturl()
                
                if script_url:
                    try:
                        script_response = requests.get(script_url, timeout=5)
                        script_content = script_response.text
                        
                        # Yaygın API pattern'lerini ara
                        import re
                        api_patterns = [
                            r'["\']([/]api[^"\']*)["\']',
                            r'["\']([/]v\d+[^"\']*)["\']',
                            r'fetch\(["\']([^"\']+)["\']',
                            r'axios\.[a-z]+\(["\']([^"\']+)["\']'
                        ]
                        
                        for pattern in api_patterns:
                            matches = re.findall(pattern, script_content)
                            for match in matches:
                                if match and match.startswith('/'):
                                    full_url = urlparse(target_url)._replace(path=match).geturl()
                                    endpoints.append({
                                        "url": full_url,
                                        "method": "GET",  # Default
                                        "status_code": "discovered",
                                        "response_content_type": "application/json",
                                        "post_data": None,
                                        "source": "js_static_analysis"
                                    })
                    except Exception as e:
                        logger.debug(f"Script analizi hatası: {e}")
                        continue
            
            # Link'lerden API pattern'lerini ara
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and ('/api/' in href or '/v1/' in href or '/v2/' in href):
                    endpoints.append({
                        "url": href if href.startswith('http') else urlparse(target_url)._replace(path=href).geturl(),
                        "method": "GET",
                        "status_code": "discovered",
                        "response_content_type": "application/json",
                        "post_data": None,
                        "source": "html_links"
                    })
            
            # Unique endpoint'leri filtrele
            unique_endpoints = []
            seen_urls = set()
            for ep in endpoints:
                if ep['url'] not in seen_urls:
                    unique_endpoints.append(ep)
                    seen_urls.add(ep['url'])
            
            return {
                "endpoints": unique_endpoints,
                "scan_duration": time.time() - start_time,
                "ai_reasoning": [
                    {"phase": "http_based", "thought": f"HTTP tabanlı endpoint keşfi tamamlandı. {len(unique_endpoints)} endpoint bulundu."}
                ]
            }
            
        except Exception as e:
            logger.error(f"HTTP tabanlı endpoint keşfi hatası: {e}")
            return {
                "endpoints": [],
                "scan_duration": time.time() - start_time,
                "ai_reasoning": [
                    {"phase": "error", "thought": f"HTTP tabanlı endpoint keşfi başarısız: {str(e)}"}
                ]
            }
    def _is_relevant_request(self, url: str, content_type: str) -> bool:
        path = urlparse(url).path.lower()
        ct_lower = content_type.lower()
        if path.endswith(IGNORED_EXTENSIONS): return False
        if any(ignored_ct in ct_lower for ignored_ct in IGNORED_CONTENT_TYPES): return False
        return True

    def _process_performance_logs(self, logs: List[Dict], context: ApiFinderContext):
        """Performans loglarından gelen ham CDP verisini işleyerek endpoint listesini oluşturur."""
        context.ai_reasoning_log.append({"phase": "processing", "thought": f"{len(logs)} adet performans log kaydı işleniyor."})

        requests = {}
        responses = {}

        for log in logs:
            try:
                message_data = json.loads(log["message"])["message"]
                method = message_data.get("method")
                params = message_data.get("params")

                if method == "Network.requestWillBeSent":
                    req_id = params["requestId"]
                    requests[req_id] = params["request"]
                elif method == "Network.responseReceived":
                    req_id = params["requestId"]
                    responses[req_id] = params["response"]
            except (json.JSONDecodeError, KeyError):
                continue

        for req_id, request_data in requests.items():
            if req_id in responses and urlparse(request_data['url']).netloc == context.target_domain:
                response_data = responses[req_id]
                content_type = response_data['headers'].get('content-type', '')
                
                if self._is_relevant_request(request_data['url'], content_type):
                    endpoint_info = {
                        "url": request_data['url'], "method": request_data['method'],
                        "status_code": response_data['status'], "response_content_type": content_type,
                        "post_data": request_data.get('postData')
                    }
                    context.endpoints.append(endpoint_info)
                    context.ai_reasoning_log.append({"phase": "finding", "thought": f"✅ İlgili endpoint bulundu: {endpoint_info['method']} {endpoint_info['url']}"})

    def _intercept_with_logs_sync(self, context: ApiFinderContext) -> ApiFinderContext:
        """Ayrı bir thread'de çalışan, Selenium ve Performans Logları ile ağ trafiğini dinleyen ana fonksiyon."""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--log-level=3")
        
        # Performans loglarını etkinleştir
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        driver = None
        try:
            logger.info("ChromeDriver (Performans Logları için) otomatik olarak ayarlanıyor...")
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            context.ai_reasoning_log.append({"phase": "navigation", "thought": f"Hedef URL'e gidiliyor: {context.target_url}"})
            driver.get(context.target_url)

            context.ai_reasoning_log.append({"phase": "wait_for_activity", "thought": f"SPA aktivitesi ve API çağrıları için {context.wait_time} saniye bekleniyor..."})
            time.sleep(context.wait_time)
            
            context.ai_reasoning_log.append({"phase": "retrieving_logs", "thought": "Ağ aktivite logları tarayıcıdan alınıyor."})
            logs = driver.get_log('performance')
            
            self._process_performance_logs(logs, context)

            return context
        finally:
            if driver:
                driver.quit()
                logger.info("ChromeDriver kapatıldı.")
    
    # _build_final_json ve execute metodları önceki versiyon ile uyumlu, değişiklik gerekmiyor.
    def _build_final_json(self, context: ApiFinderContext, error: Exception = None) -> Dict[str, Any]:
        if error:
            error_message = f"{type(error).__name__}: {str(error)}"
            context.ai_reasoning_log.append({"phase": "critical_error", "thought": error_message})
            return {"success": False, "data": {}, "ai_summary": "API keşif aracı kritik bir hatayla karşılaştı.", "ai_reasoning": context.ai_reasoning_log, "recommendations": [], "error": error_message}
        
        summary = (f"Ağ trafiği analizi {time.time() - context.start_time:.2f} saniyede tamamlandı. "
                   f"{len(context.endpoints)} adet potansiyel API endpoint'i keşfedildi.")
        
        recommendations = []
        if context.endpoints:
            recommendations.append({
                "priority": "critical", "tool": "manual_analysis_burp",
                "reason": "Keşfedilen endpoint'ler, iş mantığı ve yetkilendirme hataları için Burp Suite ile manuel analiz edilmelidir.",
                "params": {"endpoints": [ep['url'] for ep in context.endpoints]}
            })
            post_endpoints = [ep for ep in context.endpoints if ep['method'] == 'POST' and ep['post_data']]
            if post_endpoints:
                recommendations.append({ "priority": "high", "tool": "api_vuln_idor_scanner",
                    "reason": f"{len(post_endpoints)} adet POST endpoint'i bulundu. IDOR zafiyetlerine karşı test edilmelidir.",
                    "params": {"endpoints": post_endpoints}})

        context.ai_reasoning_log.append({"phase": "complete", "thought": f"Analiz tamamlandı. {len(recommendations)} adet eylem önerisi oluşturuldu."})
        return {"success": True, "data": {"target_domain": context.target_domain, "discovered_endpoints": context.endpoints}, "ai_summary": summary, "ai_reasoning": context.ai_reasoning_log, "recommendations": recommendations, "error": None}

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        target_url = params.get("url")
        if not target_url: return self._build_final_json(ApiFinderContext("", "", 0), ValueError("URL parametresi zorunludur."))
        if not SELENIUM_AVAILABLE: return self._build_final_json(ApiFinderContext(target_url, "", 0), ImportError("Gerekli kütüphaneler bulunamadı. Lütfen 'pip install selenium webdriver-manager-core' komutunu çalıştırın."))
        if not target_url.startswith(('http://', 'https://')): target_url = 'https://' + target_url

        context = ApiFinderContext(target_url=target_url, target_domain=urlparse(target_url).netloc, wait_time=params.get("wait_time", 10))
        context.ai_reasoning_log.append({"phase": "initialization", "thought": f"Hedef {context.target_domain} için ağ trafiği analizi başlatılıyor (Motor: Selenium + Performans Logları)."})

        try:
            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                context = await loop.run_in_executor(pool, self._intercept_with_logs_sync, context)
            return self._build_final_json(context)
        except Exception as e:
            logger.error(f"Execute metodunda kritik hata: {repr(e)}", exc_info=True)
            return self._build_final_json(context, e)


# main fonksiyonu önceki versiyon ile uyumlu, değişiklik gerekmiyor.
async def main():
    parser = argparse.ArgumentParser(description="Pentagent API Endpoint Finder (v3 - Performans Logları).")
    parser.add_argument("url", help="Analiz edilecek web uygulamasının URL'i.")
    parser.add_argument("--wait-time", type=int, default=10, help="Sayfanın ağ aktivitesi oluşturması için beklenecek süre (saniye).")
    parser.add_argument("--json", action="store_true", help="Çıktıyı ham JSON formatında göster.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Detaylı (INFO seviyesi) logları göster.")
    args = parser.parse_args()

    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s', stream=sys.stderr)

    finder = ReconApiEndpointFinderTool()
    result = await finder.execute(vars(args))

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return
    
    print("\n" + "="*50 + "\n Pentagent API Endpoint Finder Raporu\n" + "="*50)
    if not result.get("success"):
        print(f"\n❌ HATA: Analiz Başarısız!\n   Sebep: {result.get('error')}")
    else:
        print(f"\n📊 ÖZET: {result.get('ai_summary')}\n")
        endpoints = result.get("data", {}).get("discovered_endpoints", [])
        if endpoints:
            print(f"🔍 Keşfedilen Endpoint'ler ({len(endpoints)} adet):")
            for ep in endpoints:
                print(f"  - {ep['method']} {ep['status_code']} {ep['url']}")
                if ep.get('post_data'):
                    print(f"    POST Data: {ep['post_data'][:100] if ep['post_data'] else 'N/A'}")
        else:
            print("🔍 Analiz sonucunda ilgili herhangi bir API endpoint'i bulunamadı.")
            
    recommendations = result.get("recommendations", [])
    if recommendations:
        print("\n💡 Eylem Önerileri:")
        for rec in recommendations: print(f"  - [{rec['priority'].upper()}] -> {rec['tool']}\n    Neden: {rec['reason']}")
    
    print("\n🤔 AI Düşünce Akışı:")
    for thought in result.get("ai_reasoning", []): print(f"   [{thought['phase']}] {thought['thought']}")
    
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())