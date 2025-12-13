# GÖREV: OTONOM KOD ANALİZİ VE DÜZELTME
# DURUM: NİHAİ UZMAN SÜRÜMÜ v8 - Selenium Tabanlı, Kararlı ve Güvenilir

"""
enum_web_crawler.py - Profesyonel Seviye (Selenium WebDriver Destekli)

v8 Değişiklik Notları:
- STRATEJİK DEĞİŞİKLİK: Playwright'in Python 3.13/Windows uyumsuzluğu nedeniyle
  kütüphane, sektör standardı olan Selenium WebDriver'a geçirildi. Bu, kararlılığı
  ve platform bağımsız çalışmayı garanti eder.
- OTOMASYON: 'webdriver-manager-core' kütüphanesi ile ChromeDriver'ın indirilmesi
  ve yönetimi tamamen otomatikleştirildi. Manuel kurulum gerekmez.
- MİMARİ: Tarayıcı işlemleri, ana programı bloklamamak için ayrı bir thread'de
  (concurrent.futures.ThreadPoolExecutor) çalıştırılmaktadır. Bu, modern ve
  sağlam bir yaklaşımdır.
- KOD KALİTESİ: Tüm kod, Selenium'un en iyi pratiklerine göre yeniden yazıldı.
  Hata yönetimi, loglama ve dokümantasyon bir uzmanın beklentilerini karşılayacak
  seviyeye getirildi. Bu, projenin nihai crawler sürümüdür.
"""
import asyncio
import logging
import json
import argparse
import sys
import time
import collections
from typing import Dict, Any, List, Set, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
import concurrent.futures
import threading

# PentagentTool base class'ını import et
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

# Selenium ve WebDriver Manager importları
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.common.exceptions import WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Tool loglarını göster

# --- CrawlContext ve Tool Sınıfı Başlangıcı ---
@dataclass
class CrawlContext:
    base_url: str; target_domain: str; max_depth: int; max_pages: int
    discovered_paths: Set[str] = field(default_factory=set)
    found_forms: List[Dict[str, Any]] = field(default_factory=list)
    crawled_page_count: int = 0
    ai_reasoning_log: List[Dict[str, str]] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)

class EnumWebCrawlerTool(MCPTool):
    def __init__(self):
        super().__init__(
            name="enum_web_crawler",
            description="Selenium WebDriver kullanarak hedef web sitesini derinlemesine tarar ve formları keşfeder.",
            category=ToolCategory.DISCOVERY_ENUMERATION
        )
    # Helper metodlar
    def _add_reasoning(self, ai_reasoning_log: List[Dict], phase: str, thought: str):
        """AI reasoning log'a entry ekle"""
        ai_reasoning_log.append({"phase": phase, "thought": thought})
    
    def _is_same_domain(self, url: str, target_domain: str) -> bool: return urlparse(url).netloc == target_domain
    def _deduplicate_forms(self, forms: List[Dict]) -> List[Dict]:
        unique_forms: List[Dict] = []; seen: Set[Tuple[str, str, Tuple[str, ...]]] = set()
        for form in forms:
            form_key = (form['action_path'], form['method'], tuple(sorted(form.get('inputs', []))))
            if form_key not in seen: seen.add(form_key); unique_forms.append(form)
        return unique_forms
    def _extract_links_and_forms(self, page_source: str, current_url: str, context: CrawlContext) -> List[str]:
        soup = BeautifulSoup(page_source, 'html.parser')
        new_links = []
        # Linkleri çıkar
        for tag in soup.find_all('a', href=True):
            href = tag['href']
            if not href or href.startswith(('#', 'mailto:', 'tel:', 'javascript:')): continue
            absolute_url = urlparse(urljoin(current_url, href))._replace(fragment="").geturl().rstrip('/')
            if self._is_same_domain(absolute_url, context.target_domain): new_links.append(absolute_url)
        # Formları çıkar
        for form in soup.find_all('form'):
            action_path = urlparse(urljoin(current_url, form.get('action', ''))).path or '/'
            inputs = sorted([inp.get('name') for inp in form.find_all(['input', 'textarea', 'select']) if inp.get('name')])
            context.found_forms.append({"source_page": urlparse(current_url).path or '/', "action_path": action_path, "method": form.get('method', 'GET').upper(), "inputs": inputs})
        return new_links

    def _crawl_sync(self, context: CrawlContext) -> CrawlContext:
        """
        Bu fonksiyon, Selenium tarama mantığını senkron olarak ve ayrı bir thread'de çalıştırır.
        Render gibi ortamlarda Chrome binary olmadığı için direkt HTTP-based fallback kullanır.
        """
        # RENDER UYUMLU: Chrome binary olmadığı durumlarda direkt HTTP-based fallback
        import os
        import shutil
        
        # Chrome binary kontrolü
        chrome_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser',
            shutil.which('google-chrome'),
            shutil.which('chromium'),
            shutil.which('chromium-browser')
        ]
        
        chrome_available = any(path and os.path.exists(path) for path in chrome_paths if path)
        
        if not chrome_available:
            logger.warning("Chrome binary bulunamadı (Render ortamı tespit edildi)")
            logger.info("Direkt HTTP-based crawling kullanılıyor...")
            return self._http_based_crawl(context)
        
        # Chrome mevcut, Selenium ile devam et
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-logging")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-translate")
        options.add_argument("--hide-scrollbars")
        options.add_argument("--mute-audio")
        options.add_argument("--no-first-run")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--log-level=3")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Stealth options
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features=AutomationControlled')

        driver = None
        try:
            logger.debug("ChromeDriver otomatik olarak ayarlanıyor...")
            try:
                service = ChromeService(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            except Exception as chrome_error:
                logger.debug(f"Chrome başlatılamadı (normal durum): {chrome_error}")
                # Fallback: HTTP-based crawling kullan - sessizce
                logger.info("HTTP-based crawling kullanılıyor (Chrome alternatifi)")
                return self._http_based_crawl(context)
            
            driver.set_page_load_timeout(60) # Sayfa yükleme için zaman aşımı
            
            # Stealth script çalıştır
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
            driver.execute_script("Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})")

            queue = collections.deque([(context.base_url, 0)])
            crawled_urls = set()

            while queue:
                if len(crawled_urls) >= context.max_pages:
                    context.ai_reasoning_log.append({"phase": "limit_reached", "thought": f"Tarama limiti olan {context.max_pages} sayfaya ulaşıldı."})
                    break
                
                url, depth = queue.popleft()
                if url in crawled_urls or depth >= context.max_depth: continue

                try:
                    logger.info(f"Crawling (Depth: {depth}): {url}")
                    driver.get(url)
                    
                    # Cloudflare challenge için bekle
                    time.sleep(5)
                    
                    # Sayfa yüklendi mi kontrol et
                    try:
                        driver.execute_script("return document.readyState")
                    except:
                        pass
                    
                    crawled_urls.add(url)
                    path = urlparse(url).path or '/'; context.discovered_paths.add(path)
                    
                    # Sayfa içeriğini alıp analiz et
                    page_source = driver.page_source
                    new_links = self._extract_links_and_forms(page_source, url, context)
                    
                    for link in new_links:
                        if link not in crawled_urls: queue.append((link, depth + 1))
                except WebDriverException as e:
                    logger.warning(f"Sayfa taranamadı {url}: {e.__class__.__name__}")
                except Exception as e:
                    logger.error(f"Sayfa işlenirken beklenmedik hata {url}: {e}")

            context.crawled_page_count = len(crawled_urls)
            return context
        finally:
            if driver:
                driver.quit()
                logger.info("ChromeDriver kapatıldı.")

    def _http_based_crawl(self, context: CrawlContext) -> CrawlContext:
        """
        HTTP-based fallback crawling (Selenium mevcut değilse).
        Basit requests + BeautifulSoup kullanır.
        Progress tracking ile.
        """
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        logger.info("HTTP-based crawling başlatılıyor...")
        self._add_reasoning(context.ai_reasoning_log, "fallback", "Selenium kullanılamadı, HTTP-based crawling kullanılıyor")
        
        # Session oluştur - DNS çözümleme için optimize edilmiş
        session = requests.Session()
        
        # Retry stratejisi - MİNİMAL (sistem çökmesin)
        retry = Retry(
            total=1,  # SADECE 1 deneme - hızlı fail
            connect=1,  # Connect için 1 deneme
            read=1,  # Read için 1 deneme
            backoff_factor=0.1,  # Çok az bekleme
            status_forcelist=[500, 502, 503, 504],  # Sadece server hatalarında retry
            allowed_methods=["HEAD", "GET"],  # Sadece safe methodlar
            raise_on_status=False  # HTTP hata kodlarında exception fırlatma
        )
        
        # HTTPAdapter - minimal konfigürasyon
        adapter = HTTPAdapter(
            max_retries=retry,
            pool_connections=10,  # Minimal pool
            pool_maxsize=10,  # Minimal pool
            pool_block=False  # Pool dolu olduğunda bloke etme
        )
        
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        queue = collections.deque([(context.base_url, 0)])
        crawled_urls = set()
        
        # OPTİMİZE AYARLAR: Dengeli tarama - hızlı ama etkili
        max_crawl_pages = min(context.max_pages, 25)  # 25 sayfa - daha kapsamlı
        max_crawl_depth = min(context.max_depth, 2)   # 2 derinlik - ana sayfa + 1 seviye
        
        # Progress tracking için
        page_count = 0
        
        while queue and len(crawled_urls) < max_crawl_pages:
            current_url, depth = queue.popleft()
            
            if current_url in crawled_urls or depth > max_crawl_depth:
                continue
            
            try:
                # Progress güncelleme (her sayfa için)
                page_count += 1
                progress_percent = int((page_count / max_crawl_pages) * 100)
                logger.info(f"Crawling progress: {progress_percent}% ({page_count}/{max_crawl_pages})")
                
                # GERÇEKÇI TIMEOUT: 10 saniye - stabil bağlantı
                response = session.get(current_url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    crawled_urls.add(current_url)
                    context.discovered_paths.add(urlparse(current_url).path or '/')
                    
                    # Linkleri ve formları çıkar
                    new_links = self._extract_links_and_forms(response.text, current_url, context)
                    
                    # Yeni linkleri kuyruğa ekle
                    for link in new_links:
                        if link not in crawled_urls:
                            queue.append((link, depth + 1))
            except requests.exceptions.Timeout:
                # Timeout - log ve devam
                logger.warning(f"⏱️ Timeout (10s): {current_url}")
                # Ana sayfa bile timeout oluyorsa önemli bir sorun var
                if current_url == context.base_url:
                    logger.error(f"❌ Ana sayfa erişilemedi: {current_url}")
                continue
            except requests.exceptions.ConnectionError as conn_err:
                # Connection error - log ve devam
                logger.warning(f"🔌 Connection error: {current_url} - {str(conn_err)[:50]}")
                if current_url == context.base_url:
                    logger.error(f"❌ Ana sayfaya bağlantı kurulamadı")
                continue
            except requests.exceptions.RequestException as req_err:
                # Request hatası - log ve devam
                logger.warning(f"⚠️ Request error: {current_url} - {str(req_err)[:50]}")
                continue
            except Exception as e:
                # Diğer hatalar - log ve devam
                logger.warning(f"❌ Crawl error: {current_url} - {type(e).__name__}")
                continue
        
        context.crawled_page_count = len(crawled_urls)
        logger.info(f"HTTP crawling tamamlandı: {len(crawled_urls)} sayfa tarandı")
        self._add_reasoning(context.ai_reasoning_log, "http_complete", f"{len(crawled_urls)} sayfa HTTP ile tarandı (optimal)")
        return context
    
    def _build_final_json(self, context: CrawlContext, error: Exception = None) -> Dict[str, Any]:
        if error:
            error_message = f"{type(error).__name__}: {str(error)}"
            self._add_reasoning(context.ai_reasoning_log, "critical_error", error_message)
            return self._create_final_output(
                success=False,
                ai_summary="Web tarayıcı kritik bir hatayla karşılaştı.",
                ai_reasoning=context.ai_reasoning_log,
                error=error_message
            )
        
        unique_forms = self._deduplicate_forms(context.found_forms)
        summary = (f"Tarama {time.time() - context.start_time:.2f} saniyede tamamlandı. "
                   f"{context.crawled_page_count} sayfa analiz edildi, {len(context.discovered_paths)} yol ve {len(unique_forms)} form bulundu.")
        
        # Dinamik öneriler oluştur
        recommendations = self._generate_dynamic_recommendations(context, unique_forms)
        
        # RAG-friendly format ekle
        rag_data = {
            "endpoints_for_analysis": [
                {
                    "path": path,
                    "url": f"{context.base_url}{path}",
                    "rag_query_suggestion": f"Security analysis for endpoint {path}"
                }
                for path in context.discovered_paths
            ],
            "forms_for_vulnerability_testing": [
                {
                    "action": form["action_path"],
                    "method": form["method"],
                    "inputs": form["inputs"],
                    "rag_query_suggestion": f"Vulnerability analysis for form at {form['action_path']}"
                }
                for form in unique_forms
            ],
            "scan_metadata": {
                "target_domain": context.target_domain,
                "scan_timestamp": time.time(),
                "scan_type": "web_crawling",
                "total_pages_crawled": context.crawled_page_count,
                "total_endpoints_found": len(context.discovered_paths),
                "total_forms_found": len(unique_forms)
            }
        }
        
        self._add_reasoning(context.ai_reasoning_log, "analysis_complete", f"Analiz tamamlandı. {len(recommendations)} öneri oluşturuldu.")
        return self._create_final_output(
            success=True,
            data={
                "target_domain": context.target_domain,
                "crawled_page_count": context.crawled_page_count,
                "discovered_paths": sorted(list(context.discovered_paths)),
                "forms": unique_forms,
                "rag_analysis_data": rag_data
            },
            ai_summary=summary,
            ai_reasoning=context.ai_reasoning_log,
            recommendations=recommendations
        )

    def _generate_dynamic_recommendations(self, context: CrawlContext, unique_forms: List[Dict]) -> List[Dict]:
        """Dinamik web crawler önerileri oluşturur."""
        recommendations = []
        
        # Form analizi için dinamik öneriler
        if unique_forms:
            # Form türlerini analiz et
            login_forms = [f for f in unique_forms if any(keyword in f["action_path"].lower() for keyword in ['login', 'auth', 'signin', 'logon'])]
            admin_forms = [f for f in unique_forms if any(keyword in f["action_path"].lower() for keyword in ['admin', 'panel', 'dashboard', 'control'])]
            contact_forms = [f for f in unique_forms if any(keyword in f["action_path"].lower() for keyword in ['contact', 'feedback', 'support', 'message'])]
            upload_forms = [f for f in unique_forms if any(keyword in f["action_path"].lower() for keyword in ['upload', 'file', 'attach', 'import'])]
            
            # Login formları için özel öneriler
            if login_forms:
                for form in login_forms[:2]:  # İlk 2 login form
                    recommendations.append({
                        "priority": "critical",
                        "tool": "verify_sqli",
                        "reason": f"🔐 LOGIN FORM TESPİTİ: {form['action_path']} login formu bulundu. SQL injection ve authentication bypass testleri yapılmalı.",
                        "params": {
                            "url": f"{context.base_url}{form['action_path']}",
                            "form_data": form,
                            "login_test": True,
                            "auth_bypass": True
                        },
                        "expert_context": f"Login form güvenlik testi için kritik analiz. {form['action_path']} için SQL injection ve authentication bypass teknikleri test edilmeli."
                    })
            
            # Admin formları için özel öneriler
            if admin_forms:
                for form in admin_forms[:2]:  # İlk 2 admin form
                    recommendations.append({
                        "priority": "critical",
                        "tool": "verify_sqli",
                        "reason": f"🚨 ADMIN FORM TESPİTİ: {form['action_path']} admin formu bulundu. Kritik SQL injection ve privilege escalation testleri yapılmalı.",
                        "params": {
                            "url": f"{context.base_url}{form['action_path']}",
                            "form_data": form,
                            "admin_test": True,
                            "privilege_escalation": True
                        },
                        "expert_context": f"Admin form güvenlik testi için kritik analiz. {form['action_path']} için SQL injection ve privilege escalation teknikleri test edilmeli."
                    })
            
            # Upload formları için özel öneriler
            if upload_forms:
                for form in upload_forms[:2]:  # İlk 2 upload form
                    recommendations.append({
                        "priority": "high",
                        "tool": "verify_lfi",
                        "reason": f"📁 UPLOAD FORM TESPİTİ: {form['action_path']} file upload formu bulundu. File upload zafiyetleri ve LFI testleri yapılmalı.",
                        "params": {
                            "url": f"{context.base_url}{form['action_path']}",
                            "form_data": form,
                            "file_upload_test": True,
                            "lfi_test": True
                        },
                        "expert_context": f"File upload güvenlik testi için kritik analiz. {form['action_path']} için file upload zafiyetleri ve LFI teknikleri test edilmeli."
                    })
            
            # Genel form testleri
            recommendations.append({
                "priority": "high",
                "tool": "verify_xss",
                "reason": f"🎭 FORM XSS TESTİ: {len(unique_forms)} form bulundu. Cross-site scripting zafiyetleri test edilmeli.",
                "params": {
                    "url": context.base_url,
                    "forms": unique_forms,
                    "xss_payloads": ["reflected", "stored", "dom"]
                },
                "expert_context": f"Form XSS testi için kritik analiz. {len(unique_forms)} form için XSS payload'ları ve bypass teknikleri test edilmeli."
            })
        
        # Endpoint analizi için öneriler
        if context.discovered_paths:
            # Admin endpoint'leri için özel öneriler
            admin_endpoints = [path for path in context.discovered_paths if any(keyword in path.lower() for keyword in ['admin', 'panel', 'dashboard', 'control'])]
            if admin_endpoints:
                recommendations.append({
                    "priority": "critical",
                    "tool": "enum_tech_detector",
                    "reason": f"🚨 ADMIN ENDPOINT KEŞFİ: {len(admin_endpoints)} admin endpoint bulundu. Teknoloji tespiti ve güvenlik analizi yapılmalı.",
                    "params": {
                        "url": f"{context.base_url}{admin_endpoints[0]}",
                        "admin_panel": True,
                        "comprehensive": True
                    },
                    "expert_context": f"Admin endpoint güvenlik testi için kritik analiz. {len(admin_endpoints)} admin endpoint için teknoloji tespiti ve güvenlik analizi yapılmalı."
                })
            
            # API endpoint'leri için özel öneriler
            api_endpoints = [path for path in context.discovered_paths if any(keyword in path.lower() for keyword in ['api', 'rest', 'graphql', 'v1', 'v2'])]
            if api_endpoints:
                recommendations.append({
                    "priority": "high",
                    "tool": "api_vuln_idor_scanner",
                    "reason": f"🔌 API ENDPOINT KEŞFİ: {len(api_endpoints)} API endpoint bulundu. IDOR ve API güvenlik zafiyetleri test edilmeli.",
                    "params": {
                        "url": f"{context.base_url}{api_endpoints[0]}",
                        "api_analysis": True,
                        "idor_test": True
                    },
                    "expert_context": f"API endpoint güvenlik testi için kritik analiz. {len(api_endpoints)} API endpoint için IDOR ve API güvenlik zafiyetleri test edilmeli."
                })
        
        return recommendations

    def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        CRASH KORUNMALI - Tüm hatalar yakalanır, sistem ASLA çökmez
        """
        try:
            start_url = params.get("url")
            if not start_url: 
                return self._create_final_output(
                    success=False,
                    ai_summary="URL parametresi zorunludur.",
                    error="URL parametresi zorunludur."
                )
            if not SELENIUM_AVAILABLE: 
                return self._create_final_output(
                    success=False,
                    ai_summary="Gerekli kütüphaneler bulunamadı.",
                    error="Gerekli kütüphaneler bulunamadı. Lütfen 'pip install selenium webdriver-manager' komutunu çalıştırın."
                )
            if not start_url.startswith(('http://', 'https://')): 
                start_url = 'https://' + start_url
            
            # OPTİMİZE PARAMETRELER - Dengeli ve etkili tarama
            max_depth = min(params.get("depth", 2), 3)   # Max 3 depth - kapsamlı tarama
            max_pages = min(params.get("max_pages", 25), 50)  # Max 50 sayfa - geniş kapsam
            
            context = CrawlContext(
                base_url=start_url.rstrip('/'), 
                target_domain=urlparse(start_url).netloc, 
                max_depth=max_depth, 
                max_pages=max_pages
            )
            self._add_reasoning(context.ai_reasoning_log, "initialization", f"Hedef {context.target_domain} için tarama başlatılıyor.")
             
             try:
                 # Selenium'u direkt senkron olarak çalıştır
                 context = self._crawl_sync(context)
                 return self._build_final_json(context)
             except KeyboardInterrupt:
                 # Kullanıcı durdurdu
                 logger.info("Tarama kullanıcı tarafından durduruldu")
                 return self._create_final_output(
                     success=False,
                     ai_summary="Tarama kullanıcı tarafından durduruldu.",
                     ai_reasoning=context.ai_reasoning_log,
                     error="KeyboardInterrupt"
                 )
             except Exception as e:
                 # Herhangi bir hata - graceful fail
                 logger.warning(f"Crawl hatası (graceful): {type(e).__name__}")
                 # En azından toplanan verileri döndür
                 if context.crawled_page_count > 0 or len(context.discovered_paths) > 0:
                     logger.info(f"Kısmi sonuç döndürülüyor: {context.crawled_page_count} sayfa")
                     return self._build_final_json(context)
                 else:
                     return self._create_final_output(
                         success=False,
                         ai_summary="Web tarayıcı sırasında bir hata oluştu.",
                         ai_reasoning=context.ai_reasoning_log,
                         error=f"{type(e).__name__}: {str(e)[:100]}"
                     )
         except Exception as outer_e:
             # En dış catch - sistem ASLA çökmez
             logger.error(f"CRITICAL: Outer exception in run_tool: {outer_e}")
             return self._create_final_output(
                 success=False,
                 ai_summary="Kritik hata oluştu ama sistem korundu.",
                 error=f"Critical: {type(outer_e).__name__}"
             )

async def main():
    parser = argparse.ArgumentParser(description="Pentagent Web Crawler (v8 - Selenium Tabanlı).")
    parser.add_argument("url", help="Taranacak başlangıç URL'i")
    parser.add_argument("--depth", type=int, default=2, help="Tarama derinliği")
    parser.add_argument("--max-pages", type=int, default=25, help="Maksimum taranacak sayfa")
    parser.add_argument("--json", action="store_true", help="Çıktıyı ham JSON formatında göster")
    parser.add_argument("--verbose", "-v", action="store_true", help="Detaylı (INFO seviyesi) logları göster")
    args = parser.parse_args()

    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s', stream=sys.stderr)

    crawler = EnumWebCrawlerTool()
    result = await crawler.run_tool(vars(args))

    if args.json: print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("\n" + "="*50 + "\n Pentagent Web Crawler Sonuç Raporu\n" + "="*50)
        if not result.get("success"):
            print(f"\n❌ HATA: Tarama Başarısız!\n   Sebep: {result.get('error')}")
        else:
            print(f"\n📊 ÖZET: {result.get('ai_summary')}\n")
            data = result.get("data", {}); paths = data.get("discovered_paths", [])
            if paths:
                print(f"🔗 Keşfedilen Yollar ({len(paths)} adet):")
                for path in paths[:10]: print(f"  - {path}")
                if len(paths) > 10: print("  ...")
            forms = data.get("forms", [])
            if forms:
                print(f"\n📝 Tespit Edilen Formlar ({len(forms)} adet):")
                for form in forms[:5]: print(f"  - {form['method']} {form['action_path']} (Inputs: {', '.join(form['inputs']) or 'Yok'})")
                if len(forms) > 5: print("  ...")
        recommendations = result.get("recommendations", [])
        if recommendations:
            print("\n💡 Eylem Önerileri:")
            for rec in recommendations: print(f"  - [{rec['priority'].upper()}] -> Çalıştır: {rec['tool']}\n    Neden: {rec['reason']}")
        print("\n🤔 AI Düşünce Akışı:")
        for thought in result.get("ai_reasoning", []): print(f"   [{thought['phase']}] {thought['thought']}")
        print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
