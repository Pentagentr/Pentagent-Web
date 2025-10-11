"""
intel_historical_analyzer.py - Pentagent Projesi için MCP Uyumlu, Tarihsel Analiz Aracı

Amaç: 
Bu araç, bir alan adının Wayback Machine'deki dijital geçmişini derinlemesine tarar.
Amacı, zamanla unutulmuş, artık link verilmeyen ancak hala sunucuda barınıyor olabilecek
eski teknoloji versiyonları, hassas dosyalar (yedekler, konfigürasyonlar), geliştirme
artıkları ve hard-coded sırları (API anahtarları) tespit etmektir.

Temel Felsefeye Uygunluk:
- Keşfet & Tespit Et: Web Arşivi'ni bir istihbarat kaynağı olarak kullanarak, normal
  tarayıcıların göremeyeceği potansiyel zafiyetleri ve bilgi sızıntılarını tespit eder.
- Kanıtla: "2019 yılından kalma bir `config.php.bak` dosyası bulundu" gibi somut,
  doğrulanabilir kanıtlar sunar. Bu bulgular, sonraki adımların temelini oluşturur.
- RAG Girdisi Sağla: Araç, 'data' alanında bulduğu tüm zafiyetli bileşenleri, hassas
  dosya yollarını ve sızan sırları yapılandırılmış bir formatta sunar. Raporlama işini
  merkezi sisteme bırakır.
- Otonom Ajanı Yönlendir: 'recommendations' alanı ile MCP'ye "bulduğum bu `.sql`
  dosyasının hala canlı olup olmadığını kontrol et" veya "bu eski jQuery versiyonu için
  detaylı zafiyet taraması yap" gibi net komutlar vererek otomasyon zincirini devam ettirir.
"""
import asyncio
import re
import json
import logging
from typing import Dict, Any, List
from urllib.parse import urljoin
import aiohttp
from bs4 import BeautifulSoup

# PentagentTool base class'ını import et
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

# --- Yapılandırma ve Sabitler ---
CDX_API_URL = "https://web.archive.org/cdx/search/cdx"

# Aranacak zafiyetli bileşenler ve versiyonları.
VULNERABLE_COMPONENTS = {
    "jQuery": {"patterns": [r'jquery[.-]([0-9]+\.[0-9]+\.?[0-9]*)(?:\.min)?\.js'], "vulnerable_versions": {"1.6.2": "CVE-2011-4969: XSS", "2.2.0": "CVE-2015-9251: XSS"}},
    "AngularJS": {"patterns": [r'angular[.-]([0-9]+\.[0-9]+\.?[0-9]*)(?:\.min)?\.js'], "vulnerable_versions": {"1.2.0": "CVE-2020-7676: XSS"}},
    "Bootstrap": {"patterns": [r'bootstrap[.-]([0-9]+\.[0-9]+\.?[0-9]*)(?:\.min)?\.js'], "vulnerable_versions": {"3.3.0": "CVE-2019-8331: XSS"}}
}

# Aranacak hassas dosya ve yol kalıpları.
SENSITIVE_PATTERNS = {
    "sensitive_files": [r'\.sql(\.gz|\.zip|\.tar)?$', r'\.(bak|backup|old)$', r'(backup|dump)\.zip$', r'\.env', r'config\.php', r'web\.config', r'settings\.py', r'\.git/config', r'\.svn/entries'],
    "admin_panels": [r'/admin/?', r'/administrator/?', r'/wp-admin/?', r'/phpmyadmin/?'],
    "dev_artifacts": [r'phpinfo\.php', r'/test/?', r'/dev/?']
}

