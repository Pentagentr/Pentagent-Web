"""
intel_code_leak_scanner.py - Pentagent Projesi için MCP Uyumlu, Kod Sızıntısı Tarama Aracı

Amaç: 
Bu araç, GitHub üzerinde bir hedefle (domain, şirket adı) ilişkili olabilecek hassas
bilgi sızıntılarını (API anahtarları, şifreler, özel anahtarlar, konfigürasyon dosyaları)
tespit etmek için tasarlanmıştır. Akıllı dork'lar üretir, bulguları gürültüden arındırır
ve risklerini skorlar.

Temel Felsefeye Uygunluk:
- Keşfet & Tespit Et: GitHub'ın devasa kod havuzunu birincil istihbarat kaynağı olarak
  kullanarak, hedefin unuttuğu veya farkında olmadığı kod ve sır sızıntılarını tespit eder.
- Kanıtla: Her bulguyu, sızıntının URL'si, dosya yolu ve sızıntıyı içeren kod parçası
  ('snippet') ile somut bir şekilde kanıtlar.
- RAG Girdisi Sağla: Araç, bulduğu tüm sızıntıları, risk skorları ve kanıtlarıyla
  birlikte yapılandırılmış bir formatta 'data' alanında sunar. Bu, RAG sisteminin
  son raporda "GitHub üzerinde 3 kritik sır sızıntısı tespit edildi" gibi bir bölüm
  oluşturması için mükemmel bir girdidir.
- Otonom Ajanı Yönlendir: 'recommendations' alanı ile MCP'ye, "bulduğum bu API
  anahtarının hala geçerli olup olmadığını `vuln_credential_tester` ile doğrula" gibi
  net, anında eyleme geçirilebilir ve otomasyon zincirini devam ettiren komutlar verir.
"""
import asyncio
import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
import aiohttp
from datetime import datetime

# PentagentTool base class'ını import et
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

# --- Yapılandırma ve Sabitler ---
GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_API_TOKEN") # MCP ortamından sağlanmalı

# Gürültüyü azaltmak için aramalara eklenecek negatif anahtar kelimeler
NEGATIVE_KEYWORDS = " -example -test -demo -tutorial -docs -sample -placeholder"

# Aranacak dork şablonları
BASE_DORKS = {
    'credentials': ['"{target}" password', '"{target}" api_key', '"{target}" secret_key', '"{target}" "private key"'],
    'config_files': ['"{target}" filename:.env', '"{target}" filename:database extension:yml', '"{target}" filename:settings extension:py SECRET_KEY'],
    'cloud_services': ['"{target}" AKIA', '"{target}" "service_account" extension:json'],
    'database': ['"{target}" mongodb://', '"{target}" postgres:// password']
}

