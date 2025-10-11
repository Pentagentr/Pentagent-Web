# agent_core/analyzer.py

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from datetime import datetime
from agent_core.state import AgentState

logger = logging.getLogger(__name__)

class Analyzer:
    """Araç çıktısını yorumlayan ve insan tarafından anlaşılır hale getiren modül."""
    
    def __init__(self, model: genai.GenerativeModel, status_callback):
        self.model = model
        self.status_callback = status_callback
        
        # Bulgu şablonu - tutarlılık için
        self.finding_schema = {
            "title": str,
            "severity": str,  # Kritik, Yüksek, Orta, Düşük, Bilgilendirme
            "cve_id": Optional[str],
            "cvss_score": Optional[float],
            "description": str,
            "evidence": str,
            "affected_component": str,
            "recommendation_summary": str
        }
        
    async def _call_gemini_json(self, prompt: str) -> Dict[str, Any]:
        """Gemini'yi JSON formatında yanıt vermesi için çağırır."""
        try:
            response = await self.model.generate_content_async(prompt)
            response_text = response.text.strip()
            
            # JSON parse etmeye çalış
            if response_text.startswith('```json'):
                response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
            elif response_text.startswith('```'):
                response_text = response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
            
            parsed_response = json.loads(response_text)
            return parsed_response
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse hatası: {e}")
            logger.error(f"Ham yanıt: {response_text[:500]}...")
            return {}
        except Exception as e:
            logger.error(f"Gemini API hatası: {e}")
            return {}

    async def analyze_result(self, tool_name: str, tool_result: Dict[str, Any], state: AgentState) -> Optional[Dict[str, Any]]:
        """
        Araç sonucunu analiz eder, bulguyu rapor için yapılandırır ve state'e ekler.
        """
        await self.status_callback(f"🧠 DERİNLEMESİNE ANALİZ BAŞLIYOR: '{tool_name}' aracının çıktısı inceleniyor...", "ai_thinking")
        
        # Sonuç detaylarını göster
        result_summary = tool_result.get('summary', 'Sonuç alındı')
        result_data = tool_result.get('data', {})
        await self.status_callback(f"📊 Ham Sonuç: {result_summary}", "ai_reasoning")
        
        # Tool tipine ve kullanıcı görevine göre dinamik analiz stratejisi
        user_task = state.user_task.lower()
        
        if 'port' in tool_name.lower():
            if "port" in user_task:
                await self.status_callback("💭 Port tarama sonucu analizi: Kullanıcı port taraması istediği için bu sonuçları detaylıca analiz ediyorum. Her açık port için servis tespiti yapacağım.", "ai_reasoning")
            else:
                await self.status_callback("💭 Port tarama sonucu analizi: Açık portları tespit ettim. Her açık port için hangi servislerin çalıştığını ve hangi teknolojilerin kullanıldığını analiz etmeliyim.", "ai_reasoning")
            
            await self.status_callback("🔍 Port analizi stratejisi: Açık port → Servis tespiti → Teknoloji tanımlama → Zafiyet analizi", "ai_reasoning")
            
            # Sonuçlara göre dinamik teknik detaylar
            if result_data and 'open_ports' in str(result_data):
                await self.status_callback("⚙️ Tespit Edilen Portlar:", "ai_reasoning")
                # Gerçek portları analiz et ve dinamik yorum yap
                if '22' in str(result_data):
                    await self.status_callback("   • Port 22 (SSH): Banner analysis, key exchange, cipher suites", "ai_reasoning")
                if '80' in str(result_data) or '443' in str(result_data):
                    await self.status_callback("   • Port 80/443 (HTTP/HTTPS): Web server, SSL/TLS, certificates", "ai_reasoning")
                if '3306' in str(result_data):
                    await self.status_callback("   • Port 3306 (MySQL): Database version, authentication", "ai_reasoning")
                if '5432' in str(result_data):
                    await self.status_callback("   • Port 5432 (PostgreSQL): Database version, configuration", "ai_reasoning")
            else:
                await self.status_callback("⚙️ Teknik Detaylar:", "ai_reasoning")
                await self.status_callback("   • Port 22 (SSH): Banner analysis, key exchange, cipher suites", "ai_reasoning")
                await self.status_callback("   • Port 80/443 (HTTP/HTTPS): Web server, SSL/TLS, certificates", "ai_reasoning")
                await self.status_callback("   • Port 25/587 (SMTP): Mail server, authentication methods", "ai_reasoning")
                await self.status_callback("   • Port 3306 (MySQL): Database version, authentication", "ai_reasoning")
                await self.status_callback("   • Port 5432 (PostgreSQL): Database version, configuration", "ai_reasoning")
                
        elif 'tech' in tool_name.lower():
            if "sql" in user_task or "injection" in user_task:
                await self.status_callback("💭 Teknoloji tespiti analizi: Kullanıcı SQL injection testi istediği için database teknolojilerini özellikle arıyorum. SQL injection noktalarını tespit edeceğim.", "ai_reasoning")
            elif "xss" in user_task:
                await self.status_callback("💭 Teknoloji tespiti analizi: Kullanıcı XSS testi istediği için JavaScript framework'lerini ve input handling teknolojilerini özellikle arıyorum.", "ai_reasoning")
            else:
                await self.status_callback("💭 Teknoloji tespiti analizi: Web teknolojilerini tespit ettim. Bu teknolojilerin versiyonlarını kontrol edip, bilinen zafiyetleri araştırmalıyım.", "ai_reasoning")
            
            await self.status_callback("🔍 Teknoloji analizi stratejisi: Teknoloji → Versiyon kontrolü → CVE araştırması → Zafiyet testleri", "ai_reasoning")
            
            # Sonuçlara göre dinamik teknik detaylar
            if result_data and 'technologies' in str(result_data):
                await self.status_callback("⚙️ Tespit Edilen Teknolojiler:", "ai_reasoning")
                if 'wordpress' in str(result_data).lower():
                    await self.status_callback("   • WordPress: Plugin vulnerabilities, theme security, version-specific CVEs", "ai_reasoning")
                if 'apache' in str(result_data).lower():
                    await self.status_callback("   • Apache: Module vulnerabilities, configuration issues, version-specific CVEs", "ai_reasoning")
                if 'mysql' in str(result_data).lower():
                    await self.status_callback("   • MySQL: Database vulnerabilities, authentication bypass, privilege escalation", "ai_reasoning")
            else:
                await self.status_callback("⚙️ Teknik Detaylar:", "ai_reasoning")
                await self.status_callback("   • Web Server: Apache/Nginx version, modules, configuration", "ai_reasoning")
                await self.status_callback("   • Framework: Laravel/Django/Spring version, known vulnerabilities", "ai_reasoning")
                await self.status_callback("   • CMS: WordPress/Drupal version, plugins, themes", "ai_reasoning")
                await self.status_callback("   • Database: MySQL/PostgreSQL version, configuration", "ai_reasoning")
                await self.status_callback("   • JavaScript: Libraries, frameworks, known CVEs", "ai_reasoning")
                
        elif 'subdomain' in tool_name.lower():
            if "api" in user_task:
                await self.status_callback("💭 Subdomain keşfi analizi: Kullanıcı API testi istediği için API endpoint'leri içeren subdomain'leri özellikle arıyorum.", "ai_reasoning")
            else:
                await self.status_callback("💭 Subdomain keşfi analizi: Yeni subdomain'ler buldum. Her birini ayrı ayrı analiz edip, hangilerinin aktif olduğunu ve hangi servisleri sunduğunu tespit etmeliyim.", "ai_reasoning")
            
            await self.status_callback("🔍 Subdomain analizi stratejisi: Subdomain → Aktiflik kontrolü → Teknoloji tespiti → Güvenlik analizi", "ai_reasoning")
            
            # Sonuçlara göre dinamik teknik detaylar
            if result_data and 'subdomains' in str(result_data):
                await self.status_callback("⚙️ Tespit Edilen Subdomain'ler:", "ai_reasoning")
                if 'admin' in str(result_data).lower():
                    await self.status_callback("   • admin.*: Admin panels, authentication bypass", "ai_reasoning")
                if 'api' in str(result_data).lower():
                    await self.status_callback("   • api.*: API endpoints, authentication, rate limiting", "ai_reasoning")
                if 'mail' in str(result_data).lower():
                    await self.status_callback("   • mail.*: Email servers, authentication methods", "ai_reasoning")
            else:
                await self.status_callback("⚙️ Teknik Detaylar:", "ai_reasoning")
                await self.status_callback("   • admin.*: Admin panels, authentication bypass", "ai_reasoning")
                await self.status_callback("   • api.*: API endpoints, authentication, rate limiting", "ai_reasoning")
                await self.status_callback("   • mail.*: Email servers, authentication methods", "ai_reasoning")
                await self.status_callback("   • dev.*: Development environments, debug modes", "ai_reasoning")
                await self.status_callback("   • staging.*: Staging environments, test data", "ai_reasoning")
                
        elif 'whois' in tool_name.lower():
            await self.status_callback("💭 WHOIS analizi: Domain bilgilerini topladım. Bu bilgilerden domain sahibi, kayıt tarihi ve DNS sunucuları hakkında bilgi edindim.", "ai_reasoning")
            await self.status_callback("🔍 WHOIS analizi stratejisi: Domain bilgileri → DNS analizi → Subdomain keşfi → Teknoloji tespiti", "ai_reasoning")
            await self.status_callback("⚙️ Teknik Detaylar:", "ai_reasoning")
            await self.status_callback("   • Registrar: Domain provider, security features", "ai_reasoning")
            await self.status_callback("   • NS Records: DNS servers, subdomain delegation", "ai_reasoning")
            await self.status_callback("   • MX Records: Mail servers, SPF/DKIM records", "ai_reasoning")
            await self.status_callback("   • TXT Records: SPF, DKIM, DMARC policies", "ai_reasoning")
            await self.status_callback("   • Creation Date: Domain age, historical data", "ai_reasoning")
        
        # Tool'a özel analiz stratejisi belirle
        analysis_context = self._get_tool_specific_context(tool_name, tool_result, state)
        await self.status_callback(f"🔍 Detaylı analiz stratejisi: {analysis_context[:150]}...", "ai_reasoning")
        
        prompt = f"""
        Sen bir Kıdemli Siber Güvenlik Analistisin. Görevin, bir araç çıktısını yorumlamak,
        önemli bulguları tespit etmek ve bu bulguları RAPORLAMA için yapısal bir JSON formatına dönüştürmek.
        Ayrıca sonuçlara göre bir sonraki çalıştırılacak araçları öner.

        HEDEF SİSTEM: {state.target}
        MEVCUT TESTİN AMACI: {state.user_task}
        
        ANALİZ EDİLECEK ARAÇ ÇIKTISI ({tool_name}):
        {json.dumps(tool_result, indent=2, ensure_ascii=False)}

        ARAÇ ÖZEL KONTEKST:
        {analysis_context}

        PENTEST UZMANI PERSPEKTİFİNDEN DERİNLEMESİNE ANALİZ GÖREVİN:
        1. **TEKNİK DETAYLI YORUMLAMA:** Bu çıktının anlamını bir penetrasyon uzmanı gibi analiz et. Her teknik detayı incele:
           - Bu sonuçta hangi teknik bilgiler var?
           - Hedef sistemin mimarisi hakkında ne öğrendim?
           - Bu bilgiler güvenlik açısından neden kritik?
           - Hangi attack vector'leri ortaya çıkıyor?
           - Bu sonuçlar hangi exploit'leri tetiklemeli?
           - OWASP Top 10 açısından hangi kategorilerde risk var?
        
        2. **KAPSAMLI TEKNİK BULGU TESPİTİ:** Çıktıyı satır satır incele ve raporlanmaya değer teknik bulguları tespit et:
           - CVE-ID'ler ve CVSS skorları var mı?
           - Zayıf konfigürasyonlar (misconfigurations) var mı?
           - Hassas bilgi ifşaları (information disclosure) var mı?
           - Eski/güvenlik açığı olan versiyonlar var mı?
           - Eksik güvenlik başlıkları (security headers) var mı?
           - Açık portlar/servisler ve versiyonları var mı?
           - Subdomain'ler/endpoint'ler ve authentication gereksinimleri var mı?
           - SSL/TLS zafiyetleri var mı?
           - Default credentials kullanımı var mı?
        
        3. **STRATEJİK TEKNİK KARAR VERME:** Bu sonuca göre hangi araç çalıştırılmalı? PENTEST UZMANI GİBİ DÜŞÜN:
           - Bu sonuç hangi attack phase'ini tetikliyor?
           - Hangi araçlar bu sonuçla en uyumlu?
           - Kaç araç çalıştırmalıyım? (1-3 arası optimal)
           - Sonraki adımda tam olarak hangi teknik testleri yapmalıyım?
           - Bu kararımın teknik mantığı nedir?
           - Hangi payload'ları kullanmalıyım?
        
        4. **AKILLI TEKNİK ZİNCİRLEME:** Sonuçlara göre mantıklı araç zinciri öner:
           - Bu sonuç hangi araçları tetikliyor?
           - Hangi sırayla çalıştırılmalı?
           - Her araç neden teknik olarak gerekli?
           - Bu zincirleme neden mantıklı?
           - Hangi exploit chain'i oluşturabilirim?
        
        finding_schema: {{
          "title": "Bulgunun net ve açıklayıcı başlığı. Örn: 'Path Traversal Zafiyeti İçeren Apache 2.4.49 Sunucusu'",
          "severity": "Kritik, Yüksek, Orta, Düşük veya Bilgilendirme (sadece bu değerlerden biri)",
          "cve_id": "Eğer varsa CVE numarası. Örn: 'CVE-2021-42013'. Yoksa null.",
          "cvss_score": "Eğer biliniyorsa CVSS skoru (0.0-10.0 arası float). Yoksa null.",
          "description": "Bulgunun detaylı teknik açıklaması. Bu zafiyet nedir, nasıl çalışır ve neden bir risktir?",
          "evidence": "Bulgunun somut kanıtı. Tool çıktısından alıntılar, header değerleri, versiyon numaraları vb.",
          "affected_component": "Etkilenen spesifik URL, IP:Port, parametre adı veya bileşen.",
          "recommendation_summary": "Çözüm için net ve uygulanabilir öneri. Örn: 'Apache sunucusunu 2.4.54 veya üzeri bir versiyona yükseltin.'"
        }}

        ÖNEMLİ KURALLAR:
        - Sadece gerçek güvenlik bulguları için finding oluştur (bilgi toplama sonuçları değil)
        - Severity değerlendirmesi yaparken OWASP ve CVSS standartlarını göz önünde bulundur:
          * Kritik: RCE, authentication bypass, veri tabanı ele geçirme (CVSS 9.0-10.0)
          * Yüksek: SQL injection, XSS (stored), XXE, SSRF (CVSS 7.0-8.9)
          * Orta: XSS (reflected), CSRF, bilgi ifşası (CVSS 4.0-6.9)
          * Düşük: Clickjacking, verbose errors, weak SSL (CVSS 0.1-3.9)
          * Bilgilendirme: Versiyon ifşası, eksik güvenlik başlıkları
        - Evidence kısmında tool çıktısından somut kanıtlar göster
        - affected_component'te mümkün olduğunca spesifik ol

        AI KARAR VERME ÖRNEKLERİ:
        
        SONUÇ: "Port 80, 443 açık"
        AI KARARI: "Web servisi var, keşif aşamasını atla, direkt teknoloji tespiti yap"
        ÖNERİ: enum_tech_detector
        
        SONUÇ: "WordPress 5.8 tespit edildi"
        AI KARARI: "WordPress bulundu, dependency scan + directory bruteforce yap"
        ÖNERİ: vul_depency_scanner + enum_directory_bruteforce
        
        SONUÇ: "API endpoint /api/users bulundu"
        AI KARARI: "API bulundu, IDOR + JWT testleri yap"
        ÖNERİ: api_vuln_idor_scanner + api_vuln_jwt_tester
        
        SONUÇ: "S3 bucket bulundu"
        AI KARARI: "Cloud servisi bulundu, permission check yap"
        ÖNERİ: cloud_s3_bucket_scanner
        
        SONUÇ: "MySQL port 3306 açık"
        AI KARARI: "Database bulundu, SQL injection testleri yap"
        ÖNERİ: verify_sqli
        
        SONUÇ: "Subdomain admin.example.com bulundu"
        AI KARARI: "Yeni subdomain bulundu, teknoloji tespiti yap"
        ÖNERİ: enum_tech_detector (admin.example.com'a)

        ÇIKTI OLARAK AŞAĞIDAKİ FORMATTA BİR JSON DÖN:
        {{
          "thought": "PENTEST UZMANI PERSPEKTİFİNDEN DERİNLEMESİNE düşünce sürecinin detaylı açıklaması. Her teknik adımı açıkla:
          - Bu sonuçta hangi teknik bilgileri buldum?
          - Hedef sistemin mimarisi hakkında ne öğrendim?
          - Bu bulgular güvenlik açısından neden kritik?
          - Hangi attack vector'leri ortaya çıkıyor?
          - Bu sonuçlar hangi exploit'leri tetiklemeli?
          - OWASP Top 10 açısından hangi kategorilerde risk var?
          - Neden bu araçları seçiyorum?
          - Bu kararımın teknik mantığı nedir?
          - Hangi payload'ları kullanmalıyım?",
          
          "summary_for_human": "PENTEST UZMANI PERSPEKTİFİNDEN detaylı teknik özet (4-5 cümle). Ne bulduğumu, teknik detayları, güvenlik etkilerini ve sonraki adımı açıkla.",
          
          "detailed_analysis": {{
            "what_found": "Bu araçla tam olarak hangi teknik bilgileri buldum?",
            "technical_details": "Bulunan teknik detaylar neler? (versiyonlar, konfigürasyonlar, servisler)",
            "security_implications": "Bu bulguların güvenlik açısından teknik anlamı nedir?",
            "attack_vectors": "Hangi attack vector'leri ortaya çıkıyor?",
            "owasp_categories": "OWASP Top 10 açısından hangi kategorilerde risk var?",
            "risk_level": "Bu bulguların risk seviyesi nedir ve neden?",
            "next_steps_logic": "Sonraki adımları neden bu şekilde teknik olarak planlıyorum?"
          }},
          
          "structured_finding": <finding_schema'ya uygun doldurulmuş JSON nesnesi VEYA null>,
          
          "next_action_suggestion": {{ 
            "tool": "önerilen_tool_adı", 
            "params": {{"param1": "değer1"}}, 
            "goal": "Bu aracı neden çalıştırmak istediğinin teknik detaylı açıklaması",
            "reasoning": "Bu araç seçiminin teknik mantığı ve pentest uzmanı perspektifi",
            "expected_outcome": "Bu araçtan teknik olarak ne bekliyorum?",
            "why_this_tool": "Neden başka araç değil de bu araç? Teknik gerekçeleri nedir?",
            "attack_phase": "Bu araç hangi attack phase'ini tetikliyor?",
            "payload_strategy": "Hangi payload'ları kullanmalıyım?"
          }} // Sadece mantıklıysa, yoksa null
        }}
        """

        analysis_result = await self._call_gemini_json(prompt)

        # Analiz sonucunu kullanıcıya detaylı göster
        if thought := analysis_result.get("thought"):
            await self.status_callback("🤔 DERİNLEMESİNE DÜŞÜNCE SÜRECİM:", "ai_thinking")
            # Düşünce sürecini paragraflara böl
            thought_lines = thought.split('\n')
            for line in thought_lines:
                if line.strip():
                    await self.status_callback(f"   {line.strip()}", "ai_reasoning")
        
        if summary := analysis_result.get("summary_for_human"):
            await self.status_callback(f"💡 DETAYLI ANALİZ ÖZETİM: {summary}", "ai_decision")
        
        # Detaylı analizi teknik detaylarla göster
        if detailed_analysis := analysis_result.get("detailed_analysis"):
            await self.status_callback("🔍 TEKNİK DETAYLI ANALİZ SONUÇLARI:", "ai_reasoning")
            await self.status_callback(f"   📊 Ne Buldum: {detailed_analysis.get('what_found', 'Bilinmiyor')}", "ai_reasoning")
            await self.status_callback(f"   ⚙️ Teknik Detaylar: {detailed_analysis.get('technical_details', 'Bilinmiyor')}", "ai_reasoning")
            await self.status_callback(f"   ⚠️ Güvenlik Etkisi: {detailed_analysis.get('security_implications', 'Bilinmiyor')}", "ai_reasoning")
            await self.status_callback(f"   🎯 Attack Vector'leri: {detailed_analysis.get('attack_vectors', 'Bilinmiyor')}", "ai_reasoning")
            await self.status_callback(f"   🔒 OWASP Kategorileri: {detailed_analysis.get('owasp_categories', 'Bilinmiyor')}", "ai_reasoning")
            await self.status_callback(f"   🎯 Risk Seviyesi: {detailed_analysis.get('risk_level', 'Bilinmiyor')}", "ai_reasoning")
            await self.status_callback(f"   🔄 Sonraki Adım Mantığı: {detailed_analysis.get('next_steps_logic', 'Bilinmiyor')}", "ai_reasoning")

        # Yapılandırılmış bulguyu State'e ekle
        if finding := analysis_result.get("structured_finding"):
            # Bulguya metadata ekle
            finding["detected_by_tool"] = tool_name
            finding["detection_time"] = datetime.now().isoformat()
            
            # CVSS skoru float olduğundan emin ol
            if finding.get("cvss_score"):
                try:
                    finding["cvss_score"] = float(finding["cvss_score"])
                except:
                    finding["cvss_score"] = None
            
            state.add_finding(finding)
            
            # Kritik bulguları vurgula
            severity = finding.get("severity", "").lower()
            if severity in ["kritik", "critical"]:
                await self.status_callback(
                    f"🚨 KRİTİK BULGU: {finding.get('title')}", 
                    "critical_finding"
                )
            elif severity in ["yüksek", "high"]:
                await self.status_callback(
                    f"⚠️ YÜKSEK RİSKLİ BULGU: {finding.get('title')}", 
                    "high_finding"
                )

        # Bir sonraki adım önerisini döndür
        next_suggestion = analysis_result.get("next_action_suggestion")
        
        if next_suggestion:
            await self.status_callback("🎯 TEKNİK DETAYLI SONRAKI ADIM ÖNERİM:", "ai_decision")
            await self.status_callback(f"   🔧 Araç: {next_suggestion.get('tool', 'Bilinmiyor')}", "ai_reasoning")
            await self.status_callback(f"   🎯 Hedef: {next_suggestion.get('goal', 'Hedef belirtilmemiş')}", "ai_reasoning")
            await self.status_callback(f"   💭 Teknik Mantık: {next_suggestion.get('reasoning', 'Sonuçlara göre mantıklı')}", "ai_reasoning")
            await self.status_callback(f"   📈 Beklenen Sonuç: {next_suggestion.get('expected_outcome', 'Bilinmiyor')}", "ai_reasoning")
            await self.status_callback(f"   ❓ Neden Bu Araç: {next_suggestion.get('why_this_tool', 'En uygun seçenek')}", "ai_reasoning")
            await self.status_callback(f"   ⚔️ Attack Phase: {next_suggestion.get('attack_phase', 'Bilinmiyor')}", "ai_reasoning")
            await self.status_callback(f"   🎯 Payload Stratejisi: {next_suggestion.get('payload_strategy', 'Bilinmiyor')}", "ai_reasoning")
        else:
            await self.status_callback("✅ Bu adım için yeterli bilgi toplandı, sonraki adıma geçiyorum", "ai_decision")
        
        return next_suggestion
    
    def _get_tool_specific_context(self, tool_name: str, tool_result: Dict[str, Any], state: AgentState) -> str:
        """Tool'a özel analiz konteksti oluşturur"""
        context_parts = []
        
        # Tool tipine göre kontekst
        if 'port' in tool_name.lower():
            context_parts.append("Port tarama sonucu analizi")
            if 'open_ports' in str(tool_result):
                context_parts.append("Açık portlar tespit edildi")
        elif 'tech' in tool_name.lower():
            context_parts.append("Teknoloji tespiti sonucu analizi")
            if 'technologies' in str(tool_result):
                context_parts.append("Web teknolojileri tespit edildi")
        elif 'subdomain' in tool_name.lower():
            context_parts.append("Subdomain keşfi sonucu analizi")
            if 'subdomains' in str(tool_result):
                context_parts.append("Yeni subdomain'ler bulundu")
        elif 'whois' in tool_name.lower():
            context_parts.append("WHOIS analizi sonucu")
            context_parts.append("Domain bilgileri toplandı")
        
        # Kullanıcı görevine göre kontekst
        user_task = state.user_task.lower()
        if "sql" in user_task or "injection" in user_task:
            context_parts.append("SQL injection testi odaklı analiz")
        elif "xss" in user_task:
            context_parts.append("XSS testi odaklı analiz")
        elif "api" in user_task:
            context_parts.append("API güvenlik testi odaklı analiz")
        elif "port" in user_task:
            context_parts.append("Port tarama odaklı analiz")
        
        return ". ".join(context_parts) if context_parts else "Genel güvenlik analizi"

    async def generate_attack_chain_analysis(self, state: AgentState) -> Dict[str, Any]:
        """Tüm bulguları analiz ederek potansiyel saldırı zincirlerini oluştur"""
        
        if len(state.findings) < 2:
            return {"attack_chains": [], "overall_risk": "Düşük"}
        
        # Bulguları özetle
        findings_summary = []
        for finding in state.findings:
            findings_summary.append({
                "title": finding.get("title"),
                "severity": finding.get("severity"),
                "component": finding.get("affected_component"),
                "type": self._categorize_finding(finding)
            })
        
        prompt = f"""
        Sen bir Red Team Liderisin. Aşağıdaki bulguları analiz et ve potansiyel saldırı zincirlerini belirle.
        
        HEDEF: {state.target}
        
        TESPİT EDİLEN BULGULAR:
        {json.dumps(findings_summary, indent=2, ensure_ascii=False)}
        
        Bulguları birleştirerek gerçekçi saldırı senaryoları oluştur. Her senaryo için:
        1. Hangi bulgular kullanılacak
        2. Sıralama nasıl olacak
        3. Nihai etki ne olacak
        
        ÇIKTI FORMATI:
        {{
          "attack_chains": [
            {{
              "chain_name": "Saldırı senaryosunun adı",
              "severity": "Zincirin toplam risk seviyesi",
              "steps": [
                {{"finding": "Kullanılan bulgu", "action": "Ne yapılacak"}}
              ],
              "final_impact": "Başarılı olursa ne elde edilir",
              "likelihood": "Düşük/Orta/Yüksek"
            }}
          ],
          "overall_risk": "Sistemin genel risk durumu",
          "priority_remediations": ["En öncelikli düzeltmeler"]
        }}
        """
        
        result = await self._call_gemini_json(prompt)
        return result

    def _categorize_finding(self, finding: Dict[str, Any]) -> str:
        """Bulguyu kategorize et"""
        title = finding.get("title", "").lower()
        desc = finding.get("description", "").lower()
        
        if any(keyword in title + desc for keyword in ["sql", "injection", "sqli"]):
            return "injection"
        elif any(keyword in title + desc for keyword in ["xss", "cross-site", "script"]):
            return "xss"
        elif any(keyword in title + desc for keyword in ["lfi", "rfi", "file inclusion", "path traversal"]):
            return "file_inclusion"
        elif any(keyword in title + desc for keyword in ["authentication", "auth bypass", "login"]):
            return "authentication"
        elif any(keyword in title + desc for keyword in ["version", "outdated", "eski versiyon"]):
            return "outdated_software"
        elif any(keyword in title + desc for keyword in ["header", "başlık", "cors", "csp"]):
            return "configuration"
        elif any(keyword in title + desc for keyword in ["api", "endpoint", "idor"]):
            return "api_vulnerability"
        else:
            return "other"

    async def validate_finding(self, finding: Dict[str, Any]) -> bool:
        """Bulgunun geçerliliğini kontrol et"""
        
        # Zorunlu alanlar
        required_fields = ["title", "severity", "description", "evidence", "affected_component"]
        for field in required_fields:
            if not finding.get(field):
                logger.warning(f"Bulgu geçersiz: {field} alanı eksik")
                return False
        
        # Severity değeri kontrolü
        valid_severities = ["kritik", "yüksek", "orta", "düşük", "bilgilendirme", 
                           "critical", "high", "medium", "low", "info", "information"]
        if finding.get("severity", "").lower() not in valid_severities:
            logger.warning(f"Geçersiz severity değeri: {finding.get('severity')}")
            return False
        
        # CVSS skoru kontrolü
        if cvss := finding.get("cvss_score"):
            try:
                cvss_float = float(cvss)
                if not 0.0 <= cvss_float <= 10.0:
                    logger.warning(f"CVSS skoru aralık dışı: {cvss}")
                    return False
            except:
                logger.warning(f"CVSS skoru sayısal değil: {cvss}")
                return False
        
        return True

    async def enhance_finding_with_context(self, finding: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        """Bulguyu ek kontekst bilgileriyle zenginleştir"""
        
        enhanced_finding = finding.copy()
        
        # Teknoloji bağlamı ekle
        if techs := state.context_summary.get("technologies", []):
            tech_names = [t.get("name", "") if isinstance(t, dict) else str(t) for t in techs]
            enhanced_finding["technology_context"] = tech_names
        
        # WAF durumu
        if state.context_summary.get("waf_detected"):
            enhanced_finding["waf_present"] = True
            enhanced_finding["notes"] = enhanced_finding.get("notes", "") + " WAF mevcut olduğu için exploit zorlaşabilir."
        
        # İlişkili portlar
        affected_component = finding.get("affected_component", "")
        for port_info in state.context_summary.get("open_ports", []):
            if isinstance(port_info, dict) and str(port_info.get("port", "")) in affected_component:
                enhanced_finding["related_service"] = port_info.get("service", "unknown")
                break
        
        return enhanced_finding

    def get_analysis_statistics(self, state: AgentState) -> Dict[str, Any]:
        """Analiz istatistiklerini döndür"""
        
        total_findings = len(state.findings)
        
        severity_distribution = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }
        
        finding_types = {}
        tools_effectiveness = {}
        
        for finding in state.findings:
            # Severity dağılımı
            severity = finding.get("severity", "").lower()
            if "kritik" in severity or "critical" in severity:
                severity_distribution["critical"] += 1
            elif "yüksek" in severity or "high" in severity:
                severity_distribution["high"] += 1
            elif "orta" in severity or "medium" in severity:
                severity_distribution["medium"] += 1
            elif "düşük" in severity or "low" in severity:
                severity_distribution["low"] += 1
            else:
                severity_distribution["info"] += 1
            
            # Bulgu tipleri
            finding_type = self._categorize_finding(finding)
            finding_types[finding_type] = finding_types.get(finding_type, 0) + 1
            
            # Tool etkinliği
            tool = finding.get("detected_by_tool", "unknown")
            tools_effectiveness[tool] = tools_effectiveness.get(tool, 0) + 1
        
        return {
            "total_findings": total_findings,
            "severity_distribution": severity_distribution,
            "finding_types": finding_types,
            "most_effective_tools": sorted(tools_effectiveness.items(), key=lambda x: x[1], reverse=True)[:5],
            "critical_findings_count": severity_distribution["critical"],
            "exploitable_findings": sum(1 for f in state.findings if f.get("cve_id")),
            "analysis_quality_score": self._calculate_analysis_quality(state)
        }
    
        def _calculate_analysis_quality(self, state: AgentState) -> float:
         """Analiz kalitesini hesapla (0-100)"""
        
        score = 0.0
        
        # Bulgu sayısına göre puan
        finding_count = len(state.findings)
        if finding_count > 0:
            score += min(finding_count * 5, 30)  # Max 30 puan
        
        # CVE'li bulgular için ekstra puan
        cve_findings = sum(1 for f in state.findings if f.get("cve_id"))
        score += min(cve_findings * 10, 20)  # Max 20 puan
        
        # CVSS skorlu bulgular için puan
        cvss_findings = sum(1 for f in state.findings if f.get("cvss_score"))
        score += min(cvss_findings * 5, 15)  # Max 15 puan
        
        # Kanıt kalitesi için puan
        good_evidence = sum(1 for f in state.findings if len(f.get("evidence", "")) > 50)
        score += min(good_evidence * 3, 15)  # Max 15 puan
        
        # Farklı severity seviyeleri için puan
        severities = set(f.get("severity", "").lower() for f in state.findings)
        score += min(len(severities) * 5, 10)  # Max 10 puan
        
        # Recommendation kalitesi için puan
        good_recommendations = sum(1 for f in state.findings if len(f.get("recommendation_summary", "")) > 30)
        score += min(good_recommendations * 2, 10)  # Max 10 puan
        
        return min(score, 100.0)

    async def generate_executive_summary(self, state: AgentState) -> str:
        """Yöneticiler için kısa özet oluştur"""
        
        stats = self.get_analysis_statistics(state)
        
        prompt = f"""
        Sen bir Siber Güvenlik Danışmanısın. Aşağıdaki test sonuçlarından yöneticiler için 
        kısa, anlaşılır ve aksiyona yönelik bir özet hazırla.
        
        HEDEF: {state.target}
        TEST İN AMACI: {state.user_task}
        
        İSTATİSTİKLER:
        - Toplam Bulgu: {stats['total_findings']}
        - Kritik Bulgular: {stats['critical_findings_count']}
        - Risk Dağılımı: {json.dumps(stats['severity_distribution'], ensure_ascii=False)}
        
        EN KRİTİK BULGULAR:
        {self._get_critical_findings_summary(state)}
        
        Özet şunları içermeli:
        1. Genel durum değerlendirmesi (1 paragraf)
        2. En kritik 3 risk (madde madde)
        3. Acil aksiyon önerileri (madde madde)
        4. Genel risk skoru (Düşük/Orta/Yüksek/Kritik)
        
        Teknik jargon kullanma, iş etkisine odaklan.
        """
        
        response = await self.model.generate_content_async(prompt)
        return response.text

    def _get_critical_findings_summary(self, state: AgentState) -> str:
        """En kritik bulguların özetini al"""
        
        critical_findings = []
        
        for finding in state.findings:
            severity = finding.get("severity", "").lower()
            if any(level in severity for level in ["kritik", "critical", "yüksek", "high"]):
                critical_findings.append({
                    "title": finding.get("title"),
                    "impact": finding.get("description", "")[:100] + "...",
                    "component": finding.get("affected_component")
                })
        
        # En fazla 5 kritik bulgu göster
        critical_findings = critical_findings[:5]
        
        return json.dumps(critical_findings, indent=2, ensure_ascii=False)

    async def suggest_remediation_priority(self, state: AgentState) -> List[Dict[str, Any]]:
        """Düzeltme önceliklerini belirle"""
        
        # Bulguları risk skoruna göre sırala
        scored_findings = []
        
        for finding in state.findings:
            risk_score = self._calculate_finding_risk_score(finding)
            scored_findings.append({
                "finding": finding,
                "risk_score": risk_score
            })
        
        # Risk skoruna göre sırala
        scored_findings.sort(key=lambda x: x["risk_score"], reverse=True)
        
        # İlk 10 bulgu için detaylı öneri
        priority_list = []
        for i, item in enumerate(scored_findings[:10], 1):
            finding = item["finding"]
            priority_list.append({
                "priority": i,
                "title": finding.get("title"),
                "severity": finding.get("severity"),
                "risk_score": item["risk_score"],
                "affected_component": finding.get("affected_component"),
                "quick_fix": self._generate_quick_fix(finding),
                "estimated_effort": self._estimate_remediation_effort(finding)
            })
        
        return priority_list

    def _calculate_finding_risk_score(self, finding: Dict[str, Any]) -> float:
        """Bulgu için risk skoru hesapla (0-100)"""
        
        score = 0.0
        
        # CVSS skoruna göre
        if cvss := finding.get("cvss_score"):
            score += float(cvss) * 10  # Max 100
        else:
            # CVSS yoksa severity'ye göre tahmin
            severity = finding.get("severity", "").lower()
            severity_scores = {
                "kritik": 95, "critical": 95,
                "yüksek": 75, "high": 75,
                "orta": 50, "medium": 50,
                "düşük": 25, "low": 25,
                "bilgilendirme": 10, "info": 10, "information": 10
            }
            for sev_key, sev_score in severity_scores.items():
                if sev_key in severity:
                    score = sev_score
                    break
        
        # Exploitability faktörü
        if finding.get("cve_id"):
            score *= 1.2  # CVE varsa %20 artır
        
        # Affected component kritikliği
        component = finding.get("affected_component", "").lower()
        if any(critical in component for critical in ["login", "auth", "admin", "api", "database"]):
            score *= 1.1  # Kritik component ise %10 artır
        
        return min(score, 100.0)

    def _generate_quick_fix(self, finding: Dict[str, Any]) -> str:
        """Hızlı çözüm önerisi üret"""
        
        finding_type = self._categorize_finding(finding)
        
        quick_fixes = {
            "injection": "Parametrik sorgular kullanın, input validasyonu ekleyin",
            "xss": "Output encoding uygulayın, CSP header'ı ekleyin",
            "file_inclusion": "Path validasyonu ekleyin, dizin gezintisini engelleyin",
            "authentication": "Multi-factor authentication ekleyin, şifre politikasını güçlendirin",
            "outdated_software": "İlgili yazılımı en güncel kararlı sürüme yükseltin",
            "configuration": "Önerilen güvenlik başlıklarını ekleyin",
            "api_vulnerability": "API rate limiting ve authentication ekleyin",
            "other": finding.get("recommendation_summary", "Güvenlik uzmanına danışın")
        }
        
        return quick_fixes.get(finding_type, quick_fixes["other"])

    def _estimate_remediation_effort(self, finding: Dict[str, Any]) -> str:
        """Düzeltme için tahmini efor"""
        
        finding_type = self._categorize_finding(finding)
        
        effort_map = {
            "injection": "Yüksek (1-2 hafta)",
            "xss": "Orta (3-5 gün)",
            "file_inclusion": "Yüksek (1 hafta)",
            "authentication": "Çok Yüksek (2-4 hafta)",
            "outdated_software": "Düşük (1-2 gün)",
            "configuration": "Çok Düşük (Birkaç saat)",
            "api_vulnerability": "Orta (1 hafta)",
            "other": "Belirsiz"
        }
        
        return effort_map.get(finding_type, effort_map["other"])

    async def generate_technical_details(self, finding: Dict[str, Any]) -> str:
        """Bulgu için detaylı teknik açıklama üret"""
        
        prompt = f"""
        Aşağıdaki güvenlik bulgusunun detaylı teknik açıklamasını hazırla:
        
        {json.dumps(finding, indent=2, ensure_ascii=False)}
        
        Açıklama şunları içermeli:
        1. Zafiyetin teknik detayları
        2. Nasıl sömürülebileceği (teorik)
        3. Potansiyel etkiler
        4. Detaylı düzeltme adımları
        5. Test için örnek komutlar (zararsız)
        
        Profesyonel ve teknik bir dil kullan.
        """
        
        response = await self.model.generate_content_async(prompt)
        return response.text

    def export_findings_for_report(self, state: AgentState) -> Dict[str, Any]:
        """Bulguları rapor için hazır formata dönüştür"""
        
        return {
            "scan_info": {
                "target": state.target,
                "scan_date": state.start_time.isoformat(),
                "scan_duration": state.execution_time,
                "total_findings": len(state.findings)
            },
            "executive_summary": {
                "total_vulnerabilities": len(state.findings),
                "critical_count": sum(1 for f in state.findings if "kritik" in f.get("severity", "").lower() or "critical" in f.get("severity", "").lower()),
                "high_count": sum(1 for f in state.findings if "yüksek" in f.get("severity", "").lower() or "high" in f.get("severity", "").lower()),
                "medium_count": sum(1 for f in state.findings if "orta" in f.get("severity", "").lower() or "medium" in f.get("severity", "").lower()),
                "low_count": sum(1 for f in state.findings if "düşük" in f.get("severity", "").lower() or "low" in f.get("severity", "").lower()),
                "info_count": sum(1 for f in state.findings if "bilgi" in f.get("severity", "").lower() or "info" in f.get("severity", "").lower())
            },
            "detailed_findings": state.findings,
            "technology_stack": state.context_summary.get("technologies", []),
            "attack_surface": {
                "open_ports": state.context_summary.get("open_ports", []),
                "subdomains": state.context_summary.get("subdomains", []),
                "endpoints": state.context_summary.get("endpoints", [])
            },
            "recommendations": {
                "immediate_actions": [],
                "short_term": [],
                "long_term": []
            }
        }
        #