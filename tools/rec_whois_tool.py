"""
recon_whois_lookup.py - Pentagent Projesi için MCP Uyumlu, Profesyonel WHOIS Analiz Aracı

Amaç: 
Bu araç, bir alan adının (domain) WHOIS kayıt bilgilerini sorgulamakla kalmaz, aynı zamanda
bu bilgileri derinlemesine analiz ederek siber güvenlik açısından anlamlı içgörüler ve 
risk profilleri oluşturur. Sonuçları, Pentagent'in ana kontrol programı olan MCP'nin
otonom olarak bir sonraki adımı belirlemesini sağlayacak standart bir formatta sunar.

Temel Felsefeye Uygunluk:
- Keşfet & Tespit Et: Domain yaşı, registrar itibarı, gizlilik durumu gibi kritik verileri
  tespit ederek potansiyel risk vektörlerini ortaya çıkarır.
- Kanıtla: "Çok yeni domain" veya "bulletproof registrar kullanımı" gibi bulgular,
  sonraki adımlar için somut kanıtlar sunar.
- RAG Girdisi Sağla: Araç, ham teknik veriyi ('data' alanı) zenginleştirerek MCP'nin 
  RAG sistemine kaliteli girdi sağlar. CVE/CVSS detayı içermez.
- Otonom Ajanı Yönlendir: 'recommendations' alanı ile MCP'ye "eğer bu domain çok yeniyse,
  phishing analiz aracı çalıştır" gibi net ve eyleme geçirilebilir komutlar verir.
"""
try:
    import whois
    WHOIS_AVAILABLE = True
except ImportError:
    WHOIS_AVAILABLE = False
import re
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from urllib.parse import urlparse

# PentagentTool base class'ını import et
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

# --- Yapılandırma ve Sabitler ---
# Bu sabitler, kodun daha okunabilir ve yönetilebilir olmasını sağlar.
# Gerçek bir projede bunlar bir config dosyasından yüklenebilir.

# Registrar'lar risklerine göre kategorize edilmiştir.
SUSPICIOUS_REGISTRARS = {
    "high_risk_abuse": ["enom", "pdr ltd", "publicdomainregistry", "namecheap", "tucows", "gandi", "porkbun"],
    "bulletproof_hosting": ["regru", "naunet", "1api", "nicenicllc", "webnic", "internetbs", "santrex", "vdsina"],
    "privacy_service": ["whoisguard", "privacy protect", "domains by proxy", "private by design", "perfect privacy", "redacted for privacy", "gdpr masked"]
}

# Domain yaşının risk seviyesini belirleyen eşik değerleri (gün olarak).
AGE_RISK_THRESHOLDS = {
    "critical": 7,
    "high": 30,
    "medium": 180,
    "low": 365,
}

# Bilinen ve güvenilir kabul edilen DNS sağlayıcıları.
KNOWN_GOOD_NS = {
    "cloudflare": ["cloudflare.com"],
    "google": ["googledomains.com", "google.com"],
    "aws": ["awsdns"],
    "azure": ["azure-dns"]
}

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ReconWhoisLookupTool(MCPTool):
    """
    Gelişmiş WHOIS analizi ile bir domain'in güvenlik profilini çıkarır ve
    MCP için eyleme geçirilebilir öneriler üretir.
    """
    def __init__(self):
        super().__init__(
            name="recon_whois_lookup",
            description="Bir domain hakkında derinlemesine WHOIS analizi yapar ve güvenlik risklerini değerlendirir.",
            category=ToolCategory.RECONNAISSANCE
        )

    def _is_valid_domain(self, domain: str) -> bool:
        """Domain formatının geçerliliğini kontrol eder."""
        if not domain or not isinstance(domain, str): return False
        pattern = re.compile(
            r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        )
        return bool(pattern.match(domain))

    def _clean_domain(self, domain: str) -> str:
        """URL veya gereksiz karakterlerden arındırılmış saf domain adını döndürür."""
        if domain.startswith(('http://', 'https://')):
            domain = urlparse(domain).netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain.rstrip('/').strip().lower()

    def _normalize_date(self, value: Any) -> Optional[str]:
        """Tarih verisini standart ISO formatına dönüştürür."""
        if isinstance(value, list): value = value[0]
        if isinstance(value, datetime): return value.isoformat()
        return str(value) if value else None

    def _normalize_list(self, value: Any) -> List[str]:
        """Farklı formatlardaki liste verilerini standart bir listeye dönüştürür."""
        if not value: return []
        if isinstance(value, str):
            return [item.strip().lower() for item in re.split(r'[,\s]+', value) if item.strip()]
        if isinstance(value, list):
            return sorted(list(set(str(item).strip().lower() for item in value if item)))
        return []

    def _parse_whois_data(self, whois_info) -> Dict[str, Any]:
        """Ham whois nesnesini yapılandırılmış bir sözlüğe dönüştürür."""
        creation_date_str = self._normalize_date(whois_info.creation_date)
        domain_age_days = None
        if creation_date_str:
            try:
                creation_dt = datetime.fromisoformat(creation_date_str.split('T')[0])
                domain_age_days = (datetime.now() - creation_dt).days
            except (ValueError, TypeError):
                pass
        
        raw_text = str(whois_info).lower()
        privacy_protected = any(p in raw_text for p in SUSPICIOUS_REGISTRARS["privacy_service"])
        domain_name = whois_info.domain_name
        if isinstance(domain_name, list):
            domain_name = domain_name[0]

        return {
            "domain": domain_name.lower(),
            "registrar": whois_info.registrar,
            "creation_date": creation_date_str,
            "expiration_date": self._normalize_date(whois_info.expiration_date),
            "updated_date": self._normalize_date(whois_info.updated_date),
            "name_servers": self._normalize_list(whois_info.name_servers),
            "status": self._normalize_list(whois_info.status),
            "registrant_country": whois_info.country,
            "registrant_org": whois_info.org,
            "emails": self._normalize_list(whois_info.emails),
            "privacy_protected": privacy_protected,
            "domain_age_days": domain_age_days,
        }

    def _perform_whois_analysis(self, domain: str) -> Dict[str, Any]:
        """WHOIS verisini toplar ve derinlemesine analiz eder."""
        try:
            w = whois.whois(domain)
            if not w.domain_name:
                raise ValueError(f"'{domain}' için WHOIS bilgisi bulunamadı. Domain tescil edilmemiş veya korumalı olabilir.")
            
            # 1. Temel Veriyi Ayrıştır
            parsed_data = self._parse_whois_data(w)
            
            # 2. Gelişmiş Analizleri Gerçekleştir
            # Registrar İtibarı Analizi
            registrar_analysis = {"risk_level": "low", "categories": [], "insight": "Registrar bilinen bir risk taşımıyor."}
            reg = (parsed_data.get("registrar") or "").lower()
            if any(r in reg for r in SUSPICIOUS_REGISTRARS["bulletproof_hosting"]):
                registrar_analysis = {"risk_level": "critical", "categories": ["bulletproof_hosting"], "insight": "Domain, kötü amaçlı aktörler tarafından tercih edilen 'bulletproof' bir registrar üzerinde barınıyor."}
            elif any(r in reg for r in SUSPICIOUS_REGISTRARS["high_risk_abuse"]):
                registrar_analysis = {"risk_level": "medium", "categories": ["high_risk_abuse"], "insight": "Registrar, yüksek kötüye kullanım (abuse) oranlarıyla biliniyor."}

            # Domain Yaşı Riski Analizi
            age_days = parsed_data.get("domain_age_days")
            age_analysis = {"risk_level": "minimal", "age_category": "eski", "insight": "Domain yeterince eski, bu genellikle güvenilirlik işaretidir."}
            if age_days is not None:
                if age_days <= AGE_RISK_THRESHOLDS["critical"]:
                    age_analysis = {"risk_level": "critical", "age_category": "çok yeni", "insight": f"Domain sadece {age_days} günlük. Bu, geçici phishing/malware kampanyaları için güçlü bir göstergedir."}
                elif age_days <= AGE_RISK_THRESHOLDS["high"]:
                    age_analysis = {"risk_level": "high", "age_category": "yeni", "insight": f"Domain {age_days} günlük. Yeni domainler genellikle daha yüksek risk taşır."}
                elif age_days <= AGE_RISK_THRESHOLDS["medium"]:
                    age_analysis = {"risk_level": "medium", "age_category": "nispeten yeni", "insight": "Domain 6 aydan daha yeni, dikkatli olunmalı."}
            
            # Genel Risk Skoru ve Seviyesi
            risk_map = {"minimal": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
            total_risk_score = risk_map.get(registrar_analysis["risk_level"], 0) + risk_map.get(age_analysis["risk_level"], 0)
            
            overall_risk = "minimal"
            if total_risk_score >= 7: overall_risk = "critical"
            elif total_risk_score >= 5: overall_risk = "high"
            elif total_risk_score >= 3: overall_risk = "medium"
            elif total_risk_score >= 1: overall_risk = "low"
            
            analysis_summary = {
                "registrar_reputation": registrar_analysis,
                "domain_age_risk": age_analysis,
                "overall_risk_level": overall_risk
            }
            
            # Sonuçları birleştir
            return {"raw_data": parsed_data, "analysis": analysis_summary}

        except Exception as e:
            logger.error(f"'{domain}' için WHOIS analizi sırasında hata: {e}")
            raise  # Hatayı yukarıya fırlat ki run_tool yakalasın

    def _generate_mcp_recommendations(self, data: Dict, analysis: Dict) -> List[Dict]:
        """Analiz sonuçlarına göre MCP için eyleme geçirilebilir öneriler üretir."""
        recommendations = []
        domain = data.get("domain")
        risk_level = analysis.get("overall_risk_level")
        age_days = data.get("domain_age_days")

        if risk_level in ["critical", "high"]:
            recommendations.append({
                "priority": "critical",
                "tool": "recon_passive_subdomain_finder",
                "reason": f"Yüksek riskli ({risk_level}) domain tespit edildi. İlişkili altyapıyı haritalamak için subdomain taraması kritik öneme sahip.",
                "params": {"domain": domain}
            })
            recommendations.append({
                "priority": "high",
                "tool": "vuln_blacklist_checker", # Varsayımsal bir sonraki aracımız
                "reason": f"Domain, riskli profili nedeniyle karalistelerde olabilir. Kontrol edilmesi gerekiyor.",
                "params": {"domain": domain}
            })

        if age_days is not None and age_days < 30:
            recommendations.append({
                "priority": "high",
                "tool": "vuln_phishing_likelihood_analyzer", # Varsayımsal bir sonraki aracımız
                "reason": f"Domain {age_days} günlük. Aşırı yeni domainler genellikle oltalama (phishing) saldırılarında kullanılır.",
                "params": {"url": f"http://{domain}"}
            })
        
        if any(ns for provider in KNOWN_GOOD_NS["cloudflare"] for ns in data.get("name_servers", []) if provider in ns):
             recommendations.append({
                "priority": "medium",
                "tool": "recon_cloudflare_ip_resolver", # Varsayımsal bir sonraki aracımız
                "reason": "Hedef Cloudflare arkasında. Gerçek sunucu IP'sini bulmak için ek keşif adımı gerekli.",
                "params": {"domain": domain}
            })

        if data.get("registrant_org"):
            recommendations.append({
                "priority": "low",
                "tool": "recon_osint_google_dorking", # Varsayımsal bir sonraki aracımız
                "reason": "Domain kurumsal bir firmaya ait. Şirket hakkında ek bilgi toplamak faydalı olabilir.",
                "params": {"query": f'intext:"{data.get("registrant_org")}"'}
            })

        return recommendations
        
    def _create_final_output(self, data: Dict, analysis: Dict, recommendations: List, reasoning_log: List) -> Dict:
        """Tüm verileri birleştirerek standart MCP JSON formatını oluşturur."""
        risk_level = analysis.get("overall_risk_level")
        age_days = data.get("domain_age_days", "bilinmiyor")
        
        summary = (
            f"WHOIS analizi tamamlandı. '{data.get('domain')}' domaini için genel risk seviyesi '{risk_level}' olarak değerlendirildi. "
            f"Domain yaşı ({age_days} gün) ve registrar itibarı ana risk faktörleri olarak öne çıkıyor. "
            f"{len(recommendations)} adet eylem önerisi oluşturuldu."
        )

        final_data_structure = {
            "whois_record": data,
            "risk_analysis": analysis
        }
        
        return {
            "success": True,
            "data": final_data_structure,
            "ai_summary": summary,
            "ai_reasoning": reasoning_log,
            "recommendations": recommendations,
            "error": None
        }

    async def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aracın ana giriş noktası. Parametreleri alır, analizi yürütür ve
        standart MCP formatında çıktı üretir.
        """
        # Hem 'domain' hem de 'target' parametresini kabul et
        domain = params.get("domain") or params.get("target")
        reasoning_log = []

        try:
            # 1. Başlangıç ve Doğrulama
            reasoning_log.append({"phase": "initialization", "thought": f"'{domain}' için WHOIS analizi başlatılıyor."})
            if not domain:
                raise ValueError("Domain veya target parametresi zorunludur.")
            
            clean_domain = self._clean_domain(domain)
            if not self._is_valid_domain(clean_domain):
                raise ValueError(f"Geçersiz domain formatı: {clean_domain}")
            
            # 2. Analizi Gerçekleştir
            analysis_result = await asyncio.to_thread(self._perform_whois_analysis, clean_domain) # whois kütüphanesi senkron olduğu için
            raw_data = analysis_result["raw_data"]
            analysis = analysis_result["analysis"]
            
            # 3. Kritik Bulguları Kaydet
            risk_level = analysis.get("overall_risk_level")
            if risk_level in ["critical", "high"]:
                 reasoning_log.append({"phase": "critical_finding", "thought": f"⚠️ Yüksek riskli domain profili tespit edildi (Seviye: {risk_level}). Öncelikli inceleme gerekiyor."})

            # 4. Önerileri Üret
            recommendations = self._generate_mcp_recommendations(raw_data, analysis)
            reasoning_log.append({"phase": "recommendation", "thought": f"{len(recommendations)} adet bir sonraki adım önerisi oluşturuldu."})

            # 5. Standart Çıktıyı Oluştur ve Döndür
            reasoning_log.append({"phase": "completion", "thought": "Analiz başarıyla tamamlandı, sonuçlar formatlanıyor."})
            return self._create_final_output(raw_data, analysis, recommendations, reasoning_log)

        except Exception as e:
            error_message = f"WHOIS aracı çalıştırılırken hata oluştu: {str(e)}"
            logger.error(error_message)
            return {
                "success": False,
                "data": {},
                "ai_summary": "WHOIS bilgileri alınamadı veya analiz sırasında beklenmedik bir hata oluştu.",
                "ai_reasoning": reasoning_log,
                "recommendations": [],
                "error": error_message
            }

async def main():
    """
    Aracın komut satırından test edilmesi için ana fonksiyon.
    Örnek Kullanım: python recon_whois_lookup.py example.com
    """
    import sys
    if len(sys.argv) < 2:
        print("Kullanım: python recon_whois_lookup.py <domain>")
        sys.exit(1)
        
    target_domain = sys.argv[1]
    
    tool = ReconWhoisLookupTool()
    result = await tool.run_tool({"domain": target_domain})
    
    # Sonucu güzel bir JSON formatında yazdır
    print(json.dumps(result, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())