# agent_core/planner.py

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from agent_core.state import AgentState

logger = logging.getLogger(__name__)

class Planner:
    """Stratejik planlama ve adaptasyon yapan AI beyni - Güvenli ve etik odaklı."""
    
    def __init__(self, model: genai.GenerativeModel, mcp_server, status_callback=None):
        self.model = model
        self.mcp_server = mcp_server
        self.status_callback = status_callback
        
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
            
            parsed = json.loads(response_text)
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse hatası: {e}")
            logger.error(f"Ham yanıt: {response_text[:500]}...")
            return {}
        except Exception as e:
            logger.error(f"Gemini API hatası: {e}")
            # Rate limiting veya quota hatası için fallback
            if "quota" in str(e).lower() or "rate" in str(e).lower():
                logger.warning("API quota/rate limit hatası - fallback plan kullanılıyor")
                return self._get_fallback_plan()
            return {}

    async def create_initial_plan(self, state: AgentState) -> List[Dict[str, Any]]:
        """AI ile hedefe yönelik güvenli ve etik bir test planı oluşturur."""
        # Hedef analizi yap
        target_type = "domain" if '.' in state.target and not state.target.replace('.', '').isdigit() else "IP adresi" if state.target.replace('.', '').isdigit() else "URL"
        
        # Status callback ile detaylı düşünce sürecini göster
        if hasattr(self, 'status_callback'):
            await self.status_callback("🧠 DERİNLEMESİNE HEDEF ANALİZİ BAŞLIYOR...", "ai_thinking")
            await self.status_callback(f"🎯 Hedef: {state.target}", "ai_reasoning")
            await self.status_callback(f"🔍 Hedef Tipi: {target_type}", "ai_reasoning")
            await self.status_callback(f"📋 Görev: {state.user_task}", "ai_reasoning")
            
            # Hedef tipine ve kullanıcı görevine göre dinamik analiz
            await self.status_callback(f"💭 Hedef analizi: {state.target} - Bu bir {target_type}. Kullanıcının görevi: '{state.user_task}'", "ai_reasoning")
            
            # Kullanıcı görevine göre dinamik strateji
            if "port" in state.user_task.lower():
                await self.status_callback("🔍 Port odaklı strateji: Kullanıcı port taraması istiyor, direkt port scanning yapacağım", "ai_reasoning")
                await self.status_callback("⚙️ Teknik Yaklaşım:", "ai_reasoning")
                await self.status_callback("   • Port Scan: SYN scan, service detection, OS fingerprinting", "ai_reasoning")
                await self.status_callback("   • Service Enum: Banner grabbing, version detection", "ai_reasoning")
            elif "sql" in state.user_task.lower() or "injection" in state.user_task.lower():
                await self.status_callback("🔍 SQL Injection odaklı strateji: Kullanıcı SQL injection testi istiyor, web teknolojilerini tespit edip SQL testleri yapacağım", "ai_reasoning")
                await self.status_callback("⚙️ Teknik Yaklaşım:", "ai_reasoning")
                await self.status_callback("   • Tech Detection: Database teknolojileri, SQL injection noktaları", "ai_reasoning")
                await self.status_callback("   • SQL Testing: Parameter fuzzing, payload injection", "ai_reasoning")
            elif "xss" in state.user_task.lower():
                await self.status_callback("🔍 XSS odaklı strateji: Kullanıcı XSS testi istiyor, web uygulamasını analiz edip XSS noktalarını tespit edeceğim", "ai_reasoning")
                await self.status_callback("⚙️ Teknik Yaklaşım:", "ai_reasoning")
                await self.status_callback("   • Web Analysis: Input fields, reflection points", "ai_reasoning")
                await self.status_callback("   • XSS Testing: Payload injection, filter bypass", "ai_reasoning")
            elif "api" in state.user_task.lower():
                await self.status_callback("🔍 API odaklı strateji: Kullanıcı API testi istiyor, API endpoint'lerini keşfedip güvenlik testleri yapacağım", "ai_reasoning")
                await self.status_callback("⚙️ Teknik Yaklaşım:", "ai_reasoning")
                await self.status_callback("   • API Discovery: Endpoint enumeration, parameter discovery", "ai_reasoning")
                await self.status_callback("   • API Testing: Authentication, authorization, input validation", "ai_reasoning")
            else:
                # Genel güvenlik testi için hedef tipine göre strateji
                if target_type == "domain":
                    await self.status_callback("🔍 Domain için genel strateji: Reconnaissance → Subdomain Discovery → Port Scanning → Technology Detection", "ai_reasoning")
                    await self.status_callback("⚙️ Teknik Yaklaşım:", "ai_reasoning")
                    await self.status_callback("   • WHOIS: Registrar, NS kayıtları, MX kayıtları, TXT kayıtları", "ai_reasoning")
                    await self.status_callback("   • Subdomain: Passive DNS, Certificate Transparency, DNS bruteforce", "ai_reasoning")
                    await self.status_callback("   • Port Scan: Top 1000 ports, service detection, banner grabbing", "ai_reasoning")
                    await self.status_callback("   • Tech Stack: Wappalyzer, HTTP headers, favicon analysis", "ai_reasoning")
                elif target_type == "IP adresi":
                    await self.status_callback("🔍 IP için genel strateji: Port Scanning → Service Detection → Technology Identification", "ai_reasoning")
                    await self.status_callback("⚙️ Teknik Yaklaşım:", "ai_reasoning")
                    await self.status_callback("   • Port Scan: SYN scan, service detection, OS fingerprinting", "ai_reasoning")
                    await self.status_callback("   • Service Enum: Banner grabbing, version detection, vulnerability mapping", "ai_reasoning")
                    await self.status_callback("   • Web Services: HTTP/HTTPS analysis, directory bruteforce, parameter fuzzing", "ai_reasoning")
                else:
                    await self.status_callback("🔍 URL için genel strateji: Technology Detection → Vulnerability Assessment → Security Testing", "ai_reasoning")
                    await self.status_callback("⚙️ Teknik Yaklaşım:", "ai_reasoning")
                    await self.status_callback("   • Tech Detection: Framework, CMS, server version, database", "ai_reasoning")
                    await self.status_callback("   • Vulnerability: CVE lookup, dependency scan, configuration analysis", "ai_reasoning")
                    await self.status_callback("   • Security Headers: CSP, HSTS, X-Frame-Options, CORS", "ai_reasoning")
            
            await self.status_callback("🧠 Mevcut araçları analiz ediyorum ve en optimal kombinasyonu seçiyorum...", "ai_thinking")
        
        tool_info = json.dumps(self.mcp_server.get_tool_list()['categories'], indent=2)
        
        prompt = f"""
        Sen bir Etik Hacker ve Güvenlik Stratejistisin. Görevin, hedef sistemlere ZARAR VERMEDEN, 
        sadece bilgi toplama ve zafiyet tespiti odaklı bir güvenlik değerlendirme planı oluşturmak.

        HEDEF: {state.target}
        GÖREV: {state.user_task or "Kapsamlı ve güvenli güvenlik analizi"}
        
        MEVCUT ARAÇLAR:
        {tool_info}
        
        KRİTİK PLANLAMA KURALLARI:
        1. Planın amacı SÖMÜRÜ DEĞİL, TESPİT VE RAPORLAMADIR.
        2. Hedefi analiz et ve KENDİ KARARINI VER - hangi aşamaları, kaç araçla yapacağını sen belirle
        3. Aşamaları ATLA: Gereksiz aşamaları geç, direkt ilgili aşamaya geç
        4. Asla RCE, veri çalma veya sisteme zarar verebilecek araçlar kullanma
        5. Her adım şu yapıda olmalı: {{"goal": "net açıklama", "tool": "araç_adı", "params": {{"param1": "değer"}}}}
        6. BAŞLANGIÇ PLANI: Sadece 3-5 kritik araç seç, gerisini sonuçlara göre ekle
        7. AKILLI ZİNCİRLEME: Sonuçlara göre plan otomatik genişleyecek
        
        AI KARAR VERME STRATEJİSİ:
        
        HEDEF ANALİZİ YAP:
        - Bu hedef ne tür bir sistem? (Web app, API, Infrastructure, Network)
        - Hangi teknolojiler kullanılıyor olabilir?
        - Hangi zafiyetler en kritik olabilir?
        - Hangi araçlar bu hedef için en uygun?
        
        SONUÇLARA GÖRE DİNAMİK KARAR VER:
        - Port taraması sonuçlarına göre hangi servisler test edilmeli?
        - Web teknolojileri tespit edilirse hangi OWASP testleri yapılmalı?
        - API endpoint'leri bulunursa hangi API güvenlik testleri yapılmalı?
        - Subdomain'ler bulunursa hangi ek testler yapılmalı?
        
        ÖRNEK DİNAMİK ZİNCİRLEME:
        1. Port Scan → 80,443 açık → Web Technology Detection
        2. Web Tech → WordPress tespit → WordPress Vulnerability Scan
        3. WordPress Vuln → SQL Injection tespit → SQL Injection Test
        4. SQL Injection → Database access → Database Enumeration
        
        IP HEDEFİ:
        - Sadece 1 araç: Port scanner
        - Açık portlara göre direkt servis analizi
        
        WEB URL HEDEFİ:
        - Keşif atla, direkt teknoloji tespiti
        - Teknolojiye göre zafiyet testleri
        
        API HEDEFİ:
        - Keşif atla, direkt API endpoint discovery
        - API güvenlik testleri
        
        INFRASTRUCTURE HEDEFİ:
        - Port scan + Cloud servisleri
        - Exposed panel detection
        
        KARAR VERME KURALLARI:
        - Gereksiz aşamaları ATLA
        - Hedef tipine göre direkt ilgili araçları seç
        - Sonuçlara göre planı genişlet
        - Her hedef için farklı strateji uygula
        
        DİNAMİK PLANLAMA YAKLAŞIMI:
        - Hedefin tipine göre (domain/IP/URL) uygun araçları seç
        - Domain ise: subdomain keşfi, DNS analizi öncelikli olabilir
        - IP ise: port taraması, servis tespiti öncelikli olabilir
        - Web URL ise: teknoloji tespiti, güvenlik başlıkları öncelikli olabilir
        - Her hedef için farklı strateji uygula
        
        AKILLI ZİNCİRLEME STRATEJİSİ:
        - Başlangıç planı MİNİMAL olmalı (3-5 araç)
        - Sonuçlara göre Analyzer otomatik olarak yeni araçlar önerecek
        - AI kendi kararını verecek: hangi aşamaları atlayacak, hangilerini kullanacak
        
        ÖRNEK AKILLI KARARLAR:
        
        DOMAIN → WEB UYGULAMASI:
        - Başlangıç: WHOIS + Subdomain discovery (2 araç)
        - Subdomain bulundu → Teknoloji tespiti
        - WordPress bulundu → Dependency scan + Directory bruteforce
        
        IP → INFRASTRUCTURE:
        - Başlangıç: Port scanner (1 araç)
        - Port 22 açık → SSH banner check
        - Port 80/443 açık → Web teknoloji tespiti
        
        URL → API:
        - Keşif atla → Direkt API endpoint discovery
        - Endpoint bulundu → IDOR + JWT testleri
        
        CLOUD SERVİSİ:
        - Keşif atla → Direkt S3 bucket scanner
        - Bucket bulundu → Permission check
        
        ÖRNEK ADIM YAPILARI:
        
        RECONNAISSANCE ÖRNEKLERİ:
        {{
            "goal": "Hedef domain hakkında WHOIS bilgilerini topla",
            "tool": "rec_whois_tool",
            "params": {{"target": "{state.target}"}}
        }}
        
        {{
            "goal": "Hedef domain için pasif subdomain keşfi yap",
            "tool": "recon_passive_subfinder", 
            "params": {{"domain": "{state.target}"}}
        }}
        
        ENUMERATION ÖRNEKLERİ:
        {{
            "goal": "Hedefin açık portlarını ve servislerini tespit et",
            "tool": "enum_port_scanner",
            "params": {{"target": "{state.target}"}}
        }}
        
        {{
            "goal": "Web teknolojilerini ve versiyonlarını tespit et",
            "tool": "enum_tech_detector",
            "params": {{"url": "{state.target}"}}
        }}
        
        VULNERABILITY ASSESSMENT ÖRNEKLERİ:
        {{
            "goal": "HTTP güvenlik başlıklarını analiz et",
            "tool": "vuln_http_header_analyzer",
            "params": {{"target": "{state.target}"}}
        }}
        
        {{
            "goal": "Bağımlılık zafiyetlerini tara",
            "tool": "vul_depency_scanner",
            "params": {{"target": "{state.target}"}}
        }}
        
        ÖNEMLİ: Parametrelerde hedef URL/IP'yi doğru formatta kullan:
        - Web araçları için: http:// veya https:// ile başlamalı
        - Port tarayıcı için: IP adresi veya domain
        - Subdomain araçları için: sadece domain kısmı (örn: example.com)
        
        ÇIKTI OLARAK SADECE {{"plan": [adım1, adım2, ...]}} şeklinde bir JSON nesnesi dön.
        Açıklama veya yorum ekleme, sadece JSON.
        """
        
        response = await self._call_gemini_json(prompt)
        plan = response.get("plan", [])
        
        # Planı doğrula ve güvenlik kontrollerinden geçir
        validated_plan = []
        forbidden_tools = ["verify_rce", "privesc", "postexploit", "credential_tester"]
        
        for step in plan:
            if all(key in step for key in ["goal", "tool", "params"]):
                # Tehlikeli araçları filtrele
                if any(forbidden in step["tool"] for forbidden in forbidden_tools):
                    logger.warning(f"Tehlikeli araç filtrelendi: {step['tool']}")
                    continue
                    
                # Parametreleri normalize et
                step["params"] = self._normalize_params(step["tool"], step["params"], state.target)
                validated_plan.append(step)
        
        # Eğer plan çok kısa kaldıysa temel adımları ekle
        if len(validated_plan) < 4:
            validated_plan = self._add_essential_steps(validated_plan, state.target)
        
        return validated_plan

    def _normalize_params(self, tool_name: str, params: Dict[str, Any], target: str) -> Dict[str, Any]:
        """Tool parametrelerini normalize et"""
        normalized = params.copy()
        
        # Target parametresini tool tipine göre ayarla
        if "web" in tool_name or "http" in tool_name or "xss" in tool_name:
            # Web araçları için URL formatı gerekli
            if not params.get("target", "").startswith(("http://", "https://")):
                normalized["target"] = f"https://{target}"
                
        elif "subdomain" in tool_name or "dns" in tool_name:
            # Subdomain araçları için sadece domain
            target_domain = target.replace("http://", "").replace("https://", "").split("/")[0]
            normalized["target"] = target_domain
            normalized["domain"] = target_domain
            
        elif "port" in tool_name:
            # Port tarayıcı için IP veya domain
            normalized["target"] = target.replace("http://", "").replace("https://", "").split("/")[0]
        
        return normalized

    def _add_essential_steps(self, plan: List[Dict[str, Any]], target: str) -> List[Dict[str, Any]]:
        """Eksik temel adımları plana ekle"""
        essential_tools = {
            "enum_tech_detector": {
                "goal": "Web teknolojilerini tespit et",
                "params": {"target": target}
            },
            "enum_port_scanner": {
                "goal": "Açık portları tara",
                "params": {"target": target.replace("http://", "").replace("https://", "").split("/")[0]}
            },
            "vuln_http_header_analyzer": {
                "goal": "HTTP güvenlik başlıklarını kontrol et",
                "params": {"target": target}
            }
        }
        
        existing_tools = {step["tool"] for step in plan}
        
        for tool, config in essential_tools.items():
            if tool not in existing_tools:
                plan.append({
                    "goal": config["goal"],
                    "tool": tool,
                    "params": config["params"]
                })
        
        return plan

    async def adapt_plan(self, state: AgentState, suggestion: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Mevcut duruma ve Analyzer önerisine göre planı adapte eder."""
        
        if not state.completed_steps and not suggestion:
            return []
        
        # Son adımlar ve mevcut durum
        recent_steps = state.completed_steps[-3:] if state.completed_steps else []
        remaining_steps = [s for s in state.plan if s.get('status') == 'pending']
        
        # Bulguların özeti
        findings_info = {
            "total_findings": len(state.findings),
            "critical_findings": sum(1 for f in state.findings if "kritik" in f.get("severity", "").lower()),
            "technologies_found": len(state.context_summary.get("technologies", [])),
            "open_ports_found": len(state.context_summary.get("open_ports", [])),
            "vulnerabilities_found": len(state.context_summary.get("vulnerabilities", []))
        }
        
        prompt = f"""
        Sen değişen koşullara adapte olan bir Güvenlik Stratejistisin. Plan adaptasyonu yap.
        
        HEDEF: {state.target}
        MEVCUT DURUM ÖZETİ:
        {json.dumps(findings_info, indent=2)}
        
        SON TAMAMLANAN ADIMLAR:
        {json.dumps(recent_steps, indent=2) if recent_steps else "Henüz adım tamamlanmadı"}
        
        ANALİZ MODÜLÜNÜN ÖNERİSİ:
        {json.dumps(suggestion, indent=2) if suggestion else "Öneri yok, genel duruma göre karar ver."}
        
        MEVCUT KALAN ADIMLAR:
        {json.dumps(remaining_steps, indent=2) if remaining_steps else "Kalan adım yok"}
        
        TEKNOLOJİLER:
        {json.dumps(state.context_summary.get("technologies", []), indent=2)}
        
        ADAPTASYON KURALLARI:
        1. ÖNCELİKLE Analiz modülünün önerisini değerlendir ve plana dahil et
        2. Asla sisteme zarar verecek araçlar ekleme (RCE, SQL dump, privilege escalation)
        3. Bulguları derinleştirmeye odaklan, sömürü değil
        4. Maksimum 5 yeni adım ekle
        5. Zaten yapılmış işlemleri tekrarlama
        
        ÖRNEK ADAPTASYONLAR:
        - Açık API endpoint bulunduysa → api_vuln_idor_scanner çalıştır
        - Eski jQuery versiyonu bulunduysa → vuln_dependency_scanner çalıştır
        - Login paneli bulunduysa → vuln_http_header_analyzer ile güvenlik başlıklarını kontrol et
        
        ÇIKTI OLARAK SADECE {{"plan": [yeni_adım1, yeni_adım2, ...]}} şeklinde JSON dön.
        Boş plan dönebilirsin: {{"plan": []}}
        """
        
        response = await self._call_gemini_json(prompt)
        adapted_plan = response.get("plan", [])
        
        # Güvenlik filtresi ve validasyon
        validated_plan = []
        forbidden_tools = ["verify_rce", "privesc", "postexploit", "credential_tester", "linux_suggester"]
        
        for step in adapted_plan:
            if all(key in step for key in ["goal", "tool", "params"]):
                # Tehlikeli araçları filtrele
                if any(forbidden in step["tool"] for forbidden in forbidden_tools):
                    logger.warning(f"Adaptasyon sırasında tehlikeli araç filtrelendi: {step['tool']}")
                    continue
                
                # Parametreleri normalize et
                step["params"] = self._normalize_params(step["tool"], step["params"], state.target)
                
                # Tekrarlayan adımları önle
                is_duplicate = any(
                    existing["tool"] == step["tool"] and 
                    existing.get("params", {}).get("target") == step["params"].get("target")
                    for existing in state.plan
                )
                
                if not is_duplicate:
                    validated_plan.append(step)
                else:
                    logger.info(f"Tekrarlayan adım filtrelendi: {step['tool']}")
        
        return validated_plan

    async def generate_remediation_plan(self, state: AgentState) -> Dict[str, Any]:
        """Tespit edilen bulgulara göre düzeltme planı önerir."""
        
        # En kritik 10 bulguyu al
        critical_findings = []
        for finding in state.findings:
            severity = finding.get("severity", "").lower()
            if any(level in severity for level in ["kritik", "critical", "yüksek", "high"]):
                critical_findings.append({
                    "title": finding.get("title"),
                    "severity": finding.get("severity"),
                    "component": finding.get("affected_component"),
                    "recommendation": finding.get("recommendation_summary")
                })
        
        critical_findings = critical_findings[:10]
        
        prompt = f"""
        Sen bir Güvenlik Danışmanısın. Tespit edilen bulgulara göre öncelikli düzeltme planı oluştur.
        
        HEDEF: {state.target}
        
        KRİTİK BULGULAR:
        {json.dumps(critical_findings, indent=2, ensure_ascii=False)}
        
        TEKNOLOJİ STACK'İ:
        {json.dumps(state.context_summary.get("technologies", []), indent=2)}
        
        DÜZELTME PLANI OLUŞTUR:
        1. Acil (0-7 gün içinde)
        2. Kısa vadeli (1-4 hafta)
        3. Uzun vadeli (1-3 ay)
        
        Her düzeltme için:
        - Ne yapılmalı
        - Neden öncelikli
        - Tahmini efor
        - Potansiyel risk azaltma
        
        ÇIKTI FORMATI:
        {{
          "immediate_actions": [
            {{
              "action": "Yapılacak iş",
              "reason": "Neden acil",
              "effort": "1-2 gün",
              "risk_reduction": "Yüksek"
            }}
          ],
          "short_term": [...],
          "long_term": [...],
          "quick_wins": ["Hemen uygulanabilecek basit güvenlik iyileştirmeleri"],
          "estimated_total_effort": "Toplam tahmini süre"
        }}
        """
        
        response = await self._call_gemini_json(prompt)
        return response

    async def generate_attack_strategy(self, state: AgentState) -> Dict[str, Any]:
        """Mevcut bulgulara dayalı olarak savunma stratejisi önerir."""
        
        # Bulgu istatistikleri
        findings_summary = state.get_findings_summary()
        
        prompt = f"""
        Sen bir Savunma Stratejistisin. Bulgulara dayanarak potansiyel saldırı senaryolarını 
        ve savunma stratejilerini belirle.
        
        BULGULAR:
        - Toplam: {findings_summary['total']} bulgu
        - Kritik: {findings_summary['by_severity']['critical']}
        - Yüksek: {findings_summary['by_severity']['high']}
        - CVE'li: {findings_summary['with_cve']}
        
        TEKNOLOJİLER: {json.dumps(state.context_summary.get("technologies", [])[:10], indent=2)}
        AÇIK PORTLAR: {json.dumps(state.context_summary.get("open_ports", [])[:10], indent=2)}
        
        ANALİZ ET:
        1. En olası saldırı vektörleri neler?
        2. Hangi bulgular birleştirilerek daha büyük risk oluşturabilir?
        3. Öncelikli savunma noktaları nereler?
        
        ÇIKTI FORMATI:
        {{
          "threat_assessment": {{
            "overall_risk": "Düşük/Orta/Yüksek/Kritik",
            "main_attack_vectors": ["vektör1", "vektör2"],
            "likelihood": "Saldırı olasılığı değerlendirmesi"
          }},
          "defense_strategy": {{
            "immediate_focus": ["Hemen odaklanılması gerekenler"],
            "monitoring_points": ["İzlenmesi gereken noktalar"],
            "hardening_recommendations": ["Sistem sertleştirme önerileri"]
          }},
          "risk_matrix": {{
            "high_impact_high_probability": ["En riskli bulgular"],
            "high_impact_low_probability": ["Düşük olasılıklı ama yüksek etkili"],
            "quick_fixes": ["Kolay düzeltilebilir ama önemli"]
          }}
        }}
        """
        
        response = await self._call_gemini_json(prompt)
        return response

    def validate_plan_safety(self, plan: List[Dict[str, Any]]) -> tuple[bool, List[str]]:
        """Planın güvenliğini kontrol eder."""
        
        issues = []
        dangerous_patterns = {
            "rce": "Uzaktan kod çalıştırma riski",
            "privesc": "Yetki yükseltme riski",
            "postexploit": "Sömürü sonrası aktivite",
            "dump": "Veri çalma riski",
            "brute": "Kaba kuvvet saldırısı riski",
            "dos": "Hizmet reddi riski"
        }
        
        for step in plan:
            tool_name = step.get("tool", "").lower()
            goal = step.get("goal", "").lower()
            
            for pattern, risk in dangerous_patterns.items():
                if pattern in tool_name or pattern in goal:
                    issues.append(f"{step.get('tool')}: {risk}")
        
        is_safe = len(issues) == 0
        return is_safe, issues

    async def explain_plan_rationale(self, plan: List[Dict[str, Any]], state: AgentState) -> str:
        """Planın mantığını kullanıcıya açıklar."""
        
        prompt = f"""
        Aşağıdaki güvenlik test planını, teknik olmayan bir dille açıkla.
        
        HEDEF: {state.target}
        
        TEST PLANI:
        {json.dumps(plan, indent=2, ensure_ascii=False)}
        
        Açıklamanda şunları belirt:
        1. Planın genel stratejisi nedir?
        2. Her adım neden önemli?
        3. Adımlar arasındaki mantıksal bağlantı nedir?
        4. Bu plan neleri ortaya çıkaracak?
        5. Güvenlik açısından neden bu sıralama önemli?
        
        Açıklamayı paragraf formatında, akıcı bir dille yaz.
        """
        
        response = await self.model.generate_content_async(prompt)
        return response.text

    def get_plan_statistics(self, state: AgentState) -> Dict[str, Any]:
        """Plan istatistiklerini döndürür."""
        
        completed = [s for s in state.plan if s.get('status') == 'completed']
        pending = [s for s in state.plan if s.get('status') == 'pending']
        failed = [s for s in state.plan if s.get('status') == 'failed']
        
        # Tool kullanım dağılımı
        tool_usage = {}
        for step in state.plan:
            tool = step.get('tool', 'unknown')
            tool_usage[tool] = tool_usage.get(tool, 0) + 1
        
        # Kategori dağılımı
        category_distribution = {
            "reconnaissance": 0,
            "vulnerability_assessment": 0,
            "web_analysis": 0
        }
        
        for step in state.plan:
            tool_name = step.get('tool', '')
            if 'recon' in tool_name or 'enum' in tool_name:
                category_distribution['reconnaissance'] += 1
            elif 'vuln' in tool_name or 'verify' in tool_name:
                category_distribution['vulnerability_assessment'] += 1
            elif 'api' in tool_name or 'cloud' in tool_name:
                category_distribution['web_analysis'] += 1
        
        return {
            "total_steps": len(state.plan),
            "completed": len(completed),
            "pending": len(pending),
            "failed": len(failed),
            "success_rate": (len(completed) / len(state.plan) * 100) if state.plan else 0,
            "tool_usage": tool_usage,
            "category_distribution": category_distribution,
            "average_steps_per_phase": {
                "reconnaissance": category_distribution['reconnaissance'],
                "assessment": category_distribution['vulnerability_assessment'],
                "analysis": category_distribution['web_analysis']
            }
        }

    async def suggest_next_steps(self, state: AgentState) -> List[Dict[str, Any]]:
        """Test tamamlandıktan sonra yapılabilecek ek adımları önerir."""
        
        findings_summary = state.get_findings_summary()
        
        prompt = f"""
        Güvenlik testi tamamlandı. Elde edilen bulgulara göre ek test önerileri sun.
        
        TEST SONUÇLARI:
        - Toplam bulgu: {findings_summary['total']}
        - Kritik bulgu: {findings_summary['by_severity']['critical']}
        - CVE'li bulgu: {findings_summary['with_cve']}
        
        TESPİT EDİLEN TEKNOLOJİLER:
        {json.dumps(state.context_summary.get("technologies", [])[:10], indent=2)}
        
        Aşağıdaki alanlarda ek testler öner:
        1. Derinlemesine analiz gereken alanlar
        2. Manuel olarak kontrol edilmesi gereken noktalar
        3. Özelleştirilmiş testler
        
        ÇIKTI FORMATI:
        {{
          "manual_verification": [
            {{"area": "Kontrol alanı", "reason": "Neden gerekli", "method": "Nasıl yapılır"}}
          ],
          "deep_dive_areas": [
            {{"component": "Bileşen", "suggested_tests": ["test1", "test2"], "priority": "Yüksek/Orta/Düşük"}}
          ],
          "specialized_assessments": [
            {{"type": "Test tipi", "description": "Açıklama", "required_expertise": "Gerekli uzmanlık"}}
          ]
        }}
        """
        
        response = await self._call_gemini_json(prompt)
        return response

    def create_fallback_plan(self, target: str) -> List[Dict[str, Any]]:
        """API hatası durumunda kullanılacak varsayılan plan."""
        
        base_domain = target.replace("http://", "").replace("https://", "").split("/")[0]
        
        return [
            {
                "goal": "Web teknolojilerini tespit et",
                "tool": "enum_tech_detector",
                "params": {"target": f"https://{base_domain}"}
            },
            {
                "goal": "Subdomain keşfi yap",
                "tool": "recon_passive_subfinder",
                "params": {"domain": base_domain}
            },
            {
                "goal": "Port taraması gerçekleştir",
                "tool": "enum_port_scanner",
                "params": {"target": base_domain, "profile": "default"}
            },
            {
                "goal": "HTTP güvenlik başlıklarını analiz et",
                "tool": "vuln_http_header_analyzer",
                "params": {"target": f"https://{base_domain}"}
            },
            {
                "goal": "Web crawler ile sayfa keşfi yap",
                "tool": "enum_web_crawler",
                "params": {"target": f"https://{base_domain}"}
            },
            {
                "goal": "API endpoint'lerini keşfet",
                "tool": "api_enum_endpoints",
                "params": {"target": f"https://{base_domain}"}
            }
        ]

    def prioritize_tools_by_findings(self, state: AgentState) -> List[str]:
        """Mevcut bulgulara göre öncelikli araçları belirler."""
        
        priority_tools = []
        
        # Teknoloji bazlı önceliklendirme
        technologies = state.context_summary.get("technologies", [])
        tech_names = [t.get("name", "").lower() if isinstance(t, dict) else str(t).lower() for t in technologies]
        
        # WordPress varsa
        if any("wordpress" in tech for tech in tech_names):
            priority_tools.extend(["vuln_dependency_scanner", "enum_directory_bruteforce"])
        
        # API teknolojileri varsa
        if any(tech in str(technologies) for tech in ["REST", "GraphQL", "API"]):
            priority_tools.extend(["api_vuln_idor_scanner", "api_vuln_jwt_tester"])
        
        # Eski versiyon varsa dependency scanner öner
        for finding in state.findings:
            if "eski" in finding.get("title", "").lower() or "outdated" in finding.get("title", "").lower():
                priority_tools.append("vuln_dependency_scanner")
                break
        
        # Açık portlara göre
        open_ports = state.context_summary.get("open_ports", [])
        port_numbers = []
        for port in open_ports:
            if isinstance(port, dict):
                port_numbers.append(port.get("port", 0))
            else:
                port_numbers.append(port)
        
        if 443 in port_numbers or 8443 in port_numbers:
            priority_tools.append("vuln_http_header_analyzer")
        
        return list(set(priority_tools))  # Duplicateleri kaldır

    def estimate_plan_duration(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Planın tahmini süresini hesaplar."""
        
        # Tool başına tahmini süreler (saniye)
        tool_durations = {
            "enum_port_scanner": 30,
            "enum_tech_detector": 5,
            "recon_passive_subfinder": 20,
            "enum_web_crawler": 45,
            "vuln_http_header_analyzer": 3,
            "vuln_xss_detector": 60,
            "verify_sqli": 60,
            "api_enum_endpoints": 30,
            "enum_directory_bruteforce": 120,
            "default": 15
        }
        
        total_seconds = 0
        for step in plan:
            tool = step.get("tool", "")
            duration = tool_durations.get(tool, tool_durations["default"])
            total_seconds += duration
        
        # Paralel çalışma ve network gecikmesi faktörü
        estimated_seconds = total_seconds * 0.7  # %30 paralel kazanç
        
        return {
            "estimated_seconds": int(estimated_seconds),
            "estimated_minutes": round(estimated_seconds / 60, 1),
            "per_step_average": round(estimated_seconds / len(plan), 1) if plan else 0,
            "confidence": "Orta",
            "factors": [
                "Network hızı",
                "Hedef sistemin yanıt süresi", 
                "Tool'ların paralel çalışma kabiliyeti"
            ]
        }

    async def suggest_next_steps(self, state: AgentState) -> List[Dict[str, Any]]:
        """Test tamamlandıktan sonra yapılabilecek ek adımları önerir."""
        
        findings_summary = state.get_findings_summary()
        
        prompt = f"""
        Güvenlik testi tamamlandı. Elde edilen bulgulara göre ek test önerileri sun.
        
        TEST SONUÇLARI:
        - Toplam bulgu: {findings_summary['total']}
        - Kritik bulgu: {findings_summary['by_severity']['critical']}
        - CVE'li bulgu: {findings_summary['with_cve']}
        
        TESPİT EDİLEN TEKNOLOJİLER:
        {json.dumps(state.context_summary.get("technologies", [])[:10], indent=2)}
        
        Aşağıdaki alanlarda ek testler öner:
        1. Derinlemesine analiz gereken alanlar
        2. Manuel olarak kontrol edilmesi gereken noktalar
        3. Özelleştirilmiş testler
        
        ÇIKTI FORMATI:
        {{
          "manual_verification": [
            {{"area": "Kontrol alanı", "reason": "Neden gerekli", "method": "Nasıl yapılır"}}
          ],
          "deep_dive_areas": [
            {{"component": "Bileşen", "suggested_tests": ["test1", "test2"], "priority": "Yüksek/Orta/Düşük"}}
          ],
          "specialized_assessments": [
            {{"type": "Test tipi", "description": "Açıklama", "required_expertise": "Gerekli uzmanlık"}}
          ]
        }}
        """
        
        response = await self._call_gemini_json(prompt)
        return response

    async def create_testing_checklist(self, state: AgentState) -> Dict[str, Any]:
        """Bulgulara dayalı güvenlik kontrol listesi oluşturur."""
        
        # En yaygın zafiyet türlerini belirle
        vuln_types = {}
        for finding in state.findings:
            vuln_type = self._categorize_vulnerability(finding)
            vuln_types[vuln_type] = vuln_types.get(vuln_type, 0) + 1
        
        prompt = f"""
        Tespit edilen zafiyet türlerine göre detaylı bir güvenlik kontrol listesi oluştur.
        
        HEDEF: {state.target}
        
        ZAFİYET TÜRLERİ:
        {json.dumps(vuln_types, indent=2)}
        
        BULGU SAYISI: {len(state.findings)}
        
        Her zafiyet türü için:
        1. Kontrol edilecek noktalar
        2. Test metodolojisi
        3. Beklenen sonuçlar
        4. Düzeltme doğrulama yöntemi
        
        ÇIKTI FORMATI:
        {{
          "security_checklist": [
            {{
              "category": "Zafiyet kategorisi",
              "checks": [
                {{
                  "item": "Kontrol edilecek nokta",
                  "how_to_check": "Nasıl kontrol edilir",
                  "expected_secure": "Güvenli durumda beklenen",
                  "remediation_verification": "Düzeltme nasıl doğrulanır"
                }}
              ],
              "priority": "Yüksek/Orta/Düşük"
            }}
          ],
          "testing_methodology": {{
            "approach": "Test yaklaşımı",
            "tools_required": ["Gerekli araçlar"],
            "estimated_time": "Tahmini süre"
          }},
          "compliance_mapping": {{
            "owasp_top_10": ["İlgili OWASP kategorileri"],
            "cis_controls": ["İlgili CIS kontrolleri"]
          }}
        }}
        """
        
        response = await self._call_gemini_json(prompt)
        return response

    def _categorize_vulnerability(self, finding: Dict[str, Any]) -> str:
        """Bulguyu kategorize eder."""
        
        title = finding.get("title", "").lower()
        desc = finding.get("description", "").lower()
        combined = title + " " + desc
        
        categories = {
            "injection": ["sql", "injection", "sqli", "database"],
            "broken_auth": ["authentication", "session", "jwt", "login"],
            "sensitive_exposure": ["exposure", "leak", "disclosure", "sensitive"],
            "xxe": ["xxe", "xml", "entity"],
            "broken_access": ["idor", "access", "authorization"],
            "misconfig": ["misconfiguration", "header", "cors", "default"],
            "xss": ["xss", "cross-site", "scripting"],
            "deserialization": ["deserialization", "pickle", "unserialize"],
            "components": ["vulnerable", "outdated", "cve", "version"],
            "logging": ["logging", "monitoring", "audit"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in combined for keyword in keywords):
                return category
        
        return "other"

    async def generate_learning_opportunities(self, state: AgentState) -> str:
        """Test sonuçlarından öğrenme fırsatları çıkarır."""
        
        # En sık görülen zafiyet türleri
        vuln_categories = {}
        for finding in state.findings:
            category = self._categorize_vulnerability(finding)
            vuln_categories[category] = vuln_categories.get(category, 0) + 1
        
        # En çok kullanılan araçlar
        tool_usage = {}
        for step in state.completed_steps:
            tool = step.get("step_details", {}).get("tool", "unknown")
            tool_usage[tool] = tool_usage.get(tool, 0) + 1
        
        prompt = f"""
        Bu güvenlik testinden çıkarılacak öğrenme noktalarını belirle.
        
        TEST İN SONUÇLARI:
        - Bulgu sayısı: {len(state.findings)}
        - En yaygın zafiyet türleri: {json.dumps(vuln_categories, indent=2)}
        - Kullanılan araçlar: {json.dumps(list(tool_usage.keys()), indent=2)}
        
        Şu başlıklarda öğrenme fırsatları sun:
        1. Teknik beceri geliştirme alanları
        2. Güvenlik best practice'leri
        3. Tool kullanım ipuçları
        4. Gelecek testler için öneriler
        
        Eğitici ve geliştirici bir dil kullan.
        """
        
        response = await self.model.generate_content_async(prompt)
        return response.text

    def optimize_future_plans(self, state: AgentState) -> Dict[str, Any]:
        """Gelecek testler için plan optimizasyonu önerir."""
        
        # Başarılı ve başarısız adımları analiz et
        successful_tools = []
        failed_tools = []
        
        for step in state.completed_steps:
            tool = step.get("step_details", {}).get("tool")
            if step.get("result", {}).get("success"):
                successful_tools.append(tool)
            else:
                failed_tools.append(tool)
        
        # Tool verimliliğini hesapla
        tool_effectiveness = {}
        for step in state.completed_steps:
            tool = step.get("step_details", {}).get("tool")
            if tool and step.get("result", {}).get("success"):
                # Bu tool kaç bulgu üretti?
                findings_after = len([f for f in state.findings 
                                    if f.get("detected_by_tool") == tool])
                tool_effectiveness[tool] = findings_after
        
        return {
            "optimization_insights": {
                "most_effective_tools": sorted(tool_effectiveness.items(), 
                                             key=lambda x: x[1], reverse=True)[:5],
                "failed_tools": list(set(failed_tools)),
                "success_rate_by_category": self._calculate_category_success_rates(state),
                "recommended_tool_order": self._suggest_optimal_order(tool_effectiveness),
                "time_optimization_tips": [
                    "En etkili araçlarla başlayın",
                    "Paralel çalışabilen araçları gruplandırın",
                    "Başarısız olan araçlar için alternatif yaklaşımlar deneyin"
                ]
            },
            "pattern_recognition": {
                "common_vulnerabilities": self._identify_patterns(state),
                "technology_correlations": self._find_tech_correlations(state)
            }
        }

    def _calculate_category_success_rates(self, state: AgentState) -> Dict[str, float]:
        """Kategori bazında başarı oranlarını hesaplar."""
        
        category_stats = {
            "reconnaissance": {"total": 0, "successful": 0},
            "vulnerability_assessment": {"total": 0, "successful": 0},
            "web_analysis": {"total": 0, "successful": 0}
        }
        
        for step in state.completed_steps:
            tool = step.get("step_details", {}).get("tool", "")
            success = step.get("result", {}).get("success", False)
            
            # Kategoriye göre sınıflandır
            if "recon" in tool or "enum" in tool:
                category = "reconnaissance"
            elif "vuln" in tool or "verify" in tool:
                category = "vulnerability_assessment"
            elif "api" in tool or "cloud" in tool:
                category = "web_analysis"
            else:
                continue
            
            category_stats[category]["total"] += 1
            if success:
                category_stats[category]["successful"] += 1
        
        # Başarı oranlarını hesapla
        success_rates = {}
        for category, stats in category_stats.items():
            if stats["total"] > 0:
                rate = (stats["successful"] / stats["total"]) * 100
                success_rates[category] = round(rate, 1)
            else:
                success_rates[category] = 0.0
        
        return success_rates

    def _suggest_optimal_order(self, tool_effectiveness: Dict[str, int]) -> List[str]:
        """En optimal araç sırasını önerir."""
        
        # Temel araçlar her zaman önce
        essential_order = [
            "enum_tech_detector",
            "recon_passive_subfinder",
            "enum_port_scanner"
        ]
        
        # Etkili araçları ekle
        effective_tools = [tool for tool, _ in sorted(tool_effectiveness.items(), 
                                                     key=lambda x: x[1], reverse=True)
                          if tool not in essential_order]
        
        return essential_order + effective_tools[:7]  # İlk 10 araç

        def _identify_patterns(self, state: AgentState) -> List[str]:
         """Bulgulardaki kalıpları tespit eder."""
        
        patterns = []
        
        # Teknoloji bazlı kalıplar
        tech_vulns = {}
        for finding in state.findings:
            if tech_context := finding.get("technology_context"):
                for tech in tech_context:
                    if tech not in tech_vulns:
                        tech_vulns[tech] = []
                    tech_vulns[tech].append(finding.get("severity", ""))
        
        # En sorunlu teknolojiler
        for tech, severities in tech_vulns.items():
            critical_count = sum(1 for s in severities if "kritik" in s.lower() or "critical" in s.lower())
            if critical_count > 0:
                patterns.append(f"{tech} teknolojisinde {critical_count} kritik zafiyet mevcut")
        
        # Yaygın zafiyet türleri
        vuln_types = {}
        for finding in state.findings:
            vuln_type = self._categorize_vulnerability(finding)
            vuln_types[vuln_type] = vuln_types.get(vuln_type, 0) + 1
        
        most_common = sorted(vuln_types.items(), key=lambda x: x[1], reverse=True)[:3]
        for vuln_type, count in most_common:
            if count > 2:
                patterns.append(f"{vuln_type} türünde {count} zafiyet tespit edildi")
        
        # Port bazlı kalıplar
        port_findings = {}
        for finding in state.findings:
            component = finding.get("affected_component", "")
            if any(str(port) in component for port in range(1, 65536)):
                # Port numarası içeren component
                for port in range(1, 65536):
                    if str(port) in component:
                        port_findings[port] = port_findings.get(port, 0) + 1
        
        for port, count in port_findings.items():
            if count >= 2:
                patterns.append(f"Port {port} üzerinde {count} farklı zafiyet tespit edildi")
        
        return patterns

    def _find_tech_correlations(self, state: AgentState) -> Dict[str, List[str]]:
        """Teknolojiler arası korelasyonları bulur."""
        
        correlations = {}
        technologies = state.context_summary.get("technologies", [])
        
        # Teknoloji isimleri normalize et
        tech_names = []
        for tech in technologies:
            if isinstance(tech, dict):
                name = tech.get("name", "")
                version = tech.get("version", "")
                tech_names.append(f"{name} {version}".strip())
            else:
                tech_names.append(str(tech))
        
        # Bilinen teknoloji kombinasyonları ve riskleri
        known_combinations = {
            ("PHP", "MySQL"): ["SQL Injection riski", "Session yönetimi zafiyetleri"],
            ("WordPress", "PHP"): ["Plugin zafiyetleri", "Theme güvenlik sorunları"],
            ("Apache", "PHP"): ["Konfigürasyon hataları", ".htaccess bypass riskleri"],
            ("Node.js", "MongoDB"): ["NoSQL Injection", "Prototype pollution"],
            ("Angular", "REST API"): ["CORS yanlış yapılandırması", "JWT güvenlik sorunları"],
            ("React", "GraphQL"): ["Query depth limiti eksikliği", "Information disclosure"]
        }
        
        # Mevcut teknolojilerde kombinasyonları kontrol et
        for combo, risks in known_combinations.items():
            if all(any(tech_part.lower() in tech_name.lower() 
                      for tech_name in tech_names) 
                  for tech_part in combo):
                correlation_key = " + ".join(combo)
                correlations[correlation_key] = risks
        
        return correlations

    async def generate_testing_timeline(self, state: AgentState) -> Dict[str, Any]:
        """Test için detaylı zaman çizelgesi oluşturur."""
        
        # Tamamlanan adımların gerçek süreleri
        actual_durations = []
        for step in state.completed_steps:
            if exec_time := step.get("execution_time"):
                actual_durations.append({
                    "tool": step.get("step_details", {}).get("tool"),
                    "duration": exec_time
                })
        
        prompt = f"""
        Güvenlik testi zaman analizi yap.
        
        TAMAMLANAN ADIMLAR:
        {json.dumps(actual_durations, indent=2)}
        
        TOPLAM TEST SÜRE: {state.execution_time} saniye
        BULGU SAYISI: {len(state.findings)}
        
        Analiz et:
        1. Hangi aşamalar en çok zaman aldı?
        2. Zaman verimliliği nasıl artırılabilir?
        3. Optimal test süresi ne olmalı?
        
        ÇIKTI FORMATI:
        {{
          "time_analysis": {{
            "total_time": "Toplam süre",
            "average_per_step": "Adım başına ortalama",
            "longest_steps": ["En uzun süren adımlar"],
            "time_distribution": {{"reconnaissance": "x%", "assessment": "y%", "analysis": "z%"}}
          }},
          "efficiency_metrics": {{
            "findings_per_minute": "Dakika başına bulgu",
            "tool_efficiency": {{"tool_name": "süre/bulgu oranı"}},
            "bottlenecks": ["Darboğaz noktaları"]
          }},
          "optimization_suggestions": [
            "Zaman tasarrufu önerisi 1",
            "Zaman tasarrufu önerisi 2"
          ]
        }}
        """
        
        response = await self._call_gemini_json(prompt)
        return response

    def generate_plan_summary(self, state: AgentState) -> Dict[str, Any]:
        """Plan ve sonuçların özetini oluşturur."""
        
        # Başarılı ve başarısız adımları say
        successful_steps = sum(1 for s in state.plan if s.get('status') == 'completed')
        failed_steps = sum(1 for s in state.plan if s.get('status') == 'failed')
        
        # En etkili araçları bul
        tool_findings = {}
        for finding in state.findings:
            tool = finding.get("detected_by_tool", "unknown")
            tool_findings[tool] = tool_findings.get(tool, 0) + 1
        
        most_productive = sorted(tool_findings.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            "execution_summary": {
                "planned_steps": len(state.plan),
                "executed_steps": successful_steps + failed_steps,
                "successful_steps": successful_steps,
                "failed_steps": failed_steps,
                "skipped_steps": sum(1 for s in state.plan if s.get('status') == 'pending'),
                "success_rate": (successful_steps / len(state.plan) * 100) if state.plan else 0
            },
            "productivity_metrics": {
                "total_findings": len(state.findings),
                "findings_per_step": len(state.findings) / successful_steps if successful_steps > 0 else 0,
                "most_productive_tools": [
                    {"tool": tool, "findings": count} for tool, count in most_productive
                ],
                "critical_findings_ratio": sum(1 for f in state.findings if "kritik" in f.get("severity", "").lower()) / len(state.findings) if state.findings else 0
            },
            "plan_effectiveness": {
                "coverage": self._calculate_coverage(state),
                "depth": self._calculate_test_depth(state),
                "quality_score": self._calculate_plan_quality(state)
            }
        }

    def _calculate_coverage(self, state: AgentState) -> str:
        """Test kapsamını değerlendirir."""
        
        covered_areas = set()
        
        for step in state.completed_steps:
            tool = step.get("step_details", {}).get("tool", "")
            if "port" in tool:
                covered_areas.add("network")
            elif "tech" in tool or "enum" in tool:
                covered_areas.add("technology")
            elif "vuln" in tool:
                covered_areas.add("vulnerability")
            elif "api" in tool:
                covered_areas.add("api")
            elif "dns" in tool or "subdomain" in tool:
                covered_areas.add("infrastructure")
        
        coverage_percentage = (len(covered_areas) / 5) * 100  # 5 ana alan
        
        if coverage_percentage >= 80:
            return "Kapsamlı"
        elif coverage_percentage >= 60:
            return "İyi"
        elif coverage_percentage >= 40:
            return "Orta"
        else:
            return "Sınırlı"

    def _calculate_test_depth(self, state: AgentState) -> str:
        """Test derinliğini değerlendirir."""
        
        depth_indicators = 0
        
        # Farklı zafiyet türleri
        vuln_types = set()
        for finding in state.findings:
            vuln_types.add(self._categorize_vulnerability(finding))
        
        depth_indicators += len(vuln_types)
        
        # CVE'li bulgular
        cve_findings = sum(1 for f in state.findings if f.get("cve_id"))
        depth_indicators += min(cve_findings, 5)  # Max 5 puan
        
        # Farklı severity seviyeleri
        severities = set(f.get("severity", "").lower() for f in state.findings)
        depth_indicators += len(severities)
        
        if depth_indicators >= 12:
            return "Çok Derin"
        elif depth_indicators >= 8:
            return "Derin"
        elif depth_indicators >= 5:
            return "Orta"
        else:
            return "Yüzeysel"

    def _calculate_plan_quality(self, state: AgentState) -> float:
        """Plan kalitesini hesaplar (0-100)."""
        
        quality_score = 0.0
        
        # Başarı oranı (max 30 puan)
        if state.plan:
            success_rate = sum(1 for s in state.plan if s.get('status') == 'completed') / len(state.plan)
            quality_score += success_rate * 30
        
        # Bulgu/adım oranı (max 25 puan)
        if state.completed_steps:
            findings_ratio = min(len(state.findings) / len(state.completed_steps), 1.0)
            quality_score += findings_ratio * 25
        
        # Kritik bulgu varlığı (max 20 puan)
        critical_findings = sum(1 for f in state.findings if "kritik" in f.get("severity", "").lower())
        quality_score += min(critical_findings * 10, 20)
        
        # Kapsam genişliği (max 15 puan)
        coverage = self._calculate_coverage(state)
        coverage_scores = {"Kapsamlı": 15, "İyi": 10, "Orta": 5, "Sınırlı": 2}
        quality_score += coverage_scores.get(coverage, 0)
        
        # Plan adaptasyonu (max 10 puan)
        adaptations = len([s for s in state.plan if s.get("adapted", False)])
        quality_score += min(adaptations * 5, 10)
        
        return round(min(quality_score, 100), 1)