# JavaScript içinde aranacak hard-coded sırlar.
JS_SENSITIVE_PATTERNS = {
    "api_key": [r'(?:api[_-]?key|apikey)\s*[:=]\s*["\'][a-zA-Z0-9\-_]{20,}["\']'],
    "access_token": [r'(?:access[_-]?token|accesstoken)\s*[:=]\s*["\'][a-zA-Z0-9\-_]{20,}["\']'],
    "internal_ip": [r'https?://192\.168\.[0-9]{1,3}\.[0-9]{1,3}', r'https?://10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}']
}

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class IntelHistoricalAnalyzerTool(MCPTool):
    """Web Arşivi'ni analiz ederek unutulmuş güvenlik varlıklarını ve zafiyetlerini ortaya çıkarır."""
    def __init__(self):
        super().__init__(
            name="intel_historical_analyzer",
            description="Web Arşivi'ni kullanarak bir hedefin dijital geçmişini analiz eder ve unutulmuş riskleri bulur.",
            category=ToolCategory.THREAT_INTELLIGENCE
        )

    async def _fetch_snapshots(self, session: aiohttp.ClientSession, domain: str) -> List[Dict]:
        """Tüm zaman periyotları için anlık görüntüleri (snapshot) alır."""
        params = {
            'url': f'{domain}/*', 'output': 'json', 'fl': 'timestamp,original',
            'collapse': 'digest', 'limit': 100 
        }
        try:
            async with session.get(CDX_API_URL, params=params) as response:
                if response.status != 200:
                    logger.error(f"CDX API Error: Status {response.status}")
                    return []
                data = await response.json(content_type=None)
                return [{'timestamp': item[0], 'url': item[1]} for item in data[1:]] if data and len(data) > 1 else []
        except Exception as e:
            logger.error(f"Failed to fetch snapshots for {domain}: {e}")
            return []

    async def _analyze_snapshot_content(self, session: aiohttp.ClientSession, snapshot: Dict) -> Dict[str, List]:
        """Tek bir anlık görüntünün içeriğini güvenlik odaklı analiz eder."""
        findings = {"vulnerabilities": [], "sensitive_files": [], "exposed_secrets": [], "admin_panels": [], "dev_artifacts": []}
        archive_url = f"https://web.archive.org/web/{snapshot['timestamp']}id_/{snapshot['url']}"
        try:
            async with session.get(archive_url, timeout=20) as response:
                if response.status != 200: return findings
                content = await response.text(errors='ignore')
                soup = BeautifulSoup(content, 'html.parser')
                
                # Zafiyetli bileşenleri bul
                for tech, info in VULNERABLE_COMPONENTS.items():
                    for pattern in info["patterns"]:
                        for match in re.finditer(pattern, content):
                            version = match.group(1)
                            if version in info["vulnerable_versions"]:
                                findings["vulnerabilities"].append({"component": tech, "version": version, "vulnerability": info["vulnerable_versions"][version], "source_url": snapshot['url']})

                # Hassas dosyaları ve yolları bul
                urls = {a.get('href') for a in soup.find_all('a', href=True)}
                for url in urls:
                    if not url or not isinstance(url, str): continue
                    for category, patterns in SENSITIVE_PATTERNS.items():
                        for pattern in patterns:
                            if re.search(pattern, url, re.IGNORECASE):
                                findings[category].append({"path": url, "found_in_period": snapshot['timestamp'][:8]})
                
                # JS içinde sırları ara
                for script in soup.find_all("script"):
                    script_content = str(script.string)
                    for secret_type, patterns in JS_SENSITIVE_PATTERNS.items():
                        for pattern in patterns:
                            for match in re.finditer(pattern, script_content):
                                findings["exposed_secrets"].append({"type": secret_type, "match": match.group(0), "source_url": snapshot['url']})
        except Exception as e:
            logger.warning(f"Could not analyze snapshot {archive_url}: {e}")
        return findings

    async def _perform_historical_analysis(self, domain: str) -> Dict[str, Any]:
        """Tarihsel analizin ana iş mantığını yürütür."""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=30)
        final_findings = {"vulnerabilities": [], "sensitive_files": [], "exposed_secrets": [], "admin_panels": [], "dev_artifacts": []}
        
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            snapshots = await self._fetch_snapshots(session, domain)
            if not snapshots:
                raise ValueError(f"'{domain}' için Wayback Machine'de hiç kayıt bulunamadı.")
            
            tasks = [self._analyze_snapshot_content(session, s) for s in snapshots[:25]] # En alakalı 25 snapshot'ı analiz et
            results = await asyncio.gather(*tasks)

            for category in final_findings.keys():
                unique_items = {json.dumps(d, sort_keys=True) for res in results for d in res.get(category, [])}
                final_findings[category] = [json.loads(s) for s in unique_items]
        return final_findings
    
    def _generate_mcp_recommendations(self, findings: Dict, domain: str) -> List[Dict]:
        """Analiz bulgularına göre MCP için eyleme geçirilebilir öneriler üretir."""
        recommendations = []
        base_url = f"http://{domain}"

        for vuln in findings.get("vulnerabilities", []):
            recommendations.append({"priority": "critical", "tool": "vuln_component_scanner", "reason": f"Tarihsel veride zafiyetli '{vuln['component']} v{vuln['version']}' ({vuln['vulnerability']}) tespit edildi. Bu bileşenin hala kullanımda olup olmadığını doğrula.", "params": {"url": vuln['source_url'], "component": vuln['component']}})
        for f in findings.get("sensitive_files", []):
            full_url = urljoin(base_url, f['path'])
            recommendations.append({"priority": "critical", "tool": "intel_sensitive_file_retriever", "reason": f"Tarihsel veride potansiyel bir hassas dosya ('{f['path']}') bulundu. Bu dosyanın hala erişilebilir olup olmadığını kontrol et.", "params": {"url": full_url}})
        for panel in findings.get("admin_panels", []):
            full_url = urljoin(base_url, panel['path'])
            recommendations.append({"priority": "high", "tool": "enum_http_directory_bruteforcer", "reason": f"Geçmişte bir yönetim paneli ('{panel['path']}') tespit edildi. Varlığını doğrulamak için dizin taraması yap.", "params": {"url": full_url, "wordlist": "common_admin_locations.txt"}})
        for secret in findings.get("exposed_secrets", []):
            recommendations.append({"priority": "high", "tool": "vuln_credential_tester", "reason": f"Tarihsel bir JS dosyasında hard-coded bir sır ({secret['type']}) bulundu. Bu sırrın hala geçerli olup olmadığını test et.", "params": {"credential": secret['match'], "type": secret['type']}})
        return recommendations

    def _create_final_output(self, findings: Dict, recommendations: List, reasoning_log: List) -> Dict:
        """Tüm verileri birleştirerek standart MCP JSON formatını oluşturur."""
        critical_findings_count = len(findings.get("vulnerabilities", [])) + len(findings.get("sensitive_files", []))
        summary = (
            f"Tarihsel analiz tamamlandı. Toplam {critical_findings_count} adet kritik bulgu "
            f"(zafiyetli bileşenler ve hassas dosyalar) ve {len(findings.get('exposed_secrets', []))} adet "
            f"potansiyel sır sızıntısı tespit edildi. MCP ajanı için {len(recommendations)} adet "
            f"eyleme dönüştürülebilir öneri oluşturuldu."
        )
        return {
            "success": True,
            "data": findings,
            "ai_summary": summary,
            "ai_reasoning": reasoning_log,
            "recommendations": recommendations,
            "error": None
        }

    async def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Aracın ana giriş noktası. Parametreleri alır, analizi yürütür ve standart MCP formatında çıktı üretir."""
        domain = params.get("domain")
        reasoning_log = []
        try:
            reasoning_log.append({"phase": "initialization", "thought": f"'{domain}' için tarihsel analiz başlatılıyor. Wayback Machine verileri çekilecek."})
            if not domain: raise ValueError("Domain parametresi zorunludur.")
            
            findings = await self._perform_historical_analysis(domain)
            
            critical_count = len(findings.get("vulnerabilities", [])) + len(findings.get("sensitive_files", []))
            if critical_count > 0:
                reasoning_log.append({"phase": "critical_finding", "thought": f"⚠️ {critical_count} adet kritik bulgu (zafiyetli bileşenler/hassas dosyalar) tespit edildi."})
            else:
                reasoning_log.append({"phase": "analysis_complete", "thought": "Analiz tamamlandı, kritik bir bulguya rastlanmadı."})

            recommendations = self._generate_mcp_recommendations(findings, domain)
            reasoning_log.append({"phase": "recommendation", "thought": f"Bulgulara dayanarak {len(recommendations)} adet bir sonraki adım önerisi oluşturuldu."})

            reasoning_log.append({"phase": "completion", "thought": "Analiz başarıyla tamamlandı, sonuçlar formatlanıyor."})
            return self._create_final_output(findings, recommendations, reasoning_log)

        except Exception as e:
            error_message = f"Tarihsel analiz aracı çalıştırılırken hata oluştu: {str(e)}"
            logger.error(error_message)
            reasoning_log.append({"phase": "error", "thought": error_message})
            return {
                "success": False, "data": {}, "ai_summary": "Tarihsel analiz sırasında bir hata oluştu. Hedef için yeterli arşiv verisi olmayabilir veya API limitlerine takılmış olabilir.",
                "ai_reasoning": reasoning_log, "recommendations": [], "error": error_message
            }

async def main():
    """Aracın komut satırından test edilmesi için ana fonksiyon."""
    import sys
    if len(sys.argv) < 2:
        print("Kullanım: python intel_historical_analyzer.py <domain>")
        sys.exit(1)
        
    target_domain = sys.argv[1]
    tool = IntelHistoricalAnalyzerTool()
    result = await tool.run_tool({"domain": target_domain})
    print(json.dumps(result, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())