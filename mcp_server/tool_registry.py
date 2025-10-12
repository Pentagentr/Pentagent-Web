"""
🔧 PENTAGENT TOOL REGISTRY - Merkezi Tool Yönetim Sistemi

Tüm penetrasyon test araçlarını yükler, kaydeder ve yönetir.
Dynamic import ile hata toleranslı, kapsamlı tool registry.
"""

import logging
import importlib
import inspect
from typing import Dict, Any, List, Optional, Type
from datetime import datetime

logger = logging.getLogger(__name__)

# Tool kategorileri ve tool mapping
TOOL_MAPPING = {
    # ==================== RECONNAISSANCE ====================
    "enum_port_scanner": {
        "module": "tools.enum_port_scanner",
        "class": "PortScannerModule",
        "category": "reconnaissance",
        "description": "Port tarama ve servis keşfi",
        "priority": "high"
    },
    "enum_tech_detector": {
        "module": "tools.enum_tech_detector",
        "class": "TechDetectorModule",
        "category": "reconnaissance",
        "description": "Web teknoloji ve framework tespiti",
        "priority": "high"
    },
    "enum_web_crawler": {
        "module": "tools.enum_web_crawler",
        "class": "EnumWebCrawlerTool",
        "category": "reconnaissance",
        "description": "Web sitesi tarama ve endpoint keşfi",
        "priority": "medium"
    },
    "enum_directory_bruteforce": {
        "module": "tools.enum_directory_bruteforce",
        "class": "EnumDirectoryBruteforcerTool",
        "category": "reconnaissance",
        "description": "Directory ve dosya brute force",
        "priority": "medium"
    },
    "enum_firewall_detector": {
        "module": "tools.enum_firewall_detector",
        "class": "EnumFirewallDetectorTool",
        "category": "reconnaissance",
        "description": "WAF ve firewall tespiti",
        "priority": "medium"
    },
    "enum_subdomain_bruteforcer": {
        "module": "tools.enum_subdomain_bruteforcer",
        "class": "SubdomainBruteforceModule",
        "category": "reconnaissance",
        "description": "Subdomain brute force enumeration",
        "priority": "medium"
    },
    "recon_passive_subfinder": {
        "module": "tools.recon_passive_subfinder_tool",
        "class": "SubdomainFinderModule",
        "category": "reconnaissance",
        "description": "Pasif subdomain keşfi (Certificate Transparency)",
        "priority": "high"
    },
    "recon_dns_analyzer": {
        "module": "tools.rec_dns_analyzer",
        "class": "ReconDnsAnalyzerTool",
        "category": "reconnaissance",
        "description": "DNS kayıtları ve yapılandırma analizi",
        "priority": "high"
    },
    "recon_whois_lookup": {
        "module": "tools.rec_whois_tool",
        "class": "ReconWhoisLookupTool",
        "category": "reconnaissance",
        "description": "WHOIS bilgileri ve domain sahipliği",
        "priority": "medium"
    },
    "recon_origin_ip_finder": {
        "module": "tools.recon_origin_ip_finder",
        "class": "recon_origin_ip_finder",  # Module level object
        "category": "reconnaissance",
        "description": "CloudFlare bypass ve origin IP bulma",
        "priority": "medium"
    },
    "recon_api_endpoint_finder": {
        "module": "tools.recon_api_endpoint_finder",
        "class": "ReconApiEndpointFinderTool",
        "category": "reconnaissance",
        "description": "API endpoint keşfi ve dokümantasyon",
        "priority": "medium"
    },
    
    # ==================== THREAT INTELLIGENCE ====================
    "intel_historical_analyzer": {
        "module": "tools.rec_intel_historical_analyzer",
        "class": "IntelHistoricalAnalyzerTool",
        "category": "threat_intelligence",
        "description": "Historical web snapshot analizi (Wayback Machine)",
        "priority": "low"
    },
    "intel_code_leak_scanner": {
        "module": "tools.rec_intel_code_scanner",
        "class": "IntelCodeLeakScannerTool",
        "category": "threat_intelligence",
        "description": "GitHub code leak ve secret taraması",
        "priority": "medium"
    },
    "rec_audit_email_security": {
        "module": "tools.rec_audit_email_security",
        "class": "RecAuditEmailSecurityTool",
        "category": "reconnaissance",
        "description": "Email güvenlik yapılandırması (SPF, DKIM, DMARC)",
        "priority": "low"
    },
    
    # ==================== VULNERABILITY SCANNING ====================
    "vuln_http_header_analyzer": {
        "module": "tools.vuln_http_header_analyzer",
        "class": "VulnHttpHeaderAnalyzer",
        "category": "vulnerability_scanning",
        "description": "HTTP security header analizi",
        "priority": "high"
    },
    "vul_depency_scanner": {
        "module": "tools.vul_depency_scanner",
        "class": "VulnDependencyScanner",
        "category": "vulnerability_scanning",
        "description": "Dependency ve versiyon zafiyet taraması",
        "priority": "high"
    },
    "vuln_idor_tester": {
        "module": "tools.vuln_idor_tester",
        "class": "VulnIDORTester",
        "category": "vulnerability_scanning",
        "description": "IDOR (Insecure Direct Object Reference) testi",
        "priority": "medium"
    },
    
    # ==================== VULNERABILITY VERIFICATION ====================
    "verify_xss": {
        "module": "tools.verify_xss",
        "class": "XssVerifier",
        "category": "vulnerability_verification",
        "description": "XSS (Cross-Site Scripting) zafiyet testi (Selenium)",
        "priority": "high"
    },
    "verify_xss_http": {
        "module": "tools.verify_xss_http",
        "class": "VerifyXSSHTTP",
        "category": "vulnerability_verification",
        "description": "XSS zafiyet testi (HTTP only, lightweight)",
        "priority": "high"
    },
    "verify_sqli": {
        "module": "tools.verify_sqli",
        "class": "SqliVerifier",
        "category": "vulnerability_verification",
        "description": "SQL Injection zafiyet testi",
        "priority": "high"
    },
    "verify_lfi": {
        "module": "tools.verify_lfi",
        "class": "LfiVerifier",
        "category": "vulnerability_verification",
        "description": "LFI (Local File Inclusion) zafiyet testi",
        "priority": "medium"
    },
    
    # ==================== API SECURITY ====================
    "api_vuln_jwt_tester": {
        "module": "tools.api_vuln_jwt_tester",
        "class": "ApiVulnJwtTesterTool",
        "category": "api_security",
        "description": "JWT token güvenlik analizi ve zafiyet testi",
        "priority": "high"
    },
    "api_vuln_idor_scanner": {
        "module": "tools.api_vuln_idor_scanner",
        "class": "ApiVulnIdorScannerTool",
        "category": "api_security",
        "description": "API IDOR zafiyet taraması",
        "priority": "high"
    },
    "api_finder_active": {
        "module": "tools.api_finder_active",
        "class": "ReconApiFinderActive",
        "category": "api_security",
        "description": "Aktif API endpoint keşfi",
        "priority": "medium"
    },
    
    # ==================== CLOUD SECURITY ====================
    "cloud_s3_bucket_scanner": {
        "module": "tools.cloud_s3_bucket_scanner",
        "class": "CloudS3Scanner",
        "category": "cloud_security",
        "description": "AWS S3 bucket güvenlik taraması",
        "priority": "medium"
    },
    
    # ==================== INFRASTRUCTURE ====================
    "infra_exposed_panels_finder": {
        "module": "tools.infra_exposed_panels_finder",
        "class": "InfraReconScanner",
        "category": "infrastructure",
        "description": "Exposed admin panel ve dashboard keşfi",
        "priority": "medium"
    },
    "service_fingerprinting": {
        "module": "tools.service_fingerprinting",
        "class": "ServiceFingerprintingTool",
        "category": "infrastructure",
        "description": "Service banner grabbing ve fingerprinting",
        "priority": "medium"
    },
}


class ToolRegistry:
    """
    🔧 Merkezi Tool Registry Sistemi
    
    Tüm penetrasyon test araçlarını dinamik olarak yükler, kaydeder ve yönetir.
    Hata toleranslı import sistemi ile maksimum tool availability sağlar.
    """
    
    def __init__(self):
        """Registry'yi başlat"""
        self.tools: Dict[str, Any] = {}
        self.failed_tools: Dict[str, str] = {}
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}
        self.load_timestamp = datetime.now()
        
        logger.info("🔧 Tool Registry başlatılıyor...")
        self._load_all_tools()
        
    def _load_all_tools(self):
        """Tüm tool'ları dinamik olarak yükle"""
        total_tools = len(TOOL_MAPPING)
        loaded_count = 0
        
        for tool_name, tool_config in TOOL_MAPPING.items():
            try:
                # Dynamic import
                module = importlib.import_module(tool_config["module"])
                tool_class = getattr(module, tool_config["class"])
                
                # Tool instance oluştur
                tool_instance = tool_class()
                
                # Kaydet
                self.tools[tool_name] = tool_instance
                self.tool_metadata[tool_name] = {
                    "name": tool_name,
                    "class": tool_config["class"],
                    "category": tool_config["category"],
                    "description": tool_config["description"],
                    "priority": tool_config["priority"],
                    "loaded": True,
                    "load_time": datetime.now().isoformat()
                }
                
                loaded_count += 1
                logger.info(f"✅ {tool_name} yüklendi ({loaded_count}/{total_tools})")
                
            except ImportError as e:
                error_msg = f"Import error: {str(e)}"
                self.failed_tools[tool_name] = error_msg
                logger.warning(f"⚠️ {tool_name} yüklenemedi: {error_msg}")
                
            except AttributeError as e:
                error_msg = f"Class not found: {str(e)}"
                self.failed_tools[tool_name] = error_msg
                logger.warning(f"⚠️ {tool_name} class bulunamadı: {error_msg}")
                
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                self.failed_tools[tool_name] = error_msg
                logger.error(f"❌ {tool_name} yüklenirken hata: {error_msg}")
        
        # Sonuç özeti
        success_rate = (loaded_count / total_tools) * 100 if total_tools > 0 else 0
        logger.info(f"")
        logger.info(f"{'='*60}")
        logger.info(f"📊 TOOL REGISTRY ÖZET")
        logger.info(f"{'='*60}")
        logger.info(f"✅ Başarılı: {loaded_count}/{total_tools} ({success_rate:.1f}%)")
        logger.info(f"❌ Başarısız: {len(self.failed_tools)}/{total_tools}")
        
        if self.failed_tools:
            logger.warning(f"")
            logger.warning(f"⚠️ Yüklenemeyen Tool'lar:")
            for tool_name, error in self.failed_tools.items():
                logger.warning(f"   • {tool_name}: {error}")
        
        logger.info(f"{'='*60}")
        logger.info(f"")
    
    def get_tool(self, tool_name: str) -> Optional[Any]:
        """Tool instance'ını al"""
        return self.tools.get(tool_name)
    
    def has_tool(self, tool_name: str) -> bool:
        """Tool mevcut mu kontrol et"""
        return tool_name in self.tools
    
    def get_all_tools(self) -> Dict[str, Any]:
        """Tüm tool'ları al"""
        return self.tools.copy()
    
    def get_tools_by_category(self, category: str) -> Dict[str, Any]:
        """Kategoriye göre tool'ları filtrele"""
        filtered = {}
        for tool_name, metadata in self.tool_metadata.items():
            if metadata.get("category") == category and tool_name in self.tools:
                filtered[tool_name] = self.tools[tool_name]
        return filtered
    
    def get_tool_list_for_planner(self) -> Dict[str, Any]:
        """Planner için tool listesi (metadata ile)"""
        return {
            "total_tools": len(self.tools),
            "available_tools": list(self.tools.keys()),
            "failed_tools": list(self.failed_tools.keys()),
            "tools_metadata": self.tool_metadata,
            "categories": self._get_category_summary(),
            "load_timestamp": self.load_timestamp.isoformat()
        }
    
    def _get_category_summary(self) -> Dict[str, List[str]]:
        """Kategoriye göre tool özeti"""
        categories = {}
        for tool_name, metadata in self.tool_metadata.items():
            category = metadata.get("category", "unknown")
            if category not in categories:
                categories[category] = []
            if tool_name in self.tools:
                categories[category].append(tool_name)
        return categories
    
    def get_status(self) -> Dict[str, Any]:
        """Registry durumu"""
        return {
            "status": "healthy" if self.tools else "degraded",
            "total_tools": len(TOOL_MAPPING),
            "loaded_tools": len(self.tools),
            "failed_tools": len(self.failed_tools),
            "success_rate": (len(self.tools) / len(TOOL_MAPPING)) * 100 if TOOL_MAPPING else 0,
            "load_timestamp": self.load_timestamp.isoformat(),
            "uptime_seconds": (datetime.now() - self.load_timestamp).total_seconds()
        }
    
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tool çalıştır (async/sync hybrid wrapper)
        
        Args:
            tool_name: Tool adı
            params: Tool parametreleri (target key'i mutlaka olmalı)
        
        Returns:
            Tool execution result
        """
        import asyncio
        start_time = datetime.now()
        
        try:
            # Tool kontrolü
            if tool_name not in self.tools:
                return {
                    "success": False,
                    "error": f"Tool '{tool_name}' bulunamadı",
                    "available_tools": list(self.tools.keys())[:10],  # İlk 10 tool
                    "timestamp": datetime.now().isoformat()
                }
            
            tool_instance = self.tools[tool_name]
            
            # Parametre kontrolü ve düzeltmesi
            if not params:
                params = {}
            
            # Target parametresi yoksa hata
            if "target" not in params:
                return {
                    "success": False,
                    "error": f"'target' parametresi gerekli",
                    "tool_name": tool_name,
                    "received_params": list(params.keys()),
                    "timestamp": datetime.now().isoformat()
                }
            
            # PARAMETRE NORMALIZE: target → url dönüşümü (bazı tool'lar url bekler)
            normalized_params = params.copy()
            if "url" not in normalized_params and "target" in normalized_params:
                # HTTP header analyzer gibi tool'lar için
                if tool_name in ["vuln_http_header_analyzer", "enum_tech_detector", "enum_web_crawler"]:
                    normalized_params["url"] = normalized_params["target"]
            
            # Tool'u çalıştır (async/sync detection)
            logger.info(f"🔧 {tool_name} çalıştırılıyor... (target: {params.get('target')})")
            
            # Async mi sync mi kontrol et
            import inspect
            if inspect.iscoroutinefunction(tool_instance.run_tool):
                # Async tool
                result = await tool_instance.run_tool(normalized_params)
            else:
                # Sync tool - run in executor to not block
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, tool_instance.run_tool, normalized_params)
            
            # Execution time ekle
            execution_time = (datetime.now() - start_time).total_seconds()
            if isinstance(result, dict):
                result["execution_time"] = execution_time
                result["tool_name"] = tool_name
                result["timestamp"] = datetime.now().isoformat()
            
            logger.info(f"✅ {tool_name} tamamlandı ({execution_time:.2f}s)")
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Tool execution error: {str(e)}"
            logger.error(f"❌ {tool_name} hatası: {error_msg}")
            
            return {
                "success": False,
                "error": error_msg,
                "tool_name": tool_name,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }


# Global registry instance
_registry = None

def get_tool_registry() -> ToolRegistry:
    """Global tool registry instance'ını al (singleton)"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


# Convenience functions
def get_tool(tool_name: str) -> Optional[Any]:
    """Tool instance'ını al"""
    return get_tool_registry().get_tool(tool_name)

def has_tool(tool_name: str) -> bool:
    """Tool mevcut mu"""
    return get_tool_registry().has_tool(tool_name)

def get_all_tools() -> Dict[str, Any]:
    """Tüm tool'ları al"""
    return get_tool_registry().get_all_tools()

async def execute_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Tool çalıştır"""
    return await get_tool_registry().execute_tool(tool_name, params)


if __name__ == "__main__":
    # Test
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n🔧 TOOL REGISTRY TEST\n")
    
    registry = get_tool_registry()
    status = registry.get_status()
    
    print(f"Status: {status['status']}")
    print(f"Loaded: {status['loaded_tools']}/{status['total_tools']}")
    print(f"Success Rate: {status['success_rate']:.1f}%")
    
    print(f"\n✅ Available Tools:")
    for tool_name in sorted(registry.tools.keys())[:10]:
        print(f"   • {tool_name}")
    
    if registry.failed_tools:
        print(f"\n❌ Failed Tools:")
        for tool_name in sorted(registry.failed_tools.keys()):
            print(f"   • {tool_name}")

