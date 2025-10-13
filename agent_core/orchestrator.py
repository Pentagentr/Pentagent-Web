# agent_core/orchestrator.py

import asyncio
from model_wrapper import UnifiedLLM
from typing import Callable, Optional, Dict, Any
from datetime import datetime
from config import config
from mcp_server.enhanced_mcp_tools import enhanced_mcp_server
from agent_core.state import AgentState
from agent_core.planner import Planner
from agent_core.executor import Executor
from agent_core.analyzer import Analyzer  # YENİ

class AgentOrchestrator:
    """Dinamik karar verme sistemi - her tool çıktısına göre sonraki adım belirleme"""
    
    def __init__(self, api_key: str, status_callback: Optional[Callable] = None):
        self.status_callback = status_callback or self._default_status_callback
        # Ignore api_key (legacy). Use UnifiedLLM which reads env vars (GROQ).
        self.model = UnifiedLLM()
        self.mcp_server = enhanced_mcp_server
        self.planner = Planner(self.model, self.mcp_server, self.status_callback)
        self.executor = Executor(self.model, self.mcp_server, self.status_callback)
        self.analyzer = Analyzer(self.model, self.status_callback)
        
        # Dinamik state management
        self.current_target = None
        self.user_task = None
        self.scan_context = {}
        self.execution_history = []
        self.discovered_information = {}
        self.max_steps = 15

    def _default_status_callback(self, message: str, status_type: str):
        """Varsayılan status callback"""
        print(f"[{status_type.upper()}] {message}")

    async def run_autonomous_pentest(self, target: str, user_task: str):
        """Planner-Executor-Analyzer mimarisini kullanarak otonom pentest gerçekleştirir."""
        # Ajan durumunu başlat
        state = AgentState(target, user_task or "Kapsamlı ve güvenli güvenlik değerlendirmesi")
        
        await self.status_callback(f"🚀 Akıllı Güvenlik Değerlendirmesi Başlatılıyor: {target}", "system")
        await self.status_callback(f"📋 Görev: {state.user_task}", "info")
        
        # Hedef tipine göre dinamik teknik açıklama
        target_type = "domain" if '.' in target and not target.replace('.', '').isdigit() else "IP adresi" if target.replace('.', '').isdigit() else "URL"
        
        if target_type == "domain":
            await self.status_callback("🎯 HEDEF ANALİZİ: Domain tabanlı sistem tespit edildi", "ai_thinking")
            await self.status_callback("🔍 STRATEJİK YAKLAŞIM: OSINT → Subdomain Enumeration → Service Discovery → Vulnerability Assessment", "ai_reasoning")
            await self.status_callback("⚙️ TEKNİK DETAYLAR: DNS kayıtları, Certificate Transparency, Passive DNS, Port scanning", "ai_reasoning")
        elif target_type == "IP adresi":
            await self.status_callback("🎯 HEDEF ANALİZİ: IP adresi tabanlı sistem tespit edildi", "ai_thinking")
            await self.status_callback("🔍 STRATEJİK YAKLAŞIM: Port Scanning → Service Fingerprinting → Vulnerability Mapping", "ai_reasoning")
            await self.status_callback("⚙️ TEKNİK DETAYLAR: SYN scan, Banner grabbing, Service enumeration, CVE lookup", "ai_reasoning")
        else:
            await self.status_callback("🎯 HEDEF ANALİZİ: URL tabanlı web uygulaması tespit edildi", "ai_thinking")
            await self.status_callback("🔍 STRATEJİK YAKLAŞIM: Technology Detection → OWASP Testing → Security Headers Analysis", "ai_reasoning")
            await self.status_callback("⚙️ TEKNİK DETAYLAR: Framework detection, SQL injection, XSS, CSRF, Authentication bypass", "ai_reasoning")

        # İlk planı oluştur
        await self.status_callback("🧠 DERİNLEMESİNE HEDEF ANALİZİ BAŞLIYOR...", "ai_thinking")
        
        initial_plan = await self.planner.create_initial_plan(state)
        
        if not initial_plan:
            await self.status_callback("❌ Planner başlangıç planı oluşturamadı", "error")
            return state

        # Planı duruma ekle
        state.plan = [dict(step, status='pending') for step in initial_plan]
        state.total_steps = len(state.plan)
        
        await self.status_callback(f"📊 Başlangıç Planı Oluşturuldu ({len(state.plan)} adım)", "ai_plan")
        
        # Plan detaylarını göster
        await self.status_callback("📋 Oluşturulan Plan:", "ai_reasoning")
        for i, step in enumerate(state.plan[:3], 1):  # İlk 3 adımı göster
            await self.status_callback(f"   {i}. {step['goal']} ({step['tool']})", "ai_reasoning")
        if len(state.plan) > 3:
            await self.status_callback(f"   ... ve {len(state.plan) - 3} adım daha", "ai_reasoning")
        
        # Ana döngü: Planı adım adım uygula
        step_count = 0
        while any(step['status'] == 'pending' for step in state.plan):
            step_count += 1
            
            # Sıradaki adımı al
            current_step = next(step for step in state.plan if step['status'] == 'pending')
            
            await self.status_callback(f"🔄 Adım {step_count}/{state.total_steps}: {current_step['goal']}", "info")
            await self.status_callback(f"🔧 Araç Seçimi: {current_step['tool']}", "ai_reasoning")
            await self.status_callback(f"💭 Bu Araçla Ne Yapacağım: {current_step['goal']}", "ai_reasoning")
            
            # Kullanıcı görevine göre dinamik amaç açıklaması
            user_task = state.user_task.lower()
            if "port" in user_task:
                await self.status_callback(f"🎯 Bu Adımın Amacı: Kullanıcı port taraması istediği için bu araçla açık portları tespit edeceğim", "ai_reasoning")
            elif "sql" in user_task or "injection" in user_task:
                await self.status_callback(f"🎯 Bu Adımın Amacı: Kullanıcı SQL injection testi istediği için database teknolojilerini tespit edeceğim", "ai_reasoning")
            elif "xss" in user_task:
                await self.status_callback(f"🎯 Bu Adımın Amacı: Kullanıcı XSS testi istediği için web teknolojilerini tespit edeceğim", "ai_reasoning")
            elif "api" in user_task:
                await self.status_callback(f"🎯 Bu Adımın Amacı: Kullanıcı API testi istediği için API endpoint'lerini keşfedeceğim", "ai_reasoning")
            else:
                await self.status_callback(f"🎯 Bu Adımın Amacı: Bu araçla hedef hakkında daha fazla bilgi toplayacağım ve sonraki adımları planlayacağım", "ai_reasoning")
            
            # 1. UYGULA (Executor)
            result_data = await self.executor.run_step(current_step, state)
            
            # Sonucu duruma ekle
            state.add_completed_step(result_data)
            
            # Adım durumunu güncelle
            current_step['status'] = 'completed' if result_data['result'].get('success') else 'failed'
            
            # 2. ANALİZ ET (YENİ ADIM - Analyzer)
            next_action_suggestion = None
            if result_data['result'].get('success'):
                await self.status_callback("🔍 DERİNLEMESİNE SONUÇ ANALİZİ BAŞLIYOR...", "ai_thinking")
                
                # Sonuç detaylarını göster
                result_summary = result_data['result'].get('summary', 'Sonuç alındı')
                result_data_content = result_data['result'].get('data', {})
                await self.status_callback(f"📊 Ham Sonuç: {result_summary}", "ai_reasoning")
                await self.status_callback(f"🔍 Sonuç Detayları: {str(result_data_content)[:200]}...", "ai_reasoning")
                
                # Kullanıcı görevine göre dinamik analiz açıklaması
                if "port" in user_task:
                    await self.status_callback("💭 Port tarama sonuçlarını analiz edip, açık portlara göre sonraki adımları planlıyorum...", "ai_reasoning")
                elif "sql" in user_task or "injection" in user_task:
                    await self.status_callback("💭 Database teknolojilerini analiz edip, SQL injection testleri için sonraki adımları planlıyorum...", "ai_reasoning")
                elif "xss" in user_task:
                    await self.status_callback("💭 Web teknolojilerini analiz edip, XSS testleri için sonraki adımları planlıyorum...", "ai_reasoning")
                elif "api" in user_task:
                    await self.status_callback("💭 API endpoint'lerini analiz edip, API güvenlik testleri için sonraki adımları planlıyorum...", "ai_reasoning")
                else:
                    await self.status_callback("💭 Bu sonuçları analiz edip, bir sonraki adımı stratejik olarak planlıyorum...", "ai_reasoning")
                
                # Analyzer'dan bir sonraki adım için bir öneri alıyoruz
                next_action_suggestion = await self.analyzer.analyze_result(
                    current_step['tool'], 
                    result_data['result'], 
                    state
                )
                
                # Eğer Analyzer bir öneri döndürdüyse kullanıcıya bildir
                if next_action_suggestion:
                    await self.status_callback("💡 Analiz sonucuna göre yeni bir araç öneriyorum:", "ai_decision")
                    await self.status_callback(f"   🎯 Hedef: {next_action_suggestion.get('goal', 'Yeni aksiyon önerisi')}", "ai_reasoning")
                    await self.status_callback(f"   🔧 Araç: {next_action_suggestion.get('tool', 'Bilinmiyor')}", "ai_reasoning")
                    await self.status_callback(f"   💭 Mantık: {next_action_suggestion.get('reasoning', 'Sonuçlara göre mantıklı')}", "ai_reasoning")
            else:
                await self.status_callback(
                    f"⚠️ Araç başarısız oldu: {result_data['result'].get('error', 'Bilinmeyen hata')}", 
                    "warning"
                )

            # 3. UYARLA (Planner)
            remaining_steps = [s for s in state.plan if s['status'] == 'pending']
            
            # Adaptasyon koşulları:
            # - SADECE Analyzer yeni bir aksiyon öneriyorsa
            # - Veya plan tamamen bittiyse ama henüz yeterli bilgi toplanmadıysa
            # ÇOK SIK ADAPTASYON YAPMAYI ENGELLEMEK için step_count % kontrolünü kaldırdık
            should_adapt = (remaining_steps and next_action_suggestion is not None)
            
            if should_adapt:
                   await self.status_callback("🔄 STRATEJİK PLAN ADAPTASYONU BAŞLIYOR...", "ai_thinking")
                   await self.status_callback(f"📊 Mevcut Durum Analizi:", "ai_reasoning")
                   await self.status_callback(f"   ✅ Tamamlanan Adımlar: {len([s for s in state.plan if s['status'] == 'completed'])}", "ai_reasoning")
                   await self.status_callback(f"   ⏳ Bekleyen Adımlar: {len(remaining_steps)}", "ai_reasoning") 
                
                # Kullanıcı görevine göre dinamik adaptasyon açıklaması
            if "port" in user_task:
                    await self.status_callback(f"   🔄 Adaptasyon Sebebi: {'Port tarama sonuçlarına göre servis testleri ekleniyor' if next_action_suggestion else 'Periyodik güncelleme'}", "ai_reasoning")
            elif "sql" in user_task or "injection" in user_task:
                    await self.status_callback(f"   🔄 Adaptasyon Sebebi: {'Database teknolojilerine göre SQL injection testleri ekleniyor' if next_action_suggestion else 'Periyodik güncelleme'}", "ai_reasoning")
            elif "xss" in user_task:
                    await self.status_callback(f"   🔄 Adaptasyon Sebebi: {'Web teknolojilerine göre XSS testleri ekleniyor' if next_action_suggestion else 'Periyodik güncelleme'}", "ai_reasoning")
            elif "api" in user_task:
                    await self.status_callback(f"   🔄 Adaptasyon Sebebi: {'API endpointlerine göre güvenlik testleri ekleniyor' if next_action_suggestion else 'Periyodik güncelleme'}", "ai_reasoning")
            else:
                    await self.status_callback(f"   🔄 Adaptasyon Sebebi: {'Analyzer önerisi var' if next_action_suggestion else 'Periyodik güncelleme'}", "ai_reasoning")
                
            if next_action_suggestion:
                    await self.status_callback(f"💡 Analyzer'ın Detaylı Önerisi:", "ai_reasoning")
                    await self.status_callback(f"   🔧 Önerilen Araç: {next_action_suggestion.get('tool', 'Bilinmiyor')}", "ai_reasoning")
                    await self.status_callback(f"   🎯 Önerilen Hedef: {next_action_suggestion.get('goal', 'Bilinmiyor')}", "ai_reasoning")
                    await self.status_callback(f"   💭 Önerilen Mantık: {next_action_suggestion.get('reasoning', 'Bilinmiyor')}", "ai_reasoning")
                
                # Planner'a hem kalan adımları hem de Analyzer'ın önerisini gönderiyoruz
            adapted_plan_steps = await self.planner.adapt_plan(state, next_action_suggestion)
                
            if adapted_plan_steps:
                    # Tamamlanan adımları koru, yeni adımları ekle
                    completed_steps_in_plan = [s for s in state.plan if s['status'] != 'pending']
                    new_steps = [dict(s, status='pending') for s in adapted_plan_steps]
                    
                    # Mevcut bekleyen adımlarla karşılaştır
                    # Tamamen yeni adımlar ekle, tekrar etmeyenleri
                    # GÜÇLENDIRILMIŞ DUPLICATE KONTROLÜ: Sadece tool adına bak, aynı tool tekrar çağrılmasın
                    unique_new_steps = []
                    for new_step in new_steps:
                        is_duplicate = any(
                            existing['tool'] == new_step['tool']  # Sadece tool adı kontrolü
                            for existing in state.plan
                        )
                        if not is_duplicate:
                            unique_new_steps.append(new_step)
                        else:
                            # Debug için log
                            if self.status_callback:
                                await self.status_callback(f"⏭️ {new_step['tool']} zaten çalıştırıldı, atlanıyor", "info")
                    
                    if unique_new_steps:
                        state.plan = completed_steps_in_plan + unique_new_steps
                        state.total_steps = len(state.plan)
                        await self.status_callback(
                            f"✨ Plan güncellendi ({len(unique_new_steps)} yeni adım eklendi)", 
                            "success"
                        )
                    else:
                        # Eğer analyzer'ın önerisi zaten planda varsa, mevcut planla devam et
                        state.plan = completed_steps_in_plan + remaining_steps

        # Test tamamlandı
        await self.status_callback("🏁 Test Planı Tamamlandı! Final analiz yapılıyor...", "system")
        
        # Execution time hesapla
        state.execution_time = (datetime.now() - state.start_time).total_seconds()
        
        # Final analiz
        await self._perform_final_analysis(state)
        
        return state

    async def _perform_final_analysis(self, state: AgentState):
        """Test sonunda kapsamlı analiz yapar."""
        await self.status_callback("🔍 Final analiz ve korelasyon başlatılıyor...", "ai_thinking")
        
        # Bulguları ilişkilendir
        if hasattr(self.analyzer, 'correlate_findings'):
            correlation_result = await self.analyzer.correlate_findings(state)
            if correlation_result.get("attack_chains"):
                state.context_summary["attack_chains"] = correlation_result["attack_chains"]
                await self.status_callback(
                    f"🔗 {len(correlation_result['attack_chains'])} potansiyel saldırı zinciri tespit edildi", 
                    "ai_analysis"
                )
        
        # Bulgu istatistikleri
        findings_summary = state.get_findings_summary()
        await self.status_callback(f"📊 Toplam {findings_summary['total']} yapılandırılmış bulgu tespit edildi", "info")
        
        # Kritik bulgu uyarısı
        if findings_summary['by_severity']['critical'] > 0:
            await self.status_callback(
                f"🚨 {findings_summary['by_severity']['critical']} adet KRİTİK SEVİYE bulgu var!", 
                "critical_finding"
            )
        
        # CVE'li bulgular
        if findings_summary['with_cve'] > 0:
            await self.status_callback(
                f"🔍 {findings_summary['with_cve']} bulgu bilinen CVE numaralarına sahip", 
                "info"
            )
        
                # Teknoloji analizi
        if state.context_summary.get("technologies") and hasattr(self.analyzer, 'analyze_technology_stack'):
            tech_analysis = await self.analyzer.analyze_technology_stack(
                state.context_summary["technologies"], 
                state
            )
            if tech_analysis.get("vulnerable_components"):
                state.context_summary["vulnerable_technologies"] = tech_analysis["vulnerable_components"]
                await self.status_callback(
                    f"⚠️ {len(tech_analysis['vulnerable_components'])} zafiyet içeren teknoloji tespit edildi", 
                    "warning"
                )
        
        # Genel risk değerlendirmesi
        overall_risk = self._calculate_overall_risk(state)
        state.context_summary["overall_risk_level"] = overall_risk
        await self.status_callback(f"📊 Genel Risk Seviyesi: {overall_risk}", "ai_analysis")
        
        # Başarı oranı
        await self.status_callback(f"📈 Test Başarı Oranı: {state.success_rate:.1%}", "info")
        await self.status_callback(f"⏱️ Toplam Test Süresi: {state.execution_time:.1f} saniye", "info")
        
        # Öncelikli düzeltmeler
        if hasattr(self.analyzer, 'suggest_remediation_priority'):
            priority_remediations = await self.analyzer.suggest_remediation_priority(state)
            if priority_remediations:
                state.context_summary["priority_remediations"] = priority_remediations
                await self.status_callback(
                    f"🔧 {len(priority_remediations)} öncelikli düzeltme önerisi hazırlandı", 
                    "success"
                )

    def _calculate_overall_risk(self, state: AgentState) -> str:
        """Genel risk seviyesini hesapla"""
        findings_summary = state.get_findings_summary()
        
        # Kritik bulgu varsa
        if findings_summary['by_severity']['critical'] > 0:
            return "KRİTİK"
        
        # Yüksek riskli bulgu sayısı
        high_risk_count = findings_summary['by_severity']['high']
        
        if high_risk_count >= 3:
            return "YÜKSEK"
        elif high_risk_count >= 1:
            return "ORTA-YÜKSEK"
        
        # Orta riskli bulgu sayısı
        medium_risk_count = findings_summary['by_severity']['medium']
        
        if medium_risk_count >= 5:
            return "ORTA"
        elif medium_risk_count >= 1:
            return "DÜŞÜK-ORTA"
        
        # Düşük riskli bulgular
        if findings_summary['by_severity']['low'] > 0:
            return "DÜŞÜK"
        
        return "MİNİMAL"

    def get_execution_summary(self, state: AgentState) -> Dict[str, Any]:
        """Test çalıştırma özetini döndürür."""
        findings_summary = state.get_findings_summary()
        
        return {
            "target": state.target,
            "task": state.user_task,
            "scan_info": {
                "start_time": state.start_time.isoformat(),
                "duration_seconds": state.execution_time,
                "total_steps": state.total_steps,
                "completed_steps": len(state.completed_steps),
                "success_rate": state.success_rate
            },
            "findings_overview": {
                "total": findings_summary['total'],
                "by_severity": findings_summary['by_severity'],
                "with_cve": findings_summary['with_cve']
            },
            "attack_surface": {
                "open_ports": len(state.context_summary.get("open_ports", [])),
                "technologies": len(state.context_summary.get("technologies", [])),
                "subdomains": len(state.context_summary.get("subdomains", [])),
                "endpoints": len(state.context_summary.get("endpoints", []))
            },
            "risk_assessment": {
                "overall_risk": state.context_summary.get("overall_risk_level", "UNKNOWN"),
                "attack_chains": len(state.context_summary.get("attack_chains", [])),
                "vulnerable_technologies": len(state.context_summary.get("vulnerable_technologies", []))
            },
            "recommendations": {
                "priority_count": len(state.context_summary.get("priority_remediations", [])),
                "has_critical": findings_summary['by_severity']['critical'] > 0
            }
        }

    async def generate_executive_summary(self, state: AgentState) -> str:
        """Yöneticiler için özet oluştur"""
        if hasattr(self.analyzer, 'generate_executive_summary'):
            return await self.analyzer.generate_executive_summary(state)
        
        # Fallback özet
        findings_summary = state.get_findings_summary()
        risk_level = state.context_summary.get("overall_risk_level", "UNKNOWN")
        
        summary = f"""
        ## Yönetici Özeti
        
        **Hedef Sistem:** {state.target}
        **Test Tarihi:** {state.start_time.strftime('%Y-%m-%d')}
        **Genel Risk Seviyesi:** {risk_level}
        
        ### Bulgular
        - Toplam Bulgu Sayısı: {findings_summary['total']}
        - Kritik: {findings_summary['by_severity']['critical']}
        - Yüksek: {findings_summary['by_severity']['high']}
        - Orta: {findings_summary['by_severity']['medium']}
        - Düşük: {findings_summary['by_severity']['low']}
        
        ### Öneriler
        """
        
        if findings_summary['by_severity']['critical'] > 0:
            summary += "\n⚠️ **ACİL:** Kritik seviyedeki zafiyetler derhal giderilmelidir."
        
        if findings_summary['with_cve'] > 0:
            summary += f"\n📌 {findings_summary['with_cve']} adet bulgu için bilinen güvenlik yamaları mevcuttur."
        
        return summary

    async def export_findings_for_reporting(self, state: AgentState) -> Dict[str, Any]:
        """Bulguları raporlama için hazırla"""
        
        # Analyzer'ın export fonksiyonunu kullan
        if hasattr(self.analyzer, 'export_findings_for_report'):
            report_data = self.analyzer.export_findings_for_report(state)
        else:
            # Fallback
            report_data = {
                "scan_info": {
                    "target": state.target,
                    "scan_date": state.start_time.isoformat(),
                    "scan_duration": state.execution_time,
                    "total_findings": len(state.findings)
                },
                "detailed_findings": state.findings
            }
        
        # Ek bilgiler ekle
        report_data["scan_metadata"] = {
            "tool_version": "1.0.0",
            "scan_type": "Automated Vulnerability Assessment",
            "scan_mode": "Non-Intrusive",
            "ai_powered": True
        }
        
        return report_data

# Yardımcı fonksiyonlar
def create_orchestrator(api_key: str, status_callback: Optional[Callable] = None) -> AgentOrchestrator:
    """AgentOrchestrator instance'ı oluşturur"""
    return AgentOrchestrator(api_key, status_callback)

async def run_pentest(target: str, task: str, api_key: str, status_callback: Optional[Callable] = None):
    """Tek fonksiyon çağrısı ile pentest başlat"""
    orchestrator = create_orchestrator(api_key, status_callback)
    return await orchestrator.run_autonomous_pentest(target, task)