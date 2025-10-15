
"""
Dynamic Agent Orchestrator - Tamamen dinamik karar verme sistemi
Her tool çıktısına göre sonraki adım belirleme
"""

import asyncio
import json
import logging
import os
from typing import Callable, Optional, Dict, Any, List
from datetime import datetime
from config import config
from mcp_server.enhanced_mcp_tools import enhanced_mcp_server
from agent_core.state import AgentState
from agent_core.executor import Executor
from agent_core.analyzer import Analyzer

# Google Cloud SDK uyarılarını bastır
os.environ['GRPC_DNS_RESOLVER'] = 'native'
os.environ['GOOGLE_CLOUD_DISABLE_GRPC'] = 'true'

# Logging konfigürasyonu
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Google Cloud SDK loglarını bastır
logging.getLogger('google').setLevel(logging.WARNING)
logging.getLogger('grpc').setLevel(logging.WARNING)

class DynamicAgentOrchestrator:
    """Dinamik karar verme sistemi - her tool çıktısına göre sonraki adım belirleme"""
    
    def __init__(self, api_key: str, status_callback: Optional[Callable] = None):
        self.status_callback = status_callback or self._default_status_callback
        from model_wrapper import UnifiedLLM
        # Ignore legacy api_key; UnifiedLLM reads env (GROQ)
        self.model = UnifiedLLM()
        self.mcp_server = enhanced_mcp_server
        self.executor = Executor(self.model, self.mcp_server, self.status_callback)
        self.analyzer = Analyzer(self.model, self.status_callback)
        
        # Dinamik state management
        self.current_target = None
        self.user_task = None
        self.scan_context = {}
        self.execution_history = []
        self.discovered_information = {}
        self.max_steps = 10  # Maksimum limit
        self.min_steps = 3   # Minimum gereksinim
        self.suggested_steps = 3  # Varsayılan hedef - minimum ile aynı (gereksiz tool çağrılarını engelle)
        
        logger.info("🤖 Dynamic Agent Orchestrator initialized")
    
    async def _default_status_callback(self, message: str, message_type: str = "info"):
        """Varsayılan durum geri çağrısı"""
        print(f"[{message_type.upper()}] {message}")
    
    async def _send_no_target_response(self, user_query: str, status_callback):
        """Hedef belirtilmediğinde kısa ve profesyonel yanıt"""
        # Kısa bir yanıt oluştur (token tasarrufu)
        response = """Merhaba! Ben Pentagent AI, siber güvenlik uzmanı asistanınızım. 🛡️

Sizin için kapsamlı güvenlik taraması yapabilirim, ancak bir hedef belirtmeniz gerekiyor.

📋 Örnek kullanım:
• "example.com için zafiyet taraması yap"
• "https://mysite.com üzerinde SQL injection testi yap"
• "192.168.1.1 IP adresini tara"

Hangi hedefi taramak istersiniz?"""
        
        await status_callback(response, "ai_response")
        return None
    
    async def _send_invalid_target_response(self, target: str, error: str, status_callback):
        """
        Geçersiz hedef için AKILLI YANIT
        - Target yoksa: AI ile doğal sohbet + yönlendirme
        - Geçersiz target varsa: Hata mesajı
        """
        # AI ile doğal yanıt oluştur (target olmadan)
        try:
            if hasattr(self, 'model') and self.model:
                # Gemini'den kısa, zeki yanıt al
                casual_prompt = f"""Kullanıcı şunu yazdı: "{target}"

Sen bir AI siber güvenlik uzmanısın (Pentagent AI). Kullanıcı target vermeden mesaj attı.

GÖREV:
1. Kullanıcının mesajına KISA (max 2 cümle), ZEKİ, DOSTÇA cevap ver
2. Sonra kısa bir yönlendirme yap: "Ben bir AI pentest aracıyım, bana taramak için bir hedef ver"

ÖRNEK:
Kullanıcı: "selam"
Cevap: "Selam! Nasılsın? 👋 Ben Pentagent AI, siber güvenlik taramaları yapabilirim. Bana taramak için bir hedef (domain/URL/IP) verirsen, kapsamlı bir güvenlik analizi yapabilirim! 🛡️"

KURALLAR:
- KISA ve ÖZLÜ yaz (max 3-4 cümle)
- Teknik terimler KULLANMA (normal konuş)
- Emoji kullanabilirsin
- Hedef iste ama BASKICI OLMA

ŞİMDİ CEVAP VER:"""
                
                response_obj = await self.model.generate_content_async(casual_prompt)
                
                # Response string veya object olabilir
                if isinstance(response_obj, str):
                    ai_response = response_obj.strip()
                elif hasattr(response_obj, 'text'):
                    ai_response = response_obj.text.strip()
                elif hasattr(response_obj, 'get'):
                    ai_response = response_obj.get('text', '').strip()
                else:
                    ai_response = str(response_obj).strip()
                
                # AI yanıtı varsa kullan
                if ai_response and len(ai_response) > 10:
                    await status_callback(ai_response, "ai_response")
                    return None
        
        except Exception as e:
            logger.error(f"AI casual response error: {e}")
        
        # Fallback: Basit yanıt (AI çalışmazsa)
        fallback_response = f"""Merhaba! 👋

Ben Pentagent AI, siber güvenlik uzmanı asistanınızım. 

Bana taramak için bir hedef verirsen, kapsamlı güvenlik analizi yapabilirim:

📋 Örnek:
• "example.com tara"
• "https://mysite.com için zafiyet analizi"
• "192.168.1.1 port taraması"

Hangi hedefi taramak istersin?"""
        
        await status_callback(fallback_response, "ai_response")
        return None
    
    def _complete_tool_params(self, tool_name: str, params: dict, status_callback=None) -> dict:
        """Tool için eksik parametreleri akıllıca tamamla"""
        completed_params = params.copy()
        
        # 1. Temel parametreleri ekle
        if "target" not in completed_params and self.current_target:
            completed_params["target"] = self.current_target
        if "url" not in completed_params and self.current_target:
            completed_params["url"] = self.current_target
        if "domain" not in completed_params and self.current_target:
            completed_params["domain"] = self.current_target
        
        # 2. WHOIS tool için özel domain çıkarma
        if tool_name == "recon_whois_lookup":
            # Domain parametresi yoksa target'tan çıkar
            if "domain" not in completed_params:
                target = completed_params.get("target", self.current_target)
                if target:
                    # URL ise domain'i çıkar
                    if target.startswith(('http://', 'https://')):
                        from urllib.parse import urlparse
                        parsed = urlparse(target)
                        domain = parsed.netloc or parsed.path
                    else:
                        domain = target
                    
                    # Domain'den gereksiz kelimeleri temizle
                    # "renicames.com sitesini sql injection için değerlendir" -> "renicames.com"
                    import re
                    # Sadece domain pattern'ini al
                    domain_match = re.search(r'([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', domain)
                    if domain_match:
                        domain = domain_match.group(1)
                    else:
                        # Pattern bulunamazsa ilk kelimeyi al
                        domain = domain.split()[0] if ' ' in domain else domain
                    
                    # www. kaldır
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    
                    # Port numarasını kaldır (:8080 gibi)
                    if ':' in domain:
                        domain = domain.split(':')[0]
                    
                    completed_params["domain"] = domain.strip('/')
                    logger.info(f"✨ WHOIS için domain çıkarıldı: {domain}")
        
        # 3. Zafiyet test tool'ları için özel parametreler
        vulnerability_tools = ["verify_xss", "verify_sqli", "verify_lfi"]
        if tool_name in vulnerability_tools:
            # Parameter eksikse context'ten veya varsayılan değerden al
            if "parameter" not in completed_params:
                # Context'te bulunan parametreler varsa kullan
                discovered_params = self.discovered_information.get("parameters", [])
                if discovered_params:
                    completed_params["parameter"] = discovered_params[0]
                    logger.info(f"✨ '{tool_name}' için context'ten parameter eklendi: {discovered_params[0]}")
                else:
                    # Varsayılan yaygın parametre isimleri
                    default_params = {
                        "verify_xss": "search",
                        "verify_sqli": "id",
                        "verify_lfi": "file"
                    }
                    completed_params["parameter"] = default_params.get(tool_name, "id")
                    logger.warning(f"⚠️ '{tool_name}' için varsayılan parameter kullanıldı: {completed_params['parameter']}")
                    logger.warning(f"💡 Önce enum_web_crawler ile parametreleri keşfetmelisin!")
            
            # Method yoksa GET ekle
            if "method" not in completed_params:
                completed_params["method"] = "GET"
        
        # 3. Web crawler için özel parametreler
        if tool_name == "enum_web_crawler":
            if "max_depth" not in completed_params:
                completed_params["max_depth"] = 3
        
        # 4. Port scanner için özel parametreler
        if tool_name == "enum_port_scanner":
            if "profile" not in completed_params:
                completed_params["profile"] = "quick"
        
        # 5. Tech detector için özel parametreler
        if tool_name == "enum_tech_detector":
            if "scan_type" not in completed_params:
                completed_params["scan_type"] = "quick"
        
        return completed_params
    
    async def _stream_ai_thinking(self, message: str, status_callback, reasoning: str = None):
        """AI düşünce sürecini kısa ve öz göster"""
        # Sadece ana mesajı göster
        await status_callback(f"🧠 {message}", "ai_thinking")
        
        # Kısa bekleme
        await asyncio.sleep(0.2)
        
        # Sadece önemli analiz varsa göster
        if reasoning and len(reasoning) < 100:
            await status_callback(f"🔍 {reasoning}", "ai_reasoning")
            await asyncio.sleep(0.1)

    async def _display_tool_results(self, tool_name: str, result: dict, status_callback):
        """Tool sonuçlarını TEK MESAJDA detaylı ve anlaşılır şekilde göster"""
        try:
            data = result.get("data", {})
            ai_summary = result.get("ai_summary", "")
            
            # TEK MESAJ İÇİN BUFFER
            output_lines = []
            
            # AI Summary varsa ekle
            if ai_summary:
                output_lines.append(f"📊 AI Analizi: {ai_summary}")
            
            # Tool'a özel sonuç gösterimi
            if tool_name == "enum_port_scanner":
                open_ports = data.get("open_ports", [])
                if open_ports:
                    ports_str = ", ".join([str(p) for p in open_ports[:10]])
                    output_lines.append(f"  🔓 Açık Portlar: {ports_str}")
                    if len(open_ports) > 10:
                        output_lines.append(f"      ... ve {len(open_ports) - 10} port daha")
            
            elif tool_name == "enum_tech_detector":
                technologies = data.get("detected_technologies", [])
                if technologies:
                    output_lines.append(f"  ⚙️ Tespit Edilen Teknolojiler:")
                    for tech in technologies[:5]:
                        tech_name = tech.get("technology", "Unknown")
                        tech_version = tech.get("version", "")
                        version_str = f" v{tech_version}" if tech_version else ""
                        output_lines.append(f"      • {tech_name}{version_str}")
            
            elif tool_name == "enum_web_crawler":
                parameters = data.get("parameters", [])
                forms = data.get("forms", [])
                endpoints = data.get("endpoints", [])
                
                if parameters:
                    params_str = ", ".join([str(p) for p in parameters[:10]])
                    output_lines.append(f"  🔍 Bulunan Parametreler: {params_str}")
                if forms:
                    output_lines.append(f"  📝 Bulunan Form'lar: {len(forms)} adet")
                if endpoints:
                    output_lines.append(f"  🌐 Keşfedilen Endpoint'ler: {len(endpoints)} adet")
            
            elif tool_name == "recon_whois_lookup":
                domain_info = data.get("domain_info", {})
                if domain_info:
                    registrar = domain_info.get("registrar", "Unknown")
                    creation = domain_info.get("creation_date", "Unknown")
                    output_lines.append(f"  🌐 Registrar: {registrar}")
                    output_lines.append(f"  📅 Oluşturulma: {creation}")
            
            elif tool_name == "recon_origin_ip_finder":
                potential_ips = data.get("potential_origin_ips", [])
                if potential_ips:
                    output_lines.append(f"  🎯 Origin IP'ler: {len(potential_ips)} adet")
                    for ip_data in potential_ips[:5]:  # 5 IP göster (3'ten artırıldı)
                        ip = ip_data.get("ip", "Unknown")
                        risk = ip_data.get("risk_level", "unknown")
                        confidence = ip_data.get("confidence", "")
                        conf_str = f" | Conf: {confidence}" if confidence else ""
                        output_lines.append(f"      • {ip} (Risk: {risk}{conf_str})")
            
            elif tool_name in ["verify_xss", "verify_sqli", "verify_lfi"]:
                vulnerabilities = data.get("vulnerabilities", [])
                findings = data.get("findings", [])
                
                if vulnerabilities:
                    output_lines.append(f"  🚨 {len(vulnerabilities)} zafiyet bulundu!")
                    for vuln in vulnerabilities[:3]:
                        severity = vuln.get("severity", "unknown")
                        desc = vuln.get("description", "")[:80]
                        output_lines.append(f"      • [{severity.upper()}] {desc}")
                elif findings:
                    output_lines.append(f"  🚨 {len(findings)} bulgu tespit edildi")
                else:
                    output_lines.append(f"  ✓ Zafiyet tespit edilmedi")
            
            elif tool_name == "vuln_http_header_analyzer":
                missing_headers = data.get("missing_security_headers", [])
                if missing_headers:
                    output_lines.append(f"  ⚠️ Eksik Güvenlik Header'ları: {', '.join(missing_headers[:5])}")
                else:
                    output_lines.append(f"  ✓ Tüm güvenlik header'ları mevcut")
            
            elif tool_name == "enum_subdomain_bruteforcer":
                subdomains = data.get("subdomains", [])
                if subdomains:
                    output_lines.append(f"  🎯 Bulunan Subdomain'ler: {len(subdomains)} adet")
                    for subdomain in subdomains[:5]:
                        output_lines.append(f"      • {subdomain}")
            
            elif tool_name == "enum_directory_bruteforce":
                directories = data.get("directories", [])
                files = data.get("files", [])
                
                if directories:
                    output_lines.append(f"  📁 Bulunan Dizinler: {len(directories)} adet")
                    for dir_item in directories[:3]:
                        output_lines.append(f"      • {dir_item}")
                if files:
                    output_lines.append(f"  📄 Bulunan Dosyalar: {len(files)} adet")
            
            # Genel durumda - veri noktası sayısı
            else:
                data_points = 0
                if isinstance(data, dict):
                    data_points = len(data)
                elif isinstance(data, list):
                    data_points = len(data)
                
                if data_points > 0 and data_points <= 15:  # Max 15 veri noktası göster (10'dan artırıldı)
                    output_lines.append(f"  📊 {data_points} veri noktası toplandı")
                    
                    # İlk birkaç veri noktasını göster
                    if isinstance(data, dict):
                        for key, value in list(data.items())[:5]:  # 5 item göster (3'ten artırıldı)
                            value_str = str(value)[:100]  # 100 karakter (60'tan artırıldı)
                            if len(str(value)) > 100:
                                value_str += "..."
                            output_lines.append(f"      • {key}: {value_str}")
            
            # Tool önerilerini ekle (varsa)
            recommendations = result.get("recommendations", [])
            if recommendations and len(recommendations) > 0:
                output_lines.append(f"  💡 Tool Önerileri: {len(recommendations)} öneri")
                for i, rec in enumerate(recommendations[:3], 1):  # 3 öneri göster (2'den artırıldı)
                    rec_tool = rec.get("tool", "unknown")
                    rec_reason = rec.get("reason", "")[:120]  # 120 karakter (70'ten artırıldı)
                    if len(rec.get("reason", "")) > 120:
                        rec_reason += "..."
                    output_lines.append(f"      {i}. {rec_tool}: {rec_reason}")
            
            # TEK MESAJDA GÖNDER
            if output_lines:
                combined_message = "\n".join(output_lines)
                await status_callback(combined_message, "ai_reasoning")
        
        except Exception as e:
            logger.error(f"Result display error: {e}")
    
    async def _execute_tool(self, tool_name: str, params: dict):
        """Tool'u çalıştır"""
        try:
            result = await self.mcp_server.execute_tool(tool_name, params)
            # Result'ı kontrol et ve gerekirse düzelt
            if not isinstance(result, dict):
                result = {"success": True, "data": result}
            if "success" not in result:
                result["success"] = True
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {"success": False, "error": str(e), "data": {}}

    async def _execute_tool_streaming(self, tool_name: str, params: dict, status_callback):
        """Tool'u streaming düşünce ile çalıştır - KISA VERSİYON"""
        try:
            await status_callback(f"🔧 {tool_name} başlatılıyor...", "tool_start")
            
            # Tool'u çalıştır
            result = await self._execute_tool(tool_name, params)
            
            if result.get("success"):
                await status_callback(f"✅ {tool_name} tamamlandı", "tool_complete")
                
                # DETAYLI SONUÇ GÖSTERİMİ
                await self._display_tool_results(tool_name, result, status_callback)
                
            else:
                await status_callback(f"⚠️ {tool_name} sorunlu tamamlandı", "tool_complete")
            
            return result
        except Exception as e:
            await status_callback(f"❌ {tool_name} hatası: {str(e)}", "tool_error")
            return {"success": False, "error": str(e), "data": {}}

    async def run_autonomous_pentest(self, target: str, user_task: str):
        """Normal otonom pentest - streaming olmadan"""
        return await self.run_autonomous_pentest_streaming(target, user_task, self.status_callback)

    async def run_autonomous_pentest_streaming(self, target: str, user_task: str, status_callback):
        """Streaming düşünce ile dinamik otonom pentest"""
        # ==================== AI-POWERED TARGET VALIDATION ====================
        from agent_core.target_validator import (
            validate_target, 
            smart_target_extraction,
            extract_target_from_query
        )
        
        # 1. Target var mı kontrol et
        if not target or target.strip() == "":
            # Target boş - user_task'ten çıkarmayı dene
            if user_task and user_task.strip():
                await status_callback("🧠 Hedef analiz ediliyor...", "ai_thinking")
                
                # 🤖 SMART EXTRACTION: Regex + AI
                extracted_target, method = await smart_target_extraction(user_task, self.model)
                
                if extracted_target:
                    target = extracted_target
                    if method == "ai":
                        await status_callback(f"🤖 AI ile hedef tespit edildi: {target}", "info")
                    else:
                        await status_callback(f"✅ Hedef tespit edildi: {target}", "info")
                else:
                    # Hiçbir yöntem target bulamadı
                    await status_callback("❌ Tarama hedefi belirtilmedi", "error")
                    await self._send_no_target_response(user_task, status_callback)
                    return None
            else:
                # Query de boş
                await status_callback("❌ Tarama hedefi belirtilmedi", "error")
                await self._send_no_target_response("", status_callback)
                return None
        else:
            # Target direkt verilmiş - validate et
            is_valid, normalized_target, error_msg = validate_target(target)
            if not is_valid:
                # Geçersiz - AI ile düzeltmeyi dene (sessizce)
                ai_target = None
                if hasattr(self, 'model') and self.model:
                    from agent_core.target_validator import ai_extract_target
                    # User_task ile birleştir
                    combined_query = f"{target} {user_task}" if user_task else target
                    ai_target = await ai_extract_target(combined_query, self.model)
                
                if ai_target:
                    # ✅ AI target buldu - devam et
                    target = ai_target
                    await status_callback(f"🎯 Hedef belirlendi: {target}", "info")
                else:
                    # ❌ Target bulunamadı - kullanıcı ile sohbet et (RAG yok)
                    await self._send_invalid_target_response(target, error_msg, status_callback)
                    return None
            else:
                # Valid - normalize edilmiş halini kullan
                target = normalized_target
        
        # Dinamik state'i başlat
        self.current_target = target
        self.user_task = user_task
        self.scan_context = {"target": target, "user_task": user_task}
        self.discovered_information = {}
        self.execution_history = []
        
        # Sadece önemli bilgileri göster
        await status_callback(f"🎯 Hedef: {target}", "info")
        
        # Streaming düşünce başlat - sadece ana mesaj
        await self._stream_ai_thinking("🚀 Pentest başlatılıyor", status_callback)
        
        try:
            # İlk tool'u AI belirlesin
            await self._stream_ai_thinking("İlk tool seçiliyor...", status_callback)
            first_tool_decision = await self._ai_decide_first_tool(target, user_task)
            
            if not first_tool_decision.get("success", False):
                await status_callback("❌ AI ilk tool'u belirleyemedi", "error")
                return self._create_final_state(target, user_task, success=False)
            
            # Tool seçimini göster
            selected_tool = first_tool_decision.get('tool')
            tool_reasoning = first_tool_decision.get('reasoning', '')
            await self._stream_ai_thinking(f"🔧 Tool seçildi: {selected_tool}", status_callback)
            
            # Tool seçim sebebini göster metin karakter sayısı
            if tool_reasoning:
                await status_callback(f"💡 Sebep: {tool_reasoning}", "ai_reasoning")
            
            # İlk tool için parametreleri tamamla
            first_tool_params = self._complete_tool_params(
                first_tool_decision.get("tool"),
                first_tool_decision.get("params", {}),
                status_callback
            )
            
            # Tool'u çalıştır
            tool_result = await self._execute_tool_streaming(
                first_tool_decision.get("tool"), 
                first_tool_params,
                status_callback
            )
            
            # Sonuçları analiz et
            await self._stream_ai_thinking("Sonuçlar analiz ediliyor...", status_callback)
            
            # İlk tool'u execution history'ye ekle
            self.execution_history.append({
                "step": 1,
                "tool": first_tool_decision.get("tool"),
                "params": first_tool_decision.get("params", {}),
                "result": tool_result,
                "reasoning": first_tool_decision.get("reasoning", ""),
                "timestamp": datetime.now().isoformat(),
                "success": tool_result.get("success", False)
            })
            
            # Tool sonucunu context'e ekle
            if tool_result.get("success", False):
                self._update_context_with_results(first_tool_decision.get("tool"), tool_result)
            
            # Dinamik execution - her tool çıktısına göre sonraki adım
            current_step = 2  # İlk tool zaten çalıştırıldı
            next_tool_decision = None
            tool_usage_count = {first_tool_decision.get("tool"): 1}  # İlk tool'u say
            
            # İlk tool'dan sonra sonraki adımı belirle
            if tool_result.get("success", False):
                await self._stream_ai_thinking("Sonraki adım belirleniyor...", status_callback)
                next_tool_decision = await self._ai_decide_next_tool(
                    first_tool_decision.get("tool"), 
                    tool_result, 
                    1
                )
            else:
                await status_callback(f"⚠️ İlk tool başarısız, alternatif strateji deneniyor", "warning")
                next_tool_decision = await self._ai_handle_failed_tool(
                    first_tool_decision.get("tool"),
                    tool_result,
                    1
                )
            
            # Kullanıcı görevine göre dinamik step limiti ayarla
            task_keywords = (user_task or "").lower()
            if any(word in task_keywords for word in ["hızlı", "quick", "basit", "simple", "scan"]):
                self.suggested_steps = 3
            elif any(word in task_keywords for word in ["detaylı", "comprehensive", "full", "kapsamlı"]):
                self.suggested_steps = 8
            elif any(word in task_keywords for word in ["spesifik", "specific", "sadece", "only"]):
                self.suggested_steps = 3
            else:
                self.suggested_steps = 5
            
            await status_callback(f"📊 Görev karmaşıklığı analizi: {self.suggested_steps} tool hedefleniyor (min: {self.min_steps})", "info")
            
            # Eğer hemen stop kararı verilmediyse döngüye devam et
            while current_step <= self.suggested_steps and next_tool_decision and next_tool_decision.get("action") != "stop":
                tool_name = next_tool_decision.get("tool")
                if not tool_name:
                    await status_callback("⚠️ Tool adı bulunamadı, test durduruluyor", "warning")
                    break
                
                params = next_tool_decision.get("params", {})
                
                # AKILLI DÖNGÜ KONTROLÜ - Aynı tool+parametre kombinasyonunu engelle
                tool_usage_count[tool_name] = tool_usage_count.get(tool_name, 0) + 1
                
                # Aynı tool AYNI PARAMETRELERLE 2. kez mi çalışıyor?
                tool_param_key = f"{tool_name}_{str(sorted(params.items()) if params else '')}"
                recent_tool_params = [
                    f"{h.get('tool')}_{str(sorted(h.get('params', {}).items()) if h.get('params') else '')}" 
                    for h in self.execution_history[-3:]  # Son 3 adımı kontrol et
                ]
                
                if tool_param_key in recent_tool_params:
                    # Sessizce alternatif strateji dene (kullanıcıya log gösterme)
                    logger.warning(f"{tool_name} tekrar edildi, alternatif strateji deneniyor")
                    next_tool_decision = await self._ai_force_alternative_strategy(tool_name, current_step)
                    if next_tool_decision.get("action") == "stop":
                        break
                    continue
                
                # Aynı tool farklı parametrelerle ama ÇOK SIKÇA mı çalışıyor?
                if tool_usage_count.get(tool_name, 0) > 2:
                    await status_callback(f"⚠️ {tool_name} 3. kez çalıştırılmak isteniyor, döngü riski - atlanıyor", "warning")
                    next_tool_decision = await self._ai_force_alternative_strategy(tool_name, current_step)
                    if next_tool_decision.get("action") == "stop":
                        break
                    continue
                
                # NOT: Aynı tool farklı parametrelerle kullanılabilir!
                    
                reasoning = next_tool_decision.get("reasoning", "")
                
                await status_callback(f"🔧 Adım {current_step}: {tool_name}", "info")
                if reasoning:
                    await self._stream_ai_thinking(f"Sebep: {reasoning}", status_callback)
                
                try:
                    # AKILLI PARAMETRE TAMAMLAMA
                    params = self._complete_tool_params(tool_name, params, status_callback)
                    
                    # Tool'u direkt MCP server üzerinden çalıştır - streaming ile
                    step_result = await self._execute_tool_streaming(tool_name, params, status_callback)
                    
                    # Execution history'ye ekle
                    self.execution_history.append({
                        "step": current_step,
                        "tool": tool_name,
                        "params": params,
                        "result": step_result,
                        "reasoning": reasoning,
                        "timestamp": datetime.now().isoformat(),
                        "success": step_result.get("success", False)
                    })
                    
                    if step_result.get("success", False):
                        await status_callback(f"✅ {tool_name} başarıyla tamamlandı", "success")
                        
                        # Tool sonucunu context'e ekle
                        self._update_context_with_results(tool_name, step_result)
                        
                        # Minimum step kontrolü - yeterli bilgi toplandıysa erken durdur
                        if current_step >= self.min_steps:
                            info_count = len(self.discovered_information)
                            if info_count > 0:
                                await status_callback(f"✓ Minimum {self.min_steps} tool tamamlandı, {info_count} bilgi toplandı - yeterlilik kontrolü yapılıyor", "info")
                            else:
                                await status_callback(f"⚠️ Minimum {self.min_steps} tool tamamlandı ama çok az bilgi toplandı - devam ediliyor", "warning")
                        
                        # AI'ye tool sonucunu ver ve sonraki adımı belirle
                        await self._stream_ai_thinking("Sonraki adım belirleniyor...", status_callback)
                        next_tool_decision = await self._ai_decide_next_tool(
                            tool_name, step_result, current_step
                        )
                        
                        if next_tool_decision.get("action") == "stop":
                            stop_reason = next_tool_decision.get("reasoning", "AI kararı")
                            await status_callback(f"🛑 Test tamamlandı: {stop_reason}", "ai_decision")
                            break
                        else:
                            current_step += 1
                            
                            # Max'a yaklaşıldıysa uyarı ver
                            if current_step >= self.suggested_steps:
                                await status_callback(f"⚠️ Hedeflenen {self.suggested_steps} tool'a ulaşıldı - yeterli bilgi varsa durduruluyor", "warning")
                    else:
                        await status_callback(f"❌ {tool_name} başarısız: {step_result.get('error', 'Bilinmeyen hata')}", "error")
                        
                        # Başarısız tool için AI kararı
                        await self._stream_ai_thinking("Alternatif strateji belirleniyor...", status_callback)
                        next_tool_decision = await self._ai_handle_failed_tool(
                            tool_name, step_result, current_step
                        )
                        
                        if next_tool_decision.get("action") == "stop":
                            await status_callback("🛑 Tool hatası nedeniyle test durduruldu", "error")
                            break
                        else:
                            current_step += 1
                            
                except Exception as e:
                    logger.error(f"Tool execution error: {e}")
                    await status_callback(f"❌ {tool_name} hatası: {str(e)}", "error")
                    
                    # Hata durumunda AI'ya sor ne yapacağını
                    next_tool_decision = await self._ai_handle_failed_tool(
                        tool_name, 
                        {"success": False, "error": str(e)}, 
                        current_step
                    )
                    
                    if next_tool_decision.get("action") == "stop":
                        break
                    
                    current_step += 1
            
            # Final analiz ve profesyonel rapor oluşturma
            await status_callback("📊 Sonuç analizi yapılıyor...", "ai_thinking")
            final_analysis = await self._analyze_final_results()
            
            # Profesyonel rapor oluştur
            await status_callback("📋 Profesyonel rapor oluşturuluyor...", "ai_thinking")
            professional_report = await self._generate_professional_report(self.execution_history, final_analysis)
            
            # Final state oluştur
            final_state = self._create_final_state(target, user_task, success=True)
            final_state.execution_history = self.execution_history
            final_state.discovered_information = self.discovered_information
            final_state.final_analysis = final_analysis
            
            # Session özetini JSON'a kaydet
            final_results = {
                "target": target,
                "user_task": user_task,
                "execution_results": self.execution_history,
                "final_analysis": final_analysis,
                "professional_report": professional_report,
                "discovered_information": self.discovered_information,
                "execution_summary": self._generate_execution_summary(),
                "completion_time": datetime.now().isoformat(),
                "agent_state": final_state.to_dict()
            }
            
            # Session dosyasını kaydet (rapor arayüzü için)
            await self._save_session_for_report(final_results)
            
            # Basit özet göster (uzman seviyesi)
            await self._print_expert_summary(final_analysis, professional_report)
            
            # Rapor oluşturma seçeneği
            await self._print_report_option()
            
            await self.status_callback("✅ Dinamik penetrasyon testi tamamlandı", "success")
            
            return final_state
            
        except Exception as e:
            logger.error(f"Dynamic pentest error: {e}")
            await self.status_callback(f"❌ Penetrasyon testi başarısız: {str(e)}", "error")
            return self._create_final_state(target, user_task, success=False)
    
    async def _ai_force_alternative_strategy(self, repeated_tool: str, current_step: int) -> Dict[str, Any]:
        """Döngü tespit - alternatif strateji - KISA"""
        recent_tools = [h.get("tool") for h in self.execution_history[-3:]]
        recent_tools_str = ", ".join(recent_tools)
        
        prompt = f"""
⚠️ DÖNGÜ TESPİT EDİLDİ: '{repeated_tool}' aynı parametrelerle tekrar edildi!

🎯 HEDEF: {self.current_target}
📋 GÖREV: {self.user_task or "Genel test"}
📈 ADIM: {current_step}/{self.suggested_steps} (min:{self.min_steps})
🔄 SON TOOL'LAR: {recent_tools_str}

💡 ÇÖZÜM SEÇENEKLERİ:
1. Farklı tool seç (örn: tech_detector → directory_bruteforce)
2. {current_step}>={self.min_steps} ve yeterli bilgi → "stop"

JSON ÇIKTI (Reasoning MUTLAKA TÜRKÇE):
{{"action":"continue|stop","tool":"tool_adı","params":{{"target":"{self.current_target}"}},"reasoning":"TÜRKÇE: Döngüden nasıl çıkılıyor, alternatif tool neden seçildi?"}}

⚠️ KRİTİK: Reasoning MUTLAKA TÜRKÇE + SADECE JSON!
        """
        
        try:
            response = await self._call_gemini(prompt)
            decision = json.loads(response)
            
            await self.status_callback(f"🧠 Alternatif strateji: {decision.get('reasoning', '')}", "ai_reasoning")
            
            return decision
            
        except Exception as e:
            logger.error(f"Alternative strategy failed: {e}")
            return {"action": "stop", "reasoning": "Alternatif strateji geliştirilemedi - test durduruluyor"}

    async def _ai_decide_first_tool(self, target: str, user_task: str = None) -> Dict[str, Any]:
        """AI ile ilk tool'u belirle - KISALTILMIŞ"""
        available_tools = self.mcp_server.get_tool_list()['categories']
        all_tools = set()
        for cat, tools in available_tools.items():
            all_tools.update(tools)
        
        # Context bilgilerini hazırla
        target_type = self._classify_target(target)
        
        # DENGELI TOOL LİSTESİ - performans ve token dengesi
        tools_compact = ", ".join(sorted(list(all_tools)))[:300]  # İlk 300 karakter
        
        prompt = f"""
Siber güvenlik uzmanı olarak {target} için ilk tool'u seç.

🎯 HEDEF: {target} ({target_type})
📋 GÖREV: {user_task or "Güvenlik testi"}
📦 TOOL'LAR: {tools_compact}... (29 tool mevcut)

🧠 AKILLI BAŞLANGIÇ KURALLARI:
- XSS/SQLi test → enum_web_crawler (önce parametre bul)
- Subdomain keşfi → enum_subdomain_bruteforcer  
- Port tarama → enum_port_scanner
- Genel test → enum_tech_detector (hızlı)
- Domain bilgisi → recon_whois_lookup

JSON ÇIKTI (Reasoning MUTLAKA TÜRKÇE):
{{"success":true,"action":"continue","tool":"tool_adı","params":{{"target":"{target}"}},"reasoning":"TÜRKÇE: Tool neden seçildi ve ne bulunması bekleniyor?"}}

⚠️ KRİTİK: Reasoning MUTLAKA TÜRKÇE + SADECE JSON!
"""
        
        try:
            response = await self._call_gemini(prompt)
            decision = json.loads(response)
            # Seçilen tool kayıtlı değilse fallback
            chosen = decision.get('tool')
            if chosen and chosen not in all_tools and decision.get('action') == 'continue':
                decision['tool'] = 'enum_tech_detector' if 'http' in str(self.current_target) else 'recon_whois_lookup'
            
            if decision.get("success", False) and decision.get("tool"):
                return decision
            else:
                # Fallback - hedef tipine göre basit karar
                return self._get_fallback_first_tool(target)
                    
        except Exception as e:
            logger.error(f"AI first tool decision failed: {e}")
            return self._get_fallback_first_tool(target)

    def _get_detailed_tools_info(self) -> str:
        """Detaylı tool bilgilerini al - TÜM 29 TOOL"""
        tools_info = {
            # === RECONNAISSANCE TOOLS (9 tools) ===
            "enum_port_scanner": "🔍 Port Scanner | Params: target, profile='quick'|'comprehensive' | Açık portları, servisleri, OS fingerprint tespit eder",
            "enum_tech_detector": "⚙️ Tech Detector | Params: target, scan_type='quick' | Web teknolojileri, framework, CMS, server bilgisi tespit eder",
            "enum_web_crawler": "🕷️ Web Crawler | Params: url, max_depth=3 | Sayfaları tarar, form parametreleri, endpoint'leri bulur - XSS/SQLi için ZORUNLU",
            "enum_directory_bruteforce": "📁 Directory Brute | Params: url, wordlist='common' | Gizli dizinler, backup dosyaları, admin panelleri bulur",
            "enum_subdomain_bruteforcer": "🎯 Subdomain Brute | Params: domain | Subdomain'leri bulur, saldırı yüzeyini genişletir",
            "enum_firewall_detector": "🛡️ Firewall Detector | Params: target | WAF/Firewall varlığını tespit eder (Cloudflare, AWS WAF, etc.)",
            "recon_whois_lookup": "🌐 WHOIS Lookup | Params: domain | Domain sahibi, registrar, DNS sunucuları, oluşturma tarihi",
            "recon_origin_ip_finder": "🔎 Origin IP Finder | Params: domain | Cloudflare arkasındaki gerçek IP'yi bulur (SPF, MX, SSL)",
            "recon_passive_subfinder": "🔍 Passive Subfinder | Params: domain | Pasif subdomain keşfi (DNS kayıtları, sertifikalar)",
            
            # === VULNERABILITY TESTING TOOLS (7 tools) ===
            "verify_xss": "🎭 XSS Verifier | Params: url, parameter, method='GET' | XSS zafiyeti testi - ÖNCE enum_web_crawler ile parametre bul!",
            "verify_sqli": "💉 SQLi Verifier | Params: url, parameter, method='GET' | SQL injection testi - ÖNCE enum_web_crawler ile parametre bul!",
            "verify_lfi": "📄 LFI Verifier | Params: url, parameter, method='GET' | Local File Inclusion testi - ÖNCE enum_web_crawler ile parametre bul!",
            "verify_xss_http": "🌐 XSS HTTP | Params: url, parameter | HTTP-based XSS testi, gelişmiş payload'lar",
            "vuln_idor_tester": "🔓 IDOR Tester | Params: url, endpoint, auth_token | Insecure Direct Object Reference testi",
            "vuln_http_header_analyzer": "📋 Header Analyzer | Params: url | Güvenlik header'ları analiz eder (CSP, HSTS, X-Frame-Options)",
            "vul_depency_scanner": "📦 Dependency Scanner | Params: target | Bağımlılık zafiyetleri, outdated kütüphaneler tespit eder",
            
            # === API SECURITY TOOLS (4 tools) ===
            "api_finder_active": "🔌 API Finder | Params: target | Aktif API endpoint'lerini bulur, REST/GraphQL/SOAP",
            "recon_api_endpoint_finder": "🎯 API Endpoint Finder | Params: url | API endpoint'lerini keşfeder, swagger/openapi bulur",
            "api_vuln_idor_scanner": "🔐 API IDOR Scanner | Params: url, endpoint | API IDOR zafiyetlerini tarar",
            "api_vuln_jwt_tester": "🔑 JWT Tester | Params: url, token | JWT token zafiyetleri (weak secret, algorithm confusion)",
            
            # === INFRASTRUCTURE TOOLS (4 tools) ===
            "infra_exposed_panels_finder": "🏗️ Exposed Panels | Params: target | Admin panel, phpMyAdmin, cPanel, Jenkins gibi yönetim panelleri bulur",
            "service_fingerprinting": "🔬 Service Fingerprint | Params: target, port | Servis versiyonları, banner grabbing, detaylı fingerprint",
            "rec_dns_analyzer": "🌐 DNS Analyzer | Params: domain | DNS kayıtları, zone transfer, DNSSEC, nameserver analizi",
            "rec_audit_email_security": "📧 Email Security | Params: domain | SPF, DKIM, DMARC kayıtları, email güvenlik analizi",
            
            # === INTELLIGENCE TOOLS (3 tools) ===
            "rec_intel_code_scanner": "💻 Code Scanner | Params: target | GitHub/GitLab'da kod sızıntıları, API key'ler, credential'lar bulur",
            "rec_intel_historical_analyzer": "📜 Historical Analyzer | Params: domain | Wayback Machine, eski versiyonlar, tarihsel zafiyet analizi",
            
            # === CLOUD SECURITY TOOLS (2 tools) ===
            "cloud_s3_bucket_scanner": "☁️ S3 Bucket Scanner | Params: domain | AWS S3 bucket'ları bulur, public erişim, veri sızıntısı tespit eder"
        }
        
        available_tools = []
        for category, tools in self.mcp_server.get_tool_list()['categories'].items():
            available_tools.extend(tools)
        
        detailed_info = []
        for tool in available_tools:
            if tool in tools_info:
                detailed_info.append(f"- {tool}: {tools_info[tool]}")
            else:
                detailed_info.append(f"- {tool}: Tool açıklaması mevcut değil")
        
        return "\n".join(detailed_info)

    def _classify_target(self, target: str) -> str:
        """Hedefi teknik olarak sınıflandır"""
        if target.startswith("http"):
            return "Web Application (HTTP/HTTPS)"
        elif target.replace(".", "").replace(":", "").isdigit():
            return "Network Host (IP Address)"
        elif "." in target and not target.startswith("http"):
            return "Domain Name (DNS Target)"
        else:
            return "Unknown Target Type"
    
    def _assess_target_risk(self, target: str) -> str:
        """Hedef risk seviyesini değerlendir"""
        if target.endswith(".gov") or target.endswith(".mil"):
            return "HIGH (Government/Military)"
        elif target.endswith(".edu"):
            return "MEDIUM (Educational Institution)"
        elif target.endswith(".com") or target.endswith(".org"):
            return "MEDIUM (Commercial/Organization)"
        else:
            return "UNKNOWN (Custom TLD)"

    def _get_fallback_first_tool(self, target: str) -> Dict[str, Any]:
        """Fallback ilk tool seçimi - OPTİMİZE - HIZLI TARAMA"""
        if target.startswith("http"):
            return {
                "success": True,
                "action": "continue",
                "tool": "enum_tech_detector",
                "params": {"target": target, "url": target, "scan_type": "quick", "timeout": 20},
                "reasoning": "Web - hızlı teknoloji tespiti"
            }
        elif target.replace(".", "").replace(":", "").isdigit():
            return {
                "success": True,
                "action": "continue", 
                "tool": "enum_port_scanner",
                "params": {"target": target, "profile": "quick", "timeout": 30},  # QUICK profile!
                "reasoning": "IP adresi için port taraması - açık portları, servisleri ve işletim sistemini tespit etme"
            }
        else:
            return {
                "success": True,
                "action": "continue",
                "tool": "recon_whois_lookup",
                "params": {"target": target, "domain": target, "detailed": True},
                "reasoning": "Domain bilgileri için whois lookup - domain sahipliği, kayıt bilgileri ve DNS sunucularını öğrenme"
            }

    def _summarize_tool_result(self, tool_result: Dict[str, Any]) -> Dict[str, Any]:
        """Tool sonucunu AI için özetler (token tasarrufu)"""
        summary = {
            "success": tool_result.get("success", False),
            "ai_summary": tool_result.get("ai_summary", ""),
        }
        
        # Sadece önemli data'yı al
        data = tool_result.get("data", {})
        if isinstance(data, dict):
            # Port scanner için
            if "open_ports" in data:
                summary["open_ports_count"] = len(data.get("open_ports", []))
                summary["critical_services"] = [p for p in data.get("open_ports", [])[:5]]  # İlk 5 port
            # Tech detector için
            elif "technologies" in data:
                summary["tech_stack"] = data.get("technologies", [])[:10]  # İlk 10
            # Genel data
            else:
                summary["data_keys"] = list(data.keys())[:10]  # Sadece key'ler
        
        # Recommendations varsa ilk 3'ünü al
        if "recommendations" in tool_result:
            summary["top_recommendations"] = tool_result.get("recommendations", [])[:3]
        
        return summary
    
    async def _ai_decide_next_tool(self, last_tool: str, last_result: Dict[str, Any], current_step: int) -> Dict[str, Any]:
        """Sonraki tool - KISALTILMIŞ"""
        available_tools = self.mcp_server.get_tool_list()['categories']
        
        # Create all_tools set from available tools
        all_tools = set()
        for cat, tools in available_tools.items():
            all_tools.update(tools)
        
        # Tool sonucunu özetle (token tasarrufu)
        summarized_result = self._summarize_tool_result(last_result)
        
        # Kullanılmış tool'ları listele
        used_tools = [h.get("tool") for h in self.execution_history]
        used_tools_str = ", ".join(set(used_tools))[:50]  # Kısalt
        
        # Tool'un önerilerini çıkar - KISA
        tool_recommendations = last_result.get("recommendations", [])
        recommendations_text = ""
        if tool_recommendations:
            recommendations_text = f"\nÖNERİLER: {', '.join([rec.get('tool', '') for rec in tool_recommendations[:2]])}"
        
        # DENGELI TOOL LİSTESİ
        tools_compact = ", ".join(sorted(list(all_tools)))[:250]
        
        suggested_max = self.suggested_steps
        
        prompt = f"""
Sen siber güvenlik uzmanısın. Son tool çıktısını analiz et ve sonraki adımı belirle.

🔧 SON TOOL: {last_tool}
📊 SONUÇ: {summarized_result.get('ai_summary', '')[:200]}{recommendations_text}
🎯 HEDEF: {self.current_target}
📋 GÖREV: {self.user_task or "Genel test"}
📈 ADIM: {current_step}/{suggested_max} (min:{self.min_steps})
🚫 KULLANILMIŞ: {used_tools_str}
📦 TOOL'LAR: {tools_compact}...

🧠 KARAR SÜRECİ:
1. {last_tool} ne buldu? Başarılı mı?
2. Kullanıcı isteği tamamlandı mı?
3. {current_step}>={self.min_steps} ve yeterli bilgi → "stop"
4. Sonraki tool mantıklı mı? (Döngüden kaçın!)

💡 SENARYO ÖRNEKLERİ:
- Port bulundu → service_fingerprinting (detay)
- Teknoloji bulundu → verify_xss/sqli (ama parametre gerekli!)
- Subdomain bulundu → her birine test
- Yeterli bilgi toplandı → "stop"

JSON ÇIKTI (Reasoning MUTLAKA TÜRKÇE):
{{"action":"continue|stop","tool":"tool_adı","params":{{"target":"{self.current_target}"}},"reasoning":"TÜRKÇE: Tool neden seçildi, ne bulunması bekleniyor?"}}

⚠️ KRİTİK: Reasoning MUTLAKA TÜRKÇE + SADECE JSON!
"""
        
        try:
            response = await self._call_gemini(prompt)
            decision = json.loads(response)
            chosen = decision.get('tool')
            if chosen and chosen not in all_tools and decision.get('action') == 'continue':
                decision['tool'] = 'enum_tech_detector' if 'http' in str(self.current_target) else 'recon_whois_lookup'
            
            await self.status_callback(f"🧠 Sonraki adım kararı: {decision.get('reasoning', '')}", "ai_reasoning")
            
            # En az adım zorlaması: AI 'stop' dese bile minimum adım tamamlanana kadar devam et
            try:
                if decision.get("action") == "stop" and current_step < self.min_steps:
                    fallback = self._get_fallback_first_tool(self.current_target)
                    fallback["action"] = "continue"
                    await self.status_callback(
                        f"⚠️ Min {self.min_steps} adım şartı: 'stop' yerine devam ediliyor ({fallback.get('tool')})",
                        "warning"
                    )
                    return fallback
            except Exception:
                pass
            
            return decision
            
        except Exception as e:
            logger.error(f"Next tool decision failed: {e}")
            fallback = self._get_fallback_first_tool(self.current_target)
            fallback["action"] = "continue"
            return fallback

    async def _ai_handle_failed_tool(self, failed_tool: str, error_result: Dict[str, Any], current_step: int) -> Dict[str, Any]:
        """Başarısız tool için karar ver - OPTİMİZE"""
        error_msg = error_result.get("error", "Bilinmeyen hata")
        
        # ÖNEMLİ: Selenium/Chrome hatası mı? Otomatik olarak alternatife geç
        chrome_keywords = ["Selenium", "WebDriver", "Chrome binary", "Chrome", "chromedriver", "cannot find Chrome"]
        if any(keyword in error_msg for keyword in chrome_keywords):
            logger.info(f"🔄 Chrome/Selenium hatası tespit edildi: {failed_tool}")
            
            if failed_tool == "verify_xss":
                await self.status_callback("🔄 Selenium/Chrome mevcut değil → verify_xss_http", "info")
                return {
                    "action": "continue",
                    "tool": "verify_xss_http",
                    "params": {"url": self.current_target, "parameter": "search", "method": "GET"},
                    "reasoning": "Selenium/Chrome mevcut değil (Render ortamı), HTTP-based XSS testi kullanılıyor"
                }
            elif failed_tool == "enum_web_crawler":
                await self.status_callback("🔄 Chrome binary yok → enum_directory_bruteforce", "info")
                return {
                    "action": "continue",
                    "tool": "enum_directory_bruteforce",
                    "params": {"url": self.current_target, "wordlist_type": "general"},
                    "reasoning": "Web crawler Chrome gerektirir, directory bruteforce (HTTP-only) alternatifi kullanılıyor"
                }
        
        prompt = f"""
{failed_tool} başarısız.
HATA: {error_msg[:100]}
HEDEF: {self.current_target}
ADIM: {current_step}/{self.min_steps}

ALTERNATIF:
- port_scanner → tech_detector
- tech_detector → directory_bruteforce
- web_crawler → directory_bruteforce
- {current_step}>={self.min_steps} ise "stop"

JSON (TÜRKÇE):
{{"action":"continue|stop","tool":"tool_adı","params":{{"target":"{self.current_target}"}},"reasoning":"TÜRKÇE: Neden?"}}

⚠️ SADECE JSON + TÜRKÇE!
"""
        
        try:
            response = await self._call_gemini(prompt)
            decision = json.loads(response)
            
            await self.status_callback(f"🧠 Hata yönetimi kararı: {decision.get('reasoning', '')}", "ai_reasoning")
            
            # En az adım zorlaması
            try:
                if decision.get("action") == "stop" and current_step < self.min_steps:
                    fallback = self._get_fallback_first_tool(self.current_target)
                    fallback["action"] = "continue"
                    await self.status_callback(
                        f"⚠️ Min {self.min_steps} adım şartı: 'stop' yerine devam ediliyor ({fallback.get('tool')})",
                        "warning"
                    )
                    return fallback
            except Exception:
                pass
            
            return decision
            
        except Exception as e:
            logger.error(f"Failed tool handling failed: {e}")
            fallback = self._get_fallback_first_tool(self.current_target)
            fallback["action"] = "continue"
            return fallback

    async def _analyze_final_results(self) -> Dict[str, Any]:
        """Final sonuçları analiz et - SADECE gerçek tool çıktıları"""
        # METADATA'YI FİLTRELE: sadece tool data'sını al
        clean_results = []
        for step in self.execution_history:
            tool_data = {
                "tool": step.get("tool"),
                "success": step.get("success", False),
                "data": step.get("result", {}).get("data", {}),  # SADECE data
                "ai_summary": step.get("result", {}).get("ai_summary", "")
            }
            # Boş sonuçları atla
            if tool_data["data"] or tool_data["ai_summary"]:
                clean_results.append(tool_data)
        
        prompt = f"""
Sen dünya çapında tanınan bir siber güvenlik uzmanısın ve penetrasyon testi konusunda 15+ yıl deneyime sahipsin.
Penetrasyon testi tamamlandı ve sen kapsamlı bir güvenlik analizi raporu hazırlaman gerekiyor.

📊 TEST SONUÇLARI VE DETAYLI ANALİZ:

🔧 ÇALIŞTIRILAN TOOL'LAR VE SONUÇLARI (SADECE TOOL ÇIKTILARI):
{json.dumps(clean_results, indent=2, default=str, ensure_ascii=False)[:3000]}

🎯 KEŞFEDİLEN BİLGİLER VE CONTEXT:
{json.dumps(self.discovered_information, indent=2, default=str, ensure_ascii=False)[:2000]}

📈 TEST METRİKLERİ:
- Hedef: {self.current_target}
- Görev: {self.user_task or "Genel güvenlik değerlendirmesi"}
- Toplam Adım: {len(self.execution_history)}
- Başarılı Tool: {len([r for r in self.execution_history if r.get('result', {}).get('success', False)])}

🧠 KAPSAMLI GÜVENLİK ANALİZİ GEREKTİREN ALANLAR:
1. **Güvenlik Açıkları**: Kritik, yüksek, orta, düşük seviyeli açıklar
2. **Risk Assessment**: CVSS skorları, exploit potansiyeli, business impact
3. **Attack Surface**: Keşfedilen saldırı yüzeyleri ve vektörleri
4. **Compliance**: Güvenlik standartlarına uyumluluk
5. **Recommendations**: Öncelikli düzeltme önerileri
6. **Test Coverage**: Hangi alanlar test edildi, hangileri eksik
7. **Business Impact**: İş süreçlerine etki analizi

🎯 ÇIKTI FORMATI (SADECE JSON):
{{
    "security_vulnerabilities": [
        {{
            "type": "vulnerability_type",
            "severity": "critical|high|medium|low",
            "description": "detaylı açıklama",
            "cvss_score": "X.X",
            "exploitability": "easy|moderate|hard|impossible",
            "business_impact": "high|medium|low",
            "recommendation": "düzeltme önerisi"
        }}
    ],
    "risk_level": "critical|high|medium|low",
    "attack_surface_analysis": {{
        "discovered_endpoints": "sayı",
        "open_ports": "liste",
        "technologies": "tespit edilen teknolojiler",
        "security_headers": "durum"
    }},
    "recommendations": [
        {{
            "priority": "immediate|short_term|long_term",
            "category": "network|web|infrastructure",
            "description": "detaylı öneri",
            "effort": "low|medium|high",
            "impact": "high|medium|low"
        }}
    ],
    "test_effectiveness": "excellent|good|moderate|poor",
    "coverage_analysis": {{
        "network_layer": "tested|partial|not_tested",
        "application_layer": "tested|partial|not_tested",
        "infrastructure": "tested|partial|not_tested"
    }},
    "compliance_status": {{
        "owasp_top10": "compliant|non_compliant|partial",
        "pci_dss": "compliant|non_compliant|partial",
        "iso27001": "compliant|non_compliant|partial"
    }},
    "executive_summary": "Yöneticiler için özet rapor - risk seviyesi, kritik açıklar, öncelikli aksiyonlar"
}}

⚠️ ÖNEMLİ: Sadece JSON formatında yanıt ver, başka açıklama yapma!
"""
        
        try:
            response = await self._call_gemini(prompt)
            analysis = json.loads(response)
            return analysis
        except Exception as e:
            logger.error(f"Final analysis failed: {e}")
            return {
                "security_vulnerabilities": [],
                "risk_level": "unknown",
                "recommendations": ["Test tamamlandı, detaylı analiz gerekli"],
                "test_effectiveness": "unknown",
                "summary": "Test tamamlandı"
            }

    async def _generate_professional_report(self, execution_results: Dict[str, Any], final_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Profesyonel penetrasyon test raporu oluştur"""
        try:
            from agent_core.report_generator import ReportGenerator
            
            # Report generator'ı başlat
            report_gen = ReportGenerator()
            
            # Execution history'yi AgentState formatına çevir
            state = self._create_final_state(self.current_target, self.user_task, success=True)
            state.execution_history = self.execution_history
            state.discovered_information = self.discovered_information
            
            # Bulguları state'e ekle
            findings = self.get_findings()
            if findings:
                logger.info(f"📊 {len(findings)} bulgu state'e ekleniyor")
                state.findings = findings
            
            # Profesyonel rapor oluştur
            report_data = await report_gen.generate_comprehensive_report(
                state=state,
                final_analysis=final_analysis,
                execution_results=execution_results
            )
            
            return report_data
            
        except Exception as e:
            logger.error(f"Professional report generation failed: {e}")
            # Fallback: basit analiz
            return {
                "report_type": "fallback",
                "analysis": final_analysis,
                "error": f"Professional report generation failed: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Final analysis failed: {e}")
            return {
                "security_vulnerabilities": [],
                "risk_level": "unknown",
                "recommendations": ["Test tamamlandı, detaylı analiz gerekli"],
                "test_effectiveness": "unknown",
                "summary": "Test tamamlandı"
            }

    def _update_context_with_results(self, tool_name: str, result: Dict[str, Any]):
        """Tool sonuçlarını context'e ekle ve GERÇEK BULGULAR oluştur"""
        if result.get("success", False):
            data = result.get("data", {})
            
            # Tool'a göre bilgi çıkar ve JSON serializable hale getir
            if tool_name == "enum_port_scanner":
                if "open_ports" in data:
                    # Set'i list'e çevir
                    ports = data["open_ports"]
                    if isinstance(ports, set):
                        ports = list(ports)
                    self.discovered_information["open_ports"] = ports
                if "services" in data:
                    services = data["services"]
                    if isinstance(services, set):
                        services = list(services)
                    self.discovered_information["services"] = services
                    
            elif tool_name == "recon_whois_lookup":
                if "domain_info" in data:
                    self.discovered_information["domain_info"] = data["domain_info"]
                    
            elif tool_name in ["enum_tech_detector"]:
                if "technologies" in data:
                    technologies = data["technologies"]
                    if isinstance(technologies, set):
                        technologies = list(technologies)
                    self.discovered_information["technologies"] = technologies
            
            elif tool_name == "enum_web_crawler":
                # Web crawler'dan parametreleri çıkar
                if "parameters" in data:
                    parameters = data["parameters"]
                    if isinstance(parameters, (set, list)):
                        parameters = list(parameters)
                        self.discovered_information["parameters"] = parameters
                        logger.info(f"✨ Web crawler'dan {len(parameters)} parametre keşfedildi: {parameters[:5]}")
                
                # Form'ları da kaydet
                if "forms" in data:
                    self.discovered_information["forms"] = data["forms"]
                
                # Web crawler bulgularını GERÇEK BULGU olarak ekle
                if "parameters" in data or "forms" in data:
                    finding = {
                        "title": "Web Application Discovery",
                        "severity": "medium",
                        "description": f"Web uygulamasında {len(data.get('parameters', []))} parametre ve {len(data.get('forms', []))} form tespit edildi",
                        "evidence": f"Parametreler: {data.get('parameters', [])[:5]}, Formlar: {data.get('forms', [])[:3]}",
                        "target": self.current_target,
                        "technology": "Web Application"
                    }
                    self._add_finding(finding)
            
            elif tool_name in ["verify_xss", "verify_sqli", "verify_lfi"]:
                vulnerabilities = data.get("vulnerabilities", [])
                if vulnerabilities:
                    for vuln in vulnerabilities:
                        finding = {
                            "title": vuln.get("type", f"{tool_name} vulnerability"),
                            "severity": vuln.get("severity", "medium"),
                            "description": vuln.get("description", "Vulnerability detected"),
                            "evidence": vuln.get("evidence", "Proof of concept available"),
                            "target": self.current_target,
                            "technology": "Web Application"
                        }
                        self._add_finding(finding)
            
            elif tool_name == "vuln_http_header_analyzer":
                missing_headers = data.get("missing_security_headers", [])
                if missing_headers:
                    finding = {
                        "title": "Missing Security Headers",
                        "severity": "medium",
                        "description": f"Eksik güvenlik header'ları: {', '.join(missing_headers)}",
                        "evidence": f"Missing headers: {missing_headers}",
                        "target": self.current_target,
                        "technology": "HTTP"
                    }
                    self._add_finding(finding)
            
            elif tool_name == "infra_exposed_panels_finder":
                panels = data.get("discovered_panels", [])
                if panels:
                    finding = {
                        "title": "Exposed Admin Panels",
                        "severity": "high",
                        "description": f"{len(panels)} admin panel ve management interface keşfedildi",
                        "evidence": f"Discovered panels: {panels[:3]}",
                        "target": self.current_target,
                        "technology": "Infrastructure"
                    }
                    self._add_finding(finding)
            
            elif tool_name == "enum_directory_bruteforce":
                directories = data.get("directories", [])
                if directories:
                    finding = {
                        "title": "Sensitive Directories",
                        "severity": "medium",
                        "description": f"{len(directories)} hassas dizin keşfedildi",
                        "evidence": f"Directories: {directories[:5]}",
                        "target": self.current_target,
                        "technology": "Web Application"
                    }
                    self._add_finding(finding)
            
            # Genel bilgi toplama
            self.discovered_information["last_successful_tool"] = tool_name
            self.discovered_information["total_tools_executed"] = len(self.discovered_information.get("vulnerabilities", []))
    
    def _add_finding(self, finding: Dict[str, Any]):
        """Yeni bulgu ekle"""
        if not hasattr(self, '_findings'):
            self._findings = []
        
        # Duplicate kontrolü
        existing_titles = [f.get("title", "") for f in self._findings]
        if finding.get("title", "") not in existing_titles:
            self._findings.append(finding)
            logger.info(f"🔍 Yeni bulgu eklendi: {finding.get('title')} ({finding.get('severity')})")
    
    def get_findings(self) -> List[Dict[str, Any]]:
        """Tüm bulguları döndür"""
        return getattr(self, '_findings', [])

    def _make_json_serializable(self, obj):
        """Objeyi JSON serializable hale getir"""
        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, set):
            return list(obj)
        elif hasattr(obj, '__dict__'):
            return self._make_json_serializable(obj.__dict__)
        else:
            return obj

    def _create_state_from_context(self) -> AgentState:
        """Context'ten AgentState oluştur"""
        state = AgentState(self.current_target, self.user_task)
        state.discovered_information = self.discovered_information
        return state

    def _create_final_state(self, target: str, user_task: str, success: bool) -> AgentState:
        """Final state oluştur"""
        state = AgentState(target, user_task)
        state.success = success
        state.execution_time = (datetime.now() - datetime.now()).total_seconds()  # Placeholder
        
        # Bulguları state'e ekle
        findings = self.get_findings()
        if findings:
            state.findings = findings
            logger.info(f"📊 {len(findings)} bulgu final state'e eklendi")
        
        # Context bilgilerini de ekle
        state.discovered_information = self.discovered_information.copy()
        return state

    async def _call_gemini(self, prompt: str, timeout_seconds: int = 60) -> str:
        """Gemini API'sini çağır - TIMEOUT ile (60s)"""
        try:
            # Timeout ile çalıştır
            response = await asyncio.wait_for(
                self.model.generate_content_async(prompt),
                timeout=timeout_seconds
            )
            
            # Response kontrolü
            if not response or not response.text:
                logger.warning("Empty response from Gemini API")
                return '{"action": "stop", "reasoning": "Gemini boş yanıt döndürdü"}'
            
            # Response'u temizle
            text = response.text.strip()
            
            # "JSON{" şeklinde başlıyorsa temizle
            if text.startswith('JSON{'):
                text = text[4:]  # "JSON" kelimesini kaldır
            elif text.startswith('json{'):
                text = text[4:]
            
            # JSON formatında mı kontrol et
            if text.startswith('{') and text.endswith('}'):
                return text
            elif '```json' in text.lower():
                # Markdown formatından JSON çıkar
                start_marker = '```json'
                start = text.lower().find(start_marker) + len(start_marker)
                end = text.find('```', start)
                if start > len(start_marker) - 1 and end > start:
                    return text[start:end].strip()
            
            # Son çare: { ile } arasını çıkar
            if '{' in text and '}' in text:
                start_idx = text.find('{')
                end_idx = text.rfind('}') + 1
                json_text = text[start_idx:end_idx]
                logger.info(f"JSON çıkarıldı: {json_text[:100]}...")
                return json_text
            
            logger.warning(f"Unexpected response format: {text[:100]}...")
            return '{"action": "stop", "reasoning": "Gemini beklenmeyen format döndürdü"}'
        
        except asyncio.TimeoutError:
            logger.error(f"Gemini API timeout after {timeout_seconds}s")
            # Timeout durumunda sensible default döndür
            return '{"action": "stop", "reasoning": "Gemini API timeout - test tamamlandı"}'
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return '{"action": "stop", "reasoning": "Gemini API hatası - test tamamlandı"}'

    async def _print_tool_result(self, tool_name: str, result: Dict[str, Any]):
        """Tool sonucunu güzel formatta yazdır"""
        print(f"\n{'='*60}")
        print(f"🔧 TOOL SONUCU: {tool_name}")
        print(f"{'='*60}")
        
        if result.get("success", False):
            print(f"✅ Durum: BAŞARILI")
            print(f"📊 Özet: {result.get('ai_summary', 'Sonuç alındı')}")
            
            data = result.get("data", {})
            if data:
                print(f"\n📋 DETAYLI VERİLER:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            
            recommendations = result.get("recommendations", [])
            if recommendations:
                print(f"\n💡 ÖNERİLER:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"   {i}. {rec.get('title', 'Öneri')}")
                    print(f"      {rec.get('description', 'Açıklama yok')}")
        else:
            print(f"❌ Durum: BAŞARISIZ")
            print(f"🚨 Hata: {result.get('error', 'Bilinmeyen hata')}")
        
        print(f"{'='*60}\n")

    async def _print_final_analysis(self, analysis: Dict[str, Any]):
        """Final analizi güzel formatta yazdır"""
        print(f"\n{'='*80}")
        print(f"📊 FİNAL GÜVENLİK ANALİZİ")
        print(f"{'='*80}")
        
        # Risk seviyesi
        risk_level = analysis.get("risk_level", "Bilinmiyor")
        risk_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(risk_level.lower(), "⚪")
        print(f"{risk_emoji} Risk Seviyesi: {risk_level.upper()}")
        
        # Güvenlik açıkları
        vulnerabilities = analysis.get("security_vulnerabilities", [])
        if vulnerabilities:
            print(f"\n🚨 TESPİT EDİLEN GÜVENLİK AÇIKLARI ({len(vulnerabilities)} adet):")
            for i, vuln in enumerate(vulnerabilities, 1):
                severity = vuln.get("severity", "Bilinmiyor")
                severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(severity.lower(), "⚪")
                print(f"   {i}. {severity_emoji} {vuln.get('type', 'Bilinmiyor')} - {severity.upper()}")
                print(f"      📝 {vuln.get('description', 'Açıklama yok')}")
                if vuln.get('cvss_score'):
                    print(f"      📊 CVSS: {vuln.get('cvss_score')}")
        
        # Öneriler
        recommendations = analysis.get("recommendations", [])
        if recommendations:
            print(f"\n💡 ÖNCELİKLİ ÖNERİLER:")
            for i, rec in enumerate(recommendations, 1):
                priority = rec.get("priority", "Bilinmiyor")
                priority_emoji = {"immediate": "🔴", "short_term": "🟠", "long_term": "🟡"}.get(priority.lower(), "⚪")
                print(f"   {i}. {priority_emoji} {rec.get('description', 'Öneri yok')}")
        
        # Executive Summary
        exec_summary = analysis.get("executive_summary", "")
        if exec_summary:
            print(f"\n📋 YÖNETİCİ ÖZETİ:")
            print(f"   {exec_summary}")
        
        print(f"{'='*80}\n")

    def _generate_execution_summary(self) -> Dict[str, Any]:
        """Execution özeti oluştur"""
        successful_tools = len([h for h in self.execution_history if h.get("success", False)])
        failed_tools = len([h for h in self.execution_history if not h.get("success", False)])
        
        return {
            "total_tools_executed": len(self.execution_history),
            "successful_tools": successful_tools,
            "failed_tools": failed_tools,
            "success_rate": f"{(successful_tools / len(self.execution_history) * 100):.1f}%" if self.execution_history else "0%",
            "discovered_information_keys": list(self.discovered_information.keys()),
            "execution_time": self.execution_history[-1].get("timestamp", "unknown") if self.execution_history else "unknown"
        }

    def _create_final_state(self, target: str, user_task: str, success: bool) -> AgentState:
        """Final state oluştur"""
        state = AgentState(target, user_task)
        state.status = "completed" if success else "failed"
        state.context_summary = self.discovered_information.copy()
        return state

    async def health_check(self) -> Dict[str, Any]:
        """Sistem sağlık kontrolü"""
        return {
            "status": "healthy",
            "available_tools": len(self.mcp_server.get_tool_list()['categories']),
            "current_target": self.current_target,
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0-dynamic"
        }

    async def _print_professional_report(self, report: Dict[str, Any]):
        """Profesyonel raporu güzel formatta yazdır"""
        if not report or report.get("report_type") == "fallback":
            print(f"\n{'='*80}")
            print(f"📋 PROFESYONEL RAPOR")
            print(f"{'='*80}")
            print("⚠️ Profesyonel rapor oluşturulamadı, basit analiz kullanılıyor.")
            return
            
        print(f"\n{'='*80}")
        print(f"📋 PROFESYONEL PENTEST RAPORU")
        print(f"{'='*80}")
        
        # Executive Summary
        exec_summary = report.get("executive_summary", {})
        if exec_summary:
            print(f"\n🎯 YÖNETİCİ ÖZETİ:")
            print(f"   📊 Risk Seviyesi: {exec_summary.get('risk_level', 'Bilinmiyor')}")
            print(f"   🔍 Test Kapsamı: {exec_summary.get('scope', 'Bilinmiyor')}")
            print(f"   ⏱️ Test Süresi: {exec_summary.get('duration', 'Bilinmiyor')}")
            print(f"   📈 Bulunan Açık: {exec_summary.get('vulnerabilities_found', 0)}")
        
        # Technical Findings
        tech_findings = report.get("technical_findings", [])
        if tech_findings:
            print(f"\n🔧 TEKNİK BULGULAR ({len(tech_findings)} adet):")
            for i, finding in enumerate(tech_findings, 1):
                print(f"   {i}. {finding.get('title', 'Başlık yok')}")
                print(f"      📝 {finding.get('description', 'Açıklama yok')}")
                print(f"      📊 CVSS: {finding.get('cvss_score', 'N/A')}")
                print(f"      🎯 Risk: {finding.get('risk_level', 'Bilinmiyor')}")
        
        # Compliance Status
        compliance = report.get("compliance_status", {})
        if compliance:
            print(f"\n📋 UYUMLULUK DURUMU:")
            for standard, status in compliance.items():
                status_emoji = {"compliant": "✅", "non_compliant": "❌", "partial": "⚠️"}.get(status.lower(), "❓")
                print(f"   {status_emoji} {standard.upper()}: {status}")
        
        # Recommendations
        recommendations = report.get("recommendations", [])
        if recommendations:
            print(f"\n💡 ÖNERİLER ({len(recommendations)} adet):")
            for i, rec in enumerate(recommendations, 1):
                priority = rec.get("priority", "Bilinmiyor")
                priority_emoji = {"immediate": "🔴", "short_term": "🟠", "long_term": "🟡"}.get(priority.lower(), "⚪")
                print(f"   {i}. {priority_emoji} {rec.get('title', 'Başlık yok')}")
                print(f"      📝 {rec.get('description', 'Açıklama yok')}")
                print(f"      ⏱️ Süre: {rec.get('effort', 'Bilinmiyor')}")
                print(f"      🎯 Etki: {rec.get('impact', 'Bilinmiyor')}")
        
        print("=" * 80)

    async def _save_session_for_report(self, final_results: Dict[str, Any]):
        """Rapor arayüzü için session verisini kaydet"""
        try:
            import json
            from datetime import datetime
            
            # Session ID oluştur
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            session_id = f"pentest_{timestamp}"
            
            # Session dosyası
            session_file = f"session_{session_id}.json"
            
            # Session verisini kaydet
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(final_results, f, indent=2, ensure_ascii=False)
            
            # Session ID'yi global olarak sakla (rapor arayüzü için)
            self.current_session_id = session_id
            
            print(f"💾 Session kaydedildi: {session_file}")
            print(f"🆔 Session ID: {session_id}")
            
        except Exception as e:
            print(f"⚠️ Session kaydetme hatası: {e}")

    async def _print_expert_summary(self, analysis: Dict[str, Any], report: Dict[str, Any]):
        """Uzman seviyesi basit özet - RAG entegrasyonu ile etkili"""
        print(f"\n{'='*80}")
        print(f"📊 HIZLI ÖZET - UZMAN SEVİYESİ")
        print(f"{'='*80}")
        
        # Execution summary'yi al veya oluştur
        execution_summary = self._generate_execution_summary()
        
        # Test bilgileri
        print(f"🎯 Hedef: {self.current_target}")
        print(f"⏱️ Süre: {execution_summary.get('execution_time', 'Bilinmiyor')}")
        print(f"🔧 Tool: {len(self.execution_history)} adet çalıştırıldı")
        
        # Risk seviyesi ve CVSS (RAG'dan gelen risk skoru)
        risk_level = analysis.get("risk_level", "Bilinmiyor")
        risk_score = report.get("risk_score", 0)
        risk_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(risk_level.lower(), "⚪")
        print(f"\n{risk_emoji} Risk Seviyesi: {risk_level.upper()} (Skor: {risk_score}/100)")
        
        # RAG Dynamic Insights
        dynamic_insights = report.get("dynamic_insights", {})
        if dynamic_insights:
            print(f"\n🎯 ANA TEHDİT VEKTÖRÜ:")
            print(f"   🚨 Primary Threat: {dynamic_insights.get('primary_threat_vector', 'Bilinmiyor')}")
            print(f"   ⚡ Acil Aksiyon: {dynamic_insights.get('immediate_actions_required', 0)} adet")
            print(f"   📈 Stratejik Öneri: {len(dynamic_insights.get('strategic_recommendations', []))} adet")
        
        # Attack surface analizi
        attack_surface = analysis.get("attack_surface_analysis", {})
        if attack_surface:
            print(f"\n🎯 SALDIRI YÜZEYİ:")
            print(f"   🌐 Endpoint: {attack_surface.get('discovered_endpoints', 'Bilinmiyor')}")
            print(f"   🔌 Açık Port: {attack_surface.get('open_ports', 'Bilinmiyor')}")
            print(f"   ⚙️ Teknoloji: {attack_surface.get('technologies', 'Bilinmiyor')}")
            print(f"   🛡️ Güvenlik: {attack_surface.get('security_headers', 'Bilinmiyor')}")
        
        # Güvenlik açıkları detaylı özeti (RAG ile zenginleştirilmiş)
        vulnerabilities = analysis.get("security_vulnerabilities", [])
        if vulnerabilities:
            critical_count = len([v for v in vulnerabilities if v.get("severity", "").lower() == "critical"])
            high_count = len([v for v in vulnerabilities if v.get("severity", "").lower() == "high"])
            medium_count = len([v for v in vulnerabilities if v.get("severity", "").lower() == "medium"])
            low_count = len([v for v in vulnerabilities if v.get("severity", "").lower() == "low"])
            
            print(f"\n🚨 GÜVENLİK AÇIKLARI ({len(vulnerabilities)} adet):")
            if critical_count > 0:
                print(f"   🔴 Kritik: {critical_count} açık")
            if high_count > 0:
                print(f"   🟠 Yüksek: {high_count} açık")
            if medium_count > 0:
                print(f"   🟡 Orta: {medium_count} açık")
            if low_count > 0:
                print(f"   🟢 Düşük: {low_count} açık")
        
        # En kritik açıklar detaylı (RAG ile zenginleştirilmiş)
        if vulnerabilities:
            critical_vulns = [v for v in vulnerabilities if v.get("severity", "").lower() == "critical"]
            high_vulns = [v for v in vulnerabilities if v.get("severity", "").lower() == "high"]
            
            if critical_vulns:
                print(f"\n🔴 KRİTİK AÇIKLAR:")
                for i, vuln in enumerate(critical_vulns[:3], 1):  # İlk 3 kritik açık
                    print(f"   {i}. {vuln.get('type', 'Bilinmiyor')}")
                    print(f"      📝 {vuln.get('description', 'Açıklama yok')[:100]}...")
                    if vuln.get('cvss_score'):
                        print(f"      📊 CVSS: {vuln.get('cvss_score')}")
                    if vuln.get('cve_id'):
                        print(f"      🆔 CVE: {vuln.get('cve_id')}")
                    if vuln.get('exploit_available'):
                        print(f"      ⚠️ Exploit Mevcut: {vuln.get('exploit_available')}")
                    if vuln.get('exploitability'):
                        print(f"      ⚡ Exploit: {vuln.get('exploitability')}")
                    if vuln.get('business_impact'):
                        print(f"      💼 İş Etkisi: {vuln.get('business_impact')}")
                    if vuln.get('rag_confidence'):
                        print(f"      🎯 RAG Güven: {vuln.get('rag_confidence')}")
            
            if high_vulns and not critical_vulns:
                print(f"\n🟠 YÜKSEK RİSKLİ AÇIKLAR:")
                for i, vuln in enumerate(high_vulns[:3], 1):  # İlk 3 yüksek açık
                    print(f"   {i}. {vuln.get('type', 'Bilinmiyor')}")
                    print(f"      📝 {vuln.get('description', 'Açıklama yok')[:100]}...")
                    if vuln.get('cvss_score'):
                        print(f"      📊 CVSS: {vuln.get('cvss_score')}")
                    if vuln.get('cve_id'):
                        print(f"      🆔 CVE: {vuln.get('cve_id')}")
                    if vuln.get('rag_confidence'):
                        print(f"      🎯 RAG Güven: {vuln.get('rag_confidence')}")
        
        # Compliance durumu
        compliance = analysis.get("compliance_status", {})
        if compliance:
            print(f"\n📋 UYUMLULUK DURUMU:")
            for standard, status in compliance.items():
                status_emoji = {"compliant": "✅", "non_compliant": "❌", "partial": "⚠️"}.get(status.lower(), "❓")
                print(f"   {status_emoji} {standard.upper()}: {status}")
        
        # Test etkinliği
        test_effectiveness = analysis.get("test_effectiveness", "Bilinmiyor")
        effectiveness_emoji = {"excellent": "🟢", "good": "🟡", "moderate": "🟠", "poor": "🔴"}.get(test_effectiveness.lower(), "⚪")
        print(f"\n📈 Test Etkinliği: {effectiveness_emoji} {test_effectiveness.upper()}")
        
        # Öncelikli öneriler detaylı (RAG ile zenginleştirilmiş)
        recommendations = analysis.get("recommendations", [])
        strategic_recommendations = dynamic_insights.get("strategic_recommendations", [])
        
        if recommendations or strategic_recommendations:
            print(f"\n💡 ÖNCELİKLİ ÖNERİLER:")
            
            # Acil öneriler
            immediate_recs = [r for r in recommendations if r.get("priority", "").lower() == "immediate"]
            if immediate_recs:
                print(f"   🔴 ACİL ({len(immediate_recs)} adet):")
                for i, rec in enumerate(immediate_recs[:2], 1):  # İlk 2 acil öneri
                    print(f"      {i}. {rec.get('description', 'Açıklama yok')[:80]}...")
                    print(f"         ⏱️ Süre: {rec.get('effort', 'Bilinmiyor')} | 🎯 Etki: {rec.get('impact', 'Bilinmiyor')}")
            
            # Kısa vadeli öneriler
            short_term_recs = [r for r in recommendations if r.get("priority", "").lower() == "short_term"]
            if short_term_recs and len(immediate_recs) < 2:
                print(f"   🟠 KISA VADELİ ({len(short_term_recs)} adet):")
                for i, rec in enumerate(short_term_recs[:2], 1):  # İlk 2 kısa vadeli öneri
                    print(f"      {i}. {rec.get('description', 'Açıklama yok')[:80]}...")
            
            # Stratejik öneriler (RAG'dan)
            if strategic_recommendations:
                print(f"   📈 STRATEJİK ({len(strategic_recommendations)} adet):")
                for i, rec in enumerate(strategic_recommendations[:2], 1):  # İlk 2 stratejik öneri
                    print(f"      {i}. {rec[:80]}...")
        
        # Executive summary (RAG ile zenginleştirilmiş)
        exec_summary = analysis.get("executive_summary", "")
        executive_summary = report.get("executive_summary", {})
        
        if exec_summary or executive_summary:
            print(f"\n💼 YÖNETİCİ ÖZETİ:")
            if exec_summary:
                print(f"   {exec_summary[:200]}...")
            elif executive_summary:
                print(f"   🎯 Hedef: {executive_summary.get('scope', 'Bilinmiyor')}")
                print(f"   📊 Risk Skoru: {executive_summary.get('risk_score', 'N/A')}/100")
                print(f"   🚨 Kritik Bulgu: {executive_summary.get('critical_findings', 0)} adet")
                print(f"   ⚠️ Yüksek Bulgu: {executive_summary.get('high_findings', 0)} adet")
                print(f"   📈 Test Etkinliği: {executive_summary.get('test_effectiveness', 'N/A')}")
                print(f"   📋 Compliance Gap: {executive_summary.get('compliance_gaps', 0)} adet")
        
        # RAG bilgileri
        if dynamic_insights:
            print(f"\n🤖 RAG ENTEGRASYONU:")
            print(f"   🎯 Primary Threat Vector: {dynamic_insights.get('primary_threat_vector', 'N/A')}")
            print(f"   ⚡ Immediate Actions: {dynamic_insights.get('immediate_actions_required', 0)} adet")
            print(f"   📈 Strategic Recommendations: {len(dynamic_insights.get('strategic_recommendations', []))} adet")
        
        print("=" * 80)

    async def _print_report_option(self):
        """Rapor oluşturma seçeneği"""
        print(f"\n{'='*80}")
        print(f"📋 DETAYLI RAPOR")
        print(f"{'='*80}")
        print("💡 Detaylı penetrasyon test raporu için:")
        print("   🔧 Teknik bulgular, CVSS skorları, exploit kodları")
        print("   📊 Compliance analizi (PCI DSS, GDPR, ISO27001)")
        print("   💼 Executive summary ve business impact")
        print("   📈 Risk matrix ve remediation roadmap")
        print("\n🚀 Rapor arayüzüne geçmek için:")
        print("   [RAPOR OLUŞTUR] butonuna tıklayın")
        print("   → Rapor arayüzünde detaylı analiz görüntülenecek")
        if hasattr(self, 'current_session_id'):
            print(f"   🆔 Session ID: {self.current_session_id}")
        print("=" * 80)
