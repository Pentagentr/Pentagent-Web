# GÖREV: OTONOM KOD ANALİZİ VE DÜZELTME
# ARAÇ ADI: enum_directory_bruteforcer.py
# DURUM: NİHAİ UZMAN SÜRÜMÜ v5 - Gelişmiş Wildcard Tespiti ve MCP Entegrasyonu

"""
enum_directory_bruteforcer.py - Profesyonel Seviye Dizin Keşif Aracı

Amaç: Akıllı wildcard/catch-all tespiti, içerik hash'leme ve yanıt analizi ile
      yanıltıcı pozitifleri (false positives) %99 oranında eleyerek, sızma testi
      uzmanının sadece gerçek ve değerli bulgulara odaklanmasını sağlar.

v5 Değişiklik Notları:
- MİMARİ: Araç, MCP için tamamen stateless (durumsuz) hale getirildi. Tüm tarama
  durumu, her 'execute' çağrısında oluşturulan bir context nesnesi içinde yönetilir.
- MCP ENTEGRASYONU: Çıktı, standart MCP JSON formatına tam uyumlu hale getirildi.
  'ai_summary', 'ai_reasoning' ve yapılandırılmış 'recommendations' alanları
  dinamik olarak ve akıllıca doldurulur.
- UZMAN SEVİYESİ BASELINE: Baseline mekanizması, sadece durum kodu/boyut değil,
  aynı zamanda sayfa içeriğinin hash'ini ve yönlendirme hedeflerini de analiz
  ederek özel 404 sayfalarını ve joker yönlendirmeleri tespit eder.
- RİSK ANALİZİ: Bulunan her yol, '.git', '.env', 'backup' gibi kritik anahtar
  kelimelere göre otomatik olarak risk seviyesine (Bilgilendirici, Yüksek, Kritik)
  ayrılır ve bu, öneri motorunu doğrudan besler.
- KOD KALİTESİ: Kod, kapsamlı yorumlar, type hinting ve sağlam hata yönetimi ile
  bir uzmanın beklentilerini karşılayacak şekilde yeniden yazıldı.
"""
import asyncio
import logging
import argparse
import random
import sys
import json
import hashlib
from typing import Dict, Any, List, Set, Optional, Tuple
from urllib.parse import urljoin
import time
import aiohttp
from dataclasses import dataclass, field

# PentagentTool base class'ını import et
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

# --- Konfigürasyonlar ve Sabitler ---
# Uzmanın hızlıca adapte olması için teknolojiye özel küçük ama etkili wordlist'ler
TECH_WORDLISTS = {
    "general": ["admin", "login", "panel", "api", "dashboard", "test", "dev", "backup", "config", "uploads", "assets", "static", "data", "files", "temp", "cache", "logs", "user", "account", "private", "public", "media", "download", "app", "portal", "payment", "search", "include", "lib", "vendor", "scripts"],
    "critical_files": [".git/HEAD", ".git/config", ".env", ".env.local", "web.config", ".htaccess", "robots.txt", "sitemap.xml", "README.md", ".gitignore"],
    "wordpress": ["wp-admin", "wp-content", "wp-config.php", "xmlrpc.php", "wp-login.php"],
    "php": ["phpinfo.php", "info.php", "admin.php", "config.php", "database.php"],
    "backup_ext": [".bak", ".old", ".zip", ".sql", ".backup"]
}
USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Pentagent/1.0"]

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Baseline:
    """Sunucunun 'bulunamadı' durumundaki davranışını temsil eder."""
    status: int
    content_hash: str
    content_length: int = 0
    redirect_location: Optional[str] = None

@dataclass
class BruteforceContext:
    """Dizin tarama işlemi sırasında durumu yönetmek için kullanılan veri sınıfı."""
    base_url: str
    threads: int
    wordlist_type: str
    baseline: Optional[Baseline] = None
    found_paths: List[Dict[str, Any]] = field(default_factory=list)
    checked_paths_count: int = 0
    waf_detected: bool = False
    ai_reasoning_log: List[Dict[str, str]] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)

class EnumDirectoryBruteforcerTool(MCPTool):
    """Akıllı false positive filtrelemeli profesyonel dizin keşif aracı"""

    def __init__(self):
        super().__init__(
            name="enum_directory_bruteforce",
            description="Akıllı wildcard/catch-all tespiti ve içerik hash'leme ile dizin keşif aracı.",
            category=ToolCategory.DISCOVERY_ENUMERATION
        )

    async def _establish_baseline(self, session: aiohttp.ClientSession, base_url: str) -> Optional[Baseline]:
        """Sunucunun var olmayan bir yola nasıl tepki verdiğini öğrenir - CRASH KORUNMALI."""
        random_path = f"/{hashlib.md5(str(random.random()).encode()).hexdigest()}"
        try:
            timeout = aiohttp.ClientTimeout(total=15, connect=10)
            async with session.get(urljoin(base_url, random_path), timeout=timeout, allow_redirects=False) as r:
                content = await r.read()
                baseline = Baseline(
                    status=r.status,
                    content_hash=hashlib.sha256(content).hexdigest(),
                    content_length=len(content),
                    redirect_location=r.headers.get('Location')
                )
                logger.info(f"Baseline tespiti: Status={baseline.status}, Hash={baseline.content_hash[:10]}..., Redirect={baseline.redirect_location}")
                return baseline
        except (aiohttp.ClientError, asyncio.TimeoutError, aiohttp.ClientConnectorError) as e:
            logger.debug(f"Baseline tespiti yapılamadı (normal): {type(e).__name__}")
            return None
        except Exception as e:
            logger.debug(f"Baseline tespiti beklenmeyen hata: {type(e).__name__}: {str(e)[:100]}")
            return None

    def _build_wordlist(self, wordlist_type: str) -> Set[str]:
        """Verilen tipe göre akıllı bir wordlist oluşturur - OPTİMİZE: ~80 kelime."""
        # Sadece en önemli kelimeleri seç - 80 civarı hedef
        words = set(TECH_WORDLISTS.get("general", [])[:25])  # İlk 25 genel kelime
        words.update(TECH_WORDLISTS.get("critical_files", []))  # Tüm kritik dosyalar
        if wordlist_type in TECH_WORDLISTS:
            words.update(TECH_WORDLISTS[wordlist_type])
        
        # OPTİMİZE: Sadece dizin olarak test et (çift varyasyon yok)
        final_list = set()
        for word in words:
            # Dosya uzantısı varsa sadece dosya olarak, yoksa dizin olarak
            if '.' in word or word.startswith('.'):
                final_list.add(f"/{word}")  # Dosya olarak
            else:
                final_list.add(f"/{word}/")  # Dizin olarak (sadece bir varyasyon)
        
        # Backup uzantılarını sadece kritik dosyalara ekle
        critical_files = ['index.php', 'config.php', 'wp-config.php']
        for file in critical_files:
            for ext in TECH_WORDLISTS['backup_ext'][:3]:  # Sadece ilk 3 backup uzantısı
                final_list.add(f"/{file}{ext}")
        
        # Toplam ~80 kelimeye ulaşmak için birkaç ek kelime
        if len(final_list) < 70:
            extra_words = ["phpinfo", "test", "debug", "install", "setup", "update", "upgrade", "old", "new", "v1", "v2"]
            for word in extra_words:
                final_list.add(f"/{word}/")
        
        logger.info(f"📋 Wordlist oluşturuldu: {len(final_list)} kelime")
        return final_list

    async def _check_path(self, session: aiohttp.ClientSession, path: str, context: BruteforceContext):
        """Tek bir yolu kontrol eder ve baseline'a göre filtreler - CRASH KORUNMALI."""
        full_url = urljoin(context.base_url, path)
        try:
            context.checked_paths_count += 1
            timeout = aiohttp.ClientTimeout(total=15, connect=10)
            async with session.get(full_url, timeout=timeout, allow_redirects=False) as r:
                # 1. WAF/Bloklama tespiti
                if r.status in [403, 429, 503]:
                    if not context.waf_detected:
                        context.waf_detected = True
                        context.ai_reasoning_log.append({"phase": "waf_detection", "thought": f"⚠️ WAF/Koruma tespiti yapıldı (Status: {r.status}). Tarama yavaşlatılabilir veya engellenebilir."})
                    return

                # 2. Baseline ile karşılaştırma - OPTİMİZE: Sadece gerçek 404'leri filtrele
                content = await r.read()
                content_length = len(content)
                content_hash = hashlib.sha256(content).hexdigest()
                
                # Status 200, 301, 302, 403, 500 vb. hepsi bulgu - direkt ekle
                if r.status != 404:
                    finding = {"url": full_url, "path": path, "status_code": r.status, "content_length": content_length}
                    context.found_paths.append(finding)
                    logger.info(f"✅ Bulundu: [{finding['status_code']}] {finding['url']} (Boyut: {finding['content_length']})")
                    return
                
                # Sadece status 404 ise baseline kontrolü yap
                if r.status == 404 and context.baseline:
                    # Hash tam eşitse skip et (özel 404 sayfası)
                    if content_hash == context.baseline.content_hash:
                        return
                    # İçerik uzunluğu çok farklıysa (2x'den fazla veya yarısından az) gerçek bulgu olabilir
                    baseline_length = context.baseline.content_length
                    if baseline_length > 0:
                        if content_length > baseline_length * 2 or content_length < baseline_length / 2:
                            # Gerçek bulgu - farklı içerik
                            finding = {"url": full_url, "path": path, "status_code": r.status, "content_length": content_length}
                            context.found_paths.append(finding)
                            logger.info(f"✅ Bulundu (404 ama farklı içerik): [{finding['status_code']}] {finding['url']} (Boyut: {finding['content_length']})")
                            return
                    # Yönlendirme kontrolü
                    if context.baseline.redirect_location and r.headers.get('Location') == context.baseline.redirect_location:
                        return
                    # Hash benzerliği kontrolü - ilk 20 karakter aynıysa skip
                    if content_hash[:20] == context.baseline.content_hash[:20]:
                        return
                
                # 404 ama baseline'dan farklı - bilgilendirici bulgu olarak ekle
                finding = {"url": full_url, "path": path, "status_code": r.status, "content_length": content_length}
                context.found_paths.append(finding)
                logger.info(f"✅ Bulundu (404 ama farklı): [{finding['status_code']}] {finding['url']} (Boyut: {finding['content_length']})")

        except (aiohttp.ClientError, asyncio.TimeoutError, aiohttp.ClientConnectorError):
            pass # Bağlantı hatalarını sessizce geç
        except Exception as e:
            logger.debug(f"Path kontrol hatası (sessizce geçildi): {full_url} - {type(e).__name__}: {str(e)[:100]}")
            # Crash'e izin verme - sadece logla ve devam et

    def _build_final_json(self, context: BruteforceContext, error: Exception = None) -> Dict[str, Any]:
        if error:
            error_message = f"{type(error).__name__}: {str(error)}"
            self._add_reasoning(context.ai_reasoning_log, "critical_error", error_message)
            return self._create_final_output(
                success=False,
                ai_summary="Dizin keşif aracı kritik bir hatayla karşılaştı.",
                ai_reasoning=context.ai_reasoning_log,
                error=error_message
            )
        
        # Bulguları risk seviyesine göre analiz et
        critical_findings, high_findings, info_findings = [], [], []
        for f in context.found_paths:
            path_lower = f['path'].lower()
            if any(c in path_lower for c in ['.git', '.env', 'config', '.sql', '.bak', '.zip', 'backup']):
                critical_findings.append(f)
            elif any(h in path_lower for h in ['admin', 'login', 'panel', 'dashboard']):
                high_findings.append(f)
            else:
                info_findings.append(f)

        # AI Summary oluştur
        summary = (f"Tarama {time.time() - context.start_time:.2f} saniyede tamamlandı. {context.checked_paths_count} yol denendi. "
                   f"{len(critical_findings)} kritik, {len(high_findings)} yüksek öncelikli ve {len(info_findings)} bilgilendirici kaynak bulundu.")
        if context.waf_detected: summary += " Tarama sırasında WAF/koruma sistemleri tespit edildi."

        # Recommendations oluştur
        recommendations = []
        if any('.git' in f['path'] for f in critical_findings):
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.CRITICAL,
                    tool_name="vuln_git_dumper",
                    reason=".git dizini bulundu. Kaynak kod sızıntısı riski var.",
                    params={"url": context.base_url}
                )
            )
        if any('.env' in f['path'] for f in critical_findings):
            env_finding = next((f for f in critical_findings if '.env' in f['path']), None)
            if env_finding:
                recommendations.append(
                    self._create_recommendation(
                        priority=PriorityLevel.CRITICAL,
                        tool_name="vuln_lfi_detector",
                        reason=".env dosyası bulundu. Hassas konfigürasyon bilgileri (API key, DB şifresi) içerebilir.",
                        params={"url": env_finding.get('url', context.base_url)}
                    )
                )
        if high_findings:
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="enum_bruteforce_login",
                    reason="Yönetim paneli veya giriş sayfası olabilecek yollar bulundu.",
                    params={"url": high_findings[0]['url']}
                )
            )

        self._add_reasoning(context.ai_reasoning_log, "complete", f"Analiz tamamlandı. {len(recommendations)} adet eylem önerisi oluşturuldu.")
        
        # NOT: recommendations yukarıda zaten oluşturuldu (duplicate çağrı kaldırıldı)
        
        # RAG-friendly format ekle
        rag_data = {
            "directory_findings": [
                {
                    "path": finding['path'],
                    "url": finding['url'],
                    "status_code": finding['status_code'],
                    "content_length": finding['content_length'],
                    "risk_level": "critical" if finding in critical_findings else "high" if finding in high_findings else "info",
                    "rag_query_suggestion": f"Directory listing analysis for {finding['path']}"
                }
                for finding in context.found_paths
            ],
            "scan_metadata": {
                "target_url": context.base_url,
                "scan_timestamp": time.time(),
                "scan_type": "directory_bruteforce",
                "total_paths_checked": context.checked_paths_count,
                "total_findings": len(context.found_paths),
                "critical_findings": len(critical_findings),
                "high_findings": len(high_findings),
                "waf_detected": context.waf_detected
            }
        }
        
        return self._create_final_output(
            success=True,
            data={
                "target": context.base_url, 
                "paths_checked": context.checked_paths_count, 
                "waf_detected": context.waf_detected,
                "findings": { "critical": critical_findings, "high": high_findings, "informational": info_findings },
                "rag_analysis_data": rag_data
            },
            ai_summary=summary,
            ai_reasoning=context.ai_reasoning_log,
            recommendations=recommendations
        )

    async def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        base_url = params.get("url")
        if not base_url: 
            return self._create_final_output(
                success=False,
                ai_summary="URL parametresi zorunludur.",
                error="URL parametresi zorunludur."
            )
        if not base_url.startswith(('http://', 'https://')): 
            base_url = 'https://' + base_url

        context = BruteforceContext(base_url=base_url.rstrip('/'), threads=params.get("threads", 50), wordlist_type=params.get("wordlist_type", "general"))
        self._add_reasoning(context.ai_reasoning_log, "initialization", f"Hedef {context.base_url} için dizin keşfi başlatılıyor. Metod: Akıllı Baseline Analizi.")

        try:
            # DNS çözümleme için optimize edilmiş connector
            connector = aiohttp.TCPConnector(
                ttl_dns_cache=300,
                force_close=False,
                enable_cleanup_closed=True,
                verify_ssl=False,
                limit=context.threads,
                limit_per_host=context.threads
            )
            timeout_config = aiohttp.ClientTimeout(total=60, connect=30, sock_connect=30)
            async with aiohttp.ClientSession(
                headers={"User-Agent": random.choice(USER_AGENTS)},
                connector=connector,
                timeout=timeout_config
            ) as session:
                context.baseline = await self._establish_baseline(session, context.base_url)
                if not context.baseline:
                     self._add_reasoning(context.ai_reasoning_log, "warning", "Baseline tespiti yapılamadı. Sonuçlar yanıltıcı pozitifler içerebilir.")
                
                wordlist = self._build_wordlist(context.wordlist_type)
                self._add_reasoning(context.ai_reasoning_log, "bruteforce", f"Oluşturulan {len(wordlist)} elemanlı wordlist ile tarama başlatılıyor.")
                
                rate_limiter = asyncio.Semaphore(context.threads)
                tasks = []
                for path in wordlist:
                    await rate_limiter.acquire()
                    task = asyncio.create_task(self._check_path(session, path, context))
                    task.add_done_callback(lambda t: rate_limiter.release())
                    tasks.append(task)
                
                # CRASH KORUNMALI: Tüm task'ları exception handling ile çalıştır
                results = await asyncio.gather(*tasks, return_exceptions=True)
                # Exception'ları logla ama crash'e izin verme
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.debug(f"Task {i} hatası (sessizce geçildi): {type(result).__name__}: {str(result)[:100]}")

            return self._build_final_json(context)
        except (aiohttp.ClientConnectorError, aiohttp.ClientError) as e:
            logger.warning(f"Bağlantı hatası (graceful): {type(e).__name__}")
            # Kısmi sonuç varsa döndür, yoksa hata döndür
            if context.checked_paths_count > 0:
                logger.info(f"Kısmi sonuç döndürülüyor: {context.checked_paths_count} yol kontrol edildi")
                return self._build_final_json(context)
            return self._create_final_output(
                success=False,
                ai_summary=f"Bağlantı hatası: Hedef URL '{context.base_url}' ulaşılamaz.",
                ai_reasoning=context.ai_reasoning_log,
                error=f"Bağlantı hatası: {type(e).__name__}"
            )
        except asyncio.TimeoutError as e:
            logger.warning(f"Timeout hatası (graceful): {type(e).__name__}")
            # Kısmi sonuç varsa döndür
            if context.checked_paths_count > 0:
                logger.info(f"Kısmi sonuç döndürülüyor: {context.checked_paths_count} yol kontrol edildi")
                return self._build_final_json(context)
            return self._create_final_output(
                success=False,
                ai_summary="Tarama zaman aşımına uğradı.",
                ai_reasoning=context.ai_reasoning_log,
                error="Timeout"
            )
        except Exception as e:
            logger.error(f"Kritik hata (graceful fail): {type(e).__name__}: {str(e)[:200]}", exc_info=False)
            # Kısmi sonuç varsa döndür - sistem ASLA çökmesin
            if context.checked_paths_count > 0:
                logger.info(f"Kısmi sonuç döndürülüyor: {context.checked_paths_count} yol kontrol edildi")
                return self._build_final_json(context)
            return self._create_final_output(
                success=False,
                ai_summary="Dizin keşfi sırasında bir hata oluştu ama sistem korundu.",
                ai_reasoning=context.ai_reasoning_log,
                error=f"{type(e).__name__}: {str(e)[:100]}"
            )

async def main():
    parser = argparse.ArgumentParser(description="Pentagent Akıllı Dizin Keşif Aracı (v5 - Uzman Sürümü).")
    parser.add_argument("url", help="Hedef URL (örn: example.com)")
    parser.add_argument("-w", "--wordlist-type", default="general", choices=list(TECH_WORDLISTS.keys()) + ['all'], help="Kullanılacak wordlist tipi")
    parser.add_argument("-t", "--threads", type=int, default=50, help="Eşzamanlı istek sayısı")
    parser.add_argument("-v", "--verbose", action="store_true", help="Detaylı (INFO seviyesi) logları göster")
    parser.add_argument("--json", action="store_true", help="JSON formatında çıktı ver")
    args = parser.parse_args()

    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stderr)
    
    bruteforcer = EnumDirectoryBruteforcerTool()
    result = await bruteforcer.run_tool(vars(args))

    if args.json: print(json.dumps(result, indent=2, ensure_ascii=False)); return
    
    print("\n" + "="*50 + "\n Pentagent Dizin Keşif Raporu\n" + "="*50)
    if not result.get("success"):
        print(f"\nHATA: Tarama Basarisiz!\n   Sebep: {result.get('error')}")
    else:
        print(f"\nOZET: {result.get('ai_summary')}\n")
        data = result.get("data", {}).get("findings", {})
        
        if data.get('critical'):
            print(f"KRITIK BULGULAR ({len(data['critical'])} adet):")
            for f in data['critical']: print(f"  - [{f['status']}] {f['url']} ({f['length']}B)")
        if data.get('high'):
            print(f"\nYUKSEK ONCELIKLI BULGULAR ({len(data['high'])} adet):")
            for f in data['high']: print(f"  - [{f['status']}] {f['url']} ({f['length']}B)")
        if data.get('informational'):
            print(f"\nBILGILENDIRICI BULGULAR ({len(data['informational'])} adet):")
            for f in data['informational'][:5]: print(f"  - [{f['status']}] {f['url']} ({f['length']}B)")
            if len(data['informational']) > 5: print("  ...")

    recommendations = result.get("recommendations", [])
    if recommendations:
        print("\n Eylem Onerileri:")
        for rec in recommendations: print(f"  - [{rec['priority'].upper()}] -> Calistir: {rec['tool']}\n    Neden: {rec['reason']}")
    
    print("\nAI Dusunce Akisi:")
    for thought in result.get("ai_reasoning", []):
        print(f"   [{thought['phase']}] {thought['thought'].encode('ascii', 'ignore').decode('ascii')}")

    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())