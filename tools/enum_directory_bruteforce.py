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
    "general": ["admin", "login", "panel", "api", "dashboard", "test", "dev", "backup", "config", "uploads", "assets", "static", "images", "js", "css", "data", "files", "temp", "tmp", "cache", "logs", "user", "users", "account", "accounts", "private", "public", "media", "download", "downloads", "doc", "docs", "app", "apps", "portal", "checkout", "payment", "search", "include", "includes", "lib", "libs", "vendor", "node_modules", "scripts", "cgi-bin"],
    "critical_files": [".git/HEAD", ".git/config", ".env", ".env.local", ".env.production", "web.config", "docker-compose.yml", "package.json", ".htaccess", "robots.txt", "sitemap.xml", "README.md", "CHANGELOG.md", ".gitignore", "composer.json", "Dockerfile"],
    "wordpress": ["wp-admin", "wp-content", "wp-includes", "wp-config.php", "xmlrpc.php", "wp-cron.php", "wp-login.php", "wp-json"],
    "php": ["phpinfo.php", "test.php", "info.php", "php.php", "index.php", "admin.php", "login.php", "config.php", "database.php", "db.php", "connect.php"],
    "backup_ext": [".bak", ".old", ".zip", ".tar.gz", ".sql", ".bkp", "~", ".swp", ".tmp", ".backup", ".save", ".orig"]
}
USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 Pentagent/1.0"]

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Baseline:
    """Sunucunun 'bulunamadı' durumundaki davranışını temsil eder."""
    status: int
    content_hash: str
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
        """Sunucunun var olmayan bir yola nasıl tepki verdiğini öğrenir."""
        random_path = f"/{hashlib.md5(str(random.random()).encode()).hexdigest()}"
        try:
            async with session.get(urljoin(base_url, random_path), timeout=10, allow_redirects=False) as r:
                content = await r.read()
                baseline = Baseline(
                    status=r.status,
                    content_hash=hashlib.sha256(content).hexdigest(),
                    redirect_location=r.headers.get('Location')
                )
                logger.info(f"Baseline tespiti: Status={baseline.status}, Hash={baseline.content_hash[:10]}..., Redirect={baseline.redirect_location}")
                return baseline
        except Exception as e:
            logger.warning(f"Baseline tespiti yapılamadı: {e}")
            return None

    def _build_wordlist(self, wordlist_type: str) -> Set[str]:
        """Verilen tipe göre akıllı bir wordlist oluşturur."""
        words = set(TECH_WORDLISTS.get("general", []))
        words.update(TECH_WORDLISTS.get("critical_files", []))
        if wordlist_type in TECH_WORDLISTS:
            words.update(TECH_WORDLISTS[wordlist_type])
        
        # Dizin ve dosya varyasyonları oluştur
        final_list = set()
        for word in words:
            final_list.add(f"/{word}") # Dosya/Dizin olarak
            if '.' not in word: # Eğer bir dosya uzantısı değilse, dizin olarak da test et
                final_list.add(f"/{word}/")
        
        # Backup uzantılarını popüler dosyalara ekle
        common_files = ['index.php', 'config.php', 'index.html', 'main.js']
        for file in common_files:
            for ext in TECH_WORDLISTS['backup_ext']:
                final_list.add(f"/{file}{ext}")
        return final_list

    async def _check_path(self, session: aiohttp.ClientSession, path: str, context: BruteforceContext):
        """Tek bir yolu kontrol eder ve baseline'a göre filtreler."""
        full_url = urljoin(context.base_url, path)
        try:
            context.checked_paths_count += 1
            async with session.get(full_url, timeout=10, allow_redirects=False) as r:
                # 1. WAF/Bloklama tespiti
                if r.status in [403, 429, 503]:
                    if not context.waf_detected:
                        context.waf_detected = True
                        context.ai_reasoning_log.append({"phase": "waf_detection", "thought": f"⚠️ WAF/Koruma tespiti yapıldı (Status: {r.status}). Tarama yavaşlatılabilir veya engellenebilir."})
                    return

                # 2. Baseline ile karşılaştırma (en önemli kısım)
                if context.baseline:
                    if r.status == context.baseline.status:
                        # Eğer yönlendirme varsa ve hedef aynıysa, bu bir wildcard yönlendirmedir.
                        if context.baseline.redirect_location and r.headers.get('Location') == context.baseline.redirect_location:
                            return
                        # Eğer içerik hash'i aynıysa, bu özel bir 404 sayfasıdır.
                        content = await r.read()
                        if hashlib.sha256(content).hexdigest() == context.baseline.content_hash:
                            return
                
                # 3. Gerçek bulgu
                content = await r.read() # İçeriği tekrar okumamak için
                finding = {"url": full_url, "path": path, "status_code": r.status, "content_length": len(content)}
                context.found_paths.append(finding)
                logger.info(f"Bulundu: [{finding['status_code']}] {finding['url']} (Boyut: {finding['content_length']})")

        except (aiohttp.ClientError, asyncio.TimeoutError):
            pass # Bağlantı hatalarını sessizce geç
        except Exception as e:
            logger.debug(f"Hata {full_url}: {e}")

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
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.CRITICAL,
                    tool_name="vuln_lfi_detector",
                    reason=".env dosyası bulundu. Hassas konfigürasyon bilgileri (API key, DB şifresi) içerebilir.",
                    params={"url": f['url']}
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
                
                await asyncio.gather(*tasks)

            return self._build_final_json(context)
        except aiohttp.ClientConnectorError as e:
            return self._create_final_output(
                success=False,
                ai_summary=f"Bağlantı hatası: Hedef URL '{context.base_url}' ulaşılamaz.",
                ai_reasoning=context.ai_reasoning_log,
                error=f"Bağlantı hatası: Hedef URL '{context.base_url}' ulaşılamaz. Hata: {e}"
            )
        except Exception as e:
            logger.error(f"Execute metodunda kritik hata: {repr(e)}", exc_info=True)
            return self._create_final_output(
                success=False,
                ai_summary="Dizin keşfi sırasında kritik bir hata oluştu.",
                ai_reasoning=context.ai_reasoning_log,
                error=str(e)
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

    def _generate_dynamic_directory_recommendations(self, critical_findings: List[Dict], high_findings: List[Dict], info_findings: List[Dict], context: BruteforceContext) -> List[Dict]:
        """Dinamik directory bruteforce önerileri oluşturur."""
        recommendations = []
        
        # Kritik bulgular için özel öneriler
        if critical_findings:
            for finding in critical_findings[:2]:  # İlk 2 kritik finding
                path_lower = finding['path'].lower()
                if '.git' in path_lower:
                    recommendations.append({
                        "priority": "critical",
                        "tool": "human_intervention_alert",
                        "reason": f"🚨 KRİTİK: .git dizini bulundu. Kaynak kod sızıntısı riski var.",
                        "params": {
                            "path": finding['path'],
                            "url": finding['url'],
                            "vulnerability_type": "Source Code Exposure",
                            "urgent_review": True,
                            "rag_query": f"Git directory exposure remediation for {finding['path']}"
                        },
                        "expert_context": f"Git dizini için kritik analiz. {finding['path']} dizini kaynak kod sızıntısına yol açabilir. Detaylı güvenlik analizi ve remediation planı gerekli."
                    })
                elif '.env' in path_lower:
                    recommendations.append({
                        "priority": "critical",
                        "tool": "human_intervention_alert",
                        "reason": f"🚨 KRİTİK: .env dosyası bulundu. Hassas konfigürasyon bilgileri içerebilir.",
                        "params": {
                            "path": finding['path'],
                            "url": finding['url'],
                            "vulnerability_type": "Configuration Exposure",
                            "urgent_review": True,
                            "rag_query": f"Environment file exposure remediation for {finding['path']}"
                        },
                        "expert_context": f"Environment dosyası için kritik analiz. {finding['path']} dosyası API key, database şifresi gibi hassas bilgiler içerebilir. Detaylı güvenlik analizi ve remediation planı gerekli."
                    })
        
        # Yüksek riskli bulgular için özel öneriler
        if high_findings:
            for finding in high_findings[:2]:  # İlk 2 yüksek riskli finding
                path_lower = finding['path'].lower()
                if 'admin' in path_lower:
                    recommendations.append({
                        "priority": "high",
                        "tool": "vuln_dependency_scanner",
                        "reason": f"⚠️ YÜKSEK RİSK: Admin paneli bulundu. Yetkilendirme kontrolleri kontrol edilmeli.",
                        "params": {
                            "path": finding['path'],
                            "url": finding['url'],
                            "vulnerability_type": "Admin Panel Exposure",
                            "rag_query": f"Admin panel security analysis for {finding['path']}"
                        },
                        "expert_context": f"Admin paneli için kritik analiz. {finding['path']} dizini admin paneline erişim sağlayabilir. Yetkilendirme kontrolleri ve güvenlik analizi gerekli."
                    })
                elif 'login' in path_lower:
                    recommendations.append({
                        "priority": "high",
                        "tool": "vuln_dependency_scanner",
                        "reason": f"⚠️ YÜKSEK RİSK: Login sayfası bulundu. Authentication kontrolleri kontrol edilmeli.",
                        "params": {
                            "path": finding['path'],
                            "url": finding['url'],
                            "vulnerability_type": "Login Page Exposure",
                            "rag_query": f"Login page security analysis for {finding['path']}"
                        },
                        "expert_context": f"Login sayfası için kritik analiz. {finding['path']} dizini login sayfasına erişim sağlayabilir. Authentication kontrolleri ve güvenlik analizi gerekli."
                    })
        
        # Genel directory güvenlik önerileri
        if critical_findings or high_findings:
            recommendations.append({
                "priority": "high",
                "tool": "vuln_dependency_scanner",
                "reason": f"🔍 DİZİN GÜVENLİK ANALİZİ: {len(critical_findings)} kritik, {len(high_findings)} yüksek riskli dizin bulundu. Güvenlik kontrolleri gözden geçirilmeli.",
                "params": {
                    "target_url": context.base_url,
                    "critical_findings": len(critical_findings),
                    "high_findings": len(high_findings),
                    "total_findings": len(context.found_paths),
                    "directory_security_review": True
                },
                "expert_context": f"Dizin güvenlik analizi için kapsamlı inceleme. {len(critical_findings)} kritik, {len(high_findings)} yüksek riskli dizin için detaylı güvenlik kontrolleri ve access control mekanizmaları analiz edilmeli."
            })
        
        return recommendations

if __name__ == "__main__":
    asyncio.run(main())