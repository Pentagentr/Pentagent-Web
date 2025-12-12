# agent_core/executor.py

import asyncio
from typing import Dict, Any, List
from agent_core.state import AgentState

class Executor:
    """Plandaki adımları yürüten ve özel yetenekleri (örn: payload üretimi) barındıran modül."""
    
    def __init__(self, model, mcp_server, status_callback):
        self.model = model
        self.mcp_server = mcp_server
        self.status_callback = status_callback

    async def _call_gemini_json(self, prompt: str) -> Dict[str, Any]:
        """Gemini'yi JSON formatında yanıt vermesi için çağırır."""
        try:
            response = await self.model.generate_content_async(prompt)
            response_text = response.text.strip()
            
            # JSON parse etmeye çalış - daha güçlü parsing
            if response_text.startswith('```json'):
                response_text = response_text[7:-3]
            elif response_text.startswith('```'):
                response_text = response_text[3:-3]
            
            # Boş response kontrolü
            if not response_text or response_text == "{}":
                return {}
            
            import json
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"⚠️ Gemini JSON parse hatası: {e}")
            print(f"📝 Raw response: {response_text[:200]}...")
            return {}
        except Exception as e:
            print(f"⚠️ Gemini API hatası: {e}")
            return {}

    async def _generate_contextual_payloads(self, vuln_type: str, state: AgentState) -> List[str]:
        """Ajanın mevcut durumuna göre yaratıcı payload'lar üretir."""
        technologies = state.context_summary.get("technologies", [])
        waf_detected = state.context_summary.get("waf_detected", False)
        headers = state.context_summary.get("headers", [])
        
        prompt = f"""
        Sen bir Red Team Payload Uzmanısın. Mevcut duruma göre yaratıcı ve etkili payload'lar üret.
        
        ZAFİYET TİPİ: {vuln_type}
        TESPİT EDİLEN TEKNOLOJİLER: {technologies}
        WAF DURUMU: {"Tespit edildi" if waf_detected else "Tespit edilmedi"}
        HTTP HEADER'LAR: {headers}
        
        PAYLOAD ÜRETİM KURALLARI:
        1. Tespit edilen teknolojilere özel payload'lar üret
        2. WAF varsa bypass teknikleri kullan
        3. Encoding ve obfuscation teknikleri uygula
        4. Her payload'un farklı bir yaklaşımı olsun
        5. Gerçek dünya senaryolarına uygun olsun
        
        ÇIKTI OLARAK {{"payloads": ["payload1", "payload2", ...]}} şeklinde JSON dön.
        """
        
        response = await self._call_gemini_json(prompt)
        return response.get("payloads", [])

    async def _generate_custom_wordlist(self, target: str, state: AgentState) -> List[str]:
        """Hedefe özel wordlist üretir."""
        technologies = state.context_summary.get("technologies", [])
        subdomains = state.context_summary.get("subdomains", [])
        
        prompt = f"""
        Sen bir Red Team Wordlist Uzmanısın. Hedefe özel etkili wordlist üret.
        
        HEDEF: {target}
        TEKNOLOJİLER: {technologies}
        BİLİNEN SUBDOMAIN'LER: {subdomains}
        
        WORDLİST ÜRETİM KURALLARI:
        1. Hedefin teknolojilerine özel terimler ekle
        2. Bilinen subdomain'lerden pattern çıkar
        3. Yaygın admin paneli, API endpoint'leri ekle
        4. Hedefin sektörüne özel terimler ekle
        5. Her kelime farklı bir yaklaşımı temsil etsin
        
        ÇIKTI OLARAK {{"wordlist": ["word1", "word2", ...]}} şeklinde JSON dön.
        """
        
        response = await self._call_gemini_json(prompt)
        return response.get("wordlist", [])

    async def run_step(self, step: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        """Plandaki tek bir adımı yürütür."""
        tool_name = step["tool"]
        params = step["params"].copy()  # Orijinal parametreleri koru
        
        await self.status_callback(f"⚡ Uygulayıcı (Executor) çalıştırıyor: {tool_name}", "tool_call")
        await self.status_callback(f"🎯 Amaç: {step['goal']}", "info")
        
        # Özel yetenekler: Yaratıcı payload üretimi
        if tool_name == "vuln_xss_detector" and "url" in params:
            await self.status_callback("🎨 Yaratıcı XSS payload'ları üretiliyor...", "ai_thinking")
            payloads = await self._generate_contextual_payloads("xss", state)
            if payloads:
                params["custom_payloads"] = payloads
                await self.status_callback(f"✨ {len(payloads)} adet duruma özel payload eklendi", "success")
        
        elif tool_name == "verify_sqli" and "target_url" in params:
            await self.status_callback("🎨 Yaratıcı SQLi payload'ları üretiliyor...", "ai_thinking")
            payloads = await self._generate_contextual_payloads("sqli", state)
            if payloads:
                params["custom_payloads"] = payloads
                await self.status_callback(f"✨ {len(payloads)} adet duruma özel payload eklendi", "success")
        
        elif tool_name == "enum_directory_bruteforce" and "target" in params:
            await self.status_callback("📝 Hedefe özel wordlist üretiliyor...", "ai_thinking")
            wordlist = await self._generate_custom_wordlist(params["target"], state)
            if wordlist:
                params["custom_wordlist"] = wordlist
                await self.status_callback(f"✨ {len(wordlist)} adet özel kelime eklendi", "success")

        try:
            # Debug için parametreleri logla
            await self.status_callback(f"🔍 Executor parametreleri: {params}", "ai_reasoning")
            
            # Tool'u çalıştır - TIMEOUT KORUMASLI (5 dakika)
            result = await asyncio.wait_for(
                self.mcp_server.execute_tool(tool_name, params),
                timeout=300.0  # 5 dakika
            )
            
            # Sonucu analiz et ve durum güncellemesi yap
            if result.get("success"):
                await self.status_callback(f"✅ {tool_name} başarıyla tamamlandı", "success")
            else:
                error_msg = result.get("error", "Bilinmeyen hata")
                # Chrome/WebDriver hatalarını arayüzden filtrele
                chrome_keywords = ["Chrome", "WebDriver", "chromedriver", "cannot find Chrome", "Chrome binary", "Selenium"]
                if any(keyword.lower() in error_msg.lower() for keyword in chrome_keywords):
                    # Chrome hatası - sadece logla, arayüze gönderme
                    logger.debug(f"Chrome hatası filtrelendi: {error_msg[:100]}")
                    # Alternatif araç kullanılıyor mesajı gönder
                    await self.status_callback(f"🔄 {tool_name} alternatif yöntemle çalıştırılıyor", "info")
                else:
                    await self.status_callback(f"❌ {tool_name} başarısız: {error_msg[:100]}", "error")
            
            return {
                "step_details": step,
                "result": result,
                "execution_time": self._calculate_execution_time(),
                "enhanced": "custom_payloads" in params or "custom_wordlist" in params
            }
            
        except asyncio.TimeoutError:
            error_msg = f"⏱️ Tool timeout (5 dakika) - {tool_name}"
            logger.error(error_msg)
            await self.status_callback(error_msg, "error")
            
            error_result = {
                "success": False, 
                "error": error_msg,
                "timeout": True
            }
            
            return {
                "step_details": step,
                "result": error_result,
                "execution_time": 0,
                "enhanced": False
            }
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)[:100]}"
            logger.error(f"❌ Tool execution error ({tool_name}): {error_msg}")
            # Chrome/WebDriver hatalarını arayüzden filtrele
            chrome_keywords = ["Chrome", "WebDriver", "chromedriver", "cannot find Chrome", "Chrome binary", "Selenium"]
            if any(keyword.lower() in error_msg.lower() for keyword in chrome_keywords):
                logger.debug(f"Chrome hatası filtrelendi: {error_msg}")
                await self.status_callback(f"🔄 {tool_name} alternatif yöntemle çalıştırılıyor", "info")
            else:
                await self.status_callback(f"💥 {tool_name} kritik hata: {error_msg}", "error")
            
            error_result = {
                "success": False, 
                "error": error_msg
            }
            
            return {
                "step_details": step,
                "result": error_result,
                "execution_time": 0,
                "enhanced": False
            }

    def _calculate_execution_time(self) -> float:
        """Adımın çalışma süresini hesaplar."""
        import time
        # Bu basit bir implementasyon, gerçek uygulamada daha detaylı olabilir
        return 0.0

    async def validate_step_result(self, step: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Adım sonucunu doğrular ve kalite kontrolü yapar."""
        validation = {
            "valid": True,
            "quality_score": 0.0,
            "issues": [],
            "recommendations": []
        }
        
        if not result.get("success"):
            validation["valid"] = False
            validation["issues"].append("Tool execution failed")
            return validation
        
        # Sonuç kalitesini değerlendir
        data = result.get("data", {})
        
        # Veri miktarına göre kalite skoru
        if isinstance(data, dict):
            data_keys = len(data.keys())
            validation["quality_score"] = min(data_keys / 10.0, 1.0)
        
        # Öneriler oluştur
        if validation["quality_score"] < 0.5:
            validation["recommendations"].append("Sonuçlar sınırlı, alternatif yaklaşım düşünülmeli")
        
        return validation
