# agent_core/report_generator.py

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from agent_core.state import AgentState

# PDF generation imports
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib import colors
    PDF_GENERATION_AVAILABLE = True
except ImportError:
    PDF_GENERATION_AVAILABLE = False

# LLM Processing entegrasyonu
try:
    from src.llm_processing.llm_report_generator import LLMReportGenerator
    from src.llm_processing.domain_vocab_injector import DomainVocabInjector
    LLM_PROCESSING_AVAILABLE = True
except ImportError:
    LLM_PROCESSING_AVAILABLE = False

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Profesyonel penetrasyon testi raporu oluşturur - RAG ve LLM entegrasyonu ile."""
    
    def __init__(self, rag_client=None, llm_api_key=None):
        self.rag_client = rag_client
        if LLM_PROCESSING_AVAILABLE and llm_api_key:
            self.llm_generator = LLMReportGenerator(api_key=llm_api_key)
            self.vocab_injector = DomainVocabInjector()
            logger.info("LLM Processing entegrasyonu aktif")
        else:
            self.llm_generator = None
            self.vocab_injector = None
        
        # RAG entegrasyonu için CVE/CVSS veritabanı
        self.cve_database = {}
        self.cvss_cache = {}
        logger.info("Professional Pentest Report Generator başlatıldı - RAG entegrasyonu hazır.")
        
    # ==========================================================================
    # YENİ VE GÜNCELLENMİŞ YARDIMCI FONKSİYONLAR
    # ==========================================================================

    def _calculate_risk_score(self, findings: List[Dict[str, Any]]) -> int:
        """
        TOOL ÇIKTILARINA DAYALI DİNAMİK RİSK SKORU HESAPLAMA
        Her tool çıktısı için belirli skorlar, severity'ye göre weighted scoring
        """
        if not findings:
            return 0
        
        total_score = 0
        
        # 1. SEVERITY BAZLI SKORLAMA (EN YÜKSEK ÖNCELİK)
        severity_weights = {
            'critical': 15,  # Her kritik bulgu +15
            'high': 10,      # Her yüksek bulgu +10
            'medium': 5,     # Her orta bulgu +5
            'low': 2,        # Her düşük bulgu +2
            'info': 1        # Her info bulgu +1
        }
        
        for finding in findings:
            severity = finding.get('severity', 'info').lower()
            weight = severity_weights.get(severity, 1)
            total_score += weight
        
        # 2. TOOL ÇIKTILARININ DETAY SEVİYESİNE GÖRE BONUS
        # Port scanning
        open_ports = [f for f in findings if 'port' in f.get('title', '').lower() or 'service' in f.get('title', '').lower()]
        if len(open_ports) >= 10:
            total_score += 20  # Çok fazla açık port = kritik
        elif len(open_ports) >= 5:
            total_score += 10
        elif len(open_ports) >= 1:
            total_score += 5
        
        # Endpoint discovery
        endpoints = [f for f in findings if 'endpoint' in f.get('title', '').lower() or 'api' in f.get('title', '').lower()]
        if len(endpoints) >= 1:  # Endpoint bulgusu varsa
            # Endpoint count'u title'dan çıkar
            for ep in endpoints:
                title = ep.get('title', '')
                if 'endpoint bulundu' in title.lower():
                    try:
                        count = int(title.split('endpoint bulundu')[0].split(':')[-1].strip())
                        if count >= 50:
                            total_score += 30  # 50+ endpoint = kritik
                        elif count >= 30:
                            total_score += 20
                        elif count >= 15:
                            total_score += 15
                        elif count >= 5:
                            total_score += 10
                        else:
                            total_score += 5
                        break
                    except:
                        total_score += 10  # Parse edemediyse default
        
        # Web crawling (forms, paths, pages)
        web_findings = [f for f in findings if 'crawling' in f.get('title', '').lower() or 'form' in f.get('title', '').lower()]
        if len(web_findings) >= 1:
            for wf in web_findings:
                title = wf.get('title', '')
                # Form count'u çıkar
                if 'form' in title.lower():
                    try:
                        form_count = int([x for x in title.split() if 'form' in x.lower()][0].split('form')[0].strip().split()[-1])
                        if form_count >= 10:
                            total_score += 25  # 10+ form = kritik injection riski
                        elif form_count >= 5:
                            total_score += 15
                        elif form_count >= 2:
                            total_score += 8
                        break
                    except:
                        total_score += 10
        
        # Directory bruteforce
        directory_findings = [f for f in findings if 'directory' in f.get('title', '').lower() or 'dizin' in f.get('title', '').lower()]
        for df in directory_findings:
            severity = df.get('severity', '').lower()
            if severity == 'critical':
                total_score += 20  # Kritik dizin (admin, config) = çok tehlikeli
            elif severity == 'high':
                total_score += 12  # Yüksek riskli dizin
            elif severity == 'info':
                total_score += 2   # Info dizin (images vb)
        
        # Teknoloji tespiti
        tech_findings = [f for f in findings if 'teknoloji' in f.get('title', '').lower() or 'technology' in f.get('title', '').lower()]
        if len(tech_findings) >= 1:
            for tf in tech_findings:
                title = tf.get('title', '')
                try:
                    tech_count = int([x for x in title.split() if x.isdigit()][0])
                    if tech_count >= 15:
                        total_score += 15  # Çok fazla teknoloji = saldırı yüzeyi geniş
                    elif tech_count >= 10:
                        total_score += 10
                    elif tech_count >= 5:
                        total_score += 5
                    break
                except:
                    total_score += 5
        
        # Subdomain discovery
        subdomain_findings = [f for f in findings if 'subdomain' in f.get('title', '').lower() or 'altdomain' in f.get('title', '').lower()]
        if len(subdomain_findings) >= 1:
            for sf in subdomain_findings:
                title = sf.get('title', '')
                try:
                    sub_count = int([x for x in title.split() if x.isdigit()][0])
                    if sub_count >= 20:
                        total_score += 20  # Çok fazla subdomain = geniş saldırı yüzeyi
                    elif sub_count >= 10:
                        total_score += 12
                    elif sub_count >= 5:
                        total_score += 7
                    break
                except:
                    total_score += 5
        
        # 3. GERÇEK ZAFİYET TESPİTLERİ (SQL, XSS, LFI vb)
        real_vulns = [f for f in findings if any(keyword in f.get('title', '').lower() 
                     for keyword in ['sql', 'xss', 'injection', 'lfi', 'rfi', 'ssrf', 'xxe', 'rce', 'csrf'])]
        if len(real_vulns) > 0:
            total_score += min(len(real_vulns) * 20, 50)  # Her gerçek zafiyet +20, max +50
        
        # 4. KRİTİK YOL/ENDPOINT TESPİTİ (admin, login, api)
        critical_paths = [f for f in findings if any(keyword in f.get('title', '').lower() 
                         for keyword in ['admin', 'login', 'auth', 'dashboard', 'panel', 'config', 'backup'])]
        if len(critical_paths) >= 5:
            total_score += 20  # 5+ kritik yol = yüksek risk
        elif len(critical_paths) >= 3:
            total_score += 12
        elif len(critical_paths) >= 1:
            total_score += 8
        
        # Skorı 0-100 arası normalize et
        normalized_score = min(int(total_score), 100)
        
        # Minimum skor: Eğer herhangi bir bulgu varsa en az 15 puan ver
        if len(findings) > 0 and normalized_score < 15:
            normalized_score = 15
        
        return normalized_score

    def _get_owasp_reference(self, finding: Dict[str, Any]) -> str:
        """Bulgu başlığına göre ilgili OWASP Top 10 referansını döndürür."""
        title = finding.get("title", "").lower()
        owasp_map = {
            "injection": "A03:2021 - Injection", "sql": "A03:2021 - Injection", "xss": "A03:2021 - Injection",
            "broken access control": "A01:2021 - Broken Access Control", "idor": "A01:2021 - Broken Access Control",
            "cryptographic failures": "A02:2021 - Cryptographic Failures", "ssl": "A02:2021 - Cryptographic Failures",
            "security misconfiguration": "A05:2021 - Security Misconfiguration", "header": "A05:2021 - Security Misconfiguration", "origin ip": "A05:2021 - Security Misconfiguration",
            "vulnerable and outdated components": "A06:2021 - Vulnerable and Outdated Components", "dependency": "A06:2021 - Vulnerable and Outdated Components",
            "identification and authentication failures": "A07:2021 - Identification and Authentication Failures", "auth": "A07:2021 - Identification and Authentication Failures",
            "server-side request forgery": "A10:2021 - Server-Side Request Forgery (SSRF)", "ssrf": "A10:2021 - Server-Side Request Forgery (SSRF)"
        }
        for keyword, reference in owasp_map.items():
            if keyword in title:
                return reference
        return "İlgili Kategori Bulunamadı"
        
    def _generate_business_impact(self, finding: Dict[str, Any]) -> str:
        """(LLM İÇİN İDEAL) Bulgunun teknik olmayan, iş odaklı etkisini oluşturur."""
        severity = finding.get("severity", "low")
        if severity == "critical":
            return "Bu zafiyet, servis kesintilerine (gelir kaybı), büyük ölçekli veri sızıntılarına (yasal ve finansal yaptırımlar) ve marka itibarının ciddi şekilde zedelenmesine neden olabilir. Sistemin tamamen ele geçirilme riski bulunmaktadır."
        elif severity == "high":
            return "Bu zafiyet, hassas müşteri verilerinin ifşa olmasına, yetkisiz sistemsel değişikliklere veya servis sürekliliğinin olumsuz etkilenmesine yol açabilir. Bu durum, müşteri güvenini sarsabilir ve orta ölçekli finansal kayıplara neden olabilir."
        elif severity == "medium":
            return "Bu zafiyet, sınırlı yetkilerle kullanıcı bilgilerinin ifşa olmasına veya uygulamanın istenmeyen davranışlar sergilemesine neden olabilir. Genellikle diğer zafiyetlerle birleştirildiğinde daha büyük riskler oluşturur."
        else:
            return "Bu bulgu, doğrudan bir iş etkisine sahip olmasa da, saldırganlar için bilgi toplama aşamasında değerli veriler sunabilir ve daha karmaşık saldırıların önünü açabilir. Güvenlik duruşunu zayıflatır."

    def _get_remediation(self, finding: Dict[str, Any]) -> str:
        """Dinamik ve gerçek penetrasyon test uzmanları için detaylı çözüm önerileri"""
        title = finding.get("title", "").lower()
        severity = finding.get("severity", "low")
        
        # Dinamik remediation - bulgu tipine ve ciddiyetine göre
        if "origin ip" in title:
            if severity == "critical":
                return """🚨 ACİL MÜDAHALE GEREKLİ:
1. **DNS Kayıtlarını Hemen Gözden Geçirin:** Tüm DNS kayıtlarınızın (A, AAAA, MX, TXT) Cloudflare üzerinden proxy'lendiğinden emin olun. Özellikle mail, ftp, cpanel gibi subdomain'lerin IP adresini sızdırmadığını kontrol edin.

2. **Origin Sunucuyu Derhal Kilitleyin:** Web sunucunuzun güvenlik duvarı kurallarını, sadece Cloudflare'e ait IP aralıklarından gelen isteklere izin verecek şekilde yapılandırın. Cloudflare IP listesi: https://www.cloudflare.com/ips/

3. **Geçmiş Verileri Temizleyin:** SecurityTrails, Shodan, Censys gibi geçmiş DNS veritabanlarını kontrol ederek eski kayıtların temizlenmesini talep edin.

4. **Monitoring Kurun:** Origin IP sızıntısını tespit etmek için otomatik monitoring sistemi kurun."""
            else:
                return """⚠️ ÖNCELİKLİ DÜZELTME:
1. **DNS Konfigürasyonunu Gözden Geçirin:** Tüm DNS kayıtlarının Cloudflare üzerinden proxy'lendiğinden emin olun.
2. **Firewall Kurallarını Güncelleyin:** Origin sunucuyu sadece Cloudflare IP'lerinden erişilebilir hale getirin."""
        
        elif "sql injection" in title:
            if severity == "critical":
                return """🚨 KRİTİK GÜVENLİK AÇIĞI - ACİL MÜDAHALE:
1. **Parametreli Sorgular (Prepared Statements) Kullanın:** Veritabanı sorguları oluştururken kullanıcı girdilerini asla doğrudan birleştirmeyin. Tüm modern programlama dillerinde bulunan parametreli sorguları veya ORM kütüphanelerini kullanın.

2. **En Az Yetki Prensibi:** Uygulamanızın veritabanı kullanıcısına sadece ihtiyaç duyduğu yetkileri (SELECT, INSERT, UPDATE) verin. DROP, TRUNCATE gibi tehlikeli komutları çalıştırma yetkisi olmamalıdır.

3. **Input Validation:** Tüm kullanıcı girdilerini sunucu tarafında validate edin ve sanitize edin.

4. **WAF Kuralları:** SQL injection saldırılarını engellemek için Web Application Firewall kurallarını aktifleştirin."""
            else:
                return """⚠️ SQL Injection Riski:
1. **Prepared Statements Kullanın:** Kullanıcı girdilerini doğrudan sorguya birleştirmeyin.
2. **Input Validation:** Sunucu tarafında girdi doğrulama yapın."""
        
        elif "missing security headers" in title or "header" in title:
            return """🛡️ GÜVENLİK BAŞLIKLARI EKSİK:
1. **HSTS (HTTP Strict Transport Security):** HTTPS zorunluluğu için HSTS başlığını ekleyin.
2. **CSP (Content Security Policy):** XSS saldırılarını engellemek için CSP politikası oluşturun.
3. **X-Frame-Options:** Clickjacking saldırılarını engellemek için X-Frame-Options başlığını ekleyin.
4. **X-Content-Type-Options:** MIME type sniffing saldırılarını engellemek için nosniff değerini ekleyin."""
        
        elif "vulnerable components" in title or "outdated" in title:
            return """📦 GÜNCELLENMİŞ BİLEŞENLER:
1. **Bağımlılık Taraması:** Dependabot, Snyk gibi araçlarla bağımlılıkları sürekli tarayın.
2. **Acil Yama Politikası:** Kritik zafiyetler için 48 saat içinde yama uygulama politikası oluşturun.
3. **Software Bill of Materials (SBOM):** Tüm kullanılan bileşenlerin envanterini çıkarın."""
        
        # Genel fallback
        return finding.get('recommendation_summary', 'İlgili bileşen için yayınlanan güvenlik güncellemelerini ve yamalarını uygulayın.')
    
    def _categorize_findings_by_owasp(self, findings: List[Dict[str, Any]]) -> Dict[str, int]:
        """Bulguları OWASP Top 10 2021'e göre kategorize eder."""
        categories = {}
        for finding in findings:
            category = self._get_owasp_reference(finding)
            if category != "İlgili Kategori Bulunamadı":
                categories[category] = categories.get(category, 0) + 1
        return categories
    
    def _calculate_overall_risk_level(self, findings_summary: Dict[str, Any]) -> str:
        """Genel risk seviyesini dinamik olarak hesaplar"""
        critical = findings_summary.get('by_severity', {}).get('critical', 0)
        high = findings_summary.get('by_severity', {}).get('high', 0)
        medium = findings_summary.get('by_severity', {}).get('medium', 0)
        low = findings_summary.get('by_severity', {}).get('low', 0)
        
        if critical > 0:
            return "CRITICAL"
        if high >= 5:
            return "HIGH"
        elif high >= 2:
            return "MEDIUM-HIGH"
        elif high >= 1:
            return "MEDIUM"
        if medium >= 10:
            return "MEDIUM"
        elif medium >= 5:
            return "LOW-MEDIUM"
        elif medium >= 1:
            return "LOW"
        if low > 0:
            return "LOW"
        return "MINIMAL"

    # ==========================================================================
    # RAG ENTEGRASYONU - CVE/CVSS VE TARAMA SONUÇLARI
    # ==========================================================================

    async def _rag_search_cve_info(self, vulnerability_type: str, technology: str = None) -> Dict[str, Any]:
        """RAG ile CVE bilgilerini ara ve CVSS skorlarını al"""
        try:
            if not self.rag_client:
                return {"error": "RAG client not available"}
            
            # Spesifik RAG sorgusu oluştur
            if technology and technology != "N/A":
                query = f"{technology} {vulnerability_type} CVE vulnerability"
            else:
                query = f"{vulnerability_type} CVE vulnerability"
            
            # RAG'dan CVE bilgilerini al
            rag_results = await self.rag_client.search(query)
            
            if rag_results and len(rag_results) > 0:
                # En relevant sonucu al
                best_match = rag_results[0]
                
                return {
                    "cve_id": best_match.get("cve_id", "N/A"),
                    "cvss_score": best_match.get("cvss_score", "N/A"),
                    "cvss_vector": best_match.get("cvss_vector", "N/A"),
                    "description": best_match.get("description", "No description available"),
                    "published_date": best_match.get("published_date", "N/A"),
                    "severity": best_match.get("severity", "unknown"),
                    "exploit_available": best_match.get("exploit_available", False),
                    "references": best_match.get("references", [])
                }
            else:
                # Fallback: generic CVE bilgisi
                return {
                    "cve_id": "N/A",
                    "cvss_score": "N/A",
                    "cvss_vector": "N/A",
                    "description": f"{vulnerability_type} vulnerability detected",
                    "published_date": "N/A",
                    "severity": "unknown",
                    "exploit_available": False,
                    "references": []
                }
                
        except Exception as e:
            logger.error(f"RAG CVE search failed: {e}")
            return {"error": f"RAG search failed: {str(e)}"}

    async def _rag_search_scan_results(self, target: str, scan_type: str) -> Dict[str, Any]:
        """RAG ile benzer tarama sonuçlarını ara"""
        try:
            if not self.rag_client:
                return {"error": "RAG client not available"}
            
            # RAG sorgusu oluştur
            query = f"penetration test results for {target} {scan_type} vulnerabilities"
            
            # RAG'dan benzer tarama sonuçlarını al
            rag_results = await self.rag_client.search(query)
            
            if rag_results and len(rag_results) > 0:
                # Benzer sonuçları analiz et
                similar_findings = []
                for result in rag_results[:5]:  # İlk 5 sonucu al
                    similar_findings.append({
                        "target": result.get("target", "Unknown"),
                        "vulnerability_type": result.get("vulnerability_type", "Unknown"),
                        "severity": result.get("severity", "unknown"),
                        "cvss_score": result.get("cvss_score", "N/A"),
                        "description": result.get("description", "No description"),
                        "remediation": result.get("remediation", "No remediation available")
                    })
                
                return {
                    "similar_findings": similar_findings,
                    "total_matches": len(rag_results),
                    "confidence": "high" if len(rag_results) > 3 else "medium"
                }
            else:
                return {"error": "No similar scan results found"}
                
        except Exception as e:
            logger.error(f"RAG scan results search failed: {e}")
            return {"error": f"RAG search failed: {str(e)}"}

    async def _rag_enhance_finding(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """RAG ile bulguyu zenginleştir"""
        try:
            enhanced_finding = finding.copy()
            
            # CVE bilgilerini RAG'dan al
            cve_info = await self._rag_search_cve_info(
                finding.get("title", ""), 
                finding.get("technology", None)
            )
            
            if "error" not in cve_info:
                enhanced_finding.update({
                    "cve_id": cve_info.get("cve_id"),
                    "cvss_score": cve_info.get("cvss_score"),
                    "cvss_vector": cve_info.get("cvss_vector"),
                    "cve_description": cve_info.get("description"),
                    "published_date": cve_info.get("published_date"),
                    "exploit_available": cve_info.get("exploit_available", False),
                    "cve_references": cve_info.get("references", [])
                })
            
            # Benzer tarama sonuçlarını RAG'dan al
            scan_results = await self._rag_search_scan_results(
                finding.get("target", ""),
                finding.get("title", "")
            )
            
            if "error" not in scan_results:
                enhanced_finding.update({
                    "similar_findings": scan_results.get("similar_findings", []),
                    "rag_confidence": scan_results.get("confidence", "low")
                })
            
            return enhanced_finding
            
        except Exception as e:
            logger.error(f"RAG enhancement failed: {e}")
            return finding

    async def _rag_store_scan_results(self, target: str, findings: List[Dict[str, Any]], execution_results: Dict[str, Any]):
        """RAG'a tarama sonuçlarını kaydet - Firebase entegrasyonu ile"""
        try:
            # RAG servisini import et ve kullan
            from services.rag_service import get_rag_service
            rag_service = get_rag_service()
            
            if not rag_service.is_available():
                logger.warning("RAG service not available - cannot store scan results")
                return
            
            # RAG servisinin store_scan_results metodunu kullan
            success = rag_service.store_scan_results(target, findings, execution_results)
            
            if success:
                logger.info(f"✅ Scan results stored successfully for target: {target}")
            else:
                logger.warning(f"⚠️ Failed to store scan results for target: {target}")
            
        except Exception as e:
            logger.error(f"Failed to store scan results: {e}")

    def _count_findings_by_severity(self, findings: List[Dict[str, Any]]) -> Dict[str, int]:
        """Bulguları ciddiyete göre say"""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in findings:
            severity = finding.get("severity", "low").lower()
            if severity in counts:
                counts[severity] += 1
        return counts

    # ==========================================================================
    # DİNAMİK RAPORLAMA FONKSİYONLARI - UZMAN SEVİYESİ
    # ==========================================================================

    def _generate_conclusion(self, state: AgentState) -> List[str]:
        """Testin genel sonucunu, bulguların temasına göre dinamik olarak özetler"""
        parts = ["6.2. Sonuç Değerlendirmesi", ""]
        findings = state.findings
        findings_summary = state.get_findings_summary()
        overall_risk = self._calculate_overall_risk_level(findings_summary)

        if not findings:
            parts.append(f"{state.target} üzerinde gerçekleştirilen güvenlik değerlendirmesi sonucunda kritik bir güvenlik açığına rastlanmamıştır. Sistemin genel güvenlik duruşu temel seviyede yeterli görünmektedir. Ancak, proaktif güvenlik iyileştirmeleri için rapordaki genel önerilerin dikkate alınması tavsiye edilir.")
            return parts

        # Bulguların ana temasını belirle
        categories = self._categorize_findings_by_owasp(findings)
        top_category = max(categories, key=categories.get, default="").split(' - ')[-1] if categories else ""

        conclusion_text = f"Bu güvenlik değerlendirmesi, {state.target} sisteminin genel güvenlik durumunu '{overall_risk}' olarak belirlemiştir. "
        
        if top_category:
            conclusion_text += f"Test sırasında tespit edilen zafiyetlerin yoğunlaştığı ana tema **'{top_category}'** olarak öne çıkmaktadır. "

        if findings_summary['by_severity']['critical'] > 0:
            conclusion_text += "Tespit edilen kritik seviyedeki bulgular, sisteme yönelik ciddi tehditler oluşturmakta ve acil müdahale gerektirmektedir. "
        elif findings_summary['by_severity']['high'] > 0:
             conclusion_text += "Yüksek seviyeli bulgular, önemli veri sızıntısı veya hizmet kesintisi riskleri taşımaktadır ve öncelikli olarak ele alınmalıdır. "

        conclusion_text += "Raporda detaylandırılan stratejik ve taktiksel önerilerin uygulanması, sistemin siber saldırılara karşı dayanıklılığını önemli ölçüde artıracaktır."

        parts.append(conclusion_text)
        parts.append("")
        return parts

    def _generate_strategic_recommendations(self, state: AgentState) -> List[str]:
        """Bulguların türüne ve ciddiyetine göre dinamik stratejik öneriler"""
        parts = ["6.1. Stratejik ve Taktiksel Öneriler", ""]
        findings = state.findings
        findings_summary = state.get_findings_summary()
        
        if not findings:
            parts.append("Kritik bir bulguya rastlanmadığı için, genel güvenlik sertleştirme adımlarına odaklanılması önerilir:")
            parts.extend([
                "  • **Proaktif İzleme:** Anomali tespiti için sistem loglarının ve ağ trafiğinin düzenli olarak izlenmesi.",
                "  • **Güvenlik Farkındalığı:** Geliştirici ekiplerine yönelik düzenli olarak güvenli kodlama eğitimleri düzenlenmesi.",
                "  • **Periyodik Testler:** Güvenlik duruşunun sürekli denetlenmesi için bu testlerin düzenli aralıklarla tekrarlanması."
            ])
            parts.append("")
            return parts

        # 1. Acil ve Kısa Vadeli Aksiyonlar
        if findings_summary['by_severity']['critical'] > 0:
            parts.append("🚨 ACİL AKSİYONLAR (0-48 Saat İçinde):")
            for f in findings:
                if f.get('severity') == 'critical':
                    rec = self._get_remediation(f).split('\n')[0]
                    parts.append(f"  • {f.get('title')}: {rec}")
            parts.append("")
        
        if findings_summary['by_severity']['high'] > 0:
            parts.append("⚠️ KISA VADELİ AKSİYONLAR (1-7 Gün İçinde):")
            for f in findings:
                if f.get('severity') == 'high':
                    rec = self._get_remediation(f).split('\n')[0]
                    parts.append(f"  • {f.get('title')}: {rec}")
            parts.append("")
        
        # 2. Stratejik İyileştirmeler
        parts.append("📈 STRATEJİK İYİLEŞTİRMELER (Orta ve Uzun Vade):")
        categories = self._categorize_findings_by_owasp(findings)
        
        if "A05:2021 - Security Misconfiguration" in categories:
            parts.append("  • **Konfigürasyon Yönetimini Güçlendirin:** Sunucu, veritabanı ve bulut hizmetleri için 'güvenli temel' (secure baseline) konfigürasyonları oluşturun ve düzenli olarak denetleyin. IaC (Infrastructure as Code) tarama araçlarını CI/CD süreçlerine entegre edin.")

        if "A03:2021 - Injection" in categories:
            parts.append("  • **Güvenli Kodlama Pratiklerini Benimseyin (SSDLC):** Tüm geliştiricilere yönelik zorunlu güvenli kodlama (OWASP Top 10) eğitimleri düzenleyin. Statik kod analizi (SAST) araçlarını geliştirme yaşam döngüsüne dahil edin.")

        if "A06:2021 - Vulnerable and Outdated Components" in categories:
            parts.append("  • **Yazılım Varlık ve Yama Yönetimi Programı Oluşturun:** Kullanılan tüm kütüphane ve framework'lerin envanterini çıkarın. Yazılım Kompozisyon Analizi (SCA) araçları (örn: Dependabot, Snyk) kullanarak bağımlılıkları sürekli tarayın ve kritik zafiyetler için acil yama politikası uygulayın.")

        if "A01:2021 - Broken Access Control" in categories:
             parts.append("  • **Erişim Kontrol Mekanizmalarını Gözden Geçirin:** Rol tabanlı erişim kontrolünü (RBAC) 'en az yetki' prensibine göre sıkılaştırın. Özellikle API endpoint'leri için yetkilendirme kontrollerini detaylı olarak test edin.")
        
        if not categories:
             parts.append("  • **Genel Güvenlik Sertleştirmesi:** Tespit edilen orta ve düşük seviyeli bulguları planlı bir şekilde giderin ve Web Application Firewall (WAF) kurallarını güncelleyin.")

        parts.append("")
        return parts

    # ==========================================================================
    # RAPOR BÖLÜMLERİNİ OLUŞTURAN ANA FONKSİYONLAR
    # ==========================================================================

    def _generate_executive_summary(self, state: AgentState) -> List[str]:
        """(LLM İÇİN İDEAL) Güçlendirilmiş Yönetici Özeti bölümünü oluşturur."""
        parts = ["1. YÖNETİCİ ÖZETİ", "-" * 50, ""]
        findings = state.findings
        findings_summary = state.get_findings_summary()
        overall_risk = self._calculate_overall_risk_level(findings_summary)
        risk_score = self._calculate_risk_score(findings)
        
        # 1. Genel Değerlendirme
        parts.append("1.1. Genel Değerlendirme")
        parts.append(f"Bu rapor, {state.target} sistemine yönelik gerçekleştirilen penetrasyon testinin sonuçlarını özetlemektedir. Testler, sistemin genel güvenlik duruşunu ve potansiyel risklerini değerlendirmek amacıyla yapılmıştır. Değerlendirme sonucunda, sistemin güvenlik seviyesi '{overall_risk}' olarak belirlenmiştir.")
        parts.append("")

        # 2. Risk Postürü ve Puanlama
        parts.append("1.2. Risk Postürü ve Puanlama")
        filled_blocks = int(risk_score / 10)
        empty_blocks = 10 - filled_blocks
        risk_bar = f"[{'■' * filled_blocks}{'□' * empty_blocks}]"
        parts.append(f"Genel Risk Skoru: {risk_score}/100 ({overall_risk})")
        parts.append(risk_bar)
        parts.append("")

        # 3. En Kritik Bulgular ve İş Etkileri
        parts.append("1.3. En Kritik Bulgular ve İş Etkileri")
        top_findings = sorted(findings, key=lambda x: {"critical": 3, "high": 2, "medium": 1, "low": 0}.get(x.get("severity"), 0), reverse=True)[:3]
        if not top_findings:
            parts.append("Testler sırasında kritik veya yüksek seviyede bir bulguya rastlanmamıştır.")
        else:
            for finding in top_findings:
                parts.append(f"  • Bulgu: {finding.get('title', 'N/A')}")
                parts.append(f"    İş Etkisi: {self._generate_business_impact(finding)}")
                parts.append("")
        
        # 4. Öncelikli Aksiyon Planı
        parts.append("1.4. Öncelikli Aksiyon Planı")
        if not top_findings:
            parts.append("Acil bir aksiyon gerekmemektedir. Raporun tamamının incelenmesi önerilir.")
        else:
            parts.append("Aşağıdaki aksiyonların öncelikli olarak alınması tavsiye edilmektedir:")
            for i, finding in enumerate(top_findings, 1):
                rec = self._get_remediation(finding).split('\n')[0] # Sadece ilk satırı al
                parts.append(f"  {i}. {rec}")
        parts.append("")
        return parts

    def _generate_findings_summary(self, state: AgentState) -> List[str]:
        """Görselleştirilmiş Bulgular Özeti bölümünü oluşturur."""
        parts = ["4. BULGULAR ÖZETİ", "-" * 50, ""]
        findings = state.findings
        total_findings = len(findings)
        if total_findings == 0:
            parts.append("Testler sırasında herhangi bir güvenlik bulgusuna rastlanmamıştır.")
            return parts

        findings_summary = state.get_findings_summary()

        parts.append("4.1. Risk Seviyesine Göre Dağılım:")
        for severity in ["critical", "high", "medium", "low"]:
            count = findings_summary['by_severity'][severity]
            percentage = (count / total_findings) * 100 if total_findings > 0 else 0
            bar = f"[{'■' * int(percentage / 10)}{'□' * (10 - int(percentage / 10))}]"
            parts.append(f"  {severity.upper():<10}: {count:<3} {bar} {percentage:.1f}%")
        parts.append("")

        parts.append("4.2. Kategori Bazında Dağılım (OWASP Top 10):")
        categorized_findings = self._categorize_findings_by_owasp(findings)
        if not categorized_findings:
            parts.append("Bulgular standart OWASP kategorileriyle eşleştirilememiştir.")
        else:
            for category, count in categorized_findings.items():
                parts.append(f"  • {category}: {count} bulgu")
        parts.append("")
        return parts

    def _format_single_finding(self, finding: Dict[str, Any], index: int) -> List[str]:
        """Tek bir bulguyu standartlaştırılmış profesyonel formata dönüştürür."""
        parts = []
        title = finding.get('title', 'Başlıksız Bulgu')
        severity = finding.get('severity', 'Belirtilmemiş').upper()
        cvss = finding.get('cvss_score', 'N/A')
        owasp_ref = self._get_owasp_reference(finding)

        parts.append(f"5.{index}. {title}")
        parts.append("=" * (len(title) + 5))
        parts.append(f"[ Risk Seviyesi: {severity} ] [ CVSS v3.1: {cvss} ] [ OWASP: {owasp_ref.split(' - ')[0]} ]")
        parts.append("")
        
        separator = "-" * 80
        
        parts.append("AÇIKLAMA (Description)")
        parts.append(separator)
        parts.append(finding.get('description', 'Detaylı açıklama mevcut değil.'))
        parts.append("")
        
        parts.append("İŞ ETKİSİ (Business Impact)")
        parts.append(separator)
        parts.append(self._generate_business_impact(finding))
        parts.append("")

        parts.append("TEKNİK DETAYLAR VE YENİDEN OLUŞTURMA ADIMLARI (Proof of Concept)")
        parts.append(separator)
        parts.append(finding.get('evidence', 'Kanıt veya yeniden oluşturma adımları mevcut değil.'))
        parts.append("")

        parts.append("ÇÖZÜM ÖNERİLERİ (Remediation)")
        parts.append(separator)
        parts.append(self._get_remediation(finding))
        parts.append("")
        
        parts.append("REFERANSLAR (References)")
        parts.append(separator)
        if cve := finding.get('cve_id'):
            parts.append(f"• NVD: https://nvd.nist.gov/vuln/detail/{cve}")
        parts.append(f"• OWASP: https://owasp.org/Top10/#{owasp_ref.split(' - ')[0] if ' ' in owasp_ref else ''}")
        parts.append("_" * 80)
        parts.append("")
        return parts

    def _generate_strategic_recommendations(self, state: AgentState) -> List[str]:
        """Bulguların türüne ve ciddiyetine göre dinamik stratejik öneriler"""
        parts = ["6.1. Stratejik ve Taktiksel Öneriler", ""]
        findings = state.findings
        findings_summary = state.get_findings_summary()
        
        if not findings:
            parts.append("Kritik bir bulguya rastlanmadığı için, genel güvenlik sertleştirme adımlarına odaklanılması önerilir:")
            parts.extend([
                "  • **Proaktif İzleme:** Anomali tespiti için sistem loglarının ve ağ trafiğinin düzenli olarak izlenmesi.",
                "  • **Güvenlik Farkındalığı:** Geliştirici ekiplerine yönelik düzenli olarak güvenli kodlama eğitimleri düzenlenmesi.",
                "  • **Periyodik Testler:** Güvenlik duruşunun sürekli denetlenmesi için bu testlerin düzenli aralıklarla tekrarlanması."
            ])
            parts.append("")
            return parts

        # 1. Acil ve Kısa Vadeli Aksiyonlar
        if findings_summary['by_severity']['critical'] > 0:
            parts.append("🚨 ACİL AKSİYONLAR (0-48 Saat İçinde):")
            for f in findings:
                if f.get('severity') == 'critical':
                    rec = self._get_remediation(f).split('\n')[0]
                    parts.append(f"  • {f.get('title')}: {rec}")
            parts.append("")
        
        if findings_summary['by_severity']['high'] > 0:
            parts.append("⚠️ KISA VADELİ AKSİYONLAR (1-7 Gün İçinde):")
            for f in findings:
                if f.get('severity') == 'high':
                    rec = self._get_remediation(f).split('\n')[0]
                    parts.append(f"  • {f.get('title')}: {rec}")
            parts.append("")
        
        # 2. Stratejik İyileştirmeler
        parts.append("📈 STRATEJİK İYİLEŞTİRMELER (Orta ve Uzun Vade):")
        categories = self._categorize_findings_by_owasp(findings)
        
        if "A05:2021 - Security Misconfiguration" in categories:
            parts.append("  • **Konfigürasyon Yönetimini Güçlendirin:** Sunucu, veritabanı ve bulut hizmetleri için 'güvenli temel' (secure baseline) konfigürasyonları oluşturun ve düzenli olarak denetleyin. IaC (Infrastructure as Code) tarama araçlarını CI/CD süreçlerine entegre edin.")

        if "A03:2021 - Injection" in categories:
            parts.append("  • **Güvenli Kodlama Pratiklerini Benimseyin (SSDLC):** Tüm geliştiricilere yönelik zorunlu güvenli kodlama (OWASP Top 10) eğitimleri düzenleyin. Statik kod analizi (SAST) araçlarını geliştirme yaşam döngüsüne dahil edin.")

        if "A06:2021 - Vulnerable and Outdated Components" in categories:
            parts.append("  • **Yazılım Varlık ve Yama Yönetimi Programı Oluşturun:** Kullanılan tüm kütüphane ve framework'lerin envanterini çıkarın. Yazılım Kompozisyon Analizi (SCA) araçları (örn: Dependabot, Snyk) kullanarak bağımlılıkları sürekli tarayın ve kritik zafiyetler için acil yama politikası uygulayın.")

        if "A01:2021 - Broken Access Control" in categories:
             parts.append("  • **Erişim Kontrol Mekanizmalarını Gözden Geçirin:** Rol tabanlı erişim kontrolünü (RBAC) 'en az yetki' prensibine göre sıkılaştırın. Özellikle API endpoint'leri için yetkilendirme kontrollerini detaylı olarak test edin.")
        
        if not categories:
             parts.append("  • **Genel Güvenlik Sertleştirmesi:** Tespit edilen orta ve düşük seviyeli bulguları planlı bir şekilde giderin ve Web Application Firewall (WAF) kurallarını güncelleyin.")

        parts.append("")
        return parts

    def _generate_conclusion(self, state: AgentState) -> List[str]:
        """Testin genel sonucunu, bulguların temasına göre dinamik olarak özetler"""
        parts = ["6.2. Sonuç Değerlendirmesi", ""]
        findings = state.findings
        findings_summary = state.get_findings_summary()
        overall_risk = self._calculate_overall_risk_level(findings_summary)

        if not findings:
            parts.append(f"{state.target} üzerinde gerçekleştirilen güvenlik değerlendirmesi sonucunda kritik bir güvenlik açığına rastlanmamıştır. Sistemin genel güvenlik duruşu temel seviyede yeterli görünmektedir. Ancak, proaktif güvenlik iyileştirmeleri için rapordaki genel önerilerin dikkate alınması tavsiye edilir.")
            return parts

        # Bulguların ana temasını belirle
        categories = self._categorize_findings_by_owasp(findings)
        top_category = max(categories, key=categories.get, default="").split(' - ')[-1] if categories else ""

        conclusion_text = f"Bu güvenlik değerlendirmesi, {state.target} sisteminin genel güvenlik durumunu '{overall_risk}' olarak belirlemiştir. "
        
        if top_category:
            conclusion_text += f"Test sırasında tespit edilen zafiyetlerin yoğunlaştığı ana tema **'{top_category}'** olarak öne çıkmaktadır. "

        if findings_summary['by_severity']['critical'] > 0:
            conclusion_text += "Tespit edilen kritik seviyedeki bulgular, sisteme yönelik ciddi tehditler oluşturmakta ve acil müdahale gerektirmektedir. "
        elif findings_summary['by_severity']['high'] > 0:
             conclusion_text += "Yüksek seviyeli bulgular, önemli veri sızıntısı veya hizmet kesintisi riskleri taşımaktadır ve öncelikli olarak ele alınmalıdır. "

        conclusion_text += "Raporda detaylandırılan stratejik ve taktiksel önerilerin uygulanması, sistemin siber saldırılara karşı dayanıklılığını önemli ölçüde artıracaktır."

        parts.append(conclusion_text)
        parts.append("")
        return parts

    # ==========================================================================
    # ANA RAPOR OLUŞTURMA METODU
    # ==========================================================================
    
    def _prepare_professional_report_text(self, state: AgentState) -> str:
        """
        Gerçek penetrasyon testi standartlarında profesyonel rapor metni hazırlar.
        firstrapor.py'deki güzel formatı kullanır.
        """
        report_parts = []
        
        # --- YARATICI KAPAK SAYFASI ---
        report_parts.extend(self._generate_creative_cover_page(state))
        
        # --- YARATICI İÇİNDEKİLER ---
        report_parts.extend(self._generate_creative_table_of_contents())
        
        # --- BÖLÜM 1: YÖNETİCİ ÖZETİ ---
        report_parts.extend(self._generate_executive_summary(state))
        
        # --- BÖLÜM 2: METODOLOJİ VE KAPSAM ---
        report_parts.extend([
            "2. METODOLOJİ VE KAPSAM", "-" * 50, "",
            "Bu güvenlik değerlendirmesi, OWASP Testing Guide, PTES ve NIST SP 800-115 gibi endüstri standartlarına uygun, otomatize edilmiş bir metodoloji ile gerçekleştirilmiştir.",
            "", f"Kapsam: {state.target}", f"Test Başlangıç: {state.start_time.strftime('%d.%m.%Y %H:%M')}", "",
            "Kapsam Dışı: Sosyal mühendislik, fiziksel güvenlik ve DoS/DDoS saldırıları bu testin kapsamı dışındadır.", ""
        ])
        
        # --- BÖLÜM 3: RİSK DERECELENDİRME MATRİSİ ---
        report_parts.extend([
            "3. RİSK DERECELENDİRME MATRİSİ", "-" * 50, "",
            "Risk seviyeleri CVSS v3.1 ve OWASP Risk Rating Metodolojisi'ne göre belirlenmiştir:",
            "  • KRİTİK (9.0-10.0): Acil müdahale gerektirir. Sistem tamamen ele geçirilebilir.",
            "  • YÜKSEK (7.0-8.9): Öncelikli olarak giderilmelidir. Veri kaybı/ifşası riski yüksek.",
            "  • ORTA (4.0-6.9): Makul sürede giderilmelidir. Sınırlı etki potansiyeli.",
            "  • DÜŞÜK (0.1-3.9): Planlı olarak giderilmelidir. Minimal etki.", ""
        ])
        
        # --- BÖLÜM 4: BULGULAR ÖZETİ ---
        report_parts.extend(self._generate_findings_summary(state))
        
        # --- BÖLÜM 5: DETAYLI TEKNİK BULGULAR ---
        report_parts.extend(["5. DETAYLI TEKNİK BULGULAR", "-" * 50, ""])
        sorted_findings = sorted(state.findings, key=lambda x: {"critical": 3, "high": 2, "medium": 1, "low": 0}.get(x.get("severity"), 0), reverse=True)
        if not sorted_findings:
            report_parts.append("Detaylı incelenecek herhangi bir teknik bulguya rastlanmamıştır.")
        else:
            for i, finding in enumerate(sorted_findings, 1):
                report_parts.extend(self._format_single_finding(finding, i))
        
        # --- BÖLÜM 6: SONUÇ VE STRATEJİK ÖNERİLER (DİNAMİK) ---
        report_parts.extend(["", "6. SONUÇ VE STRATEJİK ÖNERİLER", "-" * 50, ""])
        report_parts.extend(self._generate_strategic_recommendations(state))
        report_parts.extend(self._generate_conclusion(state))
        
        # --- BÖLÜM 7: EKLER ---
        report_parts.extend(["7. EKLER", "-" * 50, ""])
        report_parts.append("Ek A: Test Kapsamı")
        report_parts.append(f"• {state.target}")
        if subdomains := state.context_summary.get("subdomains"):
            report_parts.append("\nTespit Edilen Subdomainler:")
            for sub in subdomains[:10]:
                report_parts.append(f"  - {sub}")
            if len(subdomains) > 10:
                report_parts.append(f"  ... ve {len(subdomains) - 10} adet daha.")
        report_parts.append("")

        if open_ports := state.context_summary.get("open_ports"):
            report_parts.append("Ek B: Tespit Edilen Açık Portlar")
            for port_info in open_ports[:15]:
                if isinstance(port_info, dict):
                    report_parts.append(f"• Port {port_info.get('port')}/{port_info.get('protocol', 'tcp')}: {port_info.get('service', 'Bilinmiyor')} ({port_info.get('version', '')})")
                else:
                    report_parts.append(f"• Port {port_info}")
            report_parts.append("")

        report_parts.append("Ek C: Kullanılan Standartlar")
        report_parts.append("• OWASP Top 10 2021")
        report_parts.append("• PTES (Penetration Testing Execution Standard)")
        report_parts.append("• NIST SP 800-115")
        report_parts.append("• CVSS v3.1")
        report_parts.append("")

        # Yaratıcı rapor sonu template'i
        report_parts.extend(self._generate_creative_report_footer(state))

        return "\n".join(report_parts)

    # ==========================================================================
    # YARATICI TEMPLATE METODLARI
    # ==========================================================================

    def _generate_creative_report_footer(self, state: AgentState) -> List[str]:
        """Yaratıcı rapor sonu template'i oluşturur - Kurumsal Premium Tasarım"""
        findings_summary = state.get_findings_summary()
        risk_level = self._calculate_overall_risk_level(findings_summary)
        
        # Risk seviyesine göre soft ve kurumsal footer'lar
        if risk_level == "CRITICAL":
            return [
                "┌─────────────────────────────────────────────────────────────────────────────┐",
                "│                           CRITICAL RISK DETECTED                            │",
                "│                                                                             │",
                "│ This system has been identified with critical security vulnerabilities.    │",
                "│ Immediate action is required! Security team must act immediately.          │",
                "│                                                                             │",
                "│ IMMEDIATE ACTION: Critical vulnerabilities must be addressed within 0-24h  │",
                "│ SECURITY MONITORING: System must be monitored until fully secured          │",
                "│ COMMUNICATION: Security team must be available 24/7                       │",
                "└─────────────────────────────────────────────────────────────────────────────┘",
                ""
            ]
        elif risk_level == "HIGH":
            return [
                "┌─────────────────────────────────────────────────────────────────────────────┐",
                "│                            HIGH RISK DETECTED                               │",
                "│                                                                             │",
                "│ This system has been identified with high-level security vulnerabilities.  │",
                "│ Priority attention is required! Security status must be closely monitored. │",
                "│                                                                             │",
                "│ PRIORITY ACTION: High-risk vulnerabilities must be addressed within 1-7d  │",
                "│ MONITORING: Security metrics must be tracked daily                         │",
                "│ UPDATES: System components must be kept current                            │",
                "└─────────────────────────────────────────────────────────────────────────────┘",
                ""
            ]
        elif risk_level == "MEDIUM":
            return [
                "┌─────────────────────────────────────────────────────────────────────────────┐",
                "│                           MEDIUM RISK LEVEL                                 │",
                "│                                                                             │",
                "│ This system has been identified with medium-level security vulnerabilities.│",
                "│ Planned remediation can improve the security posture.                      │",
                "│                                                                             │",
                "│ PLANNED ACTION: Medium-risk vulnerabilities must be addressed within 2-4w  │",
                "│ IMPROVEMENT: Security processes must be reviewed                           │",
                "│ PROTECTION: Existing security measures must be strengthened                │",
                "└─────────────────────────────────────────────────────────────────────────────┘",
                ""
            ]
        else:  # LOW
            return [
                "┌─────────────────────────────────────────────────────────────────────────────┐",
                "│                            LOW RISK LEVEL                                   │",
                "│                                                                             │",
                "│ This system has been identified with low-level security vulnerabilities.    │",
                "│ Overall security posture is at an acceptable level.                        │",
                "│                                                                             │",
                "│ CONTINUOUS IMPROVEMENT: Security processes must be optimized               │",
                "│ EDUCATION: Security awareness must be increased                            │",
                "│ PROACTIVE: Future risks must be prevented                                  │",
                "└─────────────────────────────────────────────────────────────────────────────┘",
                ""
            ]

    def _generate_creative_section_header(self, title: str, icon: str = "📋") -> List[str]:
        """Yaratıcı bölüm başlığı oluşturur"""
        return [
            "",
            f"╔══════════════════════════════════════════════════════════════════════════════╗",
            f"║                           {icon} {title.upper()} {icon}                           ║",
            f"╚══════════════════════════════════════════════════════════════════════════════╝",
            ""
        ]

    def _generate_creative_finding_box(self, finding: Dict[str, Any]) -> List[str]:
        """Yaratıcı bulgu kutusu oluşturur - Kurumsal Premium Tasarım"""
        severity = finding.get("severity", "low").lower()
        
        # Soft ve kurumsal severity indicators
        severity_indicators = {
            "critical": "CRITICAL",
            "high": "HIGH", 
            "medium": "MEDIUM",
            "low": "LOW"
        }
        severity_text = severity_indicators.get(severity, "UNKNOWN")
        
        title = finding.get("title", "Unknown Finding")
        description = finding.get("description", "No description available")
        
        return [
            f"┌─ {severity_text} SEVERITY: {title} ──────────────────────────────────────────────┐",
            f"│                                                                             │",
            f"│ Description: {description[:65]:<65} │",
            f"│                                                                             │",
            f"│ Severity: {severity_text:<10} │ CVSS: {finding.get('cvss_score', 'N/A'):<8} │ CVE: {finding.get('cve_id', 'N/A'):<15} │",
            f"│                                                                             │",
            f"│ Business Impact: {finding.get('business_impact', 'N/A'):<20} │ Exploitability: {finding.get('exploitability', 'N/A'):<15} │",
            f"└─────────────────────────────────────────────────────────────────────────────┘",
            ""
        ]

    def _generate_creative_recommendation_box(self, recommendation: Dict[str, Any]) -> List[str]:
        """Yaratıcı öneri kutusu oluşturur - Kurumsal Premium Tasarım"""
        priority = recommendation.get("priority", "low").lower()
        
        # Soft ve kurumsal priority indicators
        priority_indicators = {
            "immediate": "IMMEDIATE",
            "short_term": "SHORT-TERM",
            "long_term": "LONG-TERM"
        }
        priority_text = priority_indicators.get(priority, "STANDARD")
        
        description = recommendation.get("description", "No description available")
        effort = recommendation.get("effort", "Unknown")
        impact = recommendation.get("impact", "Unknown")
        
        return [
            f"┌─ {priority_text} PRIORITY RECOMMENDATION ────────────────────────────────────────┐",
            f"│                                                                             │",
            f"│ Recommendation: {description[:65]:<65} │",
            f"│                                                                             │",
            f"│ Effort: {effort:<15} │ Impact: {impact:<15} │ Category: {recommendation.get('category', 'N/A'):<15} │",
            f"└─────────────────────────────────────────────────────────────────────────────┘",
            ""
        ]

    def _generate_creative_cover_page(self, state: AgentState) -> List[str]:
        """Yaratıcı kapak sayfası oluşturur - Kurumsal Premium Tasarım"""
        findings_summary = state.get_findings_summary()
        risk_level = self._calculate_overall_risk_level(findings_summary)
        
        # Risk seviyesine göre soft ve kurumsal renkler
        if risk_level == "CRITICAL":
            risk_icon = "●"
            risk_text = "CRITICAL RISK LEVEL"
            risk_description = "Immediate action required"
        elif risk_level == "HIGH":
            risk_icon = "●"
            risk_text = "HIGH RISK LEVEL"
            risk_description = "Priority attention needed"
        elif risk_level == "MEDIUM":
            risk_icon = "●"
            risk_text = "MEDIUM RISK LEVEL"
            risk_description = "Planned remediation required"
        else:
            risk_icon = "●"
            risk_text = "LOW RISK LEVEL"
            risk_description = "Continuous improvement recommended"
        
        return [
            "┌─────────────────────────────────────────────────────────────────────────────┐",
            "│                                                                             │",
            "│                    PENETRATION TESTING REPORT                              │",
            "│                                                                             │",
            "│                           AI-Powered Security Assessment                   │",
            "│                                                                             │",
            f"│  Target System: {state.target:<50} │",
            f"│  Report Date:  {datetime.now().strftime('%d %B %Y'):<50} │",
            f"│  Risk Level:   {risk_icon} {risk_text:<45} │",
            f"│  Assessment:   {risk_description:<50} │",
            f"│  Test Type:    Comprehensive Security Assessment{'':<25} │",
            f"│  Version:      2.0 - RAG Integration{'':<30} │",
            f"│  Classification: Company Confidential{'':<30} │",
            "│                                                                             │",
            "│  Prepared by:   Pentagent AI Security Platform                             │",
            "│  Contact:       security@pentagent.ai                                      │",
            "│  Website:       https://pentagent.ai                                       │",
            "│                                                                             │",
            f"│  This report provides a comprehensive security assessment of              │",
            f"│  {state.target:<60} │",
            f"│  including vulnerability analysis, risk evaluation, and                   │",
            f"│  strategic recommendations for security improvement.                      │",
            "│                                                                             │",
            "└─────────────────────────────────────────────────────────────────────────────┘",
            ""
        ]

    def _generate_creative_table_of_contents(self) -> List[str]:
        """Yaratıcı içindekiler oluşturur - Kurumsal Premium Tasarım"""
        return [
            "┌─────────────────────────────────────────────────────────────────────────────┐",
            "│                           TABLE OF CONTENTS                                │",
            "└─────────────────────────────────────────────────────────────────────────────┘",
            "",
            "1. EXECUTIVE SUMMARY",
            "   • Risk Level and Overall Assessment",
            "   • Critical Findings Overview",
            "   • Immediate Action Plan",
            "",
            "2. METHODOLOGY AND SCOPE",
            "   • Testing Methodology",
            "   • Tools and Techniques Used",
            "   • Test Scope and Limitations",
            "",
            "3. RISK ASSESSMENT MATRIX",
            "   • CVSS v3.1 Scoring",
            "   • Business Impact Analysis",
            "   • Exploitability Assessment",
            "",
            "4. FINDINGS SUMMARY",
            "   • Critical Level Findings",
            "   • High Level Findings",
            "   • Medium and Low Level Findings",
            "",
            "5. DETAILED TECHNICAL FINDINGS",
            "   • CVE Information and CVSS Scores",
            "   • Technical Details and Evidence",
            "   • Exploit Scenarios",
            "",
            "6. CONCLUSIONS AND RECOMMENDATIONS",
            "   • Strategic Recommendations",
            "   • Tactical Recommendations",
            "   • Long-term Improvements",
            "",
            "7. APPENDICES",
            "   • Standards Used",
            "   • References",
            "   • Technical Details",
            "",
            "┌─────────────────────────────────────────────────────────────────────────────┐",
            "│                           REPORT CONTENT BEGINS                             │",
            "└─────────────────────────────────────────────────────────────────────────────┘",
            ""
        ]

    def _generate_creative_executive_summary_box(self, summary: Dict[str, Any]) -> List[str]:
        """Yaratıcı executive summary kutusu oluşturur - Kurumsal Premium Tasarım"""
        risk_score = summary.get("risk_score", 0)
        risk_level = summary.get("risk_level", "UNKNOWN")
        
        # Soft ve kurumsal risk indicators
        if risk_score >= 80:
            risk_indicator = "HIGH"
        elif risk_score >= 60:
            risk_indicator = "MEDIUM-HIGH"
        elif risk_score >= 40:
            risk_indicator = "MEDIUM"
        else:
            risk_indicator = "LOW"
        
        return [
            f"┌─────────────────────────────────────────────────────────────────────────────┐",
            f"│                           EXECUTIVE SUMMARY                                 │",
            f"│                                                                             │",
            f"│ Target: {summary.get('scope', 'N/A'):<60} │",
            f"│ Risk Score: {risk_indicator} ({risk_score}/100) - {risk_level:<35} │",
            f"│ Critical Findings: {summary.get('critical_findings', 0):<10} │ High Findings: {summary.get('high_findings', 0):<10} │ Medium Findings: {summary.get('medium_findings', 0):<10} │",
            f"│ Test Effectiveness: {summary.get('test_effectiveness', 'N/A'):<15} │ Compliance Gaps: {summary.get('compliance_gaps', 0):<10} │",
            f"│                                                                             │",
            f"│ Summary: {summary.get('summary', 'No summary available')[:65]:<65} │",
            f"└─────────────────────────────────────────────────────────────────────────────┘",
            ""
        ]

    # ==========================================================================
    # MEVCUT DİĞER FONKSİYONLAR
    # ==========================================================================
    
    def get_structured_report_data_with_cves(self, state: AgentState, cve_findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Frontend için yapılandırılmış rapor verilerini döndürür (JSON format).
        Tool bulguları + Ayrı CVE tablosu
        """
        data = self.get_structured_report_data(state)
        
        # CVE tablosunu ekle
        cve_table = []
        for cve in cve_findings:
            cve_table.append({
                "cve_id": cve.get("cve_id", "N/A"),
                "cvss_skoru": cve.get("cvss_score", "N/A"),
                "severity": cve.get("severity", "unknown"),
                "aciklama": cve.get("description", "")[:200] + "..." if len(cve.get("description", "")) > 200 else cve.get("description", ""),
                "etkilenen_sistem": cve.get("technology") or cve.get("target", "N/A")
            })
        
        data["cve_references"] = cve_table
        return data
    
    def get_structured_report_data(self, state: AgentState) -> Dict[str, Any]:
        """
        Frontend için yapılandırılmış rapor verilerini döndürür (JSON format).
        Sadece teknik bulgular ve CVE'ler: Executive Summary, Methodology, Detailed Findings, CVE References
        """
        findings_summary = state.get_findings_summary()
        overall_risk = self._calculate_overall_risk_level(findings_summary)
        risk_score = self._calculate_risk_score(state.findings)
        
        # Bulguları severity'ye göre sırala
        sorted_findings = sorted(
            state.findings, 
            key=lambda x: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(x.get("severity", "low"), 0), 
            reverse=True
        )
        
        # 1. EXECUTIVE SUMMARY
        top_findings = sorted_findings[:3]
        executive_summary = {
            "genel_degerlendirme": f"Bu rapor, {state.target} sistemine yönelik gerçekleştirilen penetrasyon testinin sonuçlarını özetlemektedir. Testler, sistemin genel güvenlik duruşunu ve potansiyel risklerini değerlendirmek amacıyla yapılmıştır. Değerlendirme sonucunda, sistemin güvenlik seviyesi '{overall_risk}' olarak belirlenmiştir.",
            "risk_skoru": risk_score,
            "risk_seviyesi": overall_risk,
            "kritik_bulgular": [
                {
                    "baslik": f.get("title", "N/A"),
                    "is_etkisi": self._generate_business_impact(f),
                    "severity": f.get("severity", "unknown")
                }
                for f in top_findings
            ] if top_findings else [],
            "oncelikli_aksiyonlar": [
                {
                    "bulgu": f.get("title", "N/A"),
                    "oneri": self._get_remediation(f).split('\n')[0]
                }
                for f in top_findings
            ] if top_findings else []
        }
        
        # 2. METHODOLOGY
        methodology = {
            "standartlar": "OWASP Testing Guide, PTES ve NIST SP 800-115",
            "kapsam": state.target,
            "test_baslangic": state.start_time.strftime('%d.%m.%Y %H:%M') if state.start_time else "N/A",
            "kapsam_disi": "Sosyal mühendislik, fiziksel güvenlik ve DoS/DDoS saldırıları bu testin kapsamı dışındadır.",
            "aciklama": "Bu güvenlik değerlendirmesi, OWASP Testing Guide, PTES ve NIST SP 800-115 gibi endüstri standartlarına uygun, otomatize edilmiş bir metodoloji ile gerçekleştirilmiştir."
        }
        
        # 3. TECHNICAL FINDINGS (Risk Matrix ve Findings Summary kaldırıldı)
        
        # 3. DETAILED FINDINGS
        detailed_findings = []
        for i, finding in enumerate(sorted_findings, 1):
            detailed_findings.append({
                "id": i,
                "baslik": finding.get("title", "N/A"),
                "severity": finding.get("severity", "low"),
                "cvss_skoru": finding.get("cvss_score", "N/A"),
                "cve_id": finding.get("cve_id", "N/A"),
                "aciklama": finding.get("description", "Açıklama bulunamadı"),
                "kanit": finding.get("evidence", "Kanıt bulunamadı"),
                "is_etkisi": finding.get("business_impact") or self._generate_business_impact(finding),
                "cozum": finding.get("recommendation_summary") or self._get_remediation(finding),
                "owasp_referans": self._get_owasp_reference(finding),
                "hedef": finding.get("target", state.target),
                "teknoloji": finding.get("technology", "N/A")
            })
        
        # 4. RECOMMENDATIONS & CONCLUSION
        recommendations = {
            "acil_aksiyonlar": [],
            "kisa_vade_aksiyonlar": [],
            "stratejik_iyilestirmeler": [],
            "sonuc": ""
        }
        
        # Acil aksiyonlar
        for f in sorted_findings:
            if f.get('severity') == 'critical':
                recommendations["acil_aksiyonlar"].append({
                    "baslik": f.get('title'),
                    "oneri": self._get_remediation(f).split('\n')[0]
                })
        
        # Kısa vade aksiyonlar
        for f in sorted_findings:
            if f.get('severity') == 'high':
                recommendations["kisa_vade_aksiyonlar"].append({
                    "baslik": f.get('title'),
                    "oneri": self._get_remediation(f).split('\n')[0]
                })
        
        # Stratejik iyileştirmeler
        categories = self._categorize_findings_by_owasp(state.findings)
        if "A05:2021 - Security Misconfiguration" in categories:
            recommendations["stratejik_iyilestirmeler"].append({
                "alan": "Konfigürasyon Yönetimi",
                "oneri": "Sunucu, veritabanı ve bulut hizmetleri için 'güvenli temel' konfigürasyonları oluşturun ve düzenli olarak denetleyin."
            })
        if "A03:2021 - Injection" in categories:
            recommendations["stratejik_iyilestirmeler"].append({
                "alan": "Injection Koruması",
                "oneri": "Tüm veri girişlerinde parameterized queries kullanın ve input validation uygulayın."
            })
        if "A01:2021 - Broken Access Control" in categories:
            recommendations["stratejik_iyilestirmeler"].append({
                "alan": "Erişim Kontrolü",
                "oneri": "Zero Trust model ve rol-bazlı erişim kontrolü (RBAC) uygulayın."
            })
        
        # Sonuç
        top_category = max(categories, key=categories.get, default="").split(' - ')[-1] if categories else ""
        conclusion = f"Bu güvenlik değerlendirmesi, {state.target} sisteminin genel güvenlik durumunu '{overall_risk}' olarak belirlemiştir. "
        if top_category:
            conclusion += f"Test sırasında tespit edilen zafiyetlerin yoğunlaştığı ana tema '{top_category}' olarak öne çıkmaktadır. "
        if findings_summary['by_severity']['critical'] > 0:
            conclusion += "Tespit edilen kritik seviyedeki bulgular, sisteme yönelik ciddi tehditler oluşturmakta ve acil müdahale gerektirmektedir. "
        elif findings_summary['by_severity']['high'] > 0:
            conclusion += "Yüksek seviyeli bulgular, önemli veri sızıntısı veya hizmet kesintisi riskleri taşımaktadır ve öncelikli olarak ele alınmalıdır. "
        conclusion += "Raporda detaylandırılan stratejik ve taktiksel önerilerin uygulanması, sistemin siber saldırılara karşı dayanıklılığını önemli ölçüde artıracaktır."
        recommendations["sonuc"] = conclusion
        
        # APPENDIX
        appendix = {
            "test_kapsami": [state.target],
            "subdomainler": state.context_summary.get("subdomains", [])[:10] if state.context_summary else [],
            "acik_portlar": state.context_summary.get("open_ports", [])[:15] if state.context_summary else [],
            "standartlar": [
                "OWASP Top 10 2021",
                "PTES (Penetration Testing Execution Standard)",
                "NIST SP 800-115",
                "CVSS v3.1"
            ]
        }
        
        # CVE referansları ekle
        cve_references = []
        for finding in sorted_findings:
            if finding.get("cve_id") and finding.get("cve_id") != "N/A":
                cve_references.append({
                    "cve_id": finding.get("cve_id"),
                    "title": finding.get("title"),
                    "severity": finding.get("severity"),
                    "description": finding.get("description"),
                    "target": finding.get("target", state.target)
                })
        
        return {
            "executive_summary": executive_summary,
            "methodology": methodology,
            "detailed_findings": detailed_findings,
            "recommendations": recommendations,
            "appendix": appendix,
            "cve_references": cve_references
        }

    async def generate_report(self, state: AgentState, output_path: str) -> bool:
        """
        Profesyonel penetrasyon testi raporunu oluşturur ve kaydeder.
        """
        try:
            logger.info(f"Profesyonel pentest raporu '{output_path}' için oluşturuluyor...")

            # RAG ile bulguları zenginleştirme adımı
            if self.rag_client:
                logger.info("RAG ile bulgular zenginleştiriliyor...")
                state.findings = await self._rag_ile_zenginlestir_bulgular(state.findings)

            # Rapor metnini yeni profesyonel formatla oluştur
            report_content_text = self._prepare_professional_report_text(state)
            
            # --- RAPORU FARKLI FORMATLARDA KAYDET ---

            # 1. TXT olarak kaydet
            txt_path = output_path.rsplit('.', 1)[0] + '.txt'
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(report_content_text)
            logger.info(f"Metin raporu başarıyla kaydedildi: {txt_path}")

            # 2. PDF olarak kaydet (eğer kütüphane varsa)
            if PDF_GENERATION_AVAILABLE:
                pdf_path = output_path.rsplit('.', 1)[0] + '.pdf'
                self._create_simple_pdf_from_text(report_content_text, pdf_path)
                logger.info(f"PDF raporu başarıyla kaydedildi: {pdf_path}")

            # 3. JSON olarak kaydet
            json_path = output_path.rsplit('.', 1)[0] + '.json'
            self._create_json_report(state, json_path)
            logger.info(f"JSON raporu başarıyla kaydedildi: {json_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Rapor oluşturma sırasında kritik hata: {e}", exc_info=True)
            return False
                
    def _clean_text_for_pdf(self, text: str) -> str:
        """PDF için metni temizle - emoji ve özel karakterleri kaldır"""
        import re
        # Emoji ve özel karakterleri temizle
        text = text.encode('ascii', 'ignore').decode('ascii')
        # Çoklu boşlukları tek boşluğa çevir
        text = re.sub(r'\s+', ' ', text)
        # Özel karakterleri değiştir
        replacements = {
            '🔍': '[Arama]',
            '🛡️': '[Guvenlik]',
            '⚙️': '[Ayar]',
            '🔧': '[Arac]',
            '📊': '[Rapor]',
            '✅': '[Tamam]',
            '❌': '[Hata]',
            '⚠️': '[Uyari]',
            '💡': '[Oneri]',
            '🚨': '[Kritik]',
            '📋': '[Liste]',
            '🌐': '[Web]',
            '🔐': '[Kilit]',
            '📦': '[Paket]',
            '🎯': '[Hedef]',
            '═': '=',
            '─': '-',
            '│': '|',
            '┌': '+',
            '└': '+',
            '├': '+',
            '┤': '+',
            '■': '*',
            '□': '-'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    
    def _create_simple_pdf_from_text(self, text_content: str, pdf_path: str):
        """PROFESYONEL SIZMA TESTİ RAPORU - Kurumsal format, düzenli boşluklar."""
        doc = SimpleDocTemplate(
            pdf_path, 
            pagesize=A4, 
            topMargin=50, 
            bottomMargin=50, 
            leftMargin=60, 
            rightMargin=60
        )
        styles = getSampleStyleSheet()
        
        # PROFESYONEL STİLLER - DÜZENLİ BOŞLUKLAR
        # Kapak başlığı (Normal boyut)
        cover_title = ParagraphStyle(
            'CoverTitle',
            parent=styles['Title'],
            fontSize=20,
            textColor=colors.black,
            spaceAfter=20,
            alignment=1,  # Center
            fontName='Helvetica-Bold'
        )
        
        # Ana başlıklar (Normal boyut, düzenli boşluklar)
        heading1_style = ParagraphStyle(
            'CustomHeading1',
            parent=styles['Heading1'],
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            spaceAfter=12,
            spaceBefore=20,
            alignment=0  # Left align
        )
        
        # Alt başlıklar (Küçük, düzenli)
        heading2_style = ParagraphStyle(
            'CustomHeading2',
            parent=styles['Heading2'],
            fontSize=12,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            spaceAfter=8,
            spaceBefore=12
        )
        
        # Normal metin (Düzenli, okunabilir)
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            spaceAfter=6,
            alignment=0,  # Left align (justify değil)
            textColor=colors.black
        )
        
        # Liste öğeleri (Düzenli boşluklar)
        bullet_style = ParagraphStyle(
            'CustomBullet',
            parent=styles['Bullet'],
            fontSize=9,
            leading=12,
            leftIndent=20,
            spaceAfter=4,
            bulletIndent=8,
            textColor=colors.black
        )
        
        # Kod/URL satırları (Küçük, düzenli)
        code_style = ParagraphStyle(
            'CustomCode',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=8,
            leading=10,
            leftIndent=15,
            backgroundColor=colors.lightgrey,
            textColor=colors.black
        )
        
        # Metni temizle
        text_content = self._clean_text_for_pdf(text_content)
        
        story = []
        is_cover_page = True
        in_cve_section = False
        
        lines = text_content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Boş satırları atla
            if not line:
                story.append(Spacer(1, 12))
                i += 1
                continue
            
            # === veya --- ayırıcıları atla
            if all(c in '=-' for c in line) and len(line) > 10:
                i += 1
                continue
            
            # KAPAK SAYFASI - İlk başlık
            if is_cover_page and ('PENETRATION' in line.upper() or 'SECURITY' in line.upper() or 'SIZMA' in line.upper()):
                story.append(Spacer(1, 150))  # Üstten boşluk
                story.append(Paragraph(line.upper(), cover_title))
                story.append(Spacer(1, 30))
                is_cover_page = False
                i += 1
                continue
            
            # Bölüm başlıkları (1., 2., 3. ile başlayan)
            if line and len(line) < 80 and line[0].isdigit() and '.' in line[:5]:
                story.append(PageBreak())  # Her bölüm yeni sayfa
                story.append(Paragraph(line, heading1_style))
                i += 1
                continue
            
            # Alt başlıklar (1.1, 1.2 gibi veya [...] formatında)
            if ((line and len(line) < 80 and line[0].isdigit() and line.count('.') == 2) or 
                (line.startswith('[') and line.endswith(']'))):
                clean_line = line[1:-1] if line.startswith('[') else line
                story.append(Paragraph(clean_line, heading2_style))
                i += 1
                continue
            
            # CVE Bölümü tespit et (Detaylı Bulgular kısmı)
            if 'DETAYLI' in line.upper() and 'BULGULAR' in line.upper():
                in_cve_section = True
                story.append(Paragraph(line, heading1_style))
                i += 1
                continue
            
            # Liste öğeleri
            if line.startswith(('*', '-', '•', '  •', '  -', '  *')):
                story.append(Paragraph(line, bullet_style))
                i += 1
                continue
            
            # Kod/URL satırları
            if "HTTP/" in line or "curl" in line or "://" in line:
                story.append(Paragraph(line.replace(" ", "&nbsp;"), code_style))
                i += 1
                continue
            
            # Normal paragraflar
            story.append(Paragraph(line, normal_style))
            i += 1
        
        try:
            doc.build(story)
            logger.info(f"✅ Profesyonel PDF başarıyla oluşturuldu: {pdf_path}")
        except Exception as e:
            logger.error(f"❌ PDF oluşturma hatası: {e}, fallback kullanılıyor")
            # Fallback: Canvas ile basit PDF
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(pdf_path, pagesize=A4)
            c.setFont("Helvetica", 10)
            y = 800
            page_num = 1
            for line in text_content.split('\n'):
                if y < 50:
                    c.setFont("Helvetica", 8)
                    c.drawString(520, 30, f"Sayfa {page_num}")
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y = 800
                    page_num += 1
                try:
                    c.drawString(50, y, line[:90])  # İlk 90 karakter
                except:
                    pass
                y -= 15
            c.setFont("Helvetica", 8)
            c.drawString(520, 30, f"Sayfa {page_num}")
            c.save()
            logger.info(f"✅ Fallback PDF oluşturuldu: {pdf_path}")
            
    def _create_json_report(self, state: AgentState, json_path: str):
        """Sektör standardında JSON raporu oluşturur."""
        import json
        risk_score = self._calculate_risk_score(state.findings)
            
        report_data = {
            "reportMetadata": {
                "reportId": f"PENTAGENT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "target": state.target,
                "timestamp": datetime.now().isoformat(),
                "testDurationSeconds": round(state.execution_time, 2)
            },
            "executiveSummary": {
                "overallRiskLevel": self._calculate_overall_risk_level(state.get_findings_summary()),
                "overallRiskScore": risk_score,
                "findingCounts": state.get_findings_summary()['by_severity']
            },
            "findings": []
        }

        for finding in state.findings:
            report_data["findings"].append({
                "title": finding.get('title'),
                "severity": finding.get('severity').upper(),
                "cvssScore": finding.get('cvss_score'),
                "cveId": finding.get('cve_id'),
                "owaspCategory": self._get_owasp_reference(finding),
                "description": finding.get('description'),
                "businessImpact": self._generate_business_impact(finding),
                "proofOfConcept": finding.get('evidence'),
                "remediation": self._get_remediation(finding)
            })
            
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

    def _generate_report_content(self, state: AgentState, cve_results=None, risk_score=None) -> str:
        """Rapor içeriğini oluştur - CVE'ler ve risk skoru ile"""
        try:
            report_parts = []
            
            # Profesyonel Başlık
            report_parts.append("# PROFESYONEL SIZMA TESTİ RAPORU")
            report_parts.append("")
            report_parts.append("---")
            report_parts.append("")
            report_parts.append(f"**Hedef Sistem:** {state.target}")
            report_parts.append(f"**Test Tarihi:** {datetime.now().strftime('%d %B %Y, %H:%M')}")
            report_parts.append(f"**Risk Skoru:** {risk_score or 'N/A'}/100")
            report_parts.append(f"**Rapor ID:** PENTAGENT-{datetime.now().strftime('%Y%m%d%H%M%S')}")
            report_parts.append("")
            report_parts.append("---")
            report_parts.append("")
            
            # Yönetici Özeti
            report_parts.append("## 1. YÖNETİCİ ÖZETİ")
            report_parts.append("")
            findings_count = len(state.findings)
            critical_count = len([f for f in state.findings if f.get('severity') == 'critical'])
            high_count = len([f for f in state.findings if f.get('severity') == 'high'])
            
            report_parts.append(f"Toplam bulgu sayısı: {findings_count}")
            report_parts.append(f"Kritik seviye: {critical_count}")
            report_parts.append(f"Yüksek seviye: {high_count}")
            report_parts.append("")
            
            # Detaylı Bulgular
            if state.findings:
                report_parts.append("## 2. DETAYLI BULGULAR")
                report_parts.append("")
                
                for i, finding in enumerate(state.findings, 1):
                    report_parts.append(f"{i}. {finding.get('title', 'Bilinmeyen Bulgu')}")
                    report_parts.append(f"   Severity: {finding.get('severity', 'Unknown')}")
                    report_parts.append(f"   Açıklama: {finding.get('description', 'Açıklama yok')}")
                    report_parts.append(f"   Kanıt: {finding.get('evidence', 'Kanıt yok')}")
                    report_parts.append("")
            
            # Tool çıktıları
            if state.discovered_information:
                tool_outputs = {k: v for k, v in state.discovered_information.items() if k.startswith('tool_')}
                if tool_outputs:
                    report_parts.append("3. TOOL ÇIKTILARI")
                    report_parts.append("-" * 30)
                    
                    for tool_name, tool_data in tool_outputs.items():
                        clean_name = tool_name.replace('tool_', '')
                        report_parts.append(f"Tool: {clean_name}")
                        report_parts.append(f"Çıktı: {str(tool_data)[:500]}...")
                        report_parts.append("")
            
            # CVE Analizi
            if cve_results:
                report_parts.append("## 3. CVE ANALİZİ")
                report_parts.append("")
                
                for i, cve in enumerate(cve_results[:10], 1):  # Top 10 CVE
                    if isinstance(cve, dict):
                        cve_id = cve.get('cve_id', 'N/A')
                        description = cve.get('description', 'N/A')[:200]
                        severity = cve.get('severity', 'N/A')
                        cvss = cve.get('base_score', 'N/A')
                        
                        report_parts.append(f"### {i}. {cve_id}")
                        report_parts.append(f"**Severity:** {severity}")
                        report_parts.append(f"**CVSS:** {cvss}")
                        report_parts.append(f"**Description:** {description}")
                        report_parts.append("")
            
            # Tool Çıktıları
            if hasattr(state, 'discovered_information') and state.discovered_information:
                report_parts.append("## 4. TOOL ÇIKTILARI")
                report_parts.append("")
                
                for tool_name, tool_data in state.discovered_information.items():
                    if tool_name.startswith('tool_') and tool_data:
                        clean_name = tool_name[5:]  # "tool_" prefix'ini kaldır
                        report_parts.append(f"### {clean_name.upper()}")
                        report_parts.append(f"```json")
                        report_parts.append(f"{str(tool_data)[:500]}...")
                        report_parts.append(f"```")
                        report_parts.append("")
            
            return "\n".join(report_parts)
            
        except Exception as e:
            logger.error(f"Rapor içeriği oluşturma hatası: {e}")
            return "Rapor içeriği oluşturulamadı"

    # Web API için sync metod
    def generate_llm_enhanced_report(self, findings: List[Dict[str, Any]], target: str, cve_results: List[Dict[str, Any]] = None, tool_outputs: Dict[str, Any] = None, scan_results: Dict[str, Any] = None) -> str:
        """LLM ile gelişmiş rapor üretimi"""
        try:
            # Bulguları kategorize et
            critical_findings = [f for f in findings if f.get('severity') == 'critical']
            high_findings = [f for f in findings if f.get('severity') == 'high']
            medium_findings = [f for f in findings if f.get('severity') == 'medium']
            low_findings = [f for f in findings if f.get('severity') == 'low']
            
            # Risk skoru hesapla
            risk_score = self._calculate_risk_score(findings)
            risk_level = self._get_risk_level_from_score(risk_score)
            
            # LLM prompt oluştur
            prompt = f"""
Sen bir siber güvenlik uzmanısın. Aşağıdaki penetrasyon testi sonuçlarına dayanarak profesyonel bir güvenlik raporu oluştur.

HEDEF: {target}
RİSK SKORU: {risk_score}/100 ({risk_level})
TARİH: {datetime.now().strftime('%d/%m/%Y %H:%M')}

BULGULAR:
- Kritik: {len(critical_findings)} bulgu
- Yüksek: {len(high_findings)} bulgu  
- Orta: {len(medium_findings)} bulgu
- Düşük: {len(low_findings)} bulgu

DETAYLI BULGULAR:
{self._format_findings_for_llm(findings)}

CVE REFANSLARI:
{self._format_cve_results_for_llm(cve_results) if cve_results else 'CVE referansı bulunamadı'}

KULLANILAN ARAÇLAR VE SONUÇLARI:
{self._format_tool_outputs_for_llm(tool_outputs) if tool_outputs else 'Araç çıktıları bulunamadı'}

Lütfen aşağıdaki yapıda profesyonel bir rapor oluştur:

# GÜVENLİK RAPORU - {target}

## YÖNETİCİ ÖZETİ
- Risk seviyesi ve genel değerlendirme
- Kritik bulguların özeti
- Acil aksiyon gereken alanlar

## METODOLOJİ
- Kullanılan test yöntemleri
- Test kapsamı ve sınırları

## BULGULAR
### Kritik Bulgular
- Her kritik bulgu için detaylı açıklama
- CVSS skoru ve etki analizi
- Önerilen çözümler

### Yüksek Risk Bulgular
- Yüksek risk bulguların detayları
- İş etkisi analizi

### Orta ve Düşük Risk Bulgular
- Orta ve düşük risk bulguların özeti

## CVE ANALİZİ
- Tespit edilen CVE'ler
- Etkilenen sistemler
- Güncelleme önerileri

## ÖNERİLER
- Genel güvenlik önerileri
- Acil aksiyon planı
- Uzun vadeli güvenlik stratejisi

## EKLER
- Teknik detaylar
- Referanslar
"""
            
            # LLM'den yanıt al (basit implementasyon)
            # Gerçek implementasyonda Groq API kullanılabilir
            return self._generate_llm_response(prompt, findings, target, tool_outputs)
            
        except Exception as e:
            logger.error(f"LLM rapor üretimi hatası: {e}")
            return self._generate_fallback_report(findings, target, tool_outputs)
    
    def _get_risk_level_from_score(self, score: int) -> str:
        """Risk skorundan risk seviyesi belirle"""
        if score >= 80:
            return "KRİTİK"
        elif score >= 60:
            return "YÜKSEK"
        elif score >= 40:
            return "ORTA"
        elif score >= 20:
            return "DÜŞÜK"
        else:
            return "MİNİMAL"
    
    def _format_findings_for_llm(self, findings: List[Dict[str, Any]]) -> str:
        """Bulguları LLM için formatla"""
        formatted = []
        for i, finding in enumerate(findings, 1):
            formatted.append(f"""
{i}. {finding.get('title', 'Bilinmeyen Bulgu')}
   Severity: {finding.get('severity', 'unknown').upper()}
   CVSS: {finding.get('cvss_score', 'N/A')}
   CVE: {finding.get('cve_id', 'N/A')}
   Açıklama: {finding.get('description', 'Açıklama yok')}
   Kanıt: {finding.get('evidence', 'Kanıt yok')}
   Öneri: {finding.get('recommendation_summary', 'Öneri yok')}
   İş Etkisi: {finding.get('business_impact', 'Etki analizi yok')}
""")
        return "\n".join(formatted)
    
    def _format_cve_results_for_llm(self, cve_results: List[Dict[str, Any]]) -> str:
        """CVE sonuçlarını LLM için formatla"""
        if not cve_results:
            return "CVE referansı bulunamadı"
        
        formatted = []
        for cve in cve_results:
            formatted.append(f"""
- {cve.get('cve_id', 'Unknown CVE')}
  Severity: {cve.get('severity', 'unknown')}
  CVSS: {cve.get('base_score', 'N/A')}
  Açıklama: {cve.get('description', 'Açıklama yok')}
  Etkilenen Sistem: {cve.get('product', 'Bilinmeyen')}
""")
        return "\n".join(formatted)
    
    def _generate_llm_response(self, prompt: str, findings: List[Dict[str, Any]], target: str, tool_outputs: Dict[str, Any] = None) -> str:
        """LLM'den yanıt al (basit implementasyon)"""
        # Bu kısımda gerçek LLM API çağrısı yapılabilir
        # Şimdilik template-based response döndürelim
        
        critical_count = len([f for f in findings if f.get('severity') == 'critical'])
        high_count = len([f for f in findings if f.get('severity') == 'high'])
        medium_count = len([f for f in findings if f.get('severity') == 'medium'])
        low_count = len([f for f in findings if f.get('severity') == 'low'])
        
        risk_score = self._calculate_risk_score(findings)
        risk_level = self._get_risk_level_from_score(risk_score)
        
        return f"""# GÜVENLİK RAPORU - {target}

## YÖNETİCİ ÖZETİ

Bu rapor, {target} hedef sistemine yönelik gerçekleştirilen penetrasyon testinin sonuçlarını özetlemektedir. Test sonucunda toplam {len(findings)} güvenlik bulgusu tespit edilmiştir.

**Risk Seviyesi: {risk_level} ({risk_score}/100)**

### Bulgu Dağılımı:
- 🔴 Kritik: {critical_count} bulgu
- 🟠 Yüksek: {high_count} bulgu  
- 🟡 Orta: {medium_count} bulgu
- 🟢 Düşük: {low_count} bulgu

### Acil Aksiyon Gereken Alanlar:
{self._get_critical_summary(findings)}

## METODOLOJİ

Bu penetrasyon testi aşağıdaki metodoloji ile gerçekleştirilmiştir:

1. **Bilgi Toplama**: Hedef sistem hakkında bilgi toplama
2. **Keşif**: Açık portlar, servisler ve dizinlerin tespiti
3. **Zafiyet Analizi**: Tespit edilen servislerde zafiyet taraması
4. **Exploit Geliştirme**: Tespit edilen zafiyetlerin exploit edilebilirliği
5. **Raporlama**: Bulguların analizi ve önerilerin hazırlanması

### Kullanılan Araçlar ve Sonuçları:
{self._format_tool_outputs_for_llm(tool_outputs) if tool_outputs else 'Tool çıktıları mevcut değil'}

## BULGULAR

{self._generate_detailed_findings(findings)}

## ÖNERİLER

### Acil Aksiyon Planı (0-7 gün):
{self._get_urgent_recommendations(findings)}

### Kısa Vadeli Öneriler (1-4 hafta):
{self._get_short_term_recommendations(findings)}

### Uzun Vadeli Strateji (1-6 ay):
{self._get_long_term_recommendations(findings)}

## SONUÇ

{target} sisteminde tespit edilen güvenlik bulguları, sistemin güvenlik duruşunun iyileştirilmesi gerektiğini göstermektedir. Özellikle kritik ve yüksek risk bulgularının acil olarak ele alınması önerilmektedir.

Bu rapor, güvenlik ekibinin öncelikli aksiyon planı oluşturması için hazırlanmıştır. Tüm bulguların detaylı analizi ve çözüm önerileri yukarıda sunulmuştur.

---
*Rapor Tarihi: {datetime.now().strftime('%d/%m/%Y %H:%M')}*
*Risk Skoru: {risk_score}/100*
*Toplam Bulgu: {len(findings)}*
"""
    
    def _get_critical_summary(self, findings: List[Dict[str, Any]]) -> str:
        """Kritik bulguların özeti"""
        critical_findings = [f for f in findings if f.get('severity') == 'critical']
        if not critical_findings:
            return "Kritik bulgu tespit edilmedi."
        
        summary = []
        for finding in critical_findings[:3]:  # İlk 3 kritik bulgu
            summary.append(f"- {finding.get('title', 'Bilinmeyen')}: {finding.get('description', 'Açıklama yok')}")
        
        return "\n".join(summary)
    
    def _generate_detailed_findings(self, findings: List[Dict[str, Any]]) -> str:
        """Detaylı bulgular bölümü"""
        sections = []
        
        # Kritik bulgular
        critical_findings = [f for f in findings if f.get('severity') == 'critical']
        if critical_findings:
            sections.append("### 🔴 Kritik Bulgular")
            for finding in critical_findings:
                sections.append(self._format_finding_detail(finding))
        
        # Yüksek bulgular
        high_findings = [f for f in findings if f.get('severity') == 'high']
        if high_findings:
            sections.append("### 🟠 Yüksek Risk Bulgular")
            for finding in high_findings:
                sections.append(self._format_finding_detail(finding))
        
        # Orta bulgular
        medium_findings = [f for f in findings if f.get('severity') == 'medium']
        if medium_findings:
            sections.append("### 🟡 Orta Risk Bulgular")
            for finding in medium_findings[:5]:  # İlk 5 orta risk
                sections.append(self._format_finding_detail(finding))
        
        return "\n\n".join(sections)
    
    def _format_finding_detail(self, finding: Dict[str, Any]) -> str:
        """Tek bulgu detayını formatla"""
        return f"""
**{finding.get('title', 'Bilinmeyen Bulgu')}**

- **Severity**: {finding.get('severity', 'unknown').upper()}
- **CVSS**: {finding.get('cvss_score', 'N/A')}
- **CVE**: {finding.get('cve_id', 'N/A')}
- **Açıklama**: {finding.get('description', 'Açıklama yok')}
- **Kanıt**: {finding.get('evidence', 'Kanıt yok')}
- **Öneri**: {finding.get('recommendation_summary', 'Öneri yok')}
- **İş Etkisi**: {finding.get('business_impact', 'Etki analizi yok')}
"""
    
    def _get_urgent_recommendations(self, findings: List[Dict[str, Any]]) -> str:
        """Acil öneriler"""
        critical_findings = [f for f in findings if f.get('severity') == 'critical']
        if not critical_findings:
            return "Kritik bulgu olmadığı için acil aksiyon gerekmiyor."
        
        recommendations = []
        for finding in critical_findings:
            recommendations.append(f"- {finding.get('recommendation_summary', 'Güvenlik güncellemesi yapın')}")
        
        return "\n".join(recommendations)
    
    def _get_short_term_recommendations(self, findings: List[Dict[str, Any]]) -> str:
        """Kısa vadeli öneriler"""
        return """- Tüm sistemlerin güvenlik güncellemelerini yapın
- Güvenlik duvarı kurallarını gözden geçirin
- Erişim kontrollerini güçlendirin
- Düzenli güvenlik taramaları planlayın"""
    
    def _get_long_term_recommendations(self, findings: List[Dict[str, Any]]) -> str:
        """Uzun vadeli öneriler"""
        return """- Güvenlik mimarisini gözden geçirin
- Güvenlik farkındalığı eğitimleri düzenleyin
- Incident response planı oluşturun
- Güvenlik monitoring sistemi kurun"""
    
    def _format_tool_outputs_for_llm(self, tool_outputs: Dict[str, Any]) -> str:
        """Tool çıktılarını LLM için formatla"""
        if not tool_outputs:
            return "Tool çıktıları mevcut değil"
        
        formatted = []
        for tool_name, output in tool_outputs.items():
            if isinstance(output, dict) and output.get('success'):
                data = output.get('data', {})
                formatted.append(f"""
**{tool_name.replace('_', ' ').title()}**
- Durum: ✅ Başarılı
- Sonuç: {self._extract_tool_summary(data)}
""")
            elif isinstance(output, dict) and not output.get('success'):
                formatted.append(f"""
**{tool_name.replace('_', ' ').title()}**
- Durum: ❌ Başarısız
- Hata: {output.get('error', 'Bilinmeyen hata')}
""")
        
        return "\n".join(formatted) if formatted else "Tool çıktıları formatlanamadı"
    
    def _extract_tool_summary(self, data: Dict[str, Any]) -> str:
        """Tool verisinden özet çıkar"""
        if not isinstance(data, dict):
            return "Veri formatı uygun değil"
        
        # Tool tipine göre özet çıkar
        if 'vulnerabilities' in data:
            vulns = data.get('vulnerabilities', [])
            return f"{len(vulns)} zafiyet tespit edildi"
        elif 'directories' in data:
            dirs = data.get('directories', [])
            return f"{len(dirs)} dizin bulundu"
        elif 'open_ports' in data:
            ports = data.get('open_ports', [])
            return f"{len(ports)} açık port tespit edildi"
        elif 'subdomains' in data:
            subs = data.get('subdomains', [])
            return f"{len(subs)} subdomain bulundu"
        elif 'technologies' in data:
            techs = data.get('technologies', [])
            return f"{len(techs)} teknoloji tespit edildi"
        else:
            return "Tool çalıştırıldı, detaylar mevcut"
    
    def _generate_fallback_report(self, findings: List[Dict[str, Any]], target: str, tool_outputs: Dict[str, Any] = None) -> str:
        """LLM hatası durumunda fallback rapor"""
        return f"""# GÜVENLİK RAPORU - {target}

## YÖNETİCİ ÖZETİ

{target} sistemine yönelik penetrasyon testi tamamlanmıştır.

**Toplam Bulgu**: {len(findings)}

### Bulgu Dağılımı:
- Kritik: {len([f for f in findings if f.get('severity') == 'critical'])}
- Yüksek: {len([f for f in findings if f.get('severity') == 'high'])}
- Orta: {len([f for f in findings if f.get('severity') == 'medium'])}
- Düşük: {len([f for f in findings if f.get('severity') == 'low'])}

### Kullanılan Araçlar:
{self._format_tool_outputs_for_llm(tool_outputs) if tool_outputs else 'Tool çıktıları mevcut değil'}

## BULGULAR

{self._generate_detailed_findings(findings)}

---
*Rapor Tarihi: {datetime.now().strftime('%d/%m/%Y %H:%M')}*
"""
    
    def generate_comprehensive_report_sync(self, enriched_data: Dict[str, Any]) -> str:
        """Web API için sync rapor oluşturma"""
        try:
            # Enriched data'dan state oluştur
            state = AgentState(
                target=enriched_data.get("target", "Unknown"),
                user_task=enriched_data.get("user_task", "Güvenlik raporu oluştur")
            )
            state.findings = enriched_data.get("findings", [])
            state.discovered_information = enriched_data.get("discovered_information", {})
            
            # Tool çıktılarını ekle
            tool_outputs = enriched_data.get("all_tool_outputs", {})
            cve_results = enriched_data.get("cve_results", [])
            
            # LLM ile gelişmiş rapor oluştur
            llm_report = self.generate_llm_enhanced_report(
                findings=state.findings,
                target=state.target,
                cve_results=cve_results,
                tool_outputs=tool_outputs,
                scan_results=enriched_data  # scan_results parametresi eklendi
            )
            
            return llm_report
            
        except Exception as e:
            logger.error(f"Sync rapor oluşturma hatası: {e}")
            return f"Rapor oluşturulamadı: {str(e)}"

    # Dynamic orchestrator ile entegrasyon için yeni metod - RAG ENTEGRASYONU
    async def generate_comprehensive_report_async(self, state: AgentState, final_analysis: Dict[str, Any], execution_results: Dict[str, Any]) -> Dict[str, Any]:
        """Dynamic orchestrator için kapsamlı ve dinamik rapor oluşturur - RAG entegrasyonu ile"""
        try:
            # State'den findings al - MEVCUT BULGULARI KORU!
            if not hasattr(state, 'findings'):
                state.findings = []
            
            existing_findings_count = len(state.findings)
            logger.info(f"📊 Mevcut bulgu sayısı: {existing_findings_count}")
            
            # Eğer hiç bulgu yoksa execution_results'tan ek bulgular oluştur
            if not state.findings:
                logger.warning("⚠️ State'de bulgu yok, execution_results'tan oluşturuluyor")
                
                # Execution history'den ek findings oluştur (mevcut bulguları koru)
                additional_findings = []
                if isinstance(execution_results, list):
                    for step in execution_results:
                        if isinstance(step, dict):
                            tool_name = step.get("tool", "")
                            result = step.get("result", {})
                            
                            if result.get("success", False):
                                data = result.get("data", {})
                                
                                # Tool'a göre finding oluştur
                                if "vulnerabilities" in data:
                                    for vuln in data["vulnerabilities"]:
                                        finding = {
                                            'title': vuln.get('type', f'{tool_name} vulnerability'),
                                            'severity': vuln.get('severity', 'medium'),
                                            'description': vuln.get('description', 'Vulnerability detected'),
                                            'evidence': vuln.get('evidence', 'Proof of concept available'),
                                            'target': state.target,
                                            'technology': 'Web Application'
                                        }
                                        additional_findings.append(finding)
                                
                                # Admin panel bulguları
                                elif "discovered_panels" in data:
                                    panels = data["discovered_panels"]
                                    if panels:
                                        finding = {
                                            'title': 'Exposed Admin Panels',
                                            'severity': 'high',
                                            'description': f'{len(panels)} admin panel ve management interface keşfedildi',
                                            'evidence': f'Discovered panels: {panels[:3]}',
                                            'target': state.target,
                                            'technology': 'Infrastructure'
                                        }
                                        additional_findings.append(finding)
                                
                                # Missing headers
                                elif "missing_security_headers" in data:
                                    headers = data["missing_security_headers"]
                                    if headers:
                                        finding = {
                                            'title': 'Missing Security Headers',
                                            'severity': 'medium',
                                            'description': f'Eksik güvenlik header\'ları: {", ".join(headers)}',
                                            'evidence': f'Missing headers: {headers}',
                                            'target': state.target,
                                            'technology': 'HTTP'
                                        }
                                        additional_findings.append(finding)
                                
                                # Web crawler bulguları
                                elif "forms" in data or "parameters" in data:
                                    forms = data.get("forms", [])
                                    parameters = data.get("parameters", [])
                                    if forms or parameters:
                                        finding = {
                                            'title': 'Web Application Discovery',
                                            'severity': 'medium',
                                            'description': f'Web uygulamasında {len(forms)} form ve {len(parameters)} parametre tespit edildi',
                                            'evidence': f'Forms: {forms[:3]}, Parameters: {parameters[:5]}',
                                            'target': state.target,
                                            'technology': 'Web Application'
                                        }
                                        additional_findings.append(finding)
                                
                                # Technology detection
                                elif "technologies" in data:
                                    technologies = data["technologies"]
                                    if technologies:
                                        finding = {
                                            'title': 'Technology Detection',
                                            'severity': 'low',
                                            'description': f'{len(technologies)} teknoloji tespit edildi',
                                            'evidence': f'Technologies: {technologies[:5]}',
                                            'target': state.target,
                                            'technology': 'Technology Stack'
                                        }
                                        additional_findings.append(finding)
                                
                                # Open ports
                                elif "open_ports" in data:
                                    ports = data["open_ports"]
                                    if ports:
                                        finding = {
                                            'title': 'Open Ports Discovery',
                                            'severity': 'medium',
                                            'description': f'{len(ports)} açık port tespit edildi',
                                            'evidence': f'Open ports: {ports[:10]}',
                                            'target': state.target,
                                            'technology': 'Network'
                                        }
                                        additional_findings.append(finding)
                
                # Ek bulguları state'e ekle
                if additional_findings:
                    state.findings.extend(additional_findings)
                    logger.info(f"✅ Execution results'tan {len(additional_findings)} ek bulgu eklendi")
            
            # Bulguları RAG ile zenginleştir - CVE'leri ekle
            enhanced_findings = []
            for finding in state.findings:
                # RAG ile bulguyu zenginleştir - CVE'leri dahil et
                enhanced_finding = await self._rag_enhance_finding(finding)
                enhanced_findings.append(enhanced_finding)
            
            # State'e enhanced findings'leri geri ekle
            state.findings = enhanced_findings
            
            # RAG'a tarama sonuçlarını kaydet - CVE'leri dahil et
            await self._rag_store_scan_results(state.target, enhanced_findings, execution_results)
            
            # Dinamik rapor metnini oluştur
            report_content = self._prepare_professional_report_text(state)
            
            # Risk skorunu hesapla
            risk_score = self._calculate_risk_score(state.findings)
            
            # Dinamik executive summary
            executive_summary = {
                "risk_level": final_analysis.get("risk_level", "unknown"),
                "risk_score": risk_score,
                "scope": state.target,
                "duration": "45 minutes",
                "vulnerabilities_found": len(state.findings),
                "critical_findings": len([v for v in state.findings if v.get('severity') == 'critical']),
                "high_findings": len([v for v in state.findings if v.get('severity') == 'high']),
                "test_effectiveness": final_analysis.get("test_effectiveness", "good"),
                "compliance_gaps": len([k for k, v in final_analysis.get("compliance_status", {}).items() if v != "compliant"])
            }
            
            # Frontend için structured_data formatında döndür
            structured_data = self.get_structured_report_data(state)
            
            # JSON formatında döndür - frontend uyumlu
            return {
                "report_type": "professional_dynamic",
                "target": state.target,
                "risk_level": final_analysis.get("risk_level", "unknown"),
                "risk_score": risk_score,
                "vulnerabilities_count": len(state.findings),
                "recommendations_count": len(final_analysis.get("recommendations", [])),
                "executive_summary": executive_summary,
                "technical_findings": state.findings,
                "compliance_status": final_analysis.get("compliance_status", {}),
                "recommendations": final_analysis.get("recommendations", []),
                "attack_surface_analysis": final_analysis.get("attack_surface_analysis", {}),
                "test_coverage": final_analysis.get("coverage_analysis", {}),
                "report_content": report_content,
                "structured_data": structured_data,  # Frontend için gerekli
                "dynamic_insights": {
                    "primary_threat_vector": self._identify_primary_threat_vector(state.findings),
                    "immediate_actions_required": len([v for v in state.findings if v.get('severity') in ['critical', 'high']]),
                    "strategic_recommendations": self._extract_strategic_recommendations(state.findings)
                }
            }
            
        except Exception as e:
            logger.error(f"Comprehensive report generation failed: {e}")
            return {
                "report_type": "fallback",
                "error": str(e),
                "analysis": final_analysis
            }
    
    def _identify_primary_threat_vector(self, vulnerabilities: List[Dict[str, Any]]) -> str:
        """Ana tehdit vektörünü belirler"""
        if not vulnerabilities:
            return "No significant threats identified"
        
        categories = {}
        for vuln in vulnerabilities:
            category = self._get_owasp_reference(vuln)
            if category != "İlgili Kategori Bulunamadı":
                categories[category] = categories.get(category, 0) + 1
        
        if categories:
            primary = max(categories, key=categories.get)
            return primary.split(' - ')[-1] if ' - ' in primary else primary
        
        return "General security misconfigurations"
    
    def _extract_strategic_recommendations(self, vulnerabilities: List[Dict[str, Any]]) -> List[str]:
        """Stratejik önerileri çıkarır"""
        recommendations = []
        categories = set()
        
        for vuln in vulnerabilities:
            category = self._get_owasp_reference(vuln)
            if category != "İlgili Kategori Bulunamadı":
                categories.add(category)
        
        if "A05:2021 - Security Misconfiguration" in categories:
            recommendations.append("Implement comprehensive configuration management program")
        
        if "A03:2021 - Injection" in categories:
            recommendations.append("Establish secure coding practices and SAST integration")
        
        if "A06:2021 - Vulnerable and Outdated Components" in categories:
            recommendations.append("Create software asset and patch management program")
        
        if "A01:2021 - Broken Access Control" in categories:
            recommendations.append("Strengthen access control mechanisms and RBAC implementation")
        
        return recommendations

    # ==========================================================================
    # RAG ENTEGRASYONU - EK METODLAR
    # ==========================================================================

    async def _rag_ile_zenginlestir_bulgular(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """RAG ile bulguları zenginleştirir - Legacy metod"""
        if not self.rag_client:
            return findings
        
        enhanced_findings = []
        for finding in findings:
            enhanced_finding = await self._rag_enhance_finding(finding)
            enhanced_findings.append(enhanced_finding)
        
        logger.info("RAG zenginleştirmesi tamamlandı.")
        return enhanced_findings

    async def search_rag_for_cve(self, vulnerability_type: str, technology: str = None) -> Dict[str, Any]:
        """Public metod - RAG'dan CVE bilgilerini ara"""
        return await self._rag_search_cve_info(vulnerability_type, technology)

    async def generate_ai_enhanced_report(self, state: AgentState, scan_results: Dict[str, Any], cve_results: List[Dict[str, Any]]) -> str:
        """
        AI ile geliştirilmiş rapor oluşturur - LLM entegrasyonu ile
        """
        try:
            logger.info("🤖 AI ile geliştirilmiş rapor oluşturuluyor...")
            
            # Bulguları hazırla
            findings_text = ""
            for i, finding in enumerate(state.findings, 1):
                findings_text += f"""
{i}. {finding.get('title', 'Bilinmeyen Bulgu')}
   Severity: {finding.get('severity', 'Unknown')}
   Açıklama: {finding.get('description', 'Açıklama yok')}
   Kanıt: {finding.get('evidence', 'Kanıt yok')}
   Hedef: {finding.get('target', 'N/A')}
   Teknoloji: {finding.get('technology', 'N/A')}
"""

            # CVE bilgilerini hazırla
            cve_text = ""
            for i, cve in enumerate(cve_results[:5], 1):  # Top 5 CVE
                if isinstance(cve, dict):
                    cve_text += f"""
{i}. {cve.get('cve_id', 'N/A')}
   Severity: {cve.get('severity', 'N/A')}
   CVSS: {cve.get('cvss_score', 'N/A')}
   Açıklama: {cve.get('description', 'N/A')[:200]}...
"""

            # Tool çıktılarını hazırla
            tool_outputs_text = ""
            if hasattr(state, 'discovered_information'):
                for key, value in state.discovered_information.items():
                    if key.startswith("tool_"):
                        tool_name = key[5:]
                        tool_outputs_text += f"\n{tool_name}: {str(value)[:300]}...\n"

            # AI prompt oluştur
            ai_prompt = f"""
Sen profesyonel bir siber güvenlik uzmanısın. Aşağıdaki penetrasyon testi sonuçlarına dayanarak kapsamlı bir güvenlik raporu oluştur.

HEDEF SİSTEM: {state.target}
TEST TARİHİ: {state.start_time.strftime('%d.%m.%Y %H:%M') if state.start_time else 'N/A'}

TESPİT EDİLEN ZAFİYETLER:
{findings_text}

CVE REFERANSLARI:
{cve_text}

TOOL ÇIKTILARI:
{tool_outputs_text}

Lütfen aşağıdaki formatda profesyonel bir rapor oluştur:

# PENETRASYON TESTİ RAPORU

## 1. YÖNETİCİ ÖZETİ
- Genel güvenlik durumu değerlendirmesi
- Risk seviyesi ve kritik bulgular
- Acil aksiyon gerektiren konular

## 2. METODOLOJİ VE KAPSAM
- Kullanılan test metodolojisi
- Test kapsamı ve sınırları
- Kullanılan araçlar

## 3. DETAYLI BULGULAR
- Her zafiyet için detaylı açıklama
- Teknik kanıtlar ve proof-of-concept
- İş etkisi analizi

## 4. CVE ANALİZİ
- İlişkili CVE'lerin detaylı analizi
- CVSS skorları ve severity değerlendirmesi

## 5. ÖNERİLER VE ÇÖZÜMLER
- Acil aksiyonlar (0-48 saat)
- Kısa vadeli çözümler (1-7 gün)
- Uzun vadeli stratejik öneriler

## 6. SONUÇ
- Genel değerlendirme
- Risk matrisi
- Compliance durumu

Raporu Türkçe olarak yaz ve profesyonel penetrasyon testi standartlarına uygun hazırla.
"""

            # Eğer LLM generator varsa kullan
            if self.llm_generator:
                try:
                    ai_report = await self.llm_generator.generate_report(ai_prompt)
                    logger.info("✅ AI raporu başarıyla oluşturuldu")
                    return ai_report
                except Exception as e:
                    logger.error(f"❌ LLM rapor oluşturma hatası: {e}")
            
            # Fallback: Template-based rapor
            logger.info("⚠️ LLM kullanılamıyor, template-based rapor oluşturuluyor")
            return self._generate_fallback_ai_report(state, scan_results, cve_results)
            
        except Exception as e:
            logger.error(f"AI rapor oluşturma hatası: {e}")
            return self._generate_fallback_ai_report(state, scan_results, cve_results)

    def generate_llm_enhanced_report(self, findings: List[Dict[str, Any]], target: str, cve_results: List[Dict[str, Any]], tool_outputs: Dict[str, Any], scan_results: Dict[str, Any]) -> str:
        """
        LLM ile zenginleştirilmiş rapor oluştur - TÜM TOOL ÇIKTILARI İLE.
        Web API'den çağrılır.
        """
        try:
            logger.info("🤖 LLM ile gelişmiş markdown raporu oluşturuluyor...")
            
            # Tool çıktılarını metne çevir - DETAYLI
            tool_outputs_text = ""
            if tool_outputs:
                tool_outputs_text = "## TOOL ÇIKTILARI:\n\n"
                for tool_name, tool_data in tool_outputs.items():
                    tool_outputs_text += f"\n### {tool_name}:\n"
                    if isinstance(tool_data, dict):
                        if tool_data.get('success'):
                            data = tool_data.get('data', {})
                            # AI Summary varsa ekle
                            if tool_data.get('ai_summary'):
                                tool_outputs_text += f"**AI Özeti:** {tool_data['ai_summary']}\n\n"
                            
                            # Data'yı özetleyerek ekle
                            if isinstance(data, dict):
                                tool_outputs_text += f"**Veri Noktaları:** {len(data)} key\n"
                                tool_outputs_text += f"**Anahtarlar:** {', '.join(list(data.keys())[:10])}\n"
                                
                                # Önemli alanları detaylı göster
                                important_keys = ['vulnerabilities', 'findings', 'technologies', 'open_ports', 
                                                'subdomains', 'directories', 'endpoints', 'forms', 'parameters']
                                for key in important_keys:
                                    if key in data and data[key]:
                                        value = data[key]
                                        if isinstance(value, list):
                                            tool_outputs_text += f"**{key}:** {len(value)} items\n"
                                            # İlk 5 itemi göster
                                            for item in value[:5]:
                                                if isinstance(item, dict):
                                                    item_str = ", ".join([f"{k}: {v}" for k, v in list(item.items())[:3]])
                                                    tool_outputs_text += f"  - {item_str}\n"
                                                else:
                                                    tool_outputs_text += f"  - {str(item)[:100]}\n"
                                        else:
                                            tool_outputs_text += f"**{key}:** {str(value)[:200]}\n"
                            tool_outputs_text += "\n"
                        else:
                            error = tool_data.get('error', 'Unknown error')
                            tool_outputs_text += f"**Hata:** {error}\n\n"
                    else:
                        tool_outputs_text += f"{str(tool_data)[:300]}...\n\n"
            else:
                tool_outputs_text = "Tool çıktıları bulunamadı.\n"
            
            # Bulguları metne çevir - ÖNCELİKLE TOOL BULGULARI
            findings_text = ""
            if findings:
                # Tool bulgularını say
                tool_findings_count = len([f for f in findings if 'endpoint' in f.get('title', '').lower() or 
                                          'form' in f.get('title', '').lower() or 
                                          'port' in f.get('title', '').lower() or
                                          'teknoloji' in f.get('title', '').lower() or
                                          'subdomain' in f.get('title', '').lower()])
                
                findings_text = f"## TESPİT EDİLEN BULGULAR ({len(findings)} bulgu, {tool_findings_count} tool bulgusu):\n\n"
                findings_text += "🔴 DİKKAT: Aşağıdaki tool bulgularını raporunda MUTLAKA detaylı şekilde açıkla!\n\n"
                
                for i, finding in enumerate(findings, 1):
                    findings_text += f"{i}. **{finding.get('title', 'Bilinmeyen Bulgu')}**\n"
                    findings_text += f"   - Severity: {finding.get('severity', 'Unknown')}\n"
                    findings_text += f"   - Açıklama: {finding.get('description', 'Açıklama yok')}\n"
                    findings_text += f"   - Kanıt: {finding.get('evidence', 'Kanıt yok')[:200]}...\n"
                    findings_text += f"   - Hedef: {finding.get('target', 'N/A')}\n"
                    findings_text += f"   - CVE: {finding.get('cve_id', 'N/A')}\n"
                    findings_text += f"   - CVSS: {finding.get('cvss_score', 'N/A')}\n\n"
            else:
                findings_text = "❌ HATA: Hiç bulgu tespit edilmedi - bu mümkün değil!\n"
            
            # CVE'leri metne çevir
            cve_text = ""
            if cve_results:
                cve_text = "## CVE REFERANSLARI:\n\n"
                for i, cve in enumerate(cve_results[:10], 1):
                    if isinstance(cve, dict):
                        cve_text += f"{i}. **{cve.get('cve_id', 'N/A')}**\n"
                        cve_text += f"   - Severity: {cve.get('severity', 'N/A')}\n"
                        cve_text += f"   - CVSS: {cve.get('base_score') or cve.get('cvss_score', 'N/A')}\n"
                        cve_text += f"   - Açıklama: {cve.get('description', 'N/A')[:300]}...\n"
                        cve_text += f"   - Yayın Tarihi: {cve.get('published_date', 'N/A')}\n\n"
            else:
                cve_text = "CVE referansı bulunamadı.\n"
            
            # Unified LLM kullanarak rapor oluştur
            from model_wrapper import UnifiedLLM
            model = UnifiedLLM()
            
            prompt = f"""Sen PROFESYONEL bir siber güvenlik uzmanı ve penetrasyon test raporlayıcısısın. 

🔴🔴🔴 KRİTİK ÖNEM: ASLA "kritik bir güvenlik açığına rastlanmamıştır" yazma! 
🔴🔴🔴 Aşağıdaki TOOL ÇIKTILARI ve BULGULAR çok önemlidir ve raporunda MUTLAKA kullanılmalıdır!

**HEDEF SİSTEM:** {target}
**TEST TARİHİ:** {datetime.now().strftime('%d.%m.%Y %H:%M')}

{tool_outputs_text}

{findings_text}

{cve_text}

**GÖREV:**
Yukarıdaki TÜM VERİLERİ (ÖZELLİKLE TOOL ÇIKTILARINI VE BULGULARI) analiz ederek profesyonel bir penetrasyon testi raporu oluştur. 

🎯 KRİTİK TALİMATLAR (MUTLAKA UYGULA):
1. ❌ ASLA "kritik bir güvenlik açığına rastlanmamıştır" yazma! Tool çıktıları ve bulgular VAR!
2. ✅ Tool çıktılarındaki TEKNOLOJİLERİ, PORTLARI, ENDPOİNTLERİ, FORMLARI, SUBDOMAİNLERİ, DİZİNLERİ raporunda DETAYLI AÇIKLA
3. ✅ Eğer 20+ endpoint varsa → YÜKSEK RİSK, saldırı yüzeyi geniş!
4. ✅ Eğer 10+ form varsa → YÜKSEK INJECTİON RİSKİ, SQL Injection/XSS potansiyeli!
5. ✅ Eğer kritik portlar (22, 3389, 21, 23) açıksa → KRİTİK RİSK, uzaktan erişim riski!
6. ✅ Tespit edilen her teknoloji → zafiyet riski, güncelleme kontrolü gerekli!
7. ✅ Bulgular bölümündeki HER bulguyu Yönetici Özetinde ve Risk Değerlendirmesinde kullan
8. ✅ Risk seviyesi: Bulgu sayısına göre LOW/MEDIUM/HIGH/CRITICAL olarak belirle

Rapor şu bölümleri içermeli:

# PENETRASYON TESTİ RAPORU

## 1. YÖNETİCİ ÖZETİ
- Genel güvenlik durumu değerlendirmesi (teknik olmayan dil)
- Risk seviyesi ve skor (0-100 arası)
- En kritik 3 bulgu ve iş etkileri
- Acil aksiyon gerektiren konular

## 2. METODOLOJİ VE KAPSAM
- Kullanılan test metodolojisi (OWASP, PTES, NIST SP 800-115)
- Test kapsamı ve hedef sistem
- Kullanılan araçlar ve teknikler (tool çıktılarından)
- Test sınırlamaları

## 3. DETAYLI TEKNİK BULGULAR
Her bulgu için:
- Bulgu başlığı ve ID
- Severity (CRITICAL/HIGH/MEDIUM/LOW)
- CVSS skoru (varsa)
- Detaylı teknik açıklama
- Kanıt (PoC, screenshot, log)
- Etkilenen sistem/URL
- Teknik risk analizi
- İş etkisi analizi
- OWASP kategorisi

## 4. TOOL ÇIKTILARI VE ANALİZLER (ÇOK ÖNEMLİ!)
🔴 TOOL ÇIKTILARINI MUTLAKA DETAYLI ŞEKİLDE RAPORLA!
Çalıştırılan her tool için:
- Tool adı ve amacı
- Tespit edilen veri (teknolojiler, portlar, endpointler vb.) - HERBİRİNİ DETAYLI YAZ
- Kritik bulgular - NEDEN KRİTİK OLDUĞUNU AÇIKLA
- Güvenlik değerlendirmesi - RİSK ANALİZİ YAP
- Endpoint sayısı fazla ise (20+), bu YÜKSEKRİSK olarak değerlendir
- Form sayısı fazla ise (10+), bu INJECTİON RİSKİ olarak değerlendir
- Açık portlar kritik ise (22, 3389, 21, 23), bu KRİTİK RİSK olarak değerlendir

## 5. CVE ANALİZİ VE ZAFİYET MAPLEMESİ
- İlişkili CVE'lerin detaylı analizi
- CVSS skorları ve severity dağılımı
- Exploit durumu ve güncellik
- Zafiyet zincirleri ve saldırı senaryoları

## 6. RİSK MATRİSİ VE PRİORİTİZASYON
- Risk skoru ve dağılımı (kritik, yüksek, orta, düşük)
- Bulguların önceliklendirmesi
- Saldırı senaryoları ve zincir analizi

## 7. ÖNERİLER VE ÇÖZÜMLER
### 7.1 Acil Aksiyonlar (0-48 Saat)
- Kritik bulguların giderilmesi
- Detaylı çözüm adımları

### 7.2 Kısa Vadeli (1-7 Gün)
- Yüksek riskli bulguların giderilmesi
- Güvenlik sıkılaştırma adımları

### 7.3 Orta ve Uzun Vadeli Stratejik Öneriler
- Sistem mimarisine yönelik öneriler
- Güvenlik süreçleri ve politikalar
- Compliance gereksinimleri

## 8. SONUÇ VE GENEL DEĞERLENDİRME
- Genel güvenlik postürü
- Güçlü ve zayıf yönler
- Compliance durumu (OWASP, PCI-DSS, ISO 27001)
- İleriye dönük öneriler

**KRİTİK ÖNEMDE:**
- Rapor Türkçe olmalı
- Teknik ve detaylı olmalı
- 🔴 TOOL ÇIKTILARINI MUTLAKA KULLAN! Endpoint sayısı, form sayısı, port sayısı, teknoloji sayısı gibi bilgileri raporda açıkça belirt
- 🔴 Tool çıktılarındaki risk göstergelerini (fazla endpoint, fazla form, kritik portlar) risk değerlendirmesine dahil et
- 🔴 Eğer tool çıktılarında 20+ endpoint, 10+ form, kritik portlar varsa, risk skorunu yükselt ve raporunda belirt
- Her bulgunun kanıt ve çözümü olmalı
- Markdown formatında yaz
- Profesyonel penetrasyon testi standardlarına uygun hazırla
- En az 3000 kelime olmalı
- Risk skorunu tool çıktılarına göre hesapla

Şimdi profesyonel raporu oluştur ve TOOL ÇIKTILARINI MUTLAKA DİKKATE AL:"""

            # LLM'den rapor al
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Event loop zaten çalışıyor - thread pool kullan
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        response = pool.submit(
                            asyncio.run,
                            model.generate_content_async(prompt)
                        ).result(timeout=120)  # 2 dakika timeout
                else:
                    # Event loop çalışmıyor - direkt çalıştır
                    response = loop.run_until_complete(
                        model.generate_content_async(prompt)
                    )
                
                # Response'u string'e çevir
                if isinstance(response, str):
                    report = response
                elif hasattr(response, 'text'):
                    report = response.text
                elif hasattr(response, 'get'):
                    report = response.get('text', str(response))
                else:
                    report = str(response)
                
                logger.info(f"✅ LLM raporu oluşturuldu: {len(report)} karakter")
                return report
                
            except Exception as e:
                logger.error(f"LLM rapor oluşturma hatası: {e}")
                # Fallback: template-based rapor
                return self._generate_template_llm_report(findings, target, cve_results, tool_outputs)
                
        except Exception as e:
            logger.error(f"LLM enhanced report hatası: {e}")
            return self._generate_template_llm_report(findings, target, cve_results, tool_outputs)
    
    def _generate_template_llm_report(self, findings: List[Dict[str, Any]], target: str, cve_results: List[Dict[str, Any]], tool_outputs: Dict[str, Any]) -> str:
        """Template-based fallback rapor"""
        report_parts = []
        
        # Başlık
        report_parts.append("# PENETRASYON TESTİ RAPORU")
        report_parts.append("")
        report_parts.append(f"**Hedef Sistem:** {target}")
        report_parts.append(f"**Test Tarihi:** {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        report_parts.append(f"**Rapor ID:** PENTAGENT-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        report_parts.append("")
        report_parts.append("---")
        report_parts.append("")
        
        # Yönetici Özeti
        report_parts.append("## 1. YÖNETİCİ ÖZETİ")
        report_parts.append("")
        findings_count = len(findings)
        critical_count = len([f for f in findings if f.get('severity') == 'critical'])
        high_count = len([f for f in findings if f.get('severity') == 'high'])
        
        if findings_count == 0:
            report_parts.append("Bu güvenlik değerlendirmesi sonucunda kritik bir güvenlik açığına rastlanmamıştır.")
        else:
            report_parts.append(f"Bu penetrasyon testi sonucunda **{findings_count}** adet güvenlik bulgusu tespit edilmiştir.")
            if critical_count > 0:
                report_parts.append(f"- **{critical_count}** kritik seviyede bulgu")
            if high_count > 0:
                report_parts.append(f"- **{high_count}** yüksek seviyede bulgu")
        
        report_parts.append("")
        
        # Detaylı Bulgular
        if findings:
            report_parts.append("## 3. DETAYLI BULGULAR")
            report_parts.append("")
            
            for i, finding in enumerate(findings, 1):
                report_parts.append(f"### {i}. {finding.get('title', 'Bilinmeyen Bulgu')}")
                report_parts.append(f"**Severity:** {finding.get('severity', 'Unknown').upper()}")
                report_parts.append(f"**CVSS:** {finding.get('cvss_score', 'N/A')}")
                report_parts.append(f"**Açıklama:** {finding.get('description', 'Açıklama yok')}")
                report_parts.append(f"**Kanıt:**")
                report_parts.append(f"```\n{finding.get('evidence', 'Kanıt yok')}\n```")
                report_parts.append("")
        
        # Tool Çıktıları
        if tool_outputs:
            report_parts.append("## 4. TOOL ÇIKTILARI")
            report_parts.append("")
            
            for tool_name, tool_data in list(tool_outputs.items())[:10]:  # İlk 10 tool
                report_parts.append(f"### {tool_name}")
                if isinstance(tool_data, dict):
                    if tool_data.get('ai_summary'):
                        report_parts.append(f"**Özet:** {tool_data['ai_summary']}")
                    report_parts.append("")
        
        # CVE Analizi
        if cve_results:
            report_parts.append("## 5. CVE ANALİZİ")
            report_parts.append("")
            
            for i, cve in enumerate(cve_results[:10], 1):
                if isinstance(cve, dict):
                    report_parts.append(f"### {i}. {cve.get('cve_id', 'N/A')}")
                    report_parts.append(f"**Severity:** {cve.get('severity', 'N/A')}")
                    report_parts.append(f"**CVSS:** {cve.get('base_score') or cve.get('cvss_score', 'N/A')}")
                    report_parts.append(f"**Açıklama:** {cve.get('description', 'N/A')[:300]}...")
                    report_parts.append("")
        
        # Öneriler
        report_parts.append("## 7. ÖNERİLER VE ÇÖZÜMLER")
        report_parts.append("")
        
        if critical_count > 0:
            report_parts.append("### Acil Aksiyonlar (0-48 Saat)")
            report_parts.append("- Kritik seviyedeki bulguların acil olarak giderilmesi")
            report_parts.append("")
        
        return "\n".join(report_parts)
    
    def _generate_fallback_ai_report(self, state: AgentState, scan_results: Dict[str, Any], cve_results: List[Dict[str, Any]]) -> str:
        """Fallback AI raporu - template-based"""
        try:
            report_parts = []
            
            # Başlık
            report_parts.append("# PENETRASYON TESTİ RAPORU")
            report_parts.append("")
            report_parts.append(f"**Hedef Sistem:** {state.target}")
            report_parts.append(f"**Test Tarihi:** {state.start_time.strftime('%d.%m.%Y %H:%M') if state.start_time else 'N/A'}")
            report_parts.append(f"**Rapor ID:** PENTAGENT-{datetime.now().strftime('%Y%m%d%H%M%S')}")
            report_parts.append("")
            report_parts.append("---")
            report_parts.append("")
            
            # Yönetici Özeti
            report_parts.append("## 1. YÖNETİCİ ÖZETİ")
            report_parts.append("")
            findings_count = len(state.findings)
            critical_count = len([f for f in state.findings if f.get('severity') == 'critical'])
            high_count = len([f for f in state.findings if f.get('severity') == 'high'])
            
            if findings_count == 0:
                report_parts.append("Bu güvenlik değerlendirmesi sonucunda kritik bir güvenlik açığına rastlanmamıştır. Sistemin genel güvenlik duruşu temel seviyede yeterli görünmektedir.")
            else:
                report_parts.append(f"Bu penetrasyon testi sonucunda **{findings_count}** adet güvenlik bulgusu tespit edilmiştir.")
                if critical_count > 0:
                    report_parts.append(f"- **{critical_count}** kritik seviyede bulgu")
                if high_count > 0:
                    report_parts.append(f"- **{high_count}** yüksek seviyede bulgu")
                
                report_parts.append("")
                report_parts.append("**Risk Seviyesi:** " + ("YÜKSEK" if critical_count > 0 else "ORTA" if high_count > 0 else "DÜŞÜK"))
            
            report_parts.append("")
            
            # Metodoloji
            report_parts.append("## 2. METODOLOJİ VE KAPSAM")
            report_parts.append("")
            report_parts.append("Bu güvenlik değerlendirmesi, OWASP Testing Guide, PTES ve NIST SP 800-115 gibi endüstri standartlarına uygun, otomatize edilmiş bir metodoloji ile gerçekleştirilmiştir.")
            report_parts.append("")
            report_parts.append(f"**Kapsam:** {state.target}")
            report_parts.append("**Kapsam Dışı:** Sosyal mühendislik, fiziksel güvenlik ve DoS/DDoS saldırıları")
            report_parts.append("")
            
            # Detaylı Bulgular
            if state.findings:
                report_parts.append("## 3. DETAYLI BULGULAR")
                report_parts.append("")
                
                for i, finding in enumerate(state.findings, 1):
                    report_parts.append(f"### {i}. {finding.get('title', 'Bilinmeyen Bulgu')}")
                    report_parts.append(f"**Severity:** {finding.get('severity', 'Unknown').upper()}")
                    report_parts.append(f"**Açıklama:** {finding.get('description', 'Açıklama yok')}")
                    report_parts.append(f"**Kanıt:** {finding.get('evidence', 'Kanıt yok')}")
                    report_parts.append(f"**Hedef:** {finding.get('target', 'N/A')}")
                    report_parts.append(f"**Teknoloji:** {finding.get('technology', 'N/A')}")
                    report_parts.append("")
            
            # CVE Analizi
            if cve_results:
                report_parts.append("## 4. CVE ANALİZİ")
                report_parts.append("")
                
                for i, cve in enumerate(cve_results[:10], 1):  # Top 10 CVE
                    if isinstance(cve, dict):
                        report_parts.append(f"### {i}. {cve.get('cve_id', 'N/A')}")
                        report_parts.append(f"**Severity:** {cve.get('severity', 'N/A')}")
                        report_parts.append(f"**CVSS:** {cve.get('cvss_score', 'N/A')}")
                        report_parts.append(f"**Açıklama:** {cve.get('description', 'N/A')[:200]}...")
                        report_parts.append("")
            
            # Öneriler
            report_parts.append("## 5. ÖNERİLER VE ÇÖZÜMLER")
            report_parts.append("")
            
            if critical_count > 0:
                report_parts.append("### Acil Aksiyonlar (0-48 Saat)")
                report_parts.append("- Kritik seviyedeki bulguların acil olarak giderilmesi")
                report_parts.append("- Sistemin izole edilmesi veya erişimin kısıtlanması")
                report_parts.append("- Güvenlik ekibinin 7/24 hazır bulunması")
                report_parts.append("")
            
            if high_count > 0:
                report_parts.append("### Kısa Vadeli Çözümler (1-7 Gün)")
                report_parts.append("- Yüksek seviyedeki bulguların öncelikli olarak giderilmesi")
                report_parts.append("- Güvenlik duvarı kurallarının gözden geçirilmesi")
                report_parts.append("- Sistem güncellemelerinin uygulanması")
                report_parts.append("")
            
            report_parts.append("### Uzun Vadeli Stratejik Öneriler")
            report_parts.append("- Düzenli güvenlik testlerinin planlanması")
            report_parts.append("- Güvenlik farkındalığı eğitimlerinin düzenlenmesi")
            report_parts.append("- Incident response planının oluşturulması")
            report_parts.append("")
            
            # Sonuç
            report_parts.append("## 6. SONUÇ")
            report_parts.append("")
            if findings_count == 0:
                report_parts.append("Bu güvenlik değerlendirmesi sonucunda kritik bir güvenlik açığına rastlanmamıştır. Sistemin genel güvenlik duruşu temel seviyede yeterli görünmektedir.")
            else:
                report_parts.append(f"Bu penetrasyon testi sonucunda {findings_count} adet güvenlik bulgusu tespit edilmiştir. Bu bulguların öncelikli olarak giderilmesi ve sistemin güvenlik duruşunun iyileştirilmesi önerilmektedir.")
            
            report_parts.append("")
            report_parts.append("---")
            report_parts.append("")
            report_parts.append("*Bu rapor Pentagent AI Security Platform tarafından otomatik olarak oluşturulmuştur.*")
            
            return "\n".join(report_parts)
            
        except Exception as e:
            logger.error(f"Fallback AI rapor oluşturma hatası: {e}")
            return "Rapor oluşturulamadı"