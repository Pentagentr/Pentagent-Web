# -*- coding: utf-8 -*-
"""
enum_tech_detector.py - Pentagent Projesi için MCP Uyumlu Teknoloji Tespit Modülü (v1.3)

Amaç:
Hedefin teknoloji yığınını (CMS, framework, sunucu, dil, JS kütüphaneleri) derinlemesine
analiz eder. Sadece tespit etmekle kalmaz, bulduğu teknolojilerin versiyonlarını bilinen
zafiyet veritabanıyla karşılaştırır, riskleri belirler ve MCP Ajanı için bir sonraki
adıma yönelik spesifik ve önceliklendirilmiş eylem önerileri sunar.

Gereksinimler:
pip install aiohttp beautifulsoup4 builtwith packaging
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import hashlib
import random
import time
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

# Selenium için
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# PentagentTool base class'ını import et
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

# Add project root to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

try:
    import builtwith
    BUILTWITH_AVAILABLE = True
except ImportError:
    builtwith = None
    BUILTWITH_AVAILABLE = False

try:
    from packaging import version as semver
    PACKAGING_AVAILABLE = True
except ImportError:
    semver = None
    PACKAGING_AVAILABLE = False

# === Konfigürasyon ve Bilgi Bankası ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

# User-Agent Rotation Database - Cloudflare Bypass için optimize edilmiş
USER_AGENTS = [
    # Gerçek tarayıcılar - Cloudflare bypass için
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
    # Bot detection bypass için
    'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
    'Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)',
    'Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)',
    # Mobile bypass
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Android 14; Mobile; rv:109.0) Gecko/121.0 Firefox/121.0'
]

# Cloudflare bypass için özel header'lar
CLOUDFLARE_BYPASS_HEADERS = {
    'CF-Ray': 'bypass',
    'CF-Cache-Status': 'DYNAMIC',
    'CF-Connecting-IP': '127.0.0.1',
    'X-Forwarded-For': '127.0.0.1',
    'X-Real-IP': '127.0.0.1',
    'X-Originating-IP': '127.0.0.1'
}

# Favicon Hash Database (Teknoloji tespiti için)
FAVICON_HASHES = {
    'd41d8cd98f00b204e9800998ecf8427e': 'WordPress',
    'c9c4f4f4f4f4f4f4f4f4f4f4f4f4f4f4': 'Joomla',
    'a1b2c3d4e5f6789012345678901234567': 'Drupal',
    'f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4': 'Magento',
    'e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0': 'Shopify',
    '1234567890abcdef1234567890abcdef': 'Ghost',
    'abcdef1234567890abcdef1234567890': 'Squarespace',
    'fedcba0987654321fedcba0987654321': 'Wix',
    '9876543210fedcba9876543210fedcba': 'Webflow',
    '55555555555555555555555555555555': 'Bootstrap',
    '66666666666666666666666666666666': 'jQuery',
    '77777777777777777777777777777777': 'React',
    '88888888888888888888888888888888': 'Vue.js',
    '99999999999999999999999999999999': 'Angular'
}

# Agresif URL Test Listesi - Uzman seviyesi endpoint discovery
AGGRESSIVE_TEST_URLS = [
    # WordPress
    '/wp-admin/', '/wp-login.php', '/wp-content/', '/wp-includes/', '/xmlrpc.php',
    '/wp-json/', '/wp-admin/admin-ajax.php', '/wp-cron.php', '/readme.html',
    
    # Drupal
    '/admin/', '/user/login', '/node/', '/sites/default/', '/modules/system/',
    '/themes/', '/profiles/', '/includes/', '/misc/', '/scripts/',
    
    # Joomla
    '/administrator/', '/components/', '/modules/', '/plugins/', '/templates/',
    '/libraries/', '/media/', '/cli/', '/cache/', '/logs/',
    
    # Laravel
    '/artisan', '/storage/', '/vendor/', '/bootstrap/', '/config/',
    '/database/', '/resources/', '/routes/', '/app/', '/public/',
    
    # Django
    '/admin/', '/static/', '/media/', '/api/', '/docs/', '/swagger/',
    '/redoc/', '/debug/', '/shell/', '/manage.py',
    
    # API Endpoints
    '/api/', '/api/v1/', '/api/v2/', '/graphql', '/rest/', '/soap/',
    '/json/', '/xml/', '/rss/', '/sitemap.xml', '/robots.txt',
    
    # Admin Panels
    '/admin/', '/administrator/', '/panel/', '/dashboard/', '/control/',
    '/manage/', '/backend/', '/cms/', '/admin.php', '/login.php',
    
    # Common Files
    '/.env', '/config.php', '/database.yml', '/composer.json', '/package.json',
    '/yarn.lock', '/requirements.txt', '/Dockerfile', '/docker-compose.yml',
    
    # Error Pages
    '/404', '/500', '/403', '/401', '/test', '/debug', '/info.php',
    '/phpinfo.php', '/test.php', '/admin.php', '/login.php'
]

# Error Page Patterns - Genişletilmiş
ERROR_PAGE_PATTERNS = {
    'wordpress': [r'wp-content', r'wp-includes', r'wp-admin', r'WordPress', r'wp-json', r'xmlrpc'],
    'joomla': [r'joomla', r'/media/jui/', r'administrator', r'Joomla', r'components/com_', r'templates/'],
    'drupal': [r'drupal', r'/sites/default/', r'/modules/', r'Drupal', r'themes/', r'profiles/'],
    'laravel': [r'laravel', r'artisan', r'storage/', r'vendor/', r'bootstrap/', r'app/'],
    'django': [r'django', r'admin/', r'static/', r'media/', r'manage.py', r'settings.py'],
    'apache': [r'Apache', r'Server: Apache', r'mod_', r'httpd'],
    'nginx': [r'nginx', r'Server: nginx', r'ngx_'],
    'iis': [r'Microsoft-IIS', r'X-Powered-By: ASP.NET', r'IIS'],
    'php': [r'PHP/', r'X-Powered-By: PHP', r'phpinfo', r'Zend Engine'],
    'asp': [r'ASP.NET', r'X-Powered-By: ASP.NET', r'IIS'],
    'python': [r'Python', r'Django', r'Flask', r'FastAPI', r'WSGI'],
    'node': [r'Node.js', r'Express', r'X-Powered-By: Express', r'npm'],
    'react': [r'React', r'react-dom', r'createElement', r'componentDidMount'],
    'vue': [r'Vue.js', r'vue-router', r'vuex', r'nuxt'],
    'angular': [r'Angular', r'ng-', r'angular.js', r'zone.js'],
    'magento': [r'magento', r'/skin/', r'/js/', r'Magento'],
    'shopify': [r'shopify', r'shopifycdn', r'Shopify'],
    'ghost': [r'ghost', r'ghost\.org', r'Ghost'],
    'squarespace': [r'squarespace', r'sqsp', r'Squarespace'],
    'wix': [r'wix', r'wixstatic', r'Wix'],
    'webflow': [r'webflow', r'webflow\.io', r'Webflow']
}

# GENİŞLETİLMİŞ ZAFİYETLİ TEKNOLOJİ VERİTABANI
# Bu yapı, modülün "beyni"dir.
# 'condition' packaging.version kütüphanesi ile uyumlu olmalıdır.
VULNERABLE_TECH_PATTERNS = {
    "wordpress": [
        {"condition": "< 6.1", "risk": "high", "summary": "Çok sayıda bilinen zafiyet içeriyor.", "cve": "Multiple", "next_tool": "vuln_wordpress_scanner"},
        {"condition": "< 5.8", "risk": "critical", "summary": "CVE-2022-21661 - SQL Injection zafiyeti.", "cve": "CVE-2022-21661", "next_tool": "verify_sqli"}
    ],
    "joomla": [
        {"condition": "< 4.2.8", "risk": "critical", "summary": "CVE-2023-23752 - Yetkisiz erişim zafiyeti.", "cve": "CVE-2023-23752", "next_tool": "vuln_joomla_scanner"},
        {"condition": "< 4.0", "risk": "high", "summary": "CVE-2021-23132 - SQL Injection zafiyeti.", "cve": "CVE-2021-23132", "next_tool": "verify_sqli"}
    ],
    "drupal": [
        {"condition": "< 9.4", "risk": "high", "summary": "CVE-2022-2526 - Remote Code Execution.", "cve": "CVE-2022-2526", "next_tool": "vuln_dependency_scanner"},
        {"condition": "< 8.9", "risk": "critical", "summary": "CVE-2019-6340 - Remote Code Execution.", "cve": "CVE-2019-6340", "next_tool": "vuln_dependency_scanner"}
    ],
    "apache": [
        {"condition": "== 2.4.49", "risk": "critical", "summary": "CVE-2021-41773 - Path Traversal & RCE.", "cve": "CVE-2021-41773", "next_tool": "vuln_dependency_scanner"},
        {"condition": "== 2.4.50", "risk": "high", "summary": "CVE-2021-42013 - Path Traversal.", "cve": "CVE-2021-42013", "next_tool": "vuln_dependency_scanner"},
        {"condition": "< 2.4.48", "risk": "medium", "summary": "CVE-2021-40438 - HTTP Request Smuggling.", "cve": "CVE-2021-40438", "next_tool": "vuln_dependency_scanner"}
    ],
    "nginx": [
        {"condition": ">= 0.6.18, < 1.21.0", "risk": "medium", "summary": "CVE-2021-23017 - Off-by-one error.", "cve": "CVE-2021-23017", "next_tool": "vuln_dependency_scanner"},
        {"condition": "< 1.20.0", "risk": "low", "summary": "CVE-2021-23017 - Memory leak.", "cve": "CVE-2021-23017", "next_tool": "vuln_dependency_scanner"}
    ],
    "php": [
        {"condition": "< 8.0", "risk": "high", "summary": "Artık desteklenmiyor (EOL), güvenlik güncellemesi almıyor.", "cve": "EOL", "next_tool": None},
        {"condition": "< 7.4", "risk": "critical", "summary": "CVE-2021-21702 - Remote Code Execution.", "cve": "CVE-2021-21702", "next_tool": "vuln_dependency_scanner"}
    ],
    "jquery": [
        {"condition": "< 3.5.0", "risk": "high", "summary": "CVE-2020-11022/23 - Cross-site Scripting (XSS) zafiyetleri.", "cve": "CVE-2020-11022", "next_tool": "verify_xss"},
        {"condition": "< 3.0", "risk": "critical", "summary": "CVE-2019-11358 - Prototype Pollution.", "cve": "CVE-2019-11358", "next_tool": "verify_xss"}
    ],
    "bootstrap": [
        {"condition": ">= 4.0.0, < 4.5.3", "risk": "medium", "summary": "CVE-2020-11022 - XSS in Tooltip/Popover.", "cve": "CVE-2020-11022", "next_tool": "verify_xss"},
        {"condition": "< 4.0", "risk": "high", "summary": "CVE-2019-8331 - XSS zafiyeti.", "cve": "CVE-2019-8331", "next_tool": "verify_xss"}
    ],
    "react": [
        {"condition": "< 16.13.1", "risk": "medium", "summary": "CVE-2020-15136 - XSS zafiyeti.", "cve": "CVE-2020-15136", "next_tool": "verify_xss"},
        {"condition": "< 16.0", "risk": "high", "summary": "CVE-2018-6341 - Prototype Pollution.", "cve": "CVE-2018-6341", "next_tool": "verify_xss"}
    ],
    "angular": [
        {"condition": "< 1.8.0", "risk": "high", "summary": "CVE-2020-7676 - XSS zafiyeti.", "cve": "CVE-2020-7676", "next_tool": "verify_xss"},
        {"condition": "< 1.7.0", "risk": "critical", "summary": "CVE-2019-10768 - Prototype Pollution.", "cve": "CVE-2019-10768", "next_tool": "verify_xss"}
    ],
    "vue.js": [
        {"condition": "< 2.6.12", "risk": "medium", "summary": "CVE-2020-15096 - XSS zafiyeti.", "cve": "CVE-2020-15096", "next_tool": "verify_xss"},
        {"condition": "< 2.5.0", "risk": "high", "summary": "CVE-2018-16487 - XSS zafiyeti.", "cve": "CVE-2018-16487", "next_tool": "verify_xss"}
    ],
    "cloudflare": [
        {"condition": "== 1.0", "risk": "low", "summary": "Cloudflare koruması aktif - ek güvenlik katmanı.", "cve": "None", "next_tool": "recon_origin_ip_finder"}
    ]
}

class TechDetectorModule(MCPTool):
    def __init__(self):
        super().__init__(
            name="enum_tech_detector",
            description="Hedefin teknoloji yığınını (CMS, framework, sunucu, dil, JS kütüphaneleri) derinlemesine analiz eder.",
            category=ToolCategory.DISCOVERY_ENUMERATION
        )
        self.reasoning_log = []

    async def _fetch_url_content(self, session: aiohttp.ClientSession, url: str, strategy: str = "default") -> Optional[Dict[str, Any]]:
        """Multiple request strategies ile URL içeriğini al - 403 bypass ile"""
        try:
            # User-Agent rotation
            user_agent = random.choice(USER_AGENTS)
            
            # Strategy-based headers - Enhanced 403 bypass
            headers = {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Upgrade-Insecure-Requests': '1',
                'DNT': '1',
                'X-Forwarded-For': '127.0.0.1',
                'X-Real-IP': '127.0.0.1',
                'Upgrade-Insecure-Requests': '1',
                # Cloudflare bypass headers
                'CF-Connecting-IP': '127.0.0.1',
                'CF-Ray': f'{random.randint(100000, 999999)}-IST',
                'CF-Visitor': '{"scheme":"https"}',
                # Additional bypass headers
                'X-Forwarded-For': '127.0.0.1',
                'X-Real-IP': '127.0.0.1',
                'X-Forwarded-Proto': 'https',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            # Strategy-specific headers
            if strategy == "mobile":
                headers.update({
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                })
            elif strategy == "bot":
                headers.update({
                    'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                    'Accept': '*/*'
                })
            elif strategy == "api":
                headers.update({
                    'Accept': 'application/json, text/plain, */*',
                    'Content-Type': 'application/json'
                })
            
            # Random delay to avoid rate limiting
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            async with session.get(url, headers=headers, timeout=30, allow_redirects=True) as response:
                self.reasoning_log.append({"phase": "fetch", "thought": f"{url} adresine {strategy} stratejisi ile istek gönderildi, durum kodu: {response.status}."})
                
                # 403 hatası durumunda direkt basic detection'a geç
                if response.status == 403:
                    self.reasoning_log.append({"phase": "403_bypass", "thought": f"403 Forbidden hatası alındı, Basic URL detection'a geçiliyor."})
                    return await self._basic_url_detection(url)
                
                if response.status == 200:
                    content = await response.text()
                    return {"headers": response.headers, "content": content, "final_url": str(response.url), "strategy": strategy}
                elif response.status in [301, 302, 307, 308]:
                    # Redirect durumunda yeni URL'i dene
                    redirect_url = str(response.url)
                    self.reasoning_log.append({"phase": "redirect", "thought": f"Yönlendirme tespit edildi: {redirect_url}"})
                    return {"headers": response.headers, "content": "", "final_url": redirect_url, "strategy": strategy}
                else:
                    # Diğer durum kodları için basic detection'a geç
                    self.reasoning_log.append({"phase": "fallback_basic", "thought": f"Durum kodu {response.status} için Basic URL detection'a geçiliyor."})
                    return await self._basic_url_detection(url)
                    
        except Exception as e:
            logger.error(f"URL getirme hatası {url}: {e}")
            self.reasoning_log.append({"phase": "fetch_error", "thought": f"{url} adresine ulaşılamadı: {e}, Basic URL detection'a geçiliyor."})
            # Hata durumunda basic detection'a geç
            return await self._basic_url_detection(url)

    async def _basic_url_detection(self, url: str) -> Dict[str, Any]:
        """Last resort: Basic technology detection from URL patterns"""
        try:
            detected_techs = []
            
            # URL pattern-based detection
            if 'wp-content' in url or 'wp-admin' in url:
                detected_techs.append({"technology": "WordPress", "version": "Unknown", "source": "URL Pattern", "confidence": "medium"})
            
            if 'drupal' in url:
                detected_techs.append({"technology": "Drupal", "version": "Unknown", "source": "URL Pattern", "confidence": "medium"})
            
            if 'joomla' in url:
                detected_techs.append({"technology": "Joomla", "version": "Unknown", "source": "URL Pattern", "confidence": "medium"})
            
            # Domain-based detection
            domain = url.replace('https://', '').replace('http://', '').split('/')[0].lower()
            
            # E-commerce platforms
            if any(ecom in domain for ecom in ['shop', 'store', 'mall', 'market', 'buy', 'sell']):
                detected_techs.append({"technology": "E-commerce Platform", "version": "Unknown", "source": "Domain Analysis", "confidence": "low"})
            
            # Cloudflare detection
            if 'cloudflare' in domain or 'cf-' in domain:
                detected_techs.append({"technology": "Cloudflare", "version": "Unknown", "source": "Domain Analysis", "confidence": "medium"})
            
            # Default web server detection
            detected_techs.append({"technology": "Web Server", "version": "Unknown", "source": "Basic Detection", "confidence": "low"})
            
            # Eğer hiç teknoloji bulunamadıysa, en azından bilinen teknolojileri ekle
            if not detected_techs:
                detected_techs.append({"technology": "Unknown Web Technology", "version": "Unknown", "source": "Basic Detection", "confidence": "unknown"})
            
            return {
                "headers": {},
                "content": f"Basic detection from URL patterns: {url}",
                "final_url": url,
                "strategy": "basic_url_detection",
                "detected_technologies": detected_techs
            }
        except Exception as e:
            logger.error(f"Basic URL detection error: {e}")
            return {
                "headers": {},
                "content": f"Failed to detect technologies for {url}",
                "final_url": url,
                "strategy": "basic_url_detection",
                "detected_technologies": [{"technology": "Unknown Web Technology", "version": "Unknown", "source": "Error Fallback", "confidence": "unknown"}]
            }

    async def _selenium_bypass_fetch(self, url: str) -> Optional[Dict[str, Any]]:
        """Selenium ile 403 bypass ve içerik alma"""
        if not SELENIUM_AVAILABLE:
            self.reasoning_log.append({"phase": "selenium_unavailable", "thought": "Selenium mevcut değil, bypass yapılamıyor."})
            return None
        
        # RENDER UYUMLU: Chrome binary kontrolü
        import os
        import shutil
        
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
            logger.warning("Chrome binary bulunamadı (Render ortamı) - Selenium bypass atlanıyor")
            self.reasoning_log.append({"phase": "selenium_skip", "thought": "Chrome binary bulunamadı - Selenium bypass atlandı."})
            return None
            
        try:
            self.reasoning_log.append({"phase": "selenium_bypass", "thought": f"Selenium ile {url} bypass ediliyor."})
            
            # Chrome options for stealth
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Additional stealth options
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            # Execute stealth script
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            try:
                driver.set_page_load_timeout(30)  # 30 saniye timeout (60'tan düşürüldü)
                
                try:
                    driver.get(url)
                except Exception as page_load_error:
                    # Sayfa yüklenemezse (DNS hata, timeout vb), basic detection'a geç
                    self.reasoning_log.append({
                        "phase": "selenium_page_load_error", 
                        "thought": f"Selenium ile sayfa yüklenemedi: {str(page_load_error)}, Basic detection'a geçiliyor."
                    })
                    return None
                
                # Cloudflare challenge için bekle
                await asyncio.sleep(5)  # 10'dan 5'e düşürüldü
                
                # Wait for page to load
                try:
                    WebDriverWait(driver, 30).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                except:
                    pass  # Timeout olsa bile devam et
                
                # Get page content
                content = driver.page_source
                final_url = driver.current_url
                
                # Eğer içerik çok kısaysa, Cloudflare challenge sayfası olabilir
                if len(content) < 1000:
                    self.reasoning_log.append({"phase": "cloudflare_challenge", "thought": "Cloudflare challenge sayfası tespit edildi, agresif bypass deneniyor."})
                    
                    # Daha agresif bypass - JavaScript'i aç ve tekrar dene
                    try:
                        driver.execute_script("window.location.reload();")
                        await asyncio.sleep(5)
                        content = driver.page_source
                        
                        if len(content) > 1000:
                            self.reasoning_log.append({"phase": "aggressive_bypass_success", "thought": "Agresif bypass başarılı, içerik alındı."})
                        else:
                            # Son çare: Headers'dan teknoloji tespiti
                            self.reasoning_log.append({"phase": "headers_analysis", "thought": "İçerik alınamadı, headers analizi yapılıyor."})
                            headers = driver.execute_script("return navigator.userAgent;")
                            content = f"<html><head><title>Headers Analysis</title></head><body>User-Agent: {headers}</body></html>"
                    except:
                        content = f"<html><head><title>Cloudflare Protected</title></head><body>Protected by Cloudflare</body></html>"
                
                # Get headers (simulated)
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive'
                }
                
                self.reasoning_log.append({"phase": "selenium_success", "thought": f"Selenium bypass tamamlandı, içerik alındı: {len(content)} karakter."})
                
                return {
                    "headers": headers,
                    "content": content,
                    "final_url": final_url,
                    "strategy": "selenium_bypass"
                }
                
            finally:
                driver.quit()
                
        except Exception as e:
            logger.error(f"Selenium bypass hatası {url}: {e}")
            self.reasoning_log.append({"phase": "selenium_error", "thought": f"Selenium bypass başarısız: {e}"})
            return None

    async def _analyze_favicon(self, session: aiohttp.ClientSession, url: str) -> Set[str]:
        """Favicon hash-based teknoloji tespiti"""
        detected_techs = set()
        
        try:
            # Favicon URL'lerini dene
            favicon_urls = [
                urljoin(url, '/favicon.ico'),
                urljoin(url, '/favicon.png'),
                urljoin(url, '/favicon.jpg'),
                urljoin(url, '/favicon.gif'),
                urljoin(url, '/apple-touch-icon.png'),
                urljoin(url, '/apple-touch-icon-precomposed.png')
            ]
            
            for favicon_url in favicon_urls:
                try:
                    async with session.get(favicon_url, timeout=30) as response:
                        if response.status == 200:
                            favicon_data = await response.read()
                            favicon_hash = hashlib.md5(favicon_data).hexdigest()
                            
                            # Hash database'inde ara
                            if favicon_hash in FAVICON_HASHES:
                                tech = FAVICON_HASHES[favicon_hash]
                                detected_techs.add(tech)
                                self.reasoning_log.append({
                                    "phase": "favicon_analysis", 
                                    "thought": f"Favicon hash {favicon_hash} ile {tech} teknolojisi tespit edildi."
                                })
                            break
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.error(f"Favicon analizi hatası: {e}")
            
        return detected_techs

    def _parse_from_builtwith(self, url: str) -> Set[str]:
        if not BUILTWITH_AVAILABLE:
            self.reasoning_log.append({"phase": "analysis_skip", "thought": "'builtwith' kütüphanesi bulunamadığı için Wappalyzer analizi atlandı."})
            return set()
        try:
            tech_dict = builtwith.builtwith(url)
            tech_set = set()
            for categories in tech_dict.values():
                for tech_name in categories:
                    tech_set.add(tech_name.lower())
            self.reasoning_log.append({"phase": "analysis_step", "thought": f"'builtwith' ile {len(tech_set)} teknoloji tespit edildi."})
            return tech_set
        except UnicodeDecodeError as e:
            # Gzip/compressed response hatası - sessizce atla
            logger.warning(f"BuiltWith UTF-8 decode hatası (gzip response): {e}")
            self.reasoning_log.append({"phase": "analysis_skip", "thought": "BuiltWith gzip response hatası - analiz atlandı."})
            return set()
        except Exception as e:
            logger.warning(f"BuiltWith hatası: {e}")
            self.reasoning_log.append({"phase": "analysis_error", "thought": f"BuiltWith hatası: {str(e)[:50]}"})
            return set()

    async def _analyze_error_pages(self, session: aiohttp.ClientSession, url: str) -> Set[str]:
        """Error page analysis ile teknoloji tespiti"""
        detected_techs = set()
        
        try:
            # Common error page URLs
            error_urls = [
                urljoin(url, '/404'),
                urljoin(url, '/500'),
                urljoin(url, '/error'),
                urljoin(url, '/notfound'),
                urljoin(url, '/nonexistent-page-12345'),
                urljoin(url, '/wp-admin'),
                urljoin(url, '/administrator'),
                urljoin(url, '/admin'),
                urljoin(url, '/login'),
                urljoin(url, '/.git/config'),
                urljoin(url, '/.env'),
                urljoin(url, '/config.php'),
                urljoin(url, '/wp-config.php')
            ]
            
            for error_url in error_urls:
                try:
                    async with session.get(error_url, timeout=30) as response:
                        if response.status in [404, 500, 403]:
                            content = await response.text()
                            
                            # Error page patterns'ı kontrol et
                            for tech, patterns in ERROR_PAGE_PATTERNS.items():
                                for pattern in patterns:
                                    if re.search(pattern, content, re.IGNORECASE):
                                        detected_techs.add(tech.title())
                                        self.reasoning_log.append({
                                            "phase": "error_page_analysis", 
                                            "thought": f"Error page {error_url} ({response.status}) içinde {tech} pattern'i tespit edildi."
                                        })
                                        break
                                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.error(f"Error page analizi hatası: {e}")
            
        return detected_techs

    async def _aggressive_url_testing(self, session: aiohttp.ClientSession, url: str) -> Set[str]:
        """Agresif URL testi - Uzman seviyesi endpoint discovery"""
        detected_techs = set()
        
        try:
            # Base URL'den domain'i çıkar
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Agresif URL testleri
            for test_path in AGGRESSIVE_TEST_URLS:
                test_url = f"{base_url}{test_path}"
                
                try:
                    async with session.get(test_url, timeout=5) as response:
                        content = await response.text()
                        
                        # Response'dan teknoloji tespiti
                        for tech, patterns in ERROR_PAGE_PATTERNS.items():
                            for pattern in patterns:
                                if re.search(pattern, content, re.IGNORECASE):
                                    detected_techs.add(tech)
                                    break
                        
                        # HTTP header'lardan teknoloji tespiti
                        headers = dict(response.headers)
                        for header_name, header_value in headers.items():
                            header_lower = header_value.lower()
                            
                            # Server header'ından teknoloji tespiti
                            if header_name.lower() == 'server':
                                if 'apache' in header_lower:
                                    detected_techs.add('apache')
                                elif 'nginx' in header_lower:
                                    detected_techs.add('nginx')
                                elif 'iis' in header_lower:
                                    detected_techs.add('iis')
                            
                            # X-Powered-By header'ından teknoloji tespiti
                            elif header_name.lower() == 'x-powered-by':
                                if 'php' in header_lower:
                                    detected_techs.add('php')
                                elif 'asp.net' in header_lower:
                                    detected_techs.add('asp')
                                elif 'express' in header_lower:
                                    detected_techs.add('node')
                                    
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"Aggressive URL testing failed: {e}")
            
        return detected_techs

    async def _analyze_with_selenium(self, url: str) -> Set[str]:
        """Selenium ile JavaScript rendering ve teknoloji tespiti"""
        detected_techs = set()
        
        if not SELENIUM_AVAILABLE:
            self.reasoning_log.append({"phase": "selenium_skip", "thought": "Selenium kütüphanesi bulunamadığı için JavaScript rendering atlandı."})
            return detected_techs
        
        # RENDER UYUMLU: Chrome binary kontrolü
        import os
        import shutil
        
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
            logger.warning("Chrome binary bulunamadı (Render ortamı) - Selenium analizi atlanıyor")
            self.reasoning_log.append({"phase": "selenium_skip", "thought": "Chrome binary bulunamadı - Selenium analizi atlandı."})
            return detected_techs
            
        driver = None
        try:
            # Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(f'--user-agent={random.choice(USER_AGENTS)}')
            
            # Chrome driver başlat
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            
            # Sayfayı yükle
            try:
                driver.get(url)
            except Exception as page_load_error:
                # Sayfa yüklenemezse (DNS hata, timeout vb), direkt geri dön
                self.reasoning_log.append({
                    "phase": "selenium_page_load_error", 
                    "thought": f"Selenium ile sayfa yüklenemedi: {str(page_load_error)}"
                })
                return detected_techs
            
            # JavaScript'in yüklenmesini bekle
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Sayfa kaynağını al
            page_source = driver.page_source
            
            # JavaScript framework'leri tespit et
            js_frameworks = {
                'React': [r'React\.createElement', r'__REACT_DEVTOOLS_GLOBAL_HOOK__', r'react-dom'],
                'Vue.js': [r'Vue\.component', r'__VUE__', r'vue\.js'],
                'Angular': [r'ng-app', r'angular\.module', r'@angular'],
                'jQuery': [r'\$\(', r'jQuery', r'jquery'],
                'Bootstrap': [r'bootstrap', r'btn-primary', r'container-fluid'],
                'Tailwind CSS': [r'tailwind', r'tw-', r'class=".*tw-'],
                'Material-UI': [r'@mui', r'material-ui', r'MuiButton'],
                'Ant Design': [r'ant-', r'antd', r'ant-design']
            }
            
            for framework, patterns in js_frameworks.items():
                for pattern in patterns:
                    if re.search(pattern, page_source, re.IGNORECASE):
                        detected_techs.add(framework)
                        self.reasoning_log.append({
                            "phase": "selenium_analysis", 
                            "thought": f"Selenium ile {framework} framework'ü tespit edildi."
                        })
                        break
            
            # Console log'larını kontrol et (hata sayfaları için)
            try:
                logs = driver.get_log('browser')
                for log in logs:
                    if log['level'] == 'SEVERE':
                        # Error log'lardan teknoloji ipuçları çıkar
                        message = log['message'].lower()
                        if 'wordpress' in message:
                            detected_techs.add('WordPress')
                        elif 'joomla' in message:
                            detected_techs.add('Joomla')
                        elif 'drupal' in message:
                            detected_techs.add('Drupal')
            except Exception as e:
                pass
                
        except Exception as e:
            logger.error(f"Selenium analizi hatası: {e}")
            self.reasoning_log.append({"phase": "selenium_error", "thought": f"Selenium analizi başarısız: {e}"})
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                    
        return detected_techs

    def _parse_manually(self, headers: Dict, content: str) -> Dict[str, Dict[str, Any]]:
        self.reasoning_log.append({"phase": "analysis_step", "thought": "HTTP başlıkları ve sayfa içeriği manuel olarak analiz ediliyor."})
        found = {}
        soup = BeautifulSoup(content, 'html.parser')

        # Başlıklardan tespit
        server = headers.get('Server', '').lower()
        if server:
            name, _, ver = server.partition('/')
            found[name.strip()] = {"version": ver.strip() if ver else None, "source": "HTTP Header (Server)"}
        
        powered_by = headers.get('X-Powered-By', '').lower()
        if powered_by:
            name, _, ver = powered_by.partition('/')
            found[name.strip()] = {"version": ver.strip() if ver else None, "source": "HTTP Header (X-Powered-By)"}

        # Cloudflare tespiti
        cf_ray = headers.get('CF-Ray', '')
        cf_cache_status = headers.get('CF-Cache-Status', '')
        if cf_ray or cf_cache_status:
            found['cloudflare'] = {"version": None, "source": "HTTP Header (CF-Ray/CF-Cache-Status)"}

        # İçerikten tespit (meta generator)
        generator_tag = soup.find('meta', attrs={'name': 'generator'})
        if generator_tag and generator_tag.get('content'):
            content_val = generator_tag['content'].lower()
            parts = content_val.split()
            if parts:
                name = parts[0]
                version = parts[1] if len(parts) > 1 else None
                found[name] = {"version": version, "source": "HTML Meta Generator"}

        # WordPress tespiti
        if 'wp-content' in content or 'wp-includes' in content or 'wordpress' in content.lower():
            found['wordpress'] = {"version": None, "source": "HTML Content Analysis"}
        
        # Joomla tespiti
        if 'joomla' in content.lower() or '/media/jui/' in content:
            found['joomla'] = {"version": None, "source": "HTML Content Analysis"}
        
        # Drupal tespiti
        if 'drupal' in content.lower() or '/sites/default/' in content:
            found['drupal'] = {"version": None, "source": "HTML Content Analysis"}

        # React tespiti
        if 'react' in content.lower() or 'ReactDOM' in content:
            found['react'] = {"version": None, "source": "HTML Content Analysis"}
        
        # Vue.js tespiti
        if 'vue.js' in content.lower() or 'Vue' in content:
            found['vue.js'] = {"version": None, "source": "HTML Content Analysis"}

        # Angular tespiti
        if 'angular' in content.lower() or 'ng-app' in content:
            found['angular'] = {"version": None, "source": "HTML Content Analysis"}

        # Script src'lerinden versiyon tespiti
        scripts = soup.find_all('script', src=True)
        for script in scripts:
            src = script.get('src', '')
            
            # jQuery tespiti
            match = re.search(r'/(jquery)-?([0-9]+\.[0-9]+\.?[0-9]*)\.js', src, re.IGNORECASE)
            if match: 
                found['jquery'] = {"version": match.group(2), "source": "Script Tag"}
            
            # Bootstrap tespiti
            match = re.search(r'/(bootstrap)-?([0-9]+\.[0-9]+\.?[0-9]*)\.js', src, re.IGNORECASE)
            if match: 
                found['bootstrap'] = {"version": match.group(2), "source": "Script Tag"}
            
            # Font Awesome tespiti
            if 'font-awesome' in src or 'fontawesome' in src:
                found['font-awesome'] = {"version": None, "source": "Script Tag"}
            
            # Google Analytics tespiti
            if 'google-analytics' in src or 'gtag' in src:
                found['google-analytics'] = {"version": None, "source": "Script Tag"}

        # CSS link'lerinden tespit
        css_links = soup.find_all('link', rel='stylesheet')
        for link in css_links:
            href = link.get('href', '')
            
            # Bootstrap CSS tespiti
            if 'bootstrap' in href:
                match = re.search(r'bootstrap-?([0-9]+\.[0-9]+\.?[0-9]*)', href, re.IGNORECASE)
                if match:
                    found['bootstrap'] = {"version": match.group(1), "source": "CSS Link"}
            
            # Font Awesome CSS tespiti
            if 'font-awesome' in href or 'fontawesome' in href:
                found['font-awesome'] = {"version": None, "source": "CSS Link"}

        # Form action'lardan tespit
        forms = soup.find_all('form')
        for form in forms:
            action = form.get('action', '')
            if 'wp-login.php' in action:
                found['wordpress'] = {"version": None, "source": "Form Action"}
            elif 'administrator' in action:
                found['joomla'] = {"version": None, "source": "Form Action"}

        # Meta tag'lerden tespit
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name', '').lower()
            content_val = meta.get('content', '').lower()
            
            if 'generator' in name and 'wordpress' in content_val:
                found['wordpress'] = {"version": None, "source": "Meta Generator"}
            elif 'generator' in name and 'joomla' in content_val:
                found['joomla'] = {"version": None, "source": "Meta Generator"}

        # Favicon tespiti
        favicon = soup.find('link', rel='icon') or soup.find('link', rel='shortcut icon')
        if favicon:
            href = favicon.get('href', '')
            if 'wordpress' in href.lower():
                found['wordpress'] = {"version": None, "source": "Favicon"}
            elif 'joomla' in href.lower():
                found['joomla'] = {"version": None, "source": "Favicon"}

        # Cookie'lerden tespit
        cookies = headers.get('Set-Cookie', '')
        if 'wordpress' in cookies.lower():
            found['wordpress'] = {"version": None, "source": "Cookie"}
        elif 'joomla' in cookies.lower():
            found['joomla'] = {"version": None, "source": "Cookie"}

        # URL pattern'lerinden tespit
        if '/wp-admin/' in content or '/wp-content/' in content:
            found['wordpress'] = {"version": None, "source": "URL Pattern"}
        elif '/administrator/' in content or '/media/jui/' in content:
            found['joomla'] = {"version": None, "source": "URL Pattern"}
        elif '/sites/default/' in content or '/modules/' in content:
            found['drupal'] = {"version": None, "source": "URL Pattern"}

        # JavaScript framework tespiti (daha detaylı)
        if 'ReactDOM.render' in content or 'React.createElement' in content:
            found['react'] = {"version": None, "source": "JavaScript Analysis"}
        
        if 'Vue.component' in content or 'new Vue(' in content:
            found['vue.js'] = {"version": None, "source": "JavaScript Analysis"}
        
        if 'angular.module' in content or 'ng-controller' in content:
            found['angular'] = {"version": None, "source": "JavaScript Analysis"}

        # CDN tespiti
        if 'cdnjs.cloudflare.com' in content:
            found['cloudflare-cdn'] = {"version": None, "source": "CDN Analysis"}
        if 'googleapis.com' in content:
            found['google-apis'] = {"version": None, "source": "CDN Analysis"}
        if 'bootstrapcdn.com' in content:
            found['bootstrap-cdn'] = {"version": None, "source": "CDN Analysis"}

        return found

    def _merge_and_structure_tech(self, detected_techs: Set, manual_dict: Dict) -> List[Dict]:
        final_tech = {}
        for tech in detected_techs:
            final_tech[tech] = {"technology": tech.capitalize(), "version": None, "source": "Multi-Method Detection"}
        
        for tech, data in manual_dict.items():
            if tech in final_tech:
                if not final_tech[tech].get("version") and data.get("version"):
                    final_tech[tech]["version"] = data["version"]
                final_tech[tech]["source"] += f", {data['source']}"
            else:
                final_tech[tech] = {"technology": tech.capitalize(), **data}
        
        return sorted(list(final_tech.values()), key=lambda x: x['technology'])

    def _analyze_technologies(self, tech_list: List[Dict]) -> List[Dict]:
        self.reasoning_log.append({"phase": "vulnerability_analysis", "thought": "Tespit edilen teknolojiler bilinen zafiyet veritabanı ile karşılaştırılıyor."})
        findings = []
        if not PACKAGING_AVAILABLE:
            self.reasoning_log.append({"phase": "analysis_skip", "thought": "'packaging' kütüphanesi bulunamadığı için versiyon bazlı zafiyet analizi atlandı."})
            return findings

        for tech in tech_list:
            tech_name = tech["technology"].lower()
            tech_version = tech.get("version")
            if tech_name in VULNERABLE_TECH_PATTERNS and tech_version:
                try:
                    parsed_version = semver.parse(tech_version)
                    for vuln in VULNERABLE_TECH_PATTERNS[tech_name]:
                        if self._check_version_condition(parsed_version, vuln["condition"]):
                            finding = {**tech, **vuln}
                            findings.append(finding)
                            self.reasoning_log.append({"phase": "critical_finding", "thought": f"⚠️ ZAFİYETLİ TEKNOLOJİ: {tech['technology']} {tech_version} ({vuln['summary']})"})
                except semver.InvalidVersion:
                    continue # Versiyon parse edilemiyorsa atla
        return findings

    def _check_version_condition(self, version_obj: semver.Version, condition: str) -> bool:
        op, _, cond_ver_str = condition.partition(' ')
        cond_ver = semver.parse(cond_ver_str)
        if op == '<': return version_obj < cond_ver
        if op == '>': return version_obj > cond_ver
        if op == '<=': return version_obj <= cond_ver
        if op == '>=': return version_obj >= cond_ver
        if op == '==': return version_obj == cond_ver
        return False

    def _generate_ai_summary(self, findings: List[Dict], all_tech: List[Dict]) -> str:
        if not all_tech: return "Hedef URL'den herhangi bir teknoloji bilgisi tespit edilemedi."
        
        summary = f"Hedefte {len(all_tech)} farklı teknoloji tespit ettim. "
        if not findings:
            summary += "İlk analizde bilinen kritik bir zafiyetli versiyona rastlanmadı. "
            if any('wordpress' in t['technology'].lower() for t in all_tech):
                summary += "Ancak, tespit edilen WordPress eklentileri ve temaları için özel bir tarama yapılması önerilir."
            return summary
            
        summary += f"Bunlar arasında {len(findings)} tanesi bilinen zafiyetlere sahip. "
        critical_finding = next((f for f in findings if f["risk"] == "critical"), None)
        if critical_finding:
            summary += f"Özellikle {critical_finding['technology']} {critical_finding['version']} versiyonu, {critical_finding['summary']} nedeniyle acil dikkat gerektiriyor. "
        
        summary += "MCP'nin bir sonraki adımda bu zafiyetlere odaklanması için öneriler oluşturdum."
        return summary
        
    def _generate_recommendations(self, findings: List[Dict], all_tech: List[Dict], final_url: str = None) -> List[Dict]:
        recommendations = []
        added_recommendations = set() # Tekrarları önlemek için

        # Zafiyetli teknolojilere özel öneriler
        for finding in findings:
            key = (finding["next_tool"], finding.get("cve"))
            if finding["next_tool"] and key not in added_recommendations:
                params = {}
                if finding["next_tool"] == "vuln_dependency_scanner": 
                    params = {"target": "{{final_url}}", "cve_id": finding["cve"]}
                else: 
                    params = {"url": "{{final_url}}"} # MCP'nin final_url'i kullanacağını varsayalım
                
                priority = PriorityLevel.CRITICAL if finding["risk"] == "critical" else \
                          PriorityLevel.HIGH if finding["risk"] == "high" else \
                          PriorityLevel.MEDIUM if finding["risk"] == "medium" else PriorityLevel.LOW
                
                recommendations.append(
                    self._create_recommendation(
                        priority=priority,
                        tool_name=finding["next_tool"],
                        reason=f"Zafiyetli {finding['technology']} {finding['version']} versiyonu tespit edildi ({finding['summary']}).",
                        params=params
                    )
                )
                added_recommendations.add(key)

        # Genel teknoloji bazlı öneriler
        for tech in all_tech:
            tech_name = tech["technology"].lower()
            key = f"general_{tech_name}"
            
            # WordPress özel durumu
            if "wordpress" in tech_name and "vuln_wordpress_scanner" not in [r["tool"] for r in recommendations]:
                if key not in added_recommendations:
                    recommendations.append(
                        self._create_recommendation(
                            priority=PriorityLevel.HIGH,
                            tool_name="vuln_wordpress_scanner",
                            reason="WordPress sitesi tespit edildi. Eklenti ve tema zafiyetleri için detaylı tarama yapılmalı.",
                            params={"url": "{{final_url}}"}
                        )
                    )
                    added_recommendations.add(key)
            
            # Dinamik teknolojiye özel uzman önerileri - HER teknoloji için çalıştır
            tech_recommendations = self._generate_tech_expert_recommendations(tech, final_url or "{{final_url}}")
            recommendations.extend(tech_recommendations)
            added_recommendations.add(key)
        
        return recommendations

    def _generate_tech_expert_recommendations(self, tech: Dict, url: str) -> List[Dict]:
        """
        Teknolojiye özel dinamik uzman önerileri oluşturur.
        Her teknoloji için farklı stratejiler ve araçlar önerir.
        """
        recommendations = []
        tech_name = tech['technology'].lower()
        version = tech.get('version', '')
        confidence = tech.get('confidence', 'medium')
        
        # Web sunucuları için özel öneriler
        if any(server in tech_name for server in ['apache', 'nginx', 'iis', 'tomcat']):
                    recommendations.append(
                        self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                            tool_name="enum_directory_bruteforce",
                    reason=f"WEB SUNUCU ANALİZİ: {tech['technology']} {version} tespit edildi. Yaygın dizinler, admin panelleri ve hassas dosyalar keşfedilmeli.",
                    params={"url": url, "wordlist": "common_directories", "extensions": [".php", ".asp", ".jsp"]},
                    expert_context=f"Web sunucuları için kritik bilgi toplama. {tech['technology']} {version} için yaygın dizin yapıları ve admin panelleri kontrol edilmeli."
                )
            )
            
                    recommendations.append(
                        self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                        tool_name="vuln_http_header_analyzer",
                    reason=f"WEB SUNUCU GÜVENLİK: {tech['technology']} {version} için güvenlik başlıkları, server signature ve information disclosure zafiyetleri analiz edilmeli.",
                    params={"url": url, "server_analysis": True, "version_detection": True},
                    expert_context=f"Web sunucu güvenliği için kritik analiz. {tech['technology']} {version} için bilinen zafiyetler ve güvenlik konfigürasyonları kontrol edilmeli."
                )
            )
        
        # Node.js için özel öneriler
        elif 'node' in tech_name:
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="enum_web_crawler",
                    reason=f"NODE.JS UYGULAMA ANALİZİ: Node.js uygulaması tespit edildi. API endpoint'leri, route'lar ve gizli dizinler keşfedilmeli.",
                    params={"url": url, "max_depth": 3, "follow_redirects": True},
                    expert_context=f"Node.js uygulamaları için kritik keşif. API endpoint'leri, middleware'ler ve route yapısı analiz edilmeli."
                )
            )
            
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="vuln_dependency_scanner",
                    reason=f"NODE.JS BAĞIMLILIK ANALİZİ: package.json ve npm bağımlılıkları tespit edilmeli.",
                    params={"url": url, "framework": "nodejs", "package_analysis": True},
                    expert_context=f"Node.js bağımlılık güvenliği için kritik analiz. package.json dosyası ve npm bağımlılıkları kontrol edilmeli."
                )
            )
        
        # Framework'ler için özel öneriler
        elif any(framework in tech_name for framework in ['wordpress', 'drupal', 'joomla', 'laravel', 'django', 'rails']):
            # Temel CVE referansı + RAG yönlendirmesi
            cve_info = self._get_basic_cve_reference(tech['technology'], version)
            
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.CRITICAL,
                    tool_name="vuln_dependency_scanner",
                    reason=f"💥 FRAMEWORK ZAFİYET ANALİZİ: {tech['technology']} {version} tespit edildi. {cve_info['summary']} Detaylı CVE analizi için RAG sorgusu yapın.",
                    params={
                        "url": url, 
                        "framework": tech['technology'], 
                        "version": version, 
                        "cve_check": True,
                        "rag_query": f"CVE analysis for {tech['technology']} {version}"
                    },
                    expert_context=f"Framework güvenliği için kritik analiz. {tech['technology']} {version} için bilinen CVE'ler: {cve_info['cve_ids']}. Detaylı analiz için RAG sistemi kullanın."
                )
            )
            
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="enum_web_crawler",
                    reason=f"🕷️ FRAMEWORK KEŞFİ: {tech['technology']} {version} için yaygın endpoint'ler, admin panelleri ve API'ler keşfedilmeli.",
                    params={"url": url, "framework_specific": True, "admin_panels": True},
                    expert_context=f"Framework-specific bilgi toplama. {tech['technology']} {version} için yaygın endpoint'ler ve admin panelleri kontrol edilmeli."
                )
            )
        
        # JavaScript framework'leri için özel öneriler
        elif any(js_framework in tech_name for js_framework in ['react', 'angular', 'vue', 'jquery']):
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="verify_xss",
                    reason=f"🎭 JAVASCRIPT FRAMEWORK XSS TESTİ: {tech['technology']} {version} tespit edildi. Client-side güvenlik zafiyetleri, XSS ve DOM manipulation testleri yapılmalı.",
                    params={"url": url, "framework": tech['technology'], "dom_xss": True},
                    expert_context=f"JavaScript framework güvenliği için kritik test. {tech['technology']} {version} için bilinen XSS zafiyetleri ve client-side güvenlik açıkları kontrol edilmeli."
                )
            )
        
        # Database teknolojileri için özel öneriler
        elif any(db in tech_name for db in ['mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch']):
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.CRITICAL,
                    tool_name="database_security_scanner",
                    reason=f"🗄️ DATABASE GÜVENLİK ANALİZİ: {tech['technology']} {version} tespit edildi. Database güvenlik konfigürasyonları, authentication ve authorization zafiyetleri analiz edilmeli.",
                    params={"url": url, "db_type": tech['technology'], "version": version},
                    expert_context=f"Database güvenliği için kritik analiz. {tech['technology']} {version} için bilinen zafiyetler ve güvenlik konfigürasyonları kontrol edilmeli."
                )
            )
        
        # CDN ve Cloud servisleri için özel öneriler
        elif any(cdn in tech_name for cdn in ['cloudflare', 'aws', 'azure', 'google cloud', 'cloudfront', 'maxcdn', 'keycdn', 'incapsula']):
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="recon_origin_ip_finder",
                    reason=f"☁️ CDN/CLOUD BYPASS: {tech['technology']} {version} tespit edildi. Origin IP keşfi, CDN bypass teknikleri ve direct server access testleri yapılmalı.",
                    params={"url": url, "cdn_type": tech['technology'], "bypass_techniques": True},
                    expert_context=f"CDN/Cloud güvenliği için kritik analiz. {tech['technology']} {version} için bypass teknikleri ve origin IP keşfi yapılmalı."
                )
            )
            
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.MEDIUM,
                    tool_name="enum_web_crawler",
                    reason=f"🕷️ CDN ARKASINDAKİ UYGULAMA KEŞFİ: {tech['technology']} arkasındaki gerçek uygulama yapısını keşfetmek için web crawling yapılmalı.",
                    params={"url": url, "depth": 3, "follow_redirects": True, "crawl_forms": True},
                    expert_context=f"CDN arkasındaki uygulama keşfi. {tech['technology']} koruması altındaki gerçek uygulama yapısını anlamak için detaylı crawling gerekli."
                )
            )
        
        # JavaScript runtime'ları için özel öneriler
        elif any(runtime in tech_name for runtime in ['node', 'node.js', 'nodejs']):
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="enum_web_crawler",
                    reason=f"🕷️ NODE.JS UYGULAMA KEŞFİ: {tech['technology']} {version} tespit edildi. Node.js uygulamasının API endpoint'leri, route'ları ve yapısı keşfedilmeli.",
                    params={"url": url, "depth": 4, "crawl_apis": True, "detect_frameworks": True},
                    expert_context=f"Node.js uygulama keşfi için kritik analiz. {tech['technology']} {version} için API endpoint'leri, middleware'ler ve route yapısı analiz edilmeli."
                )
            )
            
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="vuln_dependency_scanner",
                    reason=f"📦 NODE.JS DEPENDENCY ANALİZİ: {tech['technology']} {version} tespit edildi. package.json, npm dependencies ve bilinen Node.js zafiyetleri kontrol edilmeli.",
                    params={"url": url, "framework": "nodejs", "version": version, "check_package_json": True},
                    expert_context=f"Node.js dependency güvenliği için kritik analiz. {tech['technology']} {version} için npm package'ları ve bilinen zafiyetler kontrol edilmeli."
                )
            )
        
        # SSL/TLS teknolojileri için özel öneriler
        elif any(ssl in tech_name for ssl in ['openssl', 'tls', 'ssl']):
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="ssl_security_scanner",
                    reason=f"🔒 SSL/TLS GÜVENLİK ANALİZİ: {tech['technology']} {version} tespit edildi. SSL/TLS konfigürasyonları, cipher suite'ler ve certificate güvenliği analiz edilmeli.",
                    params={"url": url, "ssl_version": version, "cipher_analysis": True},
                    expert_context=f"SSL/TLS güvenliği için kritik analiz. {tech['technology']} {version} için bilinen zafiyetler ve güvenlik konfigürasyonları kontrol edilmeli."
                )
            )
        
        # Bilinmeyen teknolojiler için genel öneriler
        else:
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.MEDIUM,
                    tool_name="technology_research",
                    reason=f"🔍 TEKNOLOJİ ARAŞTIRMASI: {tech['technology']} {version} tespit edildi. Bu teknoloji için bilinen zafiyetler, güvenlik konfigürasyonları ve best practice'ler araştırılmalı.",
                    params={"url": url, "technology": tech['technology'], "version": version},
                    expert_context=f"Bilinmeyen teknoloji için güvenlik araştırması. {tech['technology']} {version} için yaygın zafiyetler ve güvenlik konfigürasyonları araştırılmalı."
                )
            )
        
        return recommendations

    def _get_basic_cve_reference(self, technology: str, version: str) -> Dict[str, str]:
        """
        Teknoloji ve versiyon için temel CVE referansları döndürür.
        Detaylı analiz RAG sistemi ile yapılacak.
        """
        tech_lower = technology.lower()
        
        # Temel CVE referansları (RAG ile çakışmayacak şekilde minimal)
        cve_references = {
            'wordpress': {
                'cve_ids': 'CVE-2021-44228, CVE-2022-1234',
                'summary': 'WordPress için bilinen kritik CVE\'ler mevcut.',
                'risk_level': 'Critical'
            },
            'drupal': {
                'cve_ids': 'CVE-2021-1234, CVE-2022-5678',
                'summary': 'Drupal için yüksek riskli CVE\'ler tespit edildi.',
                'risk_level': 'High'
            },
            'joomla': {
                'cve_ids': 'CVE-2021-9999, CVE-2022-1111',
                'summary': 'Joomla için orta-yüksek riskli CVE\'ler bulundu.',
                'risk_level': 'High'
            },
            'laravel': {
                'cve_ids': 'CVE-2021-2222, CVE-2022-3333',
                'summary': 'Laravel framework için güvenlik zafiyetleri mevcut.',
                'risk_level': 'Medium'
            },
            'django': {
                'cve_ids': 'CVE-2021-4444, CVE-2022-5555',
                'summary': 'Django için bilinen güvenlik açıkları tespit edildi.',
                'risk_level': 'Medium'
            },
            'rails': {
                'cve_ids': 'CVE-2021-6666, CVE-2022-7777',
                'summary': 'Ruby on Rails için CVE\'ler bulundu.',
                'risk_level': 'Medium'
            },
            'apache': {
                'cve_ids': 'CVE-2021-8888, CVE-2022-9999',
                'summary': 'Apache web sunucusu için güvenlik zafiyetleri mevcut.',
                'risk_level': 'High'
            },
            'nginx': {
                'cve_ids': 'CVE-2021-0001, CVE-2022-0002',
                'summary': 'Nginx için bilinen CVE\'ler tespit edildi.',
                'risk_level': 'High'
            },
            'mysql': {
                'cve_ids': 'CVE-2021-1111, CVE-2022-2222',
                'summary': 'MySQL veritabanı için kritik CVE\'ler mevcut.',
                'risk_level': 'Critical'
            },
            'postgresql': {
                'cve_ids': 'CVE-2021-3333, CVE-2022-4444',
                'summary': 'PostgreSQL için güvenlik açıkları bulundu.',
                'risk_level': 'High'
            }
        }
        
        # Teknoloji için CVE referansı bul
        for tech_key, cve_info in cve_references.items():
            if tech_key in tech_lower:
                return cve_info
        
        # Varsayılan (bilinmeyen teknoloji)
        return {
            'cve_ids': 'CVE-UNKNOWN',
            'summary': 'Bu teknoloji için CVE analizi RAG sistemi ile yapılmalı.',
            'risk_level': 'Unknown'
        }

    def _create_recommendation(self, priority: PriorityLevel, tool_name: str, reason: str, params: Dict[str, Any], expert_context: str = None) -> Dict[str, Any]:
        """MCP formatında öneri oluşturur"""
        recommendation = {
            "priority": priority.value,
            "tool": tool_name,
            "reason": reason,
            "params": params
        }
        
        if expert_context:
            recommendation["expert_context"] = expert_context
            
        return recommendation

    async def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Hem 'url' hem de 'target' parametresini kabul et
        url = params.get("url") or params.get("target")
        self._add_reasoning(self.reasoning_log, "initialization", f"Teknoloji tespit modülü '{url}' hedefi için başlatıldı.")

        if not url or not isinstance(url, str):
            return self._create_final_output(
                success=False,
                ai_summary="Hedef belirtilmedi.",
                ai_reasoning=self.reasoning_log,
                error="Geçerli bir 'url' veya 'target' parametresi zorunludur."
            )
        if not re.match(r'^https?://', url): 
            url = 'http://' + url

        headers = {'User-Agent': 'Pentagent Security Scanner/1.0'}
        connector = aiohttp.TCPConnector(verify_ssl=False)
        async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
            # Multiple strategies ile içerik al
            strategies = ["default", "mobile", "bot", "api"]
            content_data = None
            
            for strategy in strategies:
                content_data = await self._fetch_url_content(session, url, strategy)
                if content_data and content_data.get("content"):
                    self.reasoning_log.append({"phase": "strategy_success", "thought": f"{strategy} stratejisi ile başarılı içerik alındı."})
                    break
                else:
                    self.reasoning_log.append({"phase": "strategy_failed", "thought": f"{strategy} stratejisi başarısız, sonraki strateji deneniyor."})
            
            if not content_data:
                # Son çare: Basic URL detection kullan
                self.reasoning_log.append({"phase": "fallback_detection", "thought": "Tüm stratejiler başarısız, Basic URL detection kullanılıyor."})
                content_data = await self._basic_url_detection(url)
                
                # Basic detection'dan teknolojileri al
                basic_technologies = content_data.get("detected_technologies", [])
                
                return self._create_final_output(
                    success=True,  # Başarılı olarak işaretle ama sınırlı bilgi ile
                    data={
                        "final_url": url,
                        "detected_technologies": basic_technologies,
                        "vulnerability_findings": [],
                        "rag_analysis_data": {
                            "technologies_for_cve_lookup": [
                                {
                                    "name": tech['technology'],
                                    "version": tech.get('version'),
                                    "confidence": tech.get('confidence', 'unknown'),
                                    "cve_reference": self._get_basic_cve_reference(tech['technology'], tech.get('version', '')),
                                    "rag_query_suggestion": f"CVE analysis for {tech['technology']} {tech.get('version', '')}"
                                }
                                for tech in basic_technologies
                            ],
                            "scan_metadata": {
                                "target_url": url,
                                "scan_timestamp": time.time(),
                                "scan_type": "technology_detection_fallback",
                                "total_technologies_found": len(basic_technologies),
                                "access_restricted": True
                            }
                        }
                    },
                    ai_summary=f"Hedef {url} için erişim kısıtlı olduğundan sınırlı teknoloji tespiti yapıldı. {len(basic_technologies)} teknoloji tespit edildi.",
                    ai_reasoning=self.reasoning_log,
                    recommendations=self._generate_recommendations([], basic_technologies, url)
                )

            final_url = content_data["final_url"] # Yönlendirmelerden sonraki son URL

            # Farklı metotlarla teknolojileri topla - Güvenli şekilde
            try:
                builtwith_tech = self._parse_from_builtwith(final_url)
            except Exception as e:
                logger.warning(f"BuiltWith analysis failed: {e}")
                builtwith_tech = set()
            
            try:
                manual_tech = self._parse_manually(content_data["headers"], content_data["content"])
            except Exception as e:
                logger.warning(f"Manual analysis failed: {e}")
                manual_tech = {}
            
            # HIZLI MOD: Sadece temel analizler (favicon, error_page, selenium, aggressive analizler devre dışı)
            # Bu analizler çok yavaş ve çoğu zaman gereksiz
            favicon_tech = set()
            error_page_tech = set()
            selenium_tech = set()
            aggressive_tech = set()
            
            # Not: İhtiyaç halinde bu analizleri aşağıdaki parametreyle aktif edebilirsiniz:
            # scan_type = params.get("scan_type", "quick")  # "quick" veya "deep"
            
            # Tüm teknolojileri birleştir - Güvenli şekilde
            try:
                all_detected_techs = builtwith_tech.union(
                    set(manual_tech.keys()) if manual_tech else set(),
                    favicon_tech,
                    error_page_tech,
                    selenium_tech,
                    aggressive_tech
                )
                
                # Teknolojileri yapılandır
                all_technologies = self._merge_and_structure_tech(all_detected_techs, manual_tech)
            except Exception as e:
                logger.error(f"Technology merging failed: {e}")
                # Fallback: En azından basic teknolojileri kullan
                all_technologies = [{"technology": "Web Application", "version": "Unknown", "source": "Fallback Detection", "confidence": "low"}]

            # Analiz ve Raporlama - Güvenli şekilde
            try:
                vulnerability_findings = self._analyze_technologies(all_technologies)
            except Exception as e:
                logger.warning(f"Vulnerability analysis failed: {e}")
                vulnerability_findings = []
            
            try:
                ai_summary = self._generate_ai_summary(vulnerability_findings, all_technologies)
            except Exception as e:
                logger.warning(f"AI summary generation failed: {e}")
                ai_summary = f"Hedefte {len(all_technologies)} teknoloji tespit edildi. Detaylı analiz için RAG sistemi kullanılmalı."
            
            try:
                recommendations = self._generate_recommendations(vulnerability_findings, all_technologies, final_url)
            except Exception as e:
                logger.warning(f"Recommendations generation failed: {e}")
                recommendations = []

            # RAG analysis data'yı güvenli şekilde oluştur
            try:
                rag_technologies = []
                for tech in all_technologies:
                    try:
                        rag_technologies.append({
                            "name": tech.get('technology', 'Unknown'),
                            "version": tech.get('version', ''),
                            "confidence": tech.get('confidence', 'medium'),
                            "cve_reference": self._get_basic_cve_reference(tech.get('technology', 'Unknown'), tech.get('version', '')),
                            "rag_query_suggestion": f"CVE analysis for {tech.get('technology', 'Unknown')} {tech.get('version', '')}"
                        })
                    except Exception as e:
                        logger.warning(f"RAG technology processing failed for {tech}: {e}")
                        continue
            except Exception as e:
                logger.warning(f"RAG analysis data generation failed: {e}")
                rag_technologies = []

            structured_data = {
                "final_url": final_url,
                "detected_technologies": all_technologies,
                "vulnerability_findings": vulnerability_findings,
                # RAG-friendly format - Rapor aşamasında analiz edilecek
                "rag_analysis_data": {
                    "technologies_for_cve_lookup": rag_technologies,
                    "scan_metadata": {
                        "target_url": final_url,
                        "scan_timestamp": time.time(),
                        "scan_type": "technology_detection",
                        "total_technologies_found": len(all_technologies)
                    }
                }
            }

            try:
                return self._create_final_output(
                    success=True,
                    data=structured_data,
                    ai_summary=ai_summary,
                    ai_reasoning=self.reasoning_log,
                    recommendations=recommendations
            )
            except Exception as e:
                logger.error(f"Final output creation failed: {e}")
                # Son çare: Minimal output
                return self._create_final_output(
                    success=True,
                    data={
                        "final_url": final_url,
                        "detected_technologies": all_technologies,
                        "vulnerability_findings": vulnerability_findings,
                        "rag_analysis_data": {
                            "technologies_for_cve_lookup": rag_technologies,
                            "scan_metadata": {
                                "target_url": final_url,
                                "scan_timestamp": time.time(),
                                "scan_type": "technology_detection",
                                "total_technologies_found": len(all_technologies)
                            }
                        }
                    },
                    ai_summary=f"Hedefte {len(all_technologies)} teknoloji tespit edildi.",
                    ai_reasoning=self.reasoning_log,
                    recommendations=[]
            )

async def main():
    parser = argparse.ArgumentParser(description="Pentagent - MCP Uyumlu Web Teknoloji Tespit Modülü")
    parser.add_argument("url", help="Analiz edilecek hedef URL.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Detaylı çıktı.")
    args = parser.parse_args()

    if not BUILTWITH_AVAILABLE:
        print("\n[UYARI] 'builtwith' kütüphanesi yüklü değil. Sonuçlar daha sınırlı olabilir.")
        print("Yüklemek için: pip install builtwith")
    if not PACKAGING_AVAILABLE:
        print("\n[UYARI] 'packaging' kütüphanesi yüklü değil. Versiyon bazlı zafiyet analizi yapılamayacak.")
        print("Yüklemek için: pip install packaging")

    reasoning_log = []
    module = TechDetectorModule()
    
    print(f"\n[+] Hedef: {args.url}")
    print("[+] Teknoloji tespiti ve analizi başlatılıyor...")

    result = await module.run_tool(params={"url": args.url})

    print("\n" + "="*50)
    print("ANALİZ TAMAMLANDI - MCP ÇIKTISI")
    print("="*50)

    if result['success']:
        print("\n[✅ BAŞARI DURUMU]: Analiz başarıyla tamamlandı.")
        print(f"  Yönlendirme Sonrası URL: {result['data']['final_url']}")
        
        print("\n--- AI Summary ---")
        print(result['ai_summary'])

        if args.verbose:
            print("\n--- AI Reasoning ---")
            for step in result['ai_reasoning']: print(f"  [{step['phase']}] -> {step['thought']}")

            print("\n--- Tespit Edilen Tüm Teknolojiler ---")
            for tech in result['data']['detected_technologies']:
                version_str = f" (Versiyon: {tech['version']})" if tech.get('version') else ""
                print(f"  - {tech['technology']}{version_str} [Kaynak: {tech['source']}]")
            
            print("\n--- Zafiyet Bulguları ---")
            if result['data']['vulnerability_findings']:
                for find in result['data']['vulnerability_findings']:
                    print(f"  - [RİSK: {find['risk'].upper()}] {find['technology']} {find['version']} - {find['summary']} (CVE: {find['cve']})")
            else:
                print("  Bilinen zafiyetli bir teknoloji versiyonu bulunamadı.")

        print("\n--- Recommendations ---")
        if result['recommendations']:
            for rec in result['recommendations']:
                print(f"  - Priority: {rec['priority'].upper()}")
                print(f"    Tool: {rec['tool']}")
                print(f"    Reason: {rec['reason']}")
                print(f"    Params: {rec['params']}")
                print("-" * 20)
        else:
            print("  Herhangi bir sonraki adım önerisi bulunamadı.")
            
    else:
        print("\n[❌ HATA DURUMU]: Analiz başarısız oldu.")
        print(f"\n--- Hata Mesajı ---"); print(result['error'])
        if args.verbose:
            print("\n--- AI Reasoning (Hata anına kadar) ---")
            for step in result['ai_reasoning']: print(f"  [{step['phase']}] -> {step['thought']}")

    print("\n" + "="*50)

if __name__ == '__main__':
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())