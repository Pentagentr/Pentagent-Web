"""
🧪 COMPREHENSIVE RAG SEARCH TEST SUITE

RAG arama sisteminin performansını değerlendirir:
- 100 test query (farklı kategorilerde)
- Beklenen CVE sonuçları
- Başarı oranı hesaplama
- Detaylı performans analizi
"""

import asyncio
import sys
import os
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


# ==================== TEST QUERIES ====================

TEST_QUERIES = [
    # ==================== CATEGORY 1: PURE SEMANTIC - DENSE VECTOR TEST (40 queries) ====================
    # Subcategory: Question-based (Soru formatı - Dense vektör güçlü olmalı)
    {
        "query": "What is SQL injection and how does it work?",
        "category": "pure_semantic",
        "expected_keywords": ["sql", "injection"],
        "min_results": 5,
        "description": "[Q] SQL injection nedir?"
    },
    {
        "query": "How can attackers exploit cross-site scripting vulnerabilities?",
        "category": "pure_semantic",
        "expected_keywords": ["xss", "cross-site"],
        "min_results": 5,
        "description": "[Q] XSS nasıl exploit edilir?"
    },
    {
        "query": "Explain remote code execution attacks in web applications",
        "category": "pure_semantic",
        "expected_keywords": ["remote", "code", "execution"],
        "min_results": 5,
        "description": "[Q] RCE açıkla"
    },
    {
        "query": "What are the most dangerous authentication bypass techniques?",
        "category": "pure_semantic",
        "expected_keywords": ["authentication", "bypass"],
        "min_results": 5,
        "description": "[Q] Auth bypass teknikleri"
    },
    {
        "query": "Tell me about path traversal vulnerabilities in web servers",
        "category": "pure_semantic",
        "expected_keywords": ["path", "traversal"],
        "min_results": 5,
        "description": "[Q] Path traversal anlat"
    },
    
    # Subcategory: Descriptive (Açıklayıcı - Dense vektör dominant)
    {
        "query": "SQL injection web application vulnerability",
        "category": "pure_semantic",
        "expected_keywords": ["sql", "injection"],
        "min_results": 5,
        "description": "[D] SQL injection açıklama"
    },
    {
        "query": "Cross-site scripting attack in web browsers",
        "category": "pure_semantic",
        "expected_keywords": ["xss", "cross-site"],
        "min_results": 5,
        "description": "[D] XSS web browser"
    },
    {
        "query": "Web uygulamalarında SQL enjeksiyonu zafiyeti nasıl tespit edilir",
        "category": "pure_semantic",
        "expected_keywords": ["sql"],
        "min_results": 5,
        "description": "[D-TR] SQL tespiti Türkçe"
    },
    {
        "query": "Zararlı dosya yükleme zafiyetleri ve önleme yöntemleri",
        "category": "pure_semantic",
        "expected_keywords": ["file", "upload"],
        "min_results": 3,
        "description": "[D-TR] Dosya yükleme Türkçe"
    },
    {
        "query": "Kimlik doğrulama atlatma saldırıları ve güvenlik açıkları",
        "category": "pure_semantic",
        "expected_keywords": ["authentication"],
        "min_results": 5,
        "description": "[D-TR] Auth bypass Türkçe"
    },
    {
        "query": "Sunucu tarafı istek sahteciliği SSRF zafiyetleri",
        "category": "pure_semantic",
        "expected_keywords": ["ssrf"],
        "min_results": 3,
        "description": "[D-TR] SSRF Türkçe"
    },
    {
        "query": "Remote code execution vulnerability",
        "category": "pure_semantic",
        "expected_keywords": ["remote", "code", "execution"],
        "min_results": 5,
        "description": "RCE genel sorgu"
    },
    {
        "query": "Authentication bypass security flaw",
        "category": "pure_semantic",
        "expected_keywords": ["authentication", "bypass"],
        "min_results": 5,
        "description": "Auth bypass sorgusu"
    },
    {
        "query": "Path traversal directory traversal vulnerability",
        "category": "pure_semantic",
        "expected_keywords": ["path", "traversal"],
        "min_results": 5,
        "description": "Path traversal sorgusu"
    },
    {
        "query": "Server-side request forgery SSRF",
        "category": "pure_semantic",
        "expected_keywords": ["ssrf", "request forgery"],
        "min_results": 3,
        "description": "SSRF sorgusu"
    },
    {
        "query": "XML external entity injection XXE",
        "category": "pure_semantic",
        "expected_keywords": ["xxe", "xml"],
        "min_results": 3,
        "description": "XXE sorgusu"
    },
    {
        "query": "Insecure deserialization vulnerability",
        "category": "pure_semantic",
        "expected_keywords": ["deserialization"],
        "min_results": 3,
        "description": "Deserialization sorgusu"
    },
    {
        "query": "Command injection OS command execution",
        "category": "pure_semantic",
        "expected_keywords": ["command", "injection"],
        "min_results": 5,
        "description": "Command injection sorgusu"
    },
    {
        "query": "Privilege escalation security vulnerability",
        "category": "pure_semantic",
        "expected_keywords": ["privilege", "escalation"],
        "min_results": 5,
        "description": "Privilege escalation sorgusu"
    },
    {
        "query": "Information disclosure sensitive data leak",
        "category": "pure_semantic",
        "expected_keywords": ["disclosure", "leak"],
        "min_results": 5,
        "description": "Info disclosure sorgusu"
    },
    {
        "query": "Denial of service DoS vulnerability",
        "category": "pure_semantic",
        "expected_keywords": ["denial", "dos"],
        "min_results": 5,
        "description": "DoS sorgusu"
    },
    {
        "query": "Buffer overflow memory corruption",
        "category": "pure_semantic",
        "expected_keywords": ["buffer", "overflow"],
        "min_results": 5,
        "description": "Buffer overflow sorgusu"
    },
    {
        "query": "Improper input validation vulnerability",
        "category": "pure_semantic",
        "expected_keywords": ["input", "validation"],
        "min_results": 5,
        "description": "Input validation sorgusu"
    },
    {
        "query": "Missing authentication security flaw",
        "category": "pure_semantic",
        "expected_keywords": ["authentication"],
        "min_results": 5,
        "description": "Missing auth sorgusu"
    },
    {
        "query": "Cryptographic weakness encryption flaw",
        "category": "pure_semantic",
        "expected_keywords": ["crypto", "encryption"],
        "min_results": 5,
        "description": "Crypto sorgusu"
    },
    {
        "query": "Session fixation session hijacking",
        "category": "pure_semantic",
        "expected_keywords": ["session"],
        "min_results": 3,
        "description": "Session hijacking sorgusu"
    },
    {
        "query": "Clickjacking UI redressing attack",
        "category": "pure_semantic",
        "expected_keywords": ["clickjacking"],
        "min_results": 3,
        "description": "Clickjacking sorgusu"
    },
    {
        "query": "File upload vulnerability malicious file",
        "category": "pure_semantic",
        "expected_keywords": ["file", "upload"],
        "min_results": 5,
        "description": "File upload sorgusu"
    },
    {
        "query": "Race condition time of check vulnerability",
        "category": "pure_semantic",
        "expected_keywords": ["race", "condition"],
        "min_results": 3,
        "description": "[D] Race condition"
    },
    {
        "query": "Memory corruption vulnerabilities in C applications",
        "category": "pure_semantic",
        "expected_keywords": ["memory", "corruption"],
        "min_results": 5,
        "description": "[D] Memory corruption C"
    },
    {
        "query": "Heap overflow exploitation techniques",
        "category": "pure_semantic",
        "expected_keywords": ["heap", "overflow"],
        "min_results": 3,
        "description": "[D] Heap overflow"
    },
    {
        "query": "Use after free vulnerability exploitation",
        "category": "pure_semantic",
        "expected_keywords": ["use after free"],
        "min_results": 3,
        "description": "[D] Use after free"
    },
    {
        "query": "Integer overflow security implications",
        "category": "pure_semantic",
        "expected_keywords": ["integer", "overflow"],
        "min_results": 3,
        "description": "[D] Integer overflow"
    },
    {
        "query": "Format string vulnerability exploitation",
        "category": "pure_semantic",
        "expected_keywords": ["format string"],
        "min_results": 3,
        "description": "[D] Format string"
    },
    {
        "query": "LDAP injection attack techniques",
        "category": "pure_semantic",
        "expected_keywords": ["ldap", "injection"],
        "min_results": 3,
        "description": "[D] LDAP injection"
    },
    {
        "query": "NoSQL injection MongoDB security",
        "category": "pure_semantic",
        "expected_keywords": ["nosql", "mongodb"],
        "min_results": 3,
        "description": "[D] NoSQL injection"
    },
    {
        "query": "Template injection server-side vulnerability",
        "category": "pure_semantic",
        "expected_keywords": ["template", "injection"],
        "min_results": 3,
        "description": "[D] Template injection"
    },
    {
        "query": "API security vulnerabilities authentication",
        "category": "pure_semantic",
        "expected_keywords": ["api", "authentication"],
        "min_results": 5,
        "description": "[D] API güvenlik"
    },
    {
        "query": "JWT token manipulation and security flaws",
        "category": "pure_semantic",
        "expected_keywords": ["jwt", "token"],
        "min_results": 3,
        "description": "[D] JWT manipulation"
    },
    {
        "query": "OAuth authentication bypass vulnerabilities",
        "category": "pure_semantic",
        "expected_keywords": ["oauth", "authentication"],
        "min_results": 3,
        "description": "[D] OAuth bypass"
    },
    {
        "query": "CORS misconfiguration security risks",
        "category": "pure_semantic",
        "expected_keywords": ["cors"],
        "min_results": 3,
        "description": "[D] CORS misconfiguration"
    },
    {
        "query": "Insecure direct object reference IDOR attacks",
        "category": "pure_semantic",
        "expected_keywords": ["idor", "object"],
        "min_results": 3,
        "description": "[D] IDOR attacks"
    },
    {
        "query": "Mass assignment vulnerability in web frameworks",
        "category": "pure_semantic",
        "expected_keywords": ["mass assignment"],
        "min_results": 3,
        "description": "[D] Mass assignment"
    },
    {
        "query": "HTTP request smuggling attack techniques",
        "category": "pure_semantic",
        "expected_keywords": ["request", "smuggling"],
        "min_results": 3,
        "description": "[D] Request smuggling"
    },
    {
        "query": "Cache poisoning web application vulnerability",
        "category": "pure_semantic",
        "expected_keywords": ["cache", "poisoning"],
        "min_results": 3,
        "description": "[D] Cache poisoning"
    },
    {
        "query": "Host header injection attack vectors",
        "category": "pure_semantic",
        "expected_keywords": ["host", "header"],
        "min_results": 3,
        "description": "[D] Host header injection"
    },
    {
        "query": "Open redirect vulnerability exploitation",
        "category": "pure_semantic",
        "expected_keywords": ["redirect"],
        "min_results": 3,
        "description": "[D] Open redirect"
    },
    {
        "query": "XML bomb denial of service attack",
        "category": "pure_semantic",
        "expected_keywords": ["xml", "denial"],
        "min_results": 3,
        "description": "[D] XML bomb DoS"
    },
    
    # ==================== CATEGORY 2: VERSION-BASED (25 queries) ====================
    {
        "query": "Apache HTTP Server 2.4.49 vulnerability",
        "category": "version_based",
        "expected_cves": ["CVE-2021-41773"],
        "min_results": 3,
        "description": "Apache 2.4.49 path traversal"
    },
    {
        "query": "Apache 2.4.50 exploit",
        "category": "version_based",
        "expected_cves": ["CVE-2021-42013"],
        "min_results": 3,
        "description": "Apache 2.4.50 RCE"
    },
    {
        "query": "Log4j 2.14.1 remote code execution",
        "category": "version_based",
        "expected_cves": ["CVE-2021-44228"],
        "min_results": 3,
        "description": "Log4Shell vulnerability"
    },
    {
        "query": "OpenSSL 1.0.1 heartbleed",
        "category": "version_based",
        "expected_cves": ["CVE-2014-0160"],
        "min_results": 3,
        "description": "Heartbleed bug"
    },
    {
        "query": "Struts 2.5.10 vulnerability",
        "category": "version_based",
        "expected_cves": ["CVE-2017-5638"],
        "min_results": 3,
        "description": "Apache Struts RCE"
    },
    {
        "query": "WordPress 5.0 vulnerability",
        "category": "version_based",
        "expected_keywords": ["wordpress"],
        "min_results": 5,
        "description": "WordPress 5.0 zafiyetler"
    },
    {
        "query": "nginx 1.20.0 security issue",
        "category": "version_based",
        "expected_keywords": ["nginx"],
        "min_results": 3,
        "description": "nginx 1.20.0"
    },
    {
        "query": "PHP 7.4.0 vulnerability",
        "category": "version_based",
        "expected_keywords": ["php"],
        "min_results": 5,
        "description": "PHP 7.4.0 zafiyetler"
    },
    {
        "query": "MySQL 5.7 authentication bypass",
        "category": "version_based",
        "expected_keywords": ["mysql", "authentication"],
        "min_results": 3,
        "description": "MySQL auth bypass"
    },
    {
        "query": "Tomcat 9.0.0.M1 vulnerability",
        "category": "version_based",
        "expected_keywords": ["tomcat"],
        "min_results": 3,
        "description": "Tomcat 9.0 zafiyet"
    },
    {
        "query": "Jenkins 2.150 security flaw",
        "category": "version_based",
        "expected_keywords": ["jenkins"],
        "min_results": 3,
        "description": "Jenkins 2.150"
    },
    {
        "query": "Django 2.2.0 SQL injection",
        "category": "version_based",
        "expected_keywords": ["django", "sql"],
        "min_results": 3,
        "description": "Django SQLi"
    },
    {
        "query": "Node.js 10.0.0 vulnerability",
        "category": "version_based",
        "expected_keywords": ["node"],
        "min_results": 3,
        "description": "Node.js zafiyet"
    },
    {
        "query": "Spring Framework 5.3.0 vulnerability",
        "category": "version_based",
        "expected_keywords": ["spring"],
        "min_results": 3,
        "description": "Spring Framework"
    },
    {
        "query": "Ruby on Rails 5.2.0 security issue",
        "category": "version_based",
        "expected_keywords": ["rails", "ruby"],
        "min_results": 3,
        "description": "Rails zafiyet"
    },
    {
        "query": "Drupal 7.32 SQL injection",
        "category": "version_based",
        "expected_keywords": ["drupal", "sql"],
        "min_results": 3,
        "description": "Drupal SQLi"
    },
    {
        "query": "Joomla 3.4.5 remote code execution",
        "category": "version_based",
        "expected_keywords": ["joomla"],
        "min_results": 3,
        "description": "Joomla RCE"
    },
    {
        "query": "Magento 2.3.0 vulnerability",
        "category": "version_based",
        "expected_keywords": ["magento"],
        "min_results": 3,
        "description": "Magento zafiyet"
    },
    {
        "query": "vBulletin 5.6.0 exploit",
        "category": "version_based",
        "expected_keywords": ["vbulletin"],
        "min_results": 3,
        "description": "vBulletin exploit"
    },
    {
        "query": "Elasticsearch 1.4.2 remote code execution",
        "category": "version_based",
        "expected_keywords": ["elasticsearch"],
        "min_results": 3,
        "description": "Elasticsearch RCE"
    },
    {
        "query": "Redis 5.0.0 security vulnerability",
        "category": "version_based",
        "expected_keywords": ["redis"],
        "min_results": 3,
        "description": "Redis zafiyet"
    },
    {
        "query": "MongoDB 3.6.0 authentication bypass",
        "category": "version_based",
        "expected_keywords": ["mongodb"],
        "min_results": 3,
        "description": "MongoDB auth bypass"
    },
    {
        "query": "Docker 19.03.0 privilege escalation",
        "category": "version_based",
        "expected_keywords": ["docker"],
        "min_results": 3,
        "description": "Docker priv esc"
    },
    {
        "query": "Kubernetes 1.18.0 security issue",
        "category": "version_based",
        "expected_keywords": ["kubernetes"],
        "min_results": 3,
        "description": "Kubernetes zafiyet"
    },
    {
        "query": "Apache Struts 2.3.20 vulnerability",
        "category": "version_based",
        "expected_keywords": ["struts"],
        "min_results": 3,
        "description": "Struts 2.3.20"
    },
    
    # ==================== CATEGORY 3: CVE DIRECT (30 queries) ====================
    {
        "query": "CVE-2021-44228",
        "category": "cve_direct",
        "expected_cves": ["CVE-2021-44228"],
        "min_results": 1,
        "description": "Log4Shell - Direct CVE"
    },
    {
        "query": "CVE-2021-44228 nedir?",
        "category": "cve_direct",
        "expected_cves": ["CVE-2021-44228"],
        "min_results": 1,
        "description": "Log4Shell - Türkçe soru"
    },
    {
        "query": "Tell me about CVE-2021-44228",
        "category": "cve_direct",
        "expected_cves": ["CVE-2021-44228"],
        "min_results": 1,
        "description": "Log4Shell - İngilizce soru"
    },
    {
        "query": "CVE-2021-41773",
        "category": "cve_direct",
        "expected_cves": ["CVE-2021-41773"],
        "min_results": 1,
        "description": "Apache path traversal"
    },
    {
        "query": "CVE-2021-42013 vulnerability details",
        "category": "cve_direct",
        "expected_cves": ["CVE-2021-42013"],
        "min_results": 1,
        "description": "Apache RCE"
    },
    {
        "query": "CVE-2014-0160 heartbleed",
        "category": "cve_direct",
        "expected_cves": ["CVE-2014-0160"],
        "min_results": 1,
        "description": "Heartbleed OpenSSL"
    },
    {
        "query": "CVE-2017-5638",
        "category": "cve_direct",
        "expected_cves": ["CVE-2017-5638"],
        "min_results": 1,
        "description": "Apache Struts"
    },
    {
        "query": "CVE-2019-0708 BlueKeep",
        "category": "cve_direct",
        "expected_cves": ["CVE-2019-0708"],
        "min_results": 1,
        "description": "BlueKeep RDP"
    },
    {
        "query": "CVE-2017-0144 EternalBlue",
        "category": "cve_direct",
        "expected_cves": ["CVE-2017-0144"],
        "min_results": 1,
        "description": "EternalBlue SMB"
    },
    {
        "query": "CVE-2020-1472 Zerologon",
        "category": "cve_direct",
        "expected_cves": ["CVE-2020-1472"],
        "min_results": 1,
        "description": "Zerologon Netlogon"
    },
    {
        "query": "CVE-2014-6271 Shellshock",
        "category": "cve_direct",
        "expected_cves": ["CVE-2014-6271"],
        "min_results": 1,
        "description": "Shellshock Bash"
    },
    {
        "query": "CVE-2018-11776",
        "category": "cve_direct",
        "expected_cves": ["CVE-2018-11776"],
        "min_results": 1,
        "description": "Struts RCE"
    },
    {
        "query": "CVE-2019-11510",
        "category": "cve_direct",
        "expected_cves": ["CVE-2019-11510"],
        "min_results": 1,
        "description": "Pulse Secure"
    },
    {
        "query": "CVE-2020-0601",
        "category": "cve_direct",
        "expected_cves": ["CVE-2020-0601"],
        "min_results": 1,
        "description": "CurveBall Windows"
    },
    {
        "query": "CVE-2021-26855",
        "category": "cve_direct",
        "expected_cves": ["CVE-2021-26855"],
        "min_results": 1,
        "description": "ProxyLogon Exchange"
    },
    {
        "query": "CVE-2021-34527 PrintNightmare",
        "category": "cve_direct",
        "expected_cves": ["CVE-2021-34527"],
        "min_results": 1,
        "description": "PrintNightmare Windows"
    },
    {
        "query": "CVE-2022-30190 Follina",
        "category": "cve_direct",
        "expected_cves": ["CVE-2022-30190"],
        "min_results": 1,
        "description": "Follina MSDT"
    },
    {
        "query": "CVE-2023-23397",
        "category": "cve_direct",
        "expected_cves": ["CVE-2023-23397"],
        "min_results": 1,
        "description": "Outlook elevation"
    },
    {
        "query": "CVE-2021-3156 Baron Samedit",
        "category": "cve_direct",
        "expected_cves": ["CVE-2021-3156"],
        "min_results": 1,
        "description": "sudo heap overflow"
    },
    {
        "query": "CVE-2019-19781",
        "category": "cve_direct",
        "expected_cves": ["CVE-2019-19781"],
        "min_results": 1,
        "description": "Citrix ADC"
    },
    {
        "query": "CVE-2020-5902",
        "category": "cve_direct",
        "expected_cves": ["CVE-2020-5902"],
        "min_results": 1,
        "description": "F5 BIG-IP"
    },
    {
        "query": "CVE-2021-21972",
        "category": "cve_direct",
        "expected_cves": ["CVE-2021-21972"],
        "min_results": 1,
        "description": "VMware vCenter"
    },
    {
        "query": "CVE-2022-22965 Spring4Shell",
        "category": "cve_direct",
        "expected_cves": ["CVE-2022-22965"],
        "min_results": 1,
        "description": "Spring4Shell"
    },
    {
        "query": "CVE-2021-40438",
        "category": "cve_direct",
        "expected_cves": ["CVE-2021-40438"],
        "min_results": 1,
        "description": "Apache SSRF"
    },
    {
        "query": "CVE-2022-26134",
        "category": "cve_direct",
        "expected_cves": ["CVE-2022-26134"],
        "min_results": 1,
        "description": "Confluence RCE"
    },
    {
        "query": "CVE-2023-22515",
        "category": "cve_direct",
        "expected_cves": ["CVE-2023-22515"],
        "min_results": 1,
        "description": "Confluence privilege escalation"
    },
    {
        "query": "CVE-2023-34362",
        "category": "cve_direct",
        "expected_cves": ["CVE-2023-34362"],
        "min_results": 1,
        "description": "MOVEit Transfer"
    },
    {
        "query": "CVE-2023-0669",
        "category": "cve_direct",
        "expected_cves": ["CVE-2023-0669"],
        "min_results": 1,
        "description": "Fortra GoAnywhere"
    },
    {
        "query": "CVE-2023-27997",
        "category": "cve_direct",
        "expected_cves": ["CVE-2023-27997"],
        "min_results": 1,
        "description": "FortiOS heap overflow"
    },
    {
        "query": "CVE-2023-46747",
        "category": "cve_direct",
        "expected_cves": ["CVE-2023-46747"],
        "min_results": 1,
        "description": "F5 BIG-IP config"
    },
    
    # ==================== CATEGORY 4: HYBRID (CVE + Context) (15 queries) ====================
    {
        "query": "CVE-2021-44228 Apache Log4j vulnerability",
        "category": "hybrid",
        "expected_cves": ["CVE-2021-44228"],
        "expected_keywords": ["log4j"],
        "min_results": 3,
        "description": "Log4Shell with context"
    },
    {
        "query": "CVE-2021-41773 Apache 2.4.49 path traversal",
        "category": "hybrid",
        "expected_cves": ["CVE-2021-41773"],
        "expected_keywords": ["apache", "path"],
        "min_results": 3,
        "description": "Apache with version and type"
    },
    {
        "query": "CVE-2014-0160 OpenSSL 1.0.1 heartbleed memory leak",
        "category": "hybrid",
        "expected_cves": ["CVE-2014-0160"],
        "expected_keywords": ["openssl", "heartbleed"],
        "min_results": 3,
        "description": "Heartbleed full context"
    },
    {
        "query": "CVE-2017-5638 Apache Struts 2.5.10 remote code execution",
        "category": "hybrid",
        "expected_cves": ["CVE-2017-5638"],
        "expected_keywords": ["struts", "remote"],
        "min_results": 3,
        "description": "Struts full context"
    },
    {
        "query": "CVE-2021-42013 Apache 2.4.50 exploit",
        "category": "hybrid",
        "expected_cves": ["CVE-2021-42013"],
        "expected_keywords": ["apache"],
        "min_results": 3,
        "description": "Apache 2.4.50 context"
    },
    {
        "query": "CVE-2019-0708 Windows RDP BlueKeep vulnerability",
        "category": "hybrid",
        "expected_cves": ["CVE-2019-0708"],
        "expected_keywords": ["bluekeep", "rdp"],
        "min_results": 3,
        "description": "BlueKeep full"
    },
    {
        "query": "CVE-2017-0144 Windows SMB EternalBlue exploit",
        "category": "hybrid",
        "expected_cves": ["CVE-2017-0144"],
        "expected_keywords": ["eternalblue", "smb"],
        "min_results": 3,
        "description": "EternalBlue full"
    },
    {
        "query": "CVE-2020-1472 Netlogon Zerologon privilege escalation",
        "category": "hybrid",
        "expected_cves": ["CVE-2020-1472"],
        "expected_keywords": ["zerologon", "netlogon"],
        "min_results": 3,
        "description": "Zerologon full"
    },
    {
        "query": "CVE-2014-6271 Bash Shellshock command injection",
        "category": "hybrid",
        "expected_cves": ["CVE-2014-6271"],
        "expected_keywords": ["shellshock", "bash"],
        "min_results": 3,
        "description": "Shellshock full"
    },
    {
        "query": "CVE-2022-22965 Spring Framework Spring4Shell RCE",
        "category": "hybrid",
        "expected_cves": ["CVE-2022-22965"],
        "expected_keywords": ["spring4shell", "spring"],
        "min_results": 3,
        "description": "Spring4Shell full"
    },
    {
        "query": "CVE-2021-26855 Exchange ProxyLogon vulnerability",
        "category": "hybrid",
        "expected_cves": ["CVE-2021-26855"],
        "expected_keywords": ["exchange", "proxylogon"],
        "min_results": 3,
        "description": "ProxyLogon full"
    },
    {
        "query": "CVE-2021-34527 Windows Print Spooler PrintNightmare",
        "category": "hybrid",
        "expected_cves": ["CVE-2021-34527"],
        "expected_keywords": ["printnightmare", "print"],
        "min_results": 3,
        "description": "PrintNightmare full"
    },
    {
        "query": "CVE-2022-30190 Microsoft Support Diagnostic Tool Follina",
        "category": "hybrid",
        "expected_cves": ["CVE-2022-30190"],
        "expected_keywords": ["follina", "msdt"],
        "min_results": 3,
        "description": "Follina full"
    },
    {
        "query": "CVE-2021-3156 sudo heap overflow Baron Samedit",
        "category": "hybrid",
        "expected_cves": ["CVE-2021-3156"],
        "expected_keywords": ["sudo", "baron"],
        "min_results": 3,
        "description": "Baron Samedit full"
    },
    {
        "query": "CVE-2023-34362 MOVEit Transfer SQL injection",
        "category": "hybrid",
        "expected_cves": ["CVE-2023-34362"],
        "expected_keywords": ["moveit"],
        "min_results": 3,
        "description": "MOVEit SQLi full"
    },
    
    # ==================== CATEGORY 5: COMPLEX/CHALLENGING (10 queries) ====================
    {
        "query": "Apache web server remote code execution 2021",
        "category": "complex",
        "expected_keywords": ["apache", "remote"],
        "min_results": 5,
        "description": "Apache RCE genel (yıl filtreli)"
    },
    {
        "query": "Windows privilege escalation vulnerabilities",
        "category": "complex",
        "expected_keywords": ["windows", "privilege"],
        "min_results": 5,
        "description": "Windows priv esc genel"
    },
    {
        "query": "Java deserialization vulnerabilities",
        "category": "complex",
        "expected_keywords": ["java", "deserialization"],
        "min_results": 5,
        "description": "Java deserialize genel"
    },
    {
        "query": "Cisco router vulnerabilities critical severity",
        "category": "complex",
        "expected_keywords": ["cisco"],
        "min_results": 3,
        "description": "Cisco critical"
    },
    {
        "query": "VMware ESXi remote code execution",
        "category": "complex",
        "expected_keywords": ["vmware", "esxi"],
        "min_results": 3,
        "description": "VMware RCE"
    },
    {
        "query": "Microsoft Exchange server vulnerabilities 2021",
        "category": "complex",
        "expected_keywords": ["exchange", "microsoft"],
        "min_results": 5,
        "description": "Exchange 2021"
    },
    {
        "query": "Fortinet FortiOS authentication bypass",
        "category": "complex",
        "expected_keywords": ["fortinet", "authentication"],
        "min_results": 3,
        "description": "FortiOS auth bypass"
    },
    {
        "query": "Citrix NetScaler gateway vulnerability",
        "category": "complex",
        "expected_keywords": ["citrix"],
        "min_results": 3,
        "description": "Citrix zafiyet"
    },
    {
        "query": "SolarWinds Orion platform vulnerability",
        "category": "complex",
        "expected_keywords": ["solarwinds", "orion"],
        "min_results": 3,
        "description": "SolarWinds"
    },
    {
        "query": "Atlassian Confluence remote code execution recent",
        "category": "complex",
        "expected_keywords": ["confluence", "atlassian"],
        "min_results": 5,
        "description": "Confluence RCE"
    },
]


# ==================== TEST EXECUTION ====================

async def run_comprehensive_test():
    """Kapsamlı RAG test suite"""
    print("\n" + "="*80)
    print(" "*20 + "RAG SEARCH COMPREHENSIVE TEST SUITE")
    print("="*80 + "\n")
    
    # Initialize RAG - Render'dakiyle aynı config
    print("[*] Initializing RAG Search Engine...")
    
    # Environment variables'dan al (Render'da kullanılan)
    qdrant_host = os.getenv('QDRANT_HOST', 'https://ca7c82ea-1098-402b-a2d8-6c8ecf74b93d.europe-west3-0.gcp.cloud.qdrant.io')
    qdrant_api_key = os.getenv('QDRANT_API_KEY', 'iM-z0e_4bNbfO0M-9Xl5DM5LwL80q0OTv2UX5S7Q18XyvAVJQVQNEg')
    hf_token = os.getenv('HUGGINGFACE_TOKEN', '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')
    
    # HuggingFace Space - WORKING CONFIG (No HF token needed for public space)
    qdrant_host = "https://meryemarpaci-pentagent-qdrant.hf.space"
    config_obj = SearchConfig(
        collection_name="cve_collection_hybrid",  # Verified from HF Space API
        qdrant_host=qdrant_host,
        qdrant_port=443,
        qdrant_https=True,
        huggingface_token=None  # Public space - HF API kullanma, sadece Qdrant'tan çek
    )
    
    print(f"[*] Connecting to: {qdrant_host[:50]}...")
    
    search_engine = CVESearchEngine(config_obj)
    print("[+] RAG Search Engine initialized\n")
    
    # Test statistics
    stats = {
        "total": len(TEST_QUERIES),
        "passed": 0,
        "failed": 0,
        "by_category": {},
        "execution_times": [],
        "details": []
    }
    
    # Kategoriye göre grupla
    for test in TEST_QUERIES:
        category = test["category"]
        if category not in stats["by_category"]:
            stats["by_category"][category] = {"total": 0, "passed": 0, "failed": 0}
        stats["by_category"][category]["total"] += 1
    
    # Run tests
    print(f"[*] Running {stats['total']} test queries...\n")
    print("="*80)
    
    for i, test_case in enumerate(TEST_QUERIES, 1):
        query = test_case["query"]
        category = test_case["category"]
        expected_cves = test_case.get("expected_cves", [])
        expected_keywords = test_case.get("expected_keywords", [])
        min_results = test_case.get("min_results", 1)
        description = test_case.get("description", "")
        
        print(f"\n[{i}/{stats['total']}] {category.upper()}: {description}")
        print(f"    Query: '{query}'")
        
        # Execute search
        start_time = time.time()
        try:
            results = search_engine.search(query, limit=10)
            execution_time = time.time() - start_time
            stats["execution_times"].append(execution_time)
            
            # Check results
            passed = False
            reason = ""
            
            if len(results) >= min_results:
                # CVE ID kontrolü (eğer beklenen varsa)
                if expected_cves:
                    found_cves = [r.cve_id for r in results]
                    if any(expected_cve in found_cves for expected_cve in expected_cves):
                        passed = True
                        reason = f"Expected CVE found: {expected_cves[0]}"
                    else:
                        reason = f"Expected CVE not in top results. Got: {found_cves[:3]}"
                
                # Keyword kontrolü
                elif expected_keywords:
                    # İlk 3 sonucun description'ında keyword var mı
                    keyword_found = False
                    for result in results[:3]:
                        desc_lower = result.description.lower()
                        cve_lower = result.cve_id.lower()
                        if any(kw.lower() in desc_lower or kw.lower() in cve_lower for kw in expected_keywords):
                            keyword_found = True
                            break
                    
                    if keyword_found:
                        passed = True
                        reason = "Keywords found in results"
                    else:
                        reason = f"Keywords not found. Expected: {expected_keywords}"
                else:
                    # Sadece sonuç sayısı kontrolü
                    passed = True
                    reason = f"Minimum {min_results} results found"
            else:
                reason = f"Insufficient results: {len(results)}/{min_results}"
            
            # Update stats
            if passed:
                stats["passed"] += 1
                stats["by_category"][category]["passed"] += 1
                status = "[+] PASS"
            else:
                stats["failed"] += 1
                stats["by_category"][category]["failed"] += 1
                status = "[-] FAIL"
            
            print(f"    {status}: {reason}")
            print(f"    Results: {len(results)}, Time: {execution_time:.2f}s")
            
            if results:
                print(f"    Top result: {results[0].cve_id} (score: {results[0].score:.3f})")
            
            # Save details
            stats["details"].append({
                "query": query,
                "category": category,
                "passed": passed,
                "reason": reason,
                "results_count": len(results),
                "execution_time": execution_time,
                "top_cve": results[0].cve_id if results else None
            })
            
        except Exception as e:
            execution_time = time.time() - start_time
            stats["failed"] += 1
            stats["by_category"][category]["failed"] += 1
            stats["execution_times"].append(execution_time)
            
            print(f"    [-] EXCEPTION: {str(e)}")
            
            stats["details"].append({
                "query": query,
                "category": category,
                "passed": False,
                "reason": f"Exception: {str(e)}",
                "results_count": 0,
                "execution_time": execution_time,
                "top_cve": None
            })
    
    # ==================== SUMMARY ====================
    print("\n" + "="*80)
    print(" "*30 + "TEST SUMMARY")
    print("="*80 + "\n")
    
    success_rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0
    avg_time = sum(stats["execution_times"]) / len(stats["execution_times"]) if stats["execution_times"] else 0
    
    print(f"[*] Overall Results:")
    print(f"    Total Tests: {stats['total']}")
    print(f"    Passed: {stats['passed']} ({success_rate:.1f}%)")
    print(f"    Failed: {stats['failed']}")
    print(f"    Average Time: {avg_time:.2f}s")
    print()
    
    print(f"[*] Results by Category:")
    for category, cat_stats in sorted(stats["by_category"].items()):
        cat_success = (cat_stats["passed"] / cat_stats["total"]) * 100 if cat_stats["total"] > 0 else 0
        print(f"    {category.upper():<20}: {cat_stats['passed']}/{cat_stats['total']} ({cat_success:.1f}%)")
    print()
    
    # Failed tests detail
    if stats["failed"] > 0:
        print(f"[-] Failed Tests ({stats['failed']}):")
        failed_tests = [d for d in stats["details"] if not d["passed"]]
        for detail in failed_tests[:10]:  # İlk 10 failed test
            print(f"    • {detail['query'][:60]}")
            print(f"      Reason: {detail['reason']}")
        print()
    
    print("="*80)
    
    # Performance grade
    if success_rate >= 90:
        grade = "EXCELLENT"
        emoji = "🏆"
    elif success_rate >= 80:
        grade = "GOOD"
        emoji = "✅"
    elif success_rate >= 70:
        grade = "SATISFACTORY"
        emoji = "👍"
    elif success_rate >= 60:
        grade = "NEEDS IMPROVEMENT"
        emoji = "⚠️"
    else:
        grade = "POOR"
        emoji = "❌"
    
    print(f"\n{emoji} RAG SEARCH PERFORMANCE: {grade} ({success_rate:.1f}%)\n")
    
    return stats


if __name__ == "__main__":
    try:
        stats = asyncio.run(run_comprehensive_test())
        
        # Exit code based on success rate
        success_rate = (stats["passed"] / stats["total"]) * 100
        if success_rate >= 80:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n[!] Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[-] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