# Sızıntıları tespit etmek ve skorlamak için kullanılan regex kalıpları
SENSITIVE_PATTERNS = {
    'critical': {'patterns': [r'-----BEGIN (?:RSA|OPENSSH) PRIVATE KEY-----', r'AKIA[0-9A-Z]{16}'], 'score': 9},
    'high': {'patterns': [r'mongodb(?:\+srv)?://[^:]+:[^@]+@[^/]+', r'(?:api|secret)[_-]?key["\s:=]+["\']?[0-9a-zA-Z\-_]{20,}["\']?'], 'score': 8},
    'medium': {'patterns': [r'password["\s:=]+["\']?[^"\s]{8,}["\']?'], 'score': 6}
}

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class IntelCodeLeakScannerTool(MCPTool):
    """GitHub'da hedefe yönelik hassas bilgi sızıntılarını tespit eder."""
    def __init__(self):
        super().__init__(
            name="intel_code_leak_scanner",
            description="GitHub'da dork'lar kullanarak hassas bilgi ve sır sızıntılarını arar.",
            category=ToolCategory.THREAT_INTELLIGENCE
        )

    def _generate_dorks(self, target: str) -> List[str]:
        """Hedefe özel arama dork'ları oluşturur."""
        dorks = []
        for category in BASE_DORKS.values():
            for pattern in category:
                dorks.append(f'{pattern.format(target=target)}{NEGATIVE_KEYWORDS}')
        return list(set(dorks))

    async def _search_github(self, session: aiohttp.ClientSession, dork: str) -> List[Dict]:
        """Tek bir dork ile GitHub'da arama yapar."""
        params = {'q': dork, 'per_page': 10}
        leaks = []
        try:
            async with session.get(f"{GITHUB_API_URL}/search/code", params=params, timeout=20) as response:
                if response.status == 403 or response.status == 429:
                    logger.warning(f"Rate limit hit for dork: {dork}. Skipping.")
                    await asyncio.sleep(5) # Rate limit yendiğinde bekle
                    return []
                if response.status != 200:
                    logger.error(f"GitHub API error {response.status} for dork: {dork}")
                    return []
                
                data = await response.json()
                for item in data.get("items", []):
                    snippet = item.get("text_matches", [{}])[0].get("fragment", "")
                    # Akıllı filtreleme: Örnek kodları ve dökümantasyonu atla
                    if any(kw in snippet.lower() for kw in ['your-api-key', 'dummy', 'placeholder', 'example.com']):
                        continue
                    leaks.append({
                        "url": item.get("html_url"),
                        "path": item.get("path"),
                        "repository": item.get("repository", {}).get("full_name"),
                        "snippet": snippet
                    })
        except Exception as e:
            logger.error(f"Error searching with dork '{dork}': {e}")
        return leaks

    def _analyze_and_score_leak(self, leak: Dict) -> Optional[Dict]:
        """Bir sızıntıyı analiz eder, skorlar ve gereksizse eler."""
        snippet = leak.get("snippet", "")
        for risk_level, config in SENSITIVE_PATTERNS.items():
            for pattern in config['patterns']:
                match = re.search(pattern, snippet)
                if match:
                    leak["risk_score"] = config['score']
                    leak["risk_level"] = risk_level.upper()
                    leak["detected_pattern"] = pattern
                    leak["match"] = match.group(0)
                    return leak
        return None # Eşleşme yoksa sızıntıyı dikkate alma

    async def _perform_leak_scan(self, target: str) -> List[Dict]:
        """Kod sızıntısı taramasının ana mantığını yürütür."""
        headers = {
            "Accept": "application/vnd.github.v3.text-match+json",
            "Authorization": f"Bearer {GITHUB_TOKEN}"
        }
        dorks = self._generate_dorks(target)
        all_leaks = []
        
        async with aiohttp.ClientSession(headers=headers) as session:
            tasks = [self._search_github(session, dork) for dork in dorks[:15]] # En önemli 15 dork
            results = await asyncio.gather(*tasks)
            
            # Duplikasyonları URL bazında kaldır
            unique_leaks_map = {item['url']: item for sublist in results for item in sublist}
            
            for leak in unique_leaks_map.values():
                analyzed_leak = self._analyze_and_score_leak(leak)
                if analyzed_leak:
                    all_leaks.append(analyzed_leak)

        # En yüksek risk skoruna göre sırala
        return sorted(all_leaks, key=lambda x: x.get("risk_score", 0), reverse=True)

    def _generate_mcp_recommendations(self, findings: List[Dict]) -> List[Dict]:
        """Bulgulara göre MCP için eyleme geçirilebilir öneriler üretir."""
        recommendations = []
        for leak in findings:
            if leak.get("risk_score", 0) >= 8: # Sadece yüksek ve kritik riskliler için
                recommendations.append({
                    "priority": "critical",
                    "tool": "vuln_credential_tester",
                    "reason": f"GitHub'da '{leak['risk_level']}' seviyesinde bir sır sızıntısı ('{leak['path']}') bulundu. Sırrın geçerliliğinin acilen test edilmesi gerekiyor.",
                    "params": {"credential": leak['match'], "type": leak['risk_level']}
                })
        return recommendations

    def _create_final_output(self, findings: List[Dict], recommendations: List[Dict], reasoning_log: List[Dict]) -> Dict:
        """Tüm verileri birleştirerek standart MCP JSON formatını oluşturur."""
        critical_count = sum(1 for f in findings if f.get("risk_level") == "CRITICAL")
        high_count = sum(1 for f in findings if f.get("risk_level") == "HIGH")

        summary = (
            f"GitHub sızıntı taraması tamamlandı. {critical_count} kritik ve {high_count} yüksek seviyeli potansiyel sır sızıntısı bulundu. "
            f"MCP ajanı için {len(recommendations)} adet doğrulama görevi oluşturuldu."
        )
        if not findings:
            summary = "GitHub sızıntı taraması tamamlandı. Hedefle ilişkili dikkate değer bir sır sızıntısı bulunamadı."

        return {
            "success": True,
            "data": {"leaks": findings},
            "ai_summary": summary,
            "ai_reasoning": reasoning_log,
            "recommendations": recommendations,
            "error": None
        }

    async def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Aracın ana giriş noktası."""
        target = params.get("domain") or params.get("company_name")
        reasoning_log = []
        try:
            reasoning_log.append({"phase": "initialization", "thought": f"'{target}' için GitHub kod sızıntısı taraması başlatılıyor."})
            if not GITHUB_TOKEN:
                raise PermissionError("GITHUB_API_TOKEN ortam değişkeni ayarlanmamış. Tarama yapılamıyor.")
            if not target:
                raise ValueError("Tarama için 'domain' veya 'company_name' parametresi zorunludur.")
            
            findings = await self._perform_leak_scan(target)
            
            if findings:
                reasoning_log.append({"phase": "critical_finding", "thought": f"⚠️ {len(findings)} adet potansiyel sır sızıntısı tespit edildi. En yüksek risk skoru: {findings[0]['risk_score']}."})
            else:
                reasoning_log.append({"phase": "analysis_complete", "thought": "Analiz tamamlandı. Kritik bir sızıntıya rastlanmadı."})

            recommendations = self._generate_mcp_recommendations(findings)
            reasoning_log.append({"phase": "recommendation", "thought": f"Bulgulara dayanarak {len(recommendations)} adet bir sonraki adım önerisi oluşturuldu."})

            reasoning_log.append({"phase": "completion", "thought": "Tarama başarıyla tamamlandı, sonuçlar formatlanıyor."})
            return self._create_final_output(findings, recommendations, reasoning_log)

        except Exception as e:
            error_message = f"Kod sızıntısı tarayıcısı çalıştırılırken hata oluştu: {str(e)}"
            logger.error(error_message)
            reasoning_log.append({"phase": "error", "thought": error_message})
            return {
                "success": False, "data": {}, "ai_summary": "GitHub kod sızıntısı taraması sırasında bir hata oluştu. API token'ı geçersiz olabilir veya rate limit'e takılmış olabilirsiniz.",
                "ai_reasoning": reasoning_log, "recommendations": [], "error": error_message
            }

async def main():
    """Aracın komut satırından test edilmesi için ana fonksiyon."""
    import sys
    if not GITHUB_TOKEN:
        print("HATA: Lütfen GITHUB_API_TOKEN ortam değişkenini ayarlayın.")
        sys.exit(1)
    if len(sys.argv) < 2:
        print("Kullanım: python intel_code_leak_scanner.py <domain_veya_şirket_adı>")
        sys.exit(1)
        
    target = sys.argv[1]
    tool = IntelCodeLeakScannerTool()
    result = await tool.run_tool({"domain": target})
    print(json.dumps(result, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())