"""
🧪 COMPREHENSIVE RAG SEARCH TEST SUITE (2022-2024 CVEs)

RAG arama sisteminin performansını değerlendirir:
- 100 test query (2022-2024 CVE'lere odaklı)
- Gerçekçi kullanıcı soruları
- Başarı oranı hesaplama
- Detaylı performans analizi
"""

import os
import sys

# ✅ CRITICAL: Set environment BEFORE any other imports!
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["USE_HF_INFERENCE_API"] = "true"  # TEST WITH HF INFERENCE API (canlı sistem simülasyonu)

import logging
import time
from typing import List, Dict, Any, Tuple
from datetime import datetime

# RAG modülünü import et - Parent directory'den
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
rag_pent_path = os.path.join(parent_dir, 'Rag-Pent')
sys.path.insert(0, rag_pent_path)

from Qdrant.cve_search import CVESearchEngine, SearchConfig

logging.basicConfig(
    level=logging.WARNING,  # Test sırasında sadece önemli loglar
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== TEST QUERIES (2022-2024 CVEs) ====================

TEST_QUERIES = [
    # ==================== CATEGORY 1: PURE SEMANTIC - USER QUESTIONS (40 queries) ====================
    
    # Genel güvenlik soruları (kullanıcıların gerçekten sorduğu şeyler)
    {
        "query": "How do I detect SQL injection in my web application?",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["sql", "injection"],
        "min_results": 5,
        "description": "SQL injection nasıl tespit edilir?"
    },
    {
        "query": "What are the latest critical vulnerabilities in web applications?",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["critical", "web"],
        "min_results": 5,
        "description": "Son kritik web zafiyetleri"
    },
    {
        "query": "Remote code execution attacks and prevention methods",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["remote", "code", "execution"],
        "min_results": 5,
        "description": "RCE saldırıları ve önleme"
    },
    {
        "query": "Authentication bypass vulnerabilities in modern systems",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["authentication", "bypass"],
        "min_results": 5,
        "description": "Modern sistemlerde auth bypass"
    },
    {
        "query": "Cross-site scripting XSS prevention techniques",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["xss", "cross-site"],
        "min_results": 5,
        "description": "XSS önleme teknikleri"
    },
    {
        "query": "Path traversal and directory traversal attacks",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["path", "traversal"],
        "min_results": 5,
        "description": "Path traversal saldırıları"
    },
    {
        "query": "Server-side request forgery SSRF exploitation",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["ssrf", "request", "forgery"],
        "min_results": 3,
        "description": "SSRF exploitation"
    },
    {
        "query": "Arbitrary file upload vulnerabilities and risks",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["file", "upload"],
        "min_results": 3,
        "description": "Dosya yükleme zafiyetleri"
    },
    {
        "query": "Command injection in web applications",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["command", "injection"],
        "min_results": 5,
        "description": "Command injection"
    },
    {
        "query": "Privilege escalation vulnerabilities in Linux systems",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["privilege", "escalation"],
        "min_results": 5,
        "description": "Privilege escalation Linux"
    },
    
    # Türkçe sorular (gerçek kullanıcı dili)
    {
        "query": "Web uygulamalarında SQL enjeksiyonu nasıl tespit edilir?",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["sql"],
        "min_results": 5,
        "description": "[TR] SQL tespiti"
    },
    {
        "query": "Zararlı dosya yükleme açıklarından nasıl korunurum?",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["file", "upload"],
        "min_results": 3,
        "description": "[TR] Dosya yükleme korunma"
    },
    {
        "query": "Kimlik doğrulama atlatma saldırıları nedir?",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["authentication"],
        "min_results": 5,
        "description": "[TR] Auth bypass nedir"
    },
    {
        "query": "Sunucu tarafı istek sahteciliği SSRF nedir?",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["ssrf"],
        "min_results": 3,
        "description": "[TR] SSRF nedir"
    },
    {
        "query": "Yetki yükseltme zafiyetleri nasıl çalışır?",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["privilege", "escalation"],
        "min_results": 5,
        "description": "[TR] Privilege escalation"
    },
    
    # Spesifik saldırı tipleri
    {
        "query": "Deserialization vulnerabilities in Java applications",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["deserialization", "java"],
        "min_results": 3,
        "description": "Java deserialization"
    },
    {
        "query": "XXE external entity injection attacks",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["xxe", "xml"],
        "min_results": 3,
        "description": "XXE injection"
    },
    {
        "query": "LDAP injection vulnerabilities",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["ldap"],
        "min_results": 2,
        "description": "LDAP injection"
    },
    {
        "query": "Buffer overflow exploitation techniques",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["buffer", "overflow"],
        "min_results": 5,
        "description": "Buffer overflow"
    },
    {
        "query": "Race condition security vulnerabilities",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["race", "condition"],
        "min_results": 3,
        "description": "Race condition"
    },
    {
        "query": "Memory corruption exploits in C applications",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["memory", "corruption"],
        "min_results": 5,
        "description": "Memory corruption C"
    },
    {
        "query": "Heap overflow security implications",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["heap", "overflow"],
        "min_results": 3,
        "description": "Heap overflow"
    },
    {
        "query": "Use after free vulnerability exploitation",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["use after free"],
        "min_results": 3,
        "description": "Use after free"
    },
    {
        "query": "Integer overflow attacks and risks",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["integer", "overflow"],
        "min_results": 5,
        "description": "Integer overflow"
    },
    {
        "query": "DNS rebinding attack techniques",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["dns", "rebinding"],
        "min_results": 2,
        "description": "DNS rebinding"
    },
    {
        "query": "Cross-origin resource sharing CORS misconfiguration",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["cors"],
        "min_results": 3,
        "description": "CORS misconfiguration"
    },
    {
        "query": "JWT token vulnerabilities and attacks",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["jwt", "token"],
        "min_results": 5,
        "description": "JWT vulnerabilities"
    },
    {
        "query": "API authentication bypass methods",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["api", "authentication"],
        "min_results": 5,
        "description": "API auth bypass"
    },
    {
        "query": "GraphQL injection attacks",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["graphql"],
        "min_results": 2,
        "description": "GraphQL injection"
    },
    {
        "query": "WebSocket security vulnerabilities",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["websocket"],
        "min_results": 2,
        "description": "WebSocket güvenlik"
    },
    {
        "query": "Docker container escape techniques",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["docker", "container"],
        "min_results": 3,
        "description": "Docker escape"
    },
    {
        "query": "Kubernetes cluster security issues",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["kubernetes"],
        "min_results": 3,
        "description": "Kubernetes güvenlik"
    },
    {
        "query": "Cloud infrastructure vulnerabilities AWS Azure",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["cloud", "aws"],
        "min_results": 3,
        "description": "Cloud infrastructure"
    },
    {
        "query": "Supply chain attacks in software",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["supply", "chain"],
        "min_results": 3,
        "description": "Supply chain"
    },
    {
        "query": "Zero-day vulnerabilities and exploitation",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["zero", "day"],
        "min_results": 5,
        "description": "Zero-day"
    },
    {
        "query": "Ransomware attack vectors and prevention",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["ransomware"],
        "min_results": 2,
        "description": "Ransomware"
    },
    {
        "query": "Phishing and social engineering attacks",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["phishing"],
        "min_results": 1,
        "description": "Phishing"
    },
    {
        "query": "Malware detection and analysis techniques",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["malware"],
        "min_results": 3,
        "description": "Malware detection"
    },
    {
        "query": "Network intrusion detection systems",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["network", "intrusion"],
        "min_results": 2,
        "description": "IDS sistemleri"
    },
    {
        "query": "Wireless network security vulnerabilities",
        "category": "PURE_SEMANTIC",
        "expected_keywords": ["wireless", "network"],
        "min_results": 2,
        "description": "Wireless güvenlik"
    },
    
    # ==================== CATEGORY 2: VERSION-BASED (25 queries) ====================
    # 2022-2024 CVE'lerin olduğu popüler teknolojiler
    
    {
        "query": "Apache HTTP Server 2.4.51 vulnerabilities",
        "category": "VERSION_BASED",
        "expected_keywords": ["apache", "2.4"],
        "min_results": 1,
        "description": "Apache 2.4.51"
    },
    {
        "query": "Node.js 18.x security issues",
        "category": "VERSION_BASED",
        "expected_keywords": ["node", "18"],
        "min_results": 1,
        "description": "Node.js 18"
    },
    {
        "query": "Python 3.10 vulnerabilities",
        "category": "VERSION_BASED",
        "expected_keywords": ["python", "3.10"],
        "min_results": 1,
        "description": "Python 3.10"
    },
    {
        "query": "OpenSSL 3.0 security flaws",
        "category": "VERSION_BASED",
        "expected_keywords": ["openssl", "3.0"],
        "min_results": 1,
        "description": "OpenSSL 3.0"
    },
    {
        "query": "Nginx 1.22 vulnerabilities",
        "category": "VERSION_BASED",
        "expected_keywords": ["nginx", "1.22"],
        "min_results": 1,
        "description": "Nginx 1.22"
    },
    {
        "query": "WordPress 6.0 security issues",
        "category": "VERSION_BASED",
        "expected_keywords": ["wordpress", "6.0"],
        "min_results": 1,
        "description": "WordPress 6.0"
    },
    {
        "query": "Drupal 10.x vulnerabilities",
        "category": "VERSION_BASED",
        "expected_keywords": ["drupal", "10"],
        "min_results": 1,
        "description": "Drupal 10"
    },
    {
        "query": "Joomla 4.x security flaws",
        "category": "VERSION_BASED",
        "expected_keywords": ["joomla", "4"],
        "min_results": 1,
        "description": "Joomla 4"
    },
    {
        "query": "MySQL 8.0 vulnerabilities",
        "category": "VERSION_BASED",
        "expected_keywords": ["mysql", "8.0"],
        "min_results": 1,
        "description": "MySQL 8.0"
    },
    {
        "query": "PostgreSQL 14.x security issues",
        "category": "VERSION_BASED",
        "expected_keywords": ["postgresql", "14"],
        "min_results": 1,
        "description": "PostgreSQL 14"
    },
    {
        "query": "MongoDB 5.x vulnerabilities",
        "category": "VERSION_BASED",
        "expected_keywords": ["mongodb", "5"],
        "min_results": 1,
        "description": "MongoDB 5"
    },
    {
        "query": "Redis 7.0 security flaws",
        "category": "VERSION_BASED",
        "expected_keywords": ["redis", "7.0"],
        "min_results": 1,
        "description": "Redis 7.0"
    },
    {
        "query": "Kubernetes 1.25 vulnerabilities",
        "category": "VERSION_BASED",
        "expected_keywords": ["kubernetes", "1.25"],
        "min_results": 1,
        "description": "Kubernetes 1.25"
    },
    {
        "query": "Docker 20.x security issues",
        "category": "VERSION_BASED",
        "expected_keywords": ["docker", "20"],
        "min_results": 1,
        "description": "Docker 20"
    },
    {
        "query": "VMware ESXi 7.0 vulnerabilities",
        "category": "VERSION_BASED",
        "expected_keywords": ["vmware", "esxi", "7.0"],
        "min_results": 1,
        "description": "VMware ESXi 7.0"
    },
    {
        "query": "Microsoft Exchange Server 2019 security flaws",
        "category": "VERSION_BASED",
        "expected_keywords": ["exchange", "2019"],
        "min_results": 1,
        "description": "Exchange 2019"
    },
    {
        "query": "Citrix NetScaler 13.x vulnerabilities",
        "category": "VERSION_BASED",
        "expected_keywords": ["citrix", "netscaler"],
        "min_results": 1,
        "description": "Citrix NetScaler 13"
    },
    {
        "query": "Fortinet FortiOS 7.x security issues",
        "category": "VERSION_BASED",
        "expected_keywords": ["fortinet", "fortios"],
        "min_results": 1,
        "description": "FortiOS 7"
    },
    {
        "query": "Cisco IOS XE 17.x vulnerabilities",
        "category": "VERSION_BASED",
        "expected_keywords": ["cisco", "ios"],
        "min_results": 1,
        "description": "Cisco IOS XE 17"
    },
    {
        "query": "Palo Alto Networks PAN-OS 10.x security flaws",
        "category": "VERSION_BASED",
        "expected_keywords": ["palo", "alto", "pan-os"],
        "min_results": 1,
        "description": "PAN-OS 10"
    },
    {
        "query": "Juniper Junos OS 21.x vulnerabilities",
        "category": "VERSION_BASED",
        "expected_keywords": ["juniper", "junos"],
        "min_results": 1,
        "description": "Junos OS 21"
    },
    {
        "query": "SonicWall SonicOS 7.x security issues",
        "category": "VERSION_BASED",
        "expected_keywords": ["sonicwall", "sonicos"],
        "min_results": 1,
        "description": "SonicOS 7"
    },
    {
        "query": "Atlassian Confluence 7.x vulnerabilities",
        "category": "VERSION_BASED",
        "expected_keywords": ["atlassian", "confluence"],
        "min_results": 1,
        "description": "Confluence 7"
    },
    {
        "query": "GitLab 15.x security flaws",
        "category": "VERSION_BASED",
        "expected_keywords": ["gitlab", "15"],
        "min_results": 1,
        "description": "GitLab 15"
    },
    {
        "query": "Jenkins 2.x vulnerabilities",
        "category": "VERSION_BASED",
        "expected_keywords": ["jenkins", "2"],
        "min_results": 1,
        "description": "Jenkins 2"
    },
    
    # ==================== CATEGORY 3: CVE_DIRECT (15 queries - 2022-2024 gerçek CVE'ler) ====================
    
    {
        "query": "CVE-2022-0995",
        "category": "CVE_DIRECT",
        "expected_cves": ["CVE-2022-0995"],
        "min_results": 1,
        "description": "Linux kernel privilege escalation"
    },
    {
        "query": "CVE-2022-30190",
        "category": "CVE_DIRECT",
        "expected_cves": ["CVE-2022-30190"],
        "min_results": 1,
        "description": "Microsoft Windows Support Diagnostic Tool (Follina)"
    },
    {
        "query": "CVE-2023-23397",
        "category": "CVE_DIRECT",
        "expected_cves": ["CVE-2023-23397"],
        "min_results": 1,
        "description": "Microsoft Outlook elevation of privilege"
    },
    {
        "query": "CVE-2023-0286",
        "category": "CVE_DIRECT",
        "expected_cves": ["CVE-2023-0286"],
        "min_results": 1,
        "description": "OpenSSL X.509 certificate verification bypass"
    },
    {
        "query": "CVE-2023-2868",
        "category": "CVE_DIRECT",
        "expected_cves": ["CVE-2023-2868"],
        "min_results": 1,
        "description": "Kubernetes privilege escalation"
    },
    {
        "query": "CVE-2023-20198",
        "category": "CVE_DIRECT",
        "expected_cves": ["CVE-2023-20198"],
        "min_results": 1,
        "description": "Cisco IOS XE web UI privilege escalation"
    },
    {
        "query": "CVE-2023-34362",
        "category": "CVE_DIRECT",
        "expected_cves": ["CVE-2023-34362"],
        "min_results": 1,
        "description": "Progress MOVEit Transfer SQL injection"
    },
    {
        "query": "CVE-2023-4966",
        "category": "CVE_DIRECT",
        "expected_cves": ["CVE-2023-4966"],
        "min_results": 1,
        "description": "Citrix NetScaler ADC buffer overflow (Citrix Bleed)"
    },
    {
        "query": "CVE-2024-3400",
        "category": "CVE_DIRECT",
        "expected_cves": ["CVE-2024-3400"],
        "min_results": 1,
        "description": "Palo Alto Networks PAN-OS command injection"
    },
    {
        "query": "CVE-2024-21413",
        "category": "CVE_DIRECT",
        "expected_cves": ["CVE-2024-21413"],
        "min_results": 1,
        "description": "Microsoft Outlook remote code execution"
    },
    {
        "query": "CVE-2024-4577",
        "category": "CVE_DIRECT",
        "expected_cves": ["CVE-2024-4577"],
        "min_results": 1,
        "description": "PHP CGI argument injection"
    },
    {
        "query": "CVE-2024-1086",
        "category": "CVE_DIRECT",
        "expected_cves": ["CVE-2024-1086"],
        "min_results": 1,
        "description": "Linux kernel use-after-free"
    },
    {
        "query": "CVE-2024-23897",
        "category": "CVE_DIRECT",
        "expected_cves": ["CVE-2024-23897"],
        "min_results": 1,
        "description": "Jenkins CLI arbitrary file read"
    },
    {
        "query": "CVE-2024-27322",
        "category": "CVE_DIRECT",
        "expected_cves": ["CVE-2024-27322"],
        "min_results": 1,
        "description": "Kubernetes privilege escalation"
    },
    {
        "query": "CVE-2024-0195",
        "category": "CVE_DIRECT",
        "expected_cves": ["CVE-2024-0195"],
        "min_results": 1,
        "description": "SonicWall SMA remote code execution"
    },
    
    # ==================== CATEGORY 4: HYBRID (15 queries - CVE + Context) ====================
    
    {
        "query": "CVE-2022-30190 Follina Windows vulnerability details",
        "category": "HYBRID",
        "expected_cves": ["CVE-2022-30190"],
        "expected_keywords": ["follina", "windows"],
        "min_results": 1,
        "description": "Follina full context"
    },
    {
        "query": "CVE-2023-34362 MOVEit Transfer SQL injection exploit",
        "category": "HYBRID",
        "expected_cves": ["CVE-2023-34362"],
        "expected_keywords": ["moveit", "sql"],
        "min_results": 1,
        "description": "MOVEit full context"
    },
    {
        "query": "CVE-2023-4966 Citrix Bleed buffer overflow details",
        "category": "HYBRID",
        "expected_cves": ["CVE-2023-4966"],
        "expected_keywords": ["citrix", "bleed"],
        "min_results": 1,
        "description": "Citrix Bleed full"
    },
    {
        "query": "CVE-2024-3400 Palo Alto command injection vulnerability",
        "category": "HYBRID",
        "expected_cves": ["CVE-2024-3400"],
        "expected_keywords": ["palo", "alto", "command"],
        "min_results": 1,
        "description": "Palo Alto command injection"
    },
    {
        "query": "CVE-2023-20198 Cisco IOS XE privilege escalation",
        "category": "HYBRID",
        "expected_cves": ["CVE-2023-20198"],
        "expected_keywords": ["cisco", "privilege"],
        "min_results": 1,
        "description": "Cisco IOS XE escalation"
    },
    {
        "query": "CVE-2024-4577 PHP CGI vulnerability exploitation",
        "category": "HYBRID",
        "expected_cves": ["CVE-2024-4577"],
        "expected_keywords": ["php", "cgi"],
        "min_results": 1,
        "description": "PHP CGI exploit"
    },
    {
        "query": "CVE-2024-21413 Microsoft Outlook RCE vulnerability",
        "category": "HYBRID",
        "expected_cves": ["CVE-2024-21413"],
        "expected_keywords": ["outlook", "rce"],
        "min_results": 1,
        "description": "Outlook RCE"
    },
    {
        "query": "CVE-2022-0995 Linux kernel privilege escalation exploit",
        "category": "HYBRID",
        "expected_cves": ["CVE-2022-0995"],
        "expected_keywords": ["linux", "kernel"],
        "min_results": 1,
        "description": "Linux kernel escalation"
    },
    {
        "query": "CVE-2023-23397 Outlook elevation vulnerability",
        "category": "HYBRID",
        "expected_cves": ["CVE-2023-23397"],
        "expected_keywords": ["outlook", "elevation"],
        "min_results": 1,
        "description": "Outlook elevation"
    },
    {
        "query": "CVE-2023-0286 OpenSSL certificate bypass",
        "category": "HYBRID",
        "expected_cves": ["CVE-2023-0286"],
        "expected_keywords": ["openssl", "certificate"],
        "min_results": 1,
        "description": "OpenSSL bypass"
    },
    {
        "query": "CVE-2023-2868 Kubernetes privilege escalation",
        "category": "HYBRID",
        "expected_cves": ["CVE-2023-2868"],
        "expected_keywords": ["kubernetes", "privilege"],
        "min_results": 1,
        "description": "K8s escalation"
    },
    {
        "query": "CVE-2024-1086 Linux kernel use-after-free exploit",
        "category": "HYBRID",
        "expected_cves": ["CVE-2024-1086"],
        "expected_keywords": ["linux", "use after free"],
        "min_results": 1,
        "description": "Linux UAF"
    },
    {
        "query": "CVE-2024-23897 Jenkins CLI file read vulnerability",
        "category": "HYBRID",
        "expected_cves": ["CVE-2024-23897"],
        "expected_keywords": ["jenkins", "file", "read"],
        "min_results": 1,
        "description": "Jenkins file read"
    },
    {
        "query": "CVE-2024-27322 Kubernetes privilege escalation flaw",
        "category": "HYBRID",
        "expected_cves": ["CVE-2024-27322"],
        "expected_keywords": ["kubernetes", "privilege"],
        "min_results": 1,
        "description": "K8s escalation 2024"
    },
    {
        "query": "CVE-2024-0195 SonicWall remote code execution",
        "category": "HYBRID",
        "expected_cves": ["CVE-2024-0195"],
        "expected_keywords": ["sonicwall", "rce"],
        "min_results": 1,
        "description": "SonicWall RCE"
    },
    
    # ==================== CATEGORY 5: COMPLEX (5 queries - Multi-context) ====================
    
    {
        "query": "VMware ESXi critical vulnerabilities 2023-2024",
        "category": "COMPLEX",
        "expected_keywords": ["vmware", "esxi"],
        "min_results": 1,
        "description": "VMware ESXi zafiyet"
    },
    {
        "query": "Fortinet FortiOS authentication bypass recent",
        "category": "COMPLEX",
        "expected_keywords": ["fortinet", "authentication"],
        "min_results": 1,
        "description": "Fortinet auth bypass"
    },
    {
        "query": "Microsoft Exchange Server vulnerabilities 2024",
        "category": "COMPLEX",
        "expected_keywords": ["exchange", "microsoft"],
        "min_results": 1,
        "description": "Exchange 2024"
    },
    {
        "query": "Citrix NetScaler gateway critical security issues",
        "category": "COMPLEX",
        "expected_keywords": ["citrix", "netscaler"],
        "min_results": 1,
        "description": "Citrix zafiyet"
    },
    {
        "query": "Atlassian Confluence remote code execution recent",
        "category": "COMPLEX",
        "expected_keywords": ["atlassian", "confluence"],
        "min_results": 1,
        "description": "Confluence RCE"
    },
]

# Total: 100 queries (40 + 25 + 15 + 15 + 5)


# ==================== TEST EXECUTION ====================

def run_comprehensive_test():
    """Kapsamlı RAG test suite (2022-2024 CVEs)"""
    print("\n" + "="*80)
    print(" "*15 + "RAG SEARCH TEST SUITE (2022-2024 CVEs)")
    print("="*80 + "\n")
    
    # RAG TEST CONFIGURATION
    print("="*80)
    print("[*] RAG TEST CONFIGURATION:")
    print(f"[*] Qdrant Database: https://meryemarpaci-pentagent-qdrant.hf.space")
    print(f"[*] Collection: cve_collection_hybrid (verified)")
    
    use_hf_api = os.getenv('USE_HF_INFERENCE_API', 'false').lower() == 'true'
    if use_hf_api:
        print(f"[*] Vectorization: HuggingFace Inference API (PRODUCTION MODE)")
        print(f"[*] Sparse Vector: IMPROVED Smart Generation (TF-IDF-like)")
    else:
        print(f"[*] Vectorization: LOCAL BGE-M3 Model (BAAI/bge-m3)")
        print(f"[*] Sparse Vector: Native BGE-M3 Lexical Weights")
    
    print(f"[*] Testing: Both Dense + Sparse vectors + RRF")
    print(f"[*] Hybrid Search: RRF Algorithm (Reciprocal Rank Fusion)")
    print(f"[*] USE_HF_INFERENCE_API: {os.getenv('USE_HF_INFERENCE_API', 'not set')}")
    print("="*80 + "\n")
    
    if use_hf_api:
        print("[*] Initializing HuggingFace Inference API...")
    else:
        print("[*] Loading LOCAL BGE-M3 model...")
    
    config_obj = SearchConfig(
        collection_name="cve_collection_hybrid",
        qdrant_host="https://meryemarpaci-pentagent-qdrant.hf.space",
        qdrant_port=443,
        qdrant_https=True,
        huggingface_token=None
    )
    
    search_engine = CVESearchEngine(config_obj)
    
    if use_hf_api:
        print("[+] HuggingFace Inference API ready (with IMPROVED sparse)!")
    else:
        print("[+] BGE-M3 Model loaded successfully!")
    
    print("[+] Qdrant connection established!")
    print("[+] Ready to test HYBRID SEARCH with RRF!\n")
    
    # Test statistics
    stats = {
        "total": len(TEST_QUERIES),
        "passed": 0,
        "failed": 0,
        "by_category": {},
        "execution_times": [],
        "details": []
    }
    
    # Run tests
    for idx, test_case in enumerate(TEST_QUERIES, 1):
        query = test_case["query"]
        category = test_case["category"]
        expected_keywords = test_case.get("expected_keywords", [])
        expected_cves = test_case.get("expected_cves", [])
        min_results = test_case.get("min_results", 1)
        description = test_case.get("description", "")
        
        # Initialize category stats
        if category not in stats["by_category"]:
            stats["by_category"][category] = {"passed": 0, "failed": 0}
        
        # Print test info
        print(f"[{idx}/{len(TEST_QUERIES)}] {category}: {description}")
        print(f"    Query: '{query}'")
        
        # Execute search
        start_time = time.time()
        try:
            results = search_engine.search(query, limit=10)
            execution_time = time.time() - start_time
            stats["execution_times"].append(execution_time)
            
            # Validate results
            passed = True
            failure_reason = None
            
            # Check minimum results
            if len(results) < min_results:
                passed = False
                failure_reason = f"Insufficient results. Got {len(results)}, expected at least {min_results}"
            
            # Check expected CVEs (for CVE_DIRECT and HYBRID)
            if passed and expected_cves:
                result_cve_ids = [r.cve_id for r in results[:3]]  # Check top 3
                if not any(cve in result_cve_ids for cve in expected_cves):
                    passed = False
                    failure_reason = f"Expected CVE not in top results. Got: {result_cve_ids}"
            
            # Check expected keywords (for all categories)
            if passed and expected_keywords:
                combined_text = " ".join([r.cve_id + " " + r.description for r in results[:5]]).lower()
                missing_keywords = [kw for kw in expected_keywords if kw.lower() not in combined_text]
                if missing_keywords:
                    passed = False
                    failure_reason = f"Keywords not found. Expected: {expected_keywords}"
            
            # Update stats
            if passed:
                stats["passed"] += 1
                stats["by_category"][category]["passed"] += 1
                print(f"    [+] PASS: Keywords found in results")
            else:
                stats["failed"] += 1
                stats["by_category"][category]["failed"] += 1
                print(f"    [-] FAIL: {failure_reason}")
                stats["details"].append({
                    "query": description,
                    "reason": failure_reason
                })
            
            print(f"    Results: {len(results)}, Time: {execution_time:.2f}s")
            if results:
                print(f"    Top result: {results[0].cve_id} (score: {results[0].score:.3f})")
            
        except Exception as e:
            stats["failed"] += 1
            stats["by_category"][category]["failed"] += 1
            print(f"    [-] ERROR: {str(e)}")
            stats["details"].append({
                "query": description,
                "reason": f"Exception: {str(e)}"
            })
    
    # Print summary
    print("\n" + "="*80)
    print(" "*25 + "TEST SUMMARY")
    print("="*80)
    
    success_rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0
    avg_time = sum(stats["execution_times"]) / len(stats["execution_times"]) if stats["execution_times"] else 0
    
    print(f"[*] Overall Results:")
    print(f"    Total Tests: {stats['total']}")
    print(f"    Passed: {stats['passed']} ({success_rate:.1f}%)")
    print(f"    Failed: {stats['failed']}")
    print(f"    Average Time: {avg_time:.2f}s")
    
    print(f"[*] Results by Category:")
    for category, cat_stats in sorted(stats["by_category"].items()):
        total_cat = cat_stats["passed"] + cat_stats["failed"]
        cat_success = (cat_stats["passed"] / total_cat * 100) if total_cat > 0 else 0
        print(f"    {category:20s}: {cat_stats['passed']}/{total_cat} ({cat_success:.1f}%)")
    
    if stats["details"]:
        print(f"[-] Failed Tests ({len(stats['details'])}):")
        for detail in stats["details"][:20]:  # Show first 20
            print(f"    • {detail['query']}")
            print(f"      Reason: {detail['reason']}")
    
    print("="*80)
    
    # Overall assessment
    if success_rate >= 85:
        print("✅ RAG SEARCH PERFORMANCE: EXCELLENT!")
    elif success_rate >= 70:
        print("✅ RAG SEARCH PERFORMANCE: GOOD")
    elif success_rate >= 60:
        print("⚠️ RAG SEARCH PERFORMANCE: ACCEPTABLE")
    else:
        print("❌ RAG SEARCH PERFORMANCE: NEEDS IMPROVEMENT")
    
    return stats


# ==================== MAIN ====================

if __name__ == "__main__":
    try:
        stats = run_comprehensive_test()
        
        # Optionally save to file
        results_file = os.path.join(os.path.dirname(__file__), "RAG_TEST_RESULTS.md")
        with open(results_file, "w", encoding="utf-8", errors="replace") as f:
            f.write(f"# RAG Test Results ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n\n")
            f.write(f"## Overall Results\n\n")
            f.write(f"- **Total Tests:** {stats['total']}\n")
            f.write(f"- **Passed:** {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)\n")
            f.write(f"- **Failed:** {stats['failed']}\n\n")
            f.write(f"## Category Results\n\n")
            for category, cat_stats in sorted(stats["by_category"].items()):
                total = cat_stats["passed"] + cat_stats["failed"]
                rate = cat_stats["passed"]/total*100 if total > 0 else 0
                f.write(f"- **{category}:** {cat_stats['passed']}/{total} ({rate:.1f}%)\n")
            
        print(f"\n[+] Results saved to: {results_file}")
        
    except KeyboardInterrupt:
        print("\n[!] Test interrupted by user")
    except Exception as e:
        print(f"\n[-] Test failed: {e}")
