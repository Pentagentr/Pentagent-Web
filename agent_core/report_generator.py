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
        """Bulgulara dayalı olarak 100 üzerinden bir risk skoru hesaplar."""
        if not findings: return 0
        severity_weights = {"critical": 25, "high": 15, "medium": 5, "low": 1}
        score = sum(severity_weights.get(f.get("severity", "low"), 1) for f in findings)
        return min(score, 100)

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
        """Genel risk seviyesini hesaplar"""
        critical = findings_summary.get('by_severity', {}).get('critical', 0)
        high = findings_summary.get('by_severity', {}).get('high', 0)
        
        if critical > 0:
            return "CRITICAL"
        elif high > 2:
            return "HIGH"
        elif high > 0:
            return "MEDIUM"
        else:
            return "LOW"

    # ==========================================================================
    # RAG ENTEGRASYONU - CVE/CVSS VE TARAMA SONUÇLARI
    # ==========================================================================

    async def _rag_search_cve_info(self, vulnerability_type: str, technology: str = None) -> Dict[str, Any]:
        """RAG ile CVE bilgilerini ara ve CVSS skorlarını al"""
        try:
            if not self.rag_client:
                return {"error": "RAG client not available"}
            
            # RAG sorgusu oluştur
            query = f"CVE vulnerabilities for {vulnerability_type}"
            if technology:
                query += f" in {technology}"
            
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
                return {"error": "No CVE information found in RAG database"}
                
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
        """RAG'a tarama sonuçlarını kaydet"""
        try:
            if not self.rag_client:
                logger.warning("RAG client not available - cannot store scan results")
                return
            
            # Tarama sonuçlarını RAG formatına çevir
            scan_data = {
                "target": target,
                "scan_date": datetime.now().isoformat(),
                "findings": findings,
                "execution_summary": {
                    "total_tools_executed": len(execution_results),
                    "successful_tools": len([r for r in execution_results.values() if r.get("success", False)]),
                    "risk_level": self._calculate_overall_risk_level({"by_severity": self._count_findings_by_severity(findings)})
                },
                "metadata": {
                    "scan_type": "comprehensive",
                    "methodology": "OWASP Top 10, PTES, NIST SP 800-115"
                }
            }
            
            # RAG'a kaydet
            await self.rag_client.store_document(scan_data)
            logger.info(f"Scan results stored in RAG for target: {target}")
            
        except Exception as e:
            logger.error(f"Failed to store scan results in RAG: {e}")

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
        Tüm 6 bölüm dahil: Executive Summary, Methodology, Risk Matrix, Findings Summary, Detailed Findings, Recommendations
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
        
        # 3. RISK MATRIX
        risk_matrix = {
            "aciklama": "Risk seviyeleri CVSS v3.1 ve OWASP Risk Rating Metodolojisi'ne göre belirlenmiştir",
            "seviyeler": {
                "KRITIK": {"aralik": "9.0-10.0", "aciklama": "Acil müdahale gerektirir. Sistem tamamen ele geçirilebilir."},
                "YÜKSEK": {"aralik": "7.0-8.9", "aciklama": "Öncelikli olarak giderilmelidir. Veri kaybı/ifşası riski yüksek."},
                "ORTA": {"aralik": "4.0-6.9", "aciklama": "Makul sürede giderilmelidir. Sınırlı etki potansiyeli."},
                "DÜŞÜK": {"aralik": "0.1-3.9", "aciklama": "Planlı olarak giderilmelidir. Minimal etki."}
            }
        }
        
        # 4. FINDINGS SUMMARY
        findings_summary_data = {
            "toplam": len(state.findings),
            "ciddiyete_gore": findings_summary.get("by_severity", {}),
            "owasp_kategorileri": self._categorize_findings_by_owasp(state.findings)
        }
        
        # 5. DETAILED FINDINGS
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
        
        # 6. RECOMMENDATIONS & CONCLUSION
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
        
        return {
            "executive_summary": executive_summary,
            "methodology": methodology,
            "risk_matrix": risk_matrix,
            "findings_summary": findings_summary_data,
            "detailed_findings": detailed_findings,
            "recommendations": recommendations,
            "appendix": appendix
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
        """Verilen metin içeriğinden profesyonel bir PDF oluşturur - temiz format."""
        doc = SimpleDocTemplate(pdf_path, pagesize=A4, topMargin=50, bottomMargin=50, leftMargin=50, rightMargin=50)
        styles = getSampleStyleSheet()
        
        # Özel stiller oluştur
        heading1_style = ParagraphStyle('CustomHeading1', parent=styles['Heading1'], fontSize=16, spaceAfter=20, spaceBefore=20, textColor=colors.HexColor('#2d3748'))
        heading2_style = ParagraphStyle('CustomHeading2', parent=styles['Heading2'], fontSize=14, spaceAfter=15, spaceBefore=15, textColor=colors.HexColor('#4a5568'))
        normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=6)
        bullet_style = ParagraphStyle('CustomBullet', parent=styles['Bullet'], fontSize=10, leading=14, leftIndent=20, spaceAfter=4)
        code_style = ParagraphStyle('CustomCode', parent=styles['Normal'], fontName='Courier', fontSize=8, leading=12, leftIndent=20, backgroundColor=colors.HexColor('#f7fafc'))
        
        # Metni temizle
        text_content = self._clean_text_for_pdf(text_content)
        
        story = []
        prev_was_heading = False
        
        for line in text_content.split('\n'):
            # Boş satırlar için boşluk ekle
            if not line.strip():
                if not prev_was_heading:
                    story.append(Spacer(1, 10))
                continue
            
            line = line.strip()
            
            # Başlıklar (=== veya ---)
            if line.startswith('===') or line.startswith('---') or (len(line) > 10 and all(c == '=' or c == '-' for c in line)):
                story.append(Spacer(1, 15))
                prev_was_heading = True
                continue
            
            # Bölüm başlıkları (1., 2., 3. gibi)
            if len(line) < 100 and (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.')) or line.isupper()):
                story.append(Spacer(1, 20))
                try:
                    story.append(Paragraph(f"<b>{line}</b>", heading1_style))
                    prev_was_heading = True
                except:
                    story.append(Spacer(1, 10))
                continue
            
            # Alt başlıklar ([...] formatında)
            if line.startswith('[') and line.endswith(']'):
                story.append(Spacer(1, 12))
                try:
                    story.append(Paragraph(f"<b>{line[1:-1]}</b>", heading2_style))
                    prev_was_heading = True
                except:
                    story.append(Spacer(1, 6))
                continue
            
            # Liste öğeleri (* veya - veya •)
            if line.startswith(('*', '-', '•')) or (len(line) > 2 and line[0].isspace() and line.strip().startswith(('*', '-', '•'))):
                try:
                    story.append(Paragraph(line, bullet_style))
                    prev_was_heading = False
                except:
                    story.append(Spacer(1, 4))
                continue
            
            # Kod/URL satırları
            if "HTTP/" in line or "curl" in line or "://" in line or line.startswith("  "):
                try:
                    story.append(Paragraph(line.replace(" ", "&nbsp;"), code_style))
                    prev_was_heading = False
                except:
                    story.append(Spacer(1, 4))
                continue
            
            # Normal paragraflar
            try:
                story.append(Paragraph(line, normal_style))
                prev_was_heading = False
            except Exception as e:
                # Eğer hala sorun varsa, basit spacer ekle
                story.append(Spacer(1, 6))
        
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

    # Dynamic orchestrator ile entegrasyon için yeni metod - RAG ENTEGRASYONU
    async def generate_comprehensive_report(self, state: AgentState, final_analysis: Dict[str, Any], execution_results: Dict[str, Any]) -> Dict[str, Any]:
        """Dynamic orchestrator için kapsamlı ve dinamik rapor oluşturur - RAG entegrasyonu ile"""
        try:
            # Final analysis'den findings oluştur
            vulnerabilities = final_analysis.get("security_vulnerabilities", [])
            
            # AgentState'e findings ekle
            if not hasattr(state, 'findings'):
                state.findings = []
            
            # Vulnerabilities'i findings formatına çevir - RAG ile zenginleştirilmiş
            enhanced_findings = []
            for vuln in vulnerabilities:
                finding = {
                    'title': vuln.get('type', 'Unknown Vulnerability'),
                    'severity': vuln.get('severity', 'low'),
                    'description': vuln.get('description', 'No description available'),
                    'cvss_score': vuln.get('cvss_score', 'N/A'),
                    'evidence': vuln.get('description', 'No evidence available'),
                    'recommendation_summary': vuln.get('recommendation', 'No recommendation available'),
                    'business_impact': vuln.get('business_impact', 'Business impact not assessed'),
                    'exploitability': vuln.get('exploitability', 'Unknown'),
                    'cve_id': vuln.get('cve_id', None),
                    'target': state.target,
                    'technology': vuln.get('technology', None)
                }
                
                # RAG ile bulguyu zenginleştir
                enhanced_finding = await self._rag_enhance_finding(finding)
                enhanced_findings.append(enhanced_finding)
                state.findings.append(enhanced_finding)
            
            # RAG'a tarama sonuçlarını kaydet
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
                "vulnerabilities_found": len(vulnerabilities),
                "critical_findings": len([v for v in vulnerabilities if v.get('severity') == 'critical']),
                "high_findings": len([v for v in vulnerabilities if v.get('severity') == 'high']),
                "test_effectiveness": final_analysis.get("test_effectiveness", "good"),
                "compliance_gaps": len([k for k, v in final_analysis.get("compliance_status", {}).items() if v != "compliant"])
            }
            
            # JSON formatında döndür - uzman seviyesi
            return {
                "report_type": "professional_dynamic",
                "target": state.target,
                "risk_level": final_analysis.get("risk_level", "unknown"),
                "risk_score": risk_score,
                "vulnerabilities_count": len(vulnerabilities),
                "recommendations_count": len(final_analysis.get("recommendations", [])),
                "executive_summary": executive_summary,
                "technical_findings": vulnerabilities,
                "compliance_status": final_analysis.get("compliance_status", {}),
                "recommendations": final_analysis.get("recommendations", []),
                "attack_surface_analysis": final_analysis.get("attack_surface_analysis", {}),
                "test_coverage": final_analysis.get("coverage_analysis", {}),
                "report_content": report_content,
                "dynamic_insights": {
                    "primary_threat_vector": self._identify_primary_threat_vector(vulnerabilities),
                    "immediate_actions_required": len([v for v in vulnerabilities if v.get('severity') in ['critical', 'high']]),
                    "strategic_recommendations": self._extract_strategic_recommendations(vulnerabilities)
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

    async def search_rag_for_similar_scans(self, target: str, scan_type: str) -> Dict[str, Any]:
        """Public metod - RAG'dan benzer tarama sonuçlarını ara"""
        return await self._rag_search_scan_results(target, scan_type)

    async def store_scan_in_rag(self, target: str, findings: List[Dict[str, Any]], execution_results: Dict[str, Any]):
        """Public metod - Tarama sonuçlarını RAG'a kaydet"""
        await self._rag_store_scan_results(target, findings, execution_results)