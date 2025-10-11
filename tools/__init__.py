"""
Pentagent MCP Tools Package
===========================

Bu paket, Pentagent projesinin tüm MCP (Master Control Program) uyumlu araçlarını içerir.
Tüm araçlar MCPTool base sınıfından miras alır ve standart MCP JSON formatında çıktı üretir.

Araç Kategorileri:
- Reconnaissance: Keşif ve bilgi toplama araçları
- Vulnerability Scanning: Zafiyet tarama araçları  
- API Security: API güvenlik test araçları
- Infrastructure: Altyapı analiz araçları
"""

# Base MCP Tool sınıfını import et
try:
    from .base_mcp_tool import MCPTool, ToolCategory, PriorityLevel
    MCP_BASE_AVAILABLE = True
except ImportError as e:
    MCP_BASE_AVAILABLE = False
    print(f"Warning: MCP base tool import failed: {e}")

# =============================================================================
# RECONNAISSANCE TOOLS (Keşif Araçları)
# =============================================================================

# Enumeration Tools
try:
    from .enum_firewall_detector import EnumFirewallDetectorTool
    from .enum_tech_detector import TechDetectorModule
    from .enum_web_crawler import EnumWebCrawlerTool
    from .enum_directory_bruteforce import EnumDirectoryBruteforcerTool
    from .enum_port_scanner import PortScannerModule
    ENUM_TOOLS_AVAILABLE = True
except ImportError as e:
    ENUM_TOOLS_AVAILABLE = False
    print(f"Warning: Enumeration tools import failed: {e}")

# Reconnaissance Tools
try:
    from .rec_audit_email_security import RecAuditEmailSecurityTool
    from .rec_dns_analyzer import ReconDnsAnalyzerTool
    from .rec_intel_code_scanner import IntelCodeLeakScannerTool
    from .rec_intel_historical_analyzer import IntelHistoricalAnalyzerTool
    from .rec_whois_tool import ReconWhoisLookupTool
    from .recon_api_endpoint_finder import ReconApiEndpointFinderTool
    from .recon_passive_subfinder_tool import SubdomainFinderModule
    RECON_TOOLS_AVAILABLE = True
except ImportError as e:
    RECON_TOOLS_AVAILABLE = False
    print(f"Warning: Reconnaissance tools import failed: {e}")

# Infrastructure Tools
try:
    from .infra_exposed_panels_finder import InfraReconScanner
    INFRA_TOOLS_AVAILABLE = True
except ImportError as e:
    INFRA_TOOLS_AVAILABLE = False
    print(f"Warning: Infrastructure tools import failed: {e}")

# =============================================================================
# VULNERABILITY SCANNING TOOLS (Zafiyet Tarama Araçları)
# =============================================================================

try:
    from .vul_depency_scanner import VulnDependencyScanner
    from .vuln_http_header_analyzer import VulnHttpHeaderAnalyzer
    from .vuln_idor_tester import VulnIDORTester
    from .verify_lfi import LfiVerifier
    from .verify_sqli import SqliVerifier
    from .verify_xss import XssVerifier
    VULN_TOOLS_AVAILABLE = True
except ImportError as e:
    VULN_TOOLS_AVAILABLE = False
    print(f"Warning: Vulnerability scanning tools import failed: {e}")

# =============================================================================
# API SECURITY TOOLS (API Güvenlik Araçları)
# =============================================================================

try:
    from .api_finder_active import ReconApiFinderActive
    from .api_vuln_idor_scanner import ApiVulnIdorScannerTool
    from .api_vuln_jwt_tester import ApiVulnJwtTesterTool
    API_TOOLS_AVAILABLE = True
except ImportError as e:
    API_TOOLS_AVAILABLE = False
    print(f"Warning: API security tools import failed: {e}")

# =============================================================================
# CLOUD SECURITY TOOLS (Bulut Güvenlik Araçları)
# =============================================================================

try:
    from .cloud_s3_bucket_scanner import CloudS3Scanner
    CLOUD_TOOLS_AVAILABLE = True
except ImportError as e:
    CLOUD_TOOLS_AVAILABLE = False
    print(f"Warning: Cloud security tools import failed: {e}")

# =============================================================================
# TOOL REGISTRY (Araç Kayıt Defteri)
# =============================================================================

# Tüm mevcut araçları kategorilere göre grupla
RECONNAISSANCE_TOOLS = []
VULNERABILITY_TOOLS = []
API_SECURITY_TOOLS = []
INFRASTRUCTURE_TOOLS = []
CLOUD_TOOLS = []

if ENUM_TOOLS_AVAILABLE:
    RECONNAISSANCE_TOOLS.extend([
        EnumFirewallDetectorTool,
        TechDetectorModule,
        EnumWebCrawlerTool,
        EnumDirectoryBruteforcerTool,
        PortScannerModule
    ])

if RECON_TOOLS_AVAILABLE:
    RECONNAISSANCE_TOOLS.extend([
        RecAuditEmailSecurityTool,
        ReconDnsAnalyzerTool,
        IntelCodeLeakScannerTool,
        IntelHistoricalAnalyzerTool,
        ReconWhoisLookupTool,
        ReconApiEndpointFinderTool,
        SubdomainFinderModule
    ])

if INFRA_TOOLS_AVAILABLE:
    INFRASTRUCTURE_TOOLS.extend([
        InfraReconScanner
    ])

if VULN_TOOLS_AVAILABLE:
    VULNERABILITY_TOOLS.extend([
        VulnDependencyScanner,
        VulnHttpHeaderAnalyzer,
        VulnIDORTester,
        LfiVerifier,
        SqliVerifier,
        XssVerifier
    ])

if API_TOOLS_AVAILABLE:
    API_SECURITY_TOOLS.extend([
        ReconApiFinderActive,
        ApiVulnIdorScannerTool,
        ApiVulnJwtTesterTool
    ])

if CLOUD_TOOLS_AVAILABLE:
    CLOUD_TOOLS.extend([
        CloudS3Scanner
    ])

# Tüm araçları tek listede topla
ALL_TOOLS = (
    RECONNAISSANCE_TOOLS + 
    VULNERABILITY_TOOLS + 
    API_SECURITY_TOOLS + 
    INFRASTRUCTURE_TOOLS + 
    CLOUD_TOOLS
)

# =============================================================================
# UTILITY FUNCTIONS (Yardımcı Fonksiyonlar)
# =============================================================================

def get_tools_by_category(category: ToolCategory):
    """Belirli bir kategoriye ait araçları döndürür."""
    if not MCP_BASE_AVAILABLE:
        return []
    
    tools_by_category = {
        ToolCategory.RECONNAISSANCE: RECONNAISSANCE_TOOLS,
        ToolCategory.VULNERABILITY_SCANNING: VULNERABILITY_TOOLS,
        ToolCategory.API_SECURITY: API_SECURITY_TOOLS,
        ToolCategory.INFRASTRUCTURE: INFRASTRUCTURE_TOOLS,
        ToolCategory.CLOUD_SECURITY: CLOUD_TOOLS
    }
    
    return tools_by_category.get(category, [])

def get_tool_by_name(name: str):
    """İsme göre araç bulur."""
    for tool_class in ALL_TOOLS:
        if hasattr(tool_class, 'name') and tool_class().name == name:
            return tool_class
    return None

def get_tool_count():
    """Toplam araç sayısını döndürür."""
    return len(ALL_TOOLS)

def get_tool_stats():
    """Araç istatistiklerini döndürür."""
    return {
        'total_tools': len(ALL_TOOLS),
        'reconnaissance_tools': len(RECONNAISSANCE_TOOLS),
        'vulnerability_tools': len(VULNERABILITY_TOOLS),
        'api_security_tools': len(API_SECURITY_TOOLS),
        'infrastructure_tools': len(INFRASTRUCTURE_TOOLS),
        'cloud_tools': len(CLOUD_TOOLS),
        'mcp_base_available': MCP_BASE_AVAILABLE,
        'enum_tools_available': ENUM_TOOLS_AVAILABLE,
        'recon_tools_available': RECON_TOOLS_AVAILABLE,
        'vuln_tools_available': VULN_TOOLS_AVAILABLE,
        'api_tools_available': API_TOOLS_AVAILABLE,
        'infra_tools_available': INFRA_TOOLS_AVAILABLE,
        'cloud_tools_available': CLOUD_TOOLS_AVAILABLE
    }

def list_all_tools():
    """Tüm araçları listeler."""
    tools_list = []
    for tool_class in ALL_TOOLS:
        try:
            tool_instance = tool_class()
            tools_list.append({
                'name': tool_instance.name,
                'description': tool_instance.description,
                'category': tool_instance.category.value if hasattr(tool_instance.category, 'value') else str(tool_instance.category),
                'version': getattr(tool_instance, 'version', 'Unknown')
            })
        except Exception as e:
            print(f"Warning: Could not instantiate tool {tool_class.__name__}: {e}")
    
    return tools_list

# =============================================================================
# EXPORTS (Dışa Aktarılanlar)
# =============================================================================

# Base classes
__all__ = ['MCPTool', 'ToolCategory', 'PriorityLevel']

# Tool categories
__all__.extend([
    'RECONNAISSANCE_TOOLS',
    'VULNERABILITY_TOOLS', 
    'API_SECURITY_TOOLS',
    'INFRASTRUCTURE_TOOLS',
    'CLOUD_TOOLS',
    'ALL_TOOLS'
])

# Utility functions
__all__.extend([
    'get_tools_by_category',
    'get_tool_by_name', 
    'get_tool_count',
    'get_tool_stats',
    'list_all_tools'
])

# Individual tools (conditional exports)
if ENUM_TOOLS_AVAILABLE:
    __all__.extend([
        'EnumFirewallDetectorTool',
        'TechDetectorModule', 
        'EnumWebCrawlerTool',
        'EnumDirectoryBruteforcerTool',
        'PortScannerModule'
    ])

if RECON_TOOLS_AVAILABLE:
    __all__.extend([
        'RecAuditEmailSecurityTool',
        'ReconDnsAnalyzerTool',
        'IntelCodeLeakScannerTool', 
        'IntelHistoricalAnalyzerTool',
        'ReconWhoisLookupTool',
        'ReconApiEndpointFinderTool',
        'SubdomainFinderModule'
    ])

if INFRA_TOOLS_AVAILABLE:
    __all__.extend(['InfraReconScanner'])

if VULN_TOOLS_AVAILABLE:
    __all__.extend([
        'VulnDependencyScanner',
        'VulnHttpHeaderAnalyzer',
        'VulnIDORTester',
        'LfiVerifier',
        'SqliVerifier', 
        'XssVerifier'
    ])

if API_TOOLS_AVAILABLE:
    __all__.extend([
        'ReconApiFinderActive',
        'ApiVulnIdorScannerTool',
        'ApiVulnJwtTesterTool'
    ])

if CLOUD_TOOLS_AVAILABLE:
    __all__.extend(['CloudS3Scanner'])

# Package metadata
__version__ = "3.0.0-MCP"
__description__ = "Pentagent MCP Tools Package - Complete cybersecurity automation toolkit"
__author__ = "Pentagent Development Team"
__license__ = "MIT"

# Package status
PACKAGE_STATUS = {
    'version': __version__,
    'description': __description__,
    'author': __author__,
    'total_tools': len(ALL_TOOLS),
    'categories': {
        'reconnaissance': len(RECONNAISSANCE_TOOLS),
        'vulnerability_scanning': len(VULNERABILITY_TOOLS),
        'api_security': len(API_SECURITY_TOOLS),
        'infrastructure': len(INFRASTRUCTURE_TOOLS),
        'cloud_security': len(CLOUD_TOOLS)
    },
    'availability': {
        'mcp_base': MCP_BASE_AVAILABLE,
        'enum_tools': ENUM_TOOLS_AVAILABLE,
        'recon_tools': RECON_TOOLS_AVAILABLE,
        'vuln_tools': VULN_TOOLS_AVAILABLE,
        'api_tools': API_TOOLS_AVAILABLE,
        'infra_tools': INFRA_TOOLS_AVAILABLE,
        'cloud_tools': CLOUD_TOOLS_AVAILABLE
    }
}

__all__.append('PACKAGE_STATUS')