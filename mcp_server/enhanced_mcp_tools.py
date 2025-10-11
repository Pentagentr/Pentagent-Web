"""
PentagentMCPServer - Pentagent MCP Araçlarını Yöneten Merkezi Sunucu

Bu modül, Pentagent projesinin MCP uyumlu araçlarını yöneten merkezi sunucuyu içerir.
Tüm araçlar MCPTool base sınıfından miras alır ve standart MCP JSON formatında çıktı üretir.
"""

import asyncio
import logging
import sys
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add project root to path for tool imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# MCP Tool integration
try:
    from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel
    MCP_AVAILABLE = True
except ImportError as e:
    MCP_AVAILABLE = False
    print(f"Warning: MCPTool not available: {e}")

logger = logging.getLogger(__name__)

class PentagentMCPServer:
    """
    Pentagent MCP Araçlarını Yöneten Merkezi Sunucu
    
    Bu sınıf, Pentagent projesinin MCP uyumlu araçlarını yönetir.
    Orchestrator ve Planner ile entegre çalışır.
    """
    
    def __init__(self):
        """PentagentMCPServer'ı başlat"""
        self.tools = {}
        self.start_time = datetime.now()
        
        # Performance metrics
        self.performance_metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "tools_loaded": 0
        }
        
        # Initialize tools
        self._initialize_tools()
        
    def get_tool_list(self) -> Dict[str, Any]:
        """Get categorized tool list"""
        categories = {
            "Reconnaissance": [],
            "Vulnerability Scanning": [],
            "API Security": [],
            "Infrastructure": [],
            "Cloud Security": []
        }
        
        # Tools'ları kategorilere göre grupla
        for tool_name, tool_info in self.tools.items():
            if 'enum_' in tool_name or 'recon_' in tool_name or 'intel_' in tool_name:
                categories["Reconnaissance"].append(tool_name)
            elif 'vuln_' in tool_name or 'verify_' in tool_name:
                categories["Vulnerability Scanning"].append(tool_name)
            elif 'api_' in tool_name:
                categories["API Security"].append(tool_name)
            elif 'infra_' in tool_name or 'enum_' in tool_name:
                categories["Infrastructure"].append(tool_name)
            elif 'cloud_' in tool_name or 's3_' in tool_name:
                categories["Cloud Security"].append(tool_name)
            else:
                categories["Reconnaissance"].append(tool_name)  # Default
        
        return {
            "server_version": "3.0.0",
            "total_tools": len(self.tools),
            "status": "active",
            "message": "PentagentMCPServer aktif",
            "categories": categories
        }
    
    def _initialize_tools(self):
        """Tüm MCP araçlarını başlat ve kaydet"""
        if not MCP_AVAILABLE:
            logger.error("MCP base sınıfı mevcut değil - araçlar yüklenemiyor")
            return
        
        try:
            # API Security Tools
            self._register_tool("api_vuln_jwt_tester", self._create_jwt_tester_tool())
            self._register_tool("api_vuln_idor_scanner", self._create_idor_scanner_tool())
            self._register_tool("api_finder_active", self._create_api_finder_tool())
            
            # Reconnaissance Tools
            self._register_tool("enum_port_scanner", self._create_port_scanner_tool())
            self._register_tool("enum_tech_detector", self._create_tech_detector_tool())
            self._register_tool("enum_web_crawler", self._create_web_crawler_tool())
            self._register_tool("enum_directory_bruteforce", self._create_directory_bruteforce_tool())
            self._register_tool("enum_firewall_detector", self._create_firewall_detector_tool())
            self._register_tool("recon_passive_subfinder", self._create_subfinder_tool())
            self._register_tool("enum_subdomain_bruteforcer", self._create_subdomain_bruteforcer_tool())
            self._register_tool("recon_dns_analyzer", self._create_dns_analyzer_tool())
            self._register_tool("recon_whois_lookup", self._create_whois_tool())
            self._register_tool("recon_origin_ip_finder", self._create_origin_ip_finder_tool())
            self._register_tool("intel_historical_analyzer", self._create_historical_analyzer_tool())
            self._register_tool("intel_code_leak_scanner", self._create_code_leak_scanner_tool())
            self._register_tool("rec_audit_email_security", self._create_email_security_tool())
            self._register_tool("recon_api_endpoint_finder", self._create_api_endpoint_finder_tool())
            
            # Vulnerability Scanning Tools
            self._register_tool("vuln_idor_tester", self._create_vuln_idor_tester_tool())
            self._register_tool("vuln_http_header_analyzer", self._create_http_header_analyzer_tool())
            self._register_tool("vul_depency_scanner", self._create_dependency_scanner_tool())
            self._register_tool("verify_xss", self._create_xss_verifier_tool())
            self._register_tool("verify_sqli", self._create_sqli_verifier_tool())
            self._register_tool("verify_lfi", self._create_lfi_verifier_tool())
            
            # Cloud Security Tools
            self._register_tool("cloud_s3_bucket_scanner", self._create_s3_scanner_tool())
            
            # Infrastructure Tools
            self._register_tool("infra_exposed_panels_finder", self._create_exposed_panels_tool())
            
            logger.info(f"✅ {len(self.tools)} araç başarıyla kaydedildi")
            
        except Exception as e:
            logger.error(f"❌ Araç başlatma hatası: {e}")
    
    def _create_jwt_tester_tool(self):
        """ApiVulnJwtTesterTool instance'ı oluştur"""
        try:
            from tools.api_vuln_jwt_tester import ApiVulnJwtTesterTool
            return ApiVulnJwtTesterTool()
        except ImportError as e:
            logger.error(f"ApiVulnJwtTesterTool import edilemedi: {e}")
            return None
    
    def _create_idor_scanner_tool(self):
        """ApiVulnIdorScannerTool instance'ı oluştur"""
        try:
            from tools.api_vuln_idor_scanner import ApiVulnIdorScannerTool
            return ApiVulnIdorScannerTool()
        except ImportError as e:
            logger.error(f"ApiVulnIdorScannerTool import edilemedi: {e}")
            return None
    
    def _create_api_finder_tool(self):
        """ReconApiFinderActive instance'ı oluştur"""
        try:
            from tools.api_finder_active import ReconApiFinderActive
            return ReconApiFinderActive()
        except ImportError as e:
            logger.error(f"ReconApiFinderActive import edilemedi: {e}")
            return None
    
    def _create_port_scanner_tool(self):
        """PortScannerModule instance'ı oluştur"""
        try:
            from tools.enum_port_scanner import PortScannerModule
            return PortScannerModule()
        except ImportError as e:
            logger.error(f"PortScannerModule import edilemedi: {e}")
            return None
    
    def _create_tech_detector_tool(self):
        """TechDetectorModule instance'ı oluştur"""
        try:
            from tools.enum_tech_detector import TechDetectorModule
            return TechDetectorModule()
        except ImportError as e:
            logger.error(f"TechDetectorModule import edilemedi: {e}")
            return None
    
    def _create_web_crawler_tool(self):
        """EnumWebCrawlerTool instance'ı oluştur"""
        try:
            from tools.enum_web_crawler import EnumWebCrawlerTool
            return EnumWebCrawlerTool()
        except ImportError as e:
            logger.error(f"EnumWebCrawlerTool import edilemedi: {e}")
            return None
    
    def _create_directory_bruteforce_tool(self):
        """EnumDirectoryBruteforcerTool instance'ı oluştur"""
        try:
            from tools.enum_directory_bruteforce import EnumDirectoryBruteforcerTool
            return EnumDirectoryBruteforcerTool()
        except ImportError as e:
            logger.error(f"EnumDirectoryBruteforcerTool import edilemedi: {e}")
            return None
    
    def _create_firewall_detector_tool(self):
        """EnumFirewallDetectorTool instance'ı oluştur"""
        try:
            from tools.enum_firewall_detector import EnumFirewallDetectorTool
            return EnumFirewallDetectorTool()
        except ImportError as e:
            logger.error(f"EnumFirewallDetectorTool import edilemedi: {e}")
            return None
    
    def _create_subfinder_tool(self):
        """SubdomainFinderModule instance'ı oluştur"""
        try:
            from tools.recon_passive_subfinder_tool import SubdomainFinderModule
            return SubdomainFinderModule()
        except ImportError as e:
            logger.error(f"SubdomainFinderModule import edilemedi: {e}")
            return None
    
    def _create_subdomain_bruteforcer_tool(self):
        """SubdomainBruteforceModule instance'ı oluştur"""
        try:
            from tools.enum_subdomain_bruteforcer import enum_subdomain_bruteforcer
            return enum_subdomain_bruteforcer
        except ImportError as e:
            logger.error(f"SubdomainBruteforceModule import edilemedi: {e}")
            return None
    
    def _create_dns_analyzer_tool(self):
        """ReconDnsAnalyzerTool instance'ı oluştur"""
        try:
            from tools.rec_dns_analyzer import ReconDnsAnalyzerTool
            return ReconDnsAnalyzerTool()
        except ImportError as e:
            logger.error(f"ReconDnsAnalyzerTool import edilemedi: {e}")
            return None
    
    def _create_whois_tool(self):
        """ReconWhoisLookupTool instance'ı oluştur"""
        try:
            from tools.rec_whois_tool import ReconWhoisLookupTool
            return ReconWhoisLookupTool()
        except ImportError as e:
            logger.error(f"ReconWhoisLookupTool import edilemedi: {e}")
            return None
    
    def _create_origin_ip_finder_tool(self):
        """ReconOriginIPFinderTool instance'ı oluştur"""
        try:
            from tools.recon_origin_ip_finder import recon_origin_ip_finder
            return recon_origin_ip_finder
        except ImportError as e:
            logger.error(f"ReconOriginIPFinderTool import edilemedi: {e}")
            return None
    
    def _create_historical_analyzer_tool(self):
        """IntelHistoricalAnalyzerTool instance'ı oluştur"""
        try:
            from tools.rec_intel_historical_analyzer import IntelHistoricalAnalyzerTool
            return IntelHistoricalAnalyzerTool()
        except ImportError as e:
            logger.error(f"IntelHistoricalAnalyzerTool import edilemedi: {e}")
            return None
    
    def _create_code_leak_scanner_tool(self):
        """IntelCodeLeakScannerTool instance'ı oluştur"""
        try:
            from tools.rec_intel_code_scanner import IntelCodeLeakScannerTool
            return IntelCodeLeakScannerTool()
        except ImportError as e:
            logger.error(f"IntelCodeLeakScannerTool import edilemedi: {e}")
            return None
    
    def _create_email_security_tool(self):
        """RecAuditEmailSecurityTool instance'ı oluştur"""
        try:
            from tools.rec_audit_email_security import RecAuditEmailSecurityTool
            return RecAuditEmailSecurityTool()
        except ImportError as e:
            logger.error(f"RecAuditEmailSecurityTool import edilemedi: {e}")
            return None
    
    def _create_api_endpoint_finder_tool(self):
        """ReconApiEndpointFinderTool instance'ı oluştur"""
        try:
            from tools.recon_api_endpoint_finder import ReconApiEndpointFinderTool
            return ReconApiEndpointFinderTool()
        except ImportError as e:
            logger.error(f"ReconApiEndpointFinderTool import edilemedi: {e}")
            return None
    
    def _create_vuln_idor_tester_tool(self):
        """VulnIDORTester instance'ı oluştur"""
        try:
            from tools.vuln_idor_tester import VulnIDORTester
            return VulnIDORTester()
        except ImportError as e:
            logger.error(f"VulnIDORTester import edilemedi: {e}")
            return None
    
    def _create_http_header_analyzer_tool(self):
        """VulnHttpHeaderAnalyzer instance'ı oluştur"""
        try:
            from tools.vuln_http_header_analyzer import VulnHttpHeaderAnalyzer
            return VulnHttpHeaderAnalyzer()
        except ImportError as e:
            logger.error(f"VulnHttpHeaderAnalyzer import edilemedi: {e}")
            return None
    
    def _create_dependency_scanner_tool(self):
        """VulnDependencyScanner instance'ı oluştur"""
        try:
            from tools.vul_depency_scanner import VulnDependencyScanner
            return VulnDependencyScanner()
        except ImportError as e:
            logger.error(f"VulnDependencyScanner import edilemedi: {e}")
            return None
    
    def _create_xss_verifier_tool(self):
        """XssVerifier instance'ı oluştur"""
        try:
            from tools.verify_xss import XssVerifier
            return XssVerifier()
        except ImportError as e:
            logger.error(f"XssVerifier import edilemedi: {e}")
            return None
    
    def _create_sqli_verifier_tool(self):
        """SqliVerifier instance'ı oluştur"""
        try:
            from tools.verify_sqli import SqliVerifier
            return SqliVerifier()
        except ImportError as e:
            logger.error(f"SqliVerifier import edilemedi: {e}")
            return None
    
    def _create_lfi_verifier_tool(self):
        """LfiVerifier instance'ı oluştur"""
        try:
            from tools.verify_lfi import LfiVerifier
            return LfiVerifier()
        except ImportError as e:
            logger.error(f"LfiVerifier import edilemedi: {e}")
            return None
    
    def _create_s3_scanner_tool(self):
        """CloudS3Scanner instance'ı oluştur"""
        try:
            from tools.cloud_s3_bucket_scanner import CloudS3Scanner
            return CloudS3Scanner()
        except ImportError as e:
            logger.error(f"CloudS3Scanner import edilemedi: {e}")
            return None
    
    def _create_exposed_panels_tool(self):
        """InfraReconScanner instance'ı oluştur"""
        try:
            from tools.infra_exposed_panels_finder import InfraReconScanner
            return InfraReconScanner()
        except ImportError as e:
            logger.error(f"InfraReconScanner import edilemedi: {e}")
            return None
    
    def _register_tool(self, tool_name: str, tool_instance: MCPTool):
        """Aracı sunucuya kaydet"""
        if tool_instance is None:
            logger.warning(f"⚠️ {tool_name} aracı None - kaydedilmiyor")
            return
        
        if not isinstance(tool_instance, MCPTool):
            logger.error(f"❌ {tool_name} MCPTool sınıfından miras almıyor")
            return
        
        self.tools[tool_name] = tool_instance
        self.performance_metrics["tools_loaded"] = len(self.tools)
        logger.info(f"✅ {tool_name} başarıyla kaydedildi")
    
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrator'ın çağıracağı araç yürütme metodu
        
        Args:
            tool_name (str): Çalıştırılacak aracın adı
            params (Dict[str, Any]): Araç parametreleri
        
        Returns:
            Dict[str, Any]: Araç sonucu
        """
        start_time = datetime.now()
        self.performance_metrics["total_executions"] += 1
        
        try:
            # Debug için parametreleri logla
            logger.info(f"🔍 MCP Server parametreleri: {params}")
            
            if tool_name not in self.tools:
                return {
                    "success": False,
                    "error": f"Araç '{tool_name}' bulunamadı",
                    "available_tools": list(self.tools.keys()),
                    "timestamp": datetime.now().isoformat()
                }
            
            tool = self.tools[tool_name]
            
            # Araçı çalıştır (async veya sync)
            if asyncio.iscoroutinefunction(tool.run_tool):
                result = await tool.run_tool(params)
            else:
                result = tool.run_tool(params)
            
            # Performance metrics güncelle
            execution_time = (datetime.now() - start_time).total_seconds()
            self.performance_metrics["successful_executions"] += 1
            self._update_average_execution_time(execution_time)
            
            # Server metadata ekle
            if isinstance(result, dict):
                result.update({
                    "server_version": "1.0.0",
                    "execution_time": execution_time,
                    "tool_name": tool_name,
                    "server_timestamp": datetime.now().isoformat()
                })
            
            logger.info(f"✅ {tool_name} başarıyla çalıştırıldı ({execution_time:.2f}s)")
            return result
            
        except Exception as e:
            self.performance_metrics["failed_executions"] += 1
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.error(f"❌ {tool_name} çalıştırma hatası: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time,
                "tool_name": tool_name,
                "server_version": "1.0.0",
                "timestamp": datetime.now().isoformat()
            }
    
    def get_tool_info_for_planner(self) -> Dict[str, Any]:
        """
        Planner'ın kullanacağı araç bilgilerini döndür
        
        Returns:
            Dict[str, Any]: Planner için formatlanmış araç bilgileri
        """
        tool_info = {
            "server_version": "1.0.0",
            "total_tools": len(self.tools),
            "tools": {}
        }
        
        for tool_name, tool in self.tools.items():
            try:
                tool_info["tools"][tool_name] = {
                    "name": tool.name,
                    "description": tool.description,
                    "category": tool.category.value if tool.category else "unknown",
                    "version": getattr(tool, 'version', '1.0.0'),
                    "available": True
                }
            except Exception as e:
                logger.warning(f"Araç bilgisi alınamadı {tool_name}: {e}")
                tool_info["tools"][tool_name] = {
                    "name": tool_name,
                    "description": "Bilgi alınamadı",
                    "category": "unknown",
                    "version": "unknown",
                    "available": False
                }
        
        return tool_info
    
    def _update_average_execution_time(self, execution_time: float):
        """Ortalama çalıştırma süresini güncelle"""
        total_executions = self.performance_metrics["total_executions"]
        current_avg = self.performance_metrics["average_execution_time"]
        self.performance_metrics["average_execution_time"] = (
            (current_avg * (total_executions - 1) + execution_time) / total_executions
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Sunucu performans metriklerini döndür"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "server_version": "1.0.0",
            "uptime_seconds": uptime,
            "performance_metrics": self.performance_metrics,
            "tools_count": len(self.tools),
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Sunucu sağlık kontrolü"""
        try:
            return {
                "status": "healthy",
                "server_version": "1.0.0",
                "tools_loaded": len(self.tools),
                "mcp_available": MCP_AVAILABLE,
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

class EnhancedPentestMCPServerV3:
    """MCP Entegre Edilmiş Tool'ları Yöneten Professional Server"""
    
    def __init__(self):
        self.tools = {}
        self.tool_categories = {
            "reconnaissance": [],
            "web_analysis": [],
            "vulnerability_assessment": [],
            "security_analysis": []
        }
        
        # Performance metrics
        self.performance_metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "tools_loaded": 0
        }
        
        # Initialize MCP tools
        self._initialize_mcp_tools()
    
    def _initialize_mcp_tools(self):
        """Initialize all MCP integrated tools"""
        if not MCP_AVAILABLE:
            logger.error("MCP tools not available")
            return
        
        try:
            # For now, just initialize empty - this is the legacy server
            logger.info(f"✅ Enhanced MCP Server V3 initialized (legacy mode)")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP tools: {e}")
    
    # Legacy methods - simplified for compatibility
    
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with enhanced MCP integration (legacy mode)"""
        return {
            "success": False,
            "error": "EnhancedPentestMCPServerV3 is in legacy mode - use PentagentMCPServer instead",
            "tool_name": tool_name,
            "server_version": "3.0.0"
        }
    
    def get_tool_list(self) -> Dict[str, Any]:
        """Get categorized tool list (legacy mode)"""
        return {
            "server_version": "3.0.0",
            "total_tools": 0,
            "status": "legacy_mode",
            "message": "Use PentagentMCPServer for active tools",
            "categories": {
                "Reconnaissance": [],
                "Vulnerability Scanning": [],
                "API Security": [],
                "Infrastructure": [],
                "Cloud Security": []
            }
        }
    
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed tool information (legacy mode)"""
        return {
            "error": f"Tool {tool_name} not found in legacy mode",
            "message": "Use PentagentMCPServer for active tools"
        }
    
    async def execute_tool(self, tool_name: str, params: dict) -> Dict[str, Any]:
        """Tool'u çalıştır"""
        try:
            if tool_name not in self.tools:
                return {"success": False, "error": f"Tool {tool_name} not found", "data": {}}
            
            tool_instance = self.tools[tool_name]
            if tool_instance is None:
                return {"success": False, "error": f"Tool {tool_name} not available", "data": {}}
            
            # Tool'u çalıştır
            result = tool_instance.run_tool(params)
            
            # Performance metrics güncelle
            self.performance_metrics["total_executions"] += 1
            if result.get("success", False):
                self.performance_metrics["successful_executions"] += 1
            else:
                self.performance_metrics["failed_executions"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            self.performance_metrics["failed_executions"] += 1
            return {"success": False, "error": str(e), "data": {}}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check (legacy mode)"""
        return {
            "status": "legacy_mode",
            "server_version": "3.0.0",
            "message": "EnhancedPentestMCPServerV3 is in legacy mode - use PentagentMCPServer instead",
            "timestamp": datetime.now().isoformat()
        }

# Create server instances
pentagent_mcp_server = PentagentMCPServer()
enhanced_mcp_server = PentagentMCPServer()

# Export functions for easy access
def get_pentagent_mcp_server():
    """Get the PentagentMCPServer instance"""
    return pentagent_mcp_server

def get_enhanced_mcp_server():
    """Get the enhanced MCP server instance"""
    return enhanced_mcp_server

def get_tool_list():
    """Get categorized tool list"""
    return enhanced_mcp_server.get_tool_list()

def get_tool_info(tool_name: str):
    """Get detailed tool information"""
    return enhanced_mcp_server.get_tool_info(tool_name)

async def execute_tool(tool_name: str, params: Dict[str, Any]):
    """Execute a tool"""
    return await enhanced_mcp_server.execute_tool(tool_name, params)

# Main execution function
async def main():
    """Main function for testing"""
    # Test PentagentMCPServer
    server = get_pentagent_mcp_server()
    
    # Health check
    health = await server.health_check()
    print("PentagentMCPServer Health Check:")
    print(json.dumps(health, indent=2))
    
    # Tool info for planner
    tool_info = server.get_tool_info_for_planner()
    print("\nTool Info for Planner:")
    print(json.dumps(tool_info, indent=2))
    
    # Test tool execution
    if "api_vuln_jwt_tester" in server.tools:
        print("\nTesting JWT Tester Tool:")
        test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        result = await server.execute_tool("api_vuln_jwt_tester", {"token": test_token})
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())