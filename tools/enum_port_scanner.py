# -*- coding: utf-8 -*-
"""
enum_port_scanner.py - Pentagent Projesi için MCP Uyumlu Port Tarama Modülü

Amaç:
Bu modül, nmap kullanarak hedef sistem üzerinde kapsamlı ve güvenli port taraması yapar.
"Keşfet, Tespit Et, Kanıtla, Raporla" felsefesine uygun olarak, aktif sömürüden
kaçınır ve bulguları MCP (Master Control Program) ajanının anlayabileceği standart
bir JSON formatında raporlar.

Temel Yetenekler:
- Farklı stratejiler için önceden tanımlanmış tarama profilleri (hızlı, standart, derin).
- Tespit edilen servisleri risk seviyelerine göre kategorize etme.
- Bilinen zafiyetli versiyonları (örn: Apache 2.4.49) tespit edip işaretleme.
- Her adımını şeffaf bir şekilde raporlayan AI düşünce süreci (`ai_reasoning`).
- Bulguları özetleyen, insan tarafından okunabilir bir AI özeti (`ai_summary`).
- MCP'nin bir sonraki adımı planlaması için akıllı ve güvenli araç önerileri (`recommendations`).
- Kapsamlı hata yönetimi ve sağlamlaştırılmış nmap entegrasyonu.
"""

import json
import logging
import os
import shutil
import subprocess
import ctypes
import time
from typing import Dict, Any, List, Optional, Tuple

# PentagentTool base class'ını import et
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

# === Konfigürasyon ve Sabitler ===

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

# STRATEJİK DEĞİŞİKLİK: Daha güvenli ve odaklı tarama profilleri.
# 'exploit' gibi tehlikeli script kategorileri kaldırıldı.
SCAN_PROFILES: Dict[str, Dict[str, str]] = {
    "quick": {
        "args": "-sT -T4 --top-ports 20 --min-rate 1000",  # OPTIMIZE: 100→20 port, TCP Connect, hızlı rate
        "description": "Çok Hızlı Tarama: En yaygın 20 port, TCP Connect scan (10-15s)."
    },
    "default": {
        "args": "-sS -sV -T4 --top-ports 1000 -O -A --script vuln",
        "description": "Standart Tarama: En yaygın 1000 port, servis/versiyon/OS tespiti, vulnerability scripts."
    },
    "comprehensive": {
        "args": "-sS -sV -sC -O -A --top-ports 1000 -T4 --script vuln,auth,discovery",
        "description": "Kapsamlı Tarama: Top 1000 port, servis/versiyon/OS tespiti, vulnerability/auth/discovery scripts."
    },
    "aggressive": {
        "args": "-sS -sV -sC -O -A -p- -T4 --script vuln,auth,discovery,exploit",
        "description": "Agresif Tarama: Tüm 65535 port, tam servis/versiyon/OS tespiti, exploit scripts. (ÇOK YAVAŞ)"
    },
    "stealth": {
        "args": "-sS -T2 -f --top-ports 1000 --scan-delay 1s",
        "description": "Gizli Tarama: SYN scan, fragment packets, yavaş timing, IDS bypass."
    }
}

# BİLGİ: Servislerin risk ve kategori analizi için kullanılan yapı.
# Bu yapı, AI'ın risk değerlendirmesi yapmasını sağlar.
SERVICE_RISK_MAP: Dict[str, Dict[str, Any]] = {
    "web": {"ports": [80, 443, 8000, 8080, 8443], "risk": "medium", "desc": "Web Servisi"},
    "database": {"ports": [3306, 5432, 1433, 27017, 6379], "risk": "high", "desc": "Veritabanı Servisi"},
    "remote_access": {"ports": [22, 23, 3389, 5900], "risk": "critical", "desc": "Uzak Erişim Servisi"},
    "file_transfer": {"ports": [21, 445, 139], "risk": "high", "desc": "Dosya Transfer Servisi"},
    "mail": {"ports": [25, 110, 143, 587, 993, 995], "risk": "medium", "desc": "E-posta Servisi"},
}

# BİLGİ: RAG sorgusu için işaretlenecek, bilinen kritik zafiyetli versiyonlar.
# Amaç sömürmek değil, RAG'a sormak üzere işaretlemektir.
KNOWN_VULNERABLE_PATTERNS: Dict[str, Dict[str, str]] = {
    "apache http server 2.4.49": {
        "cve": "CVE-2021-41773",
        "risk": "critical",
        "summary": "Path Traversal ve RCE zafiyeti. Detaylı analiz için RAG sorgusu yapın.",
        "rag_query": "CVE-2021-41773 Apache Path Traversal RCE analysis"
    },
    "vsftpd 2.3.4": {
        "cve": "CVE-2011-2523",
        "risk": "critical",
        "summary": "Komut satırı arka kapısı (backdoor). RAG ile exploit detayları sorgulanmalı.",
        "rag_query": "CVE-2011-2523 vsftpd backdoor exploit analysis"
    },
    "microsoft iis httpd 6.0": {
        "cve": "CVE-2017-7269",
        "risk": "critical",
        "summary": "WebDAV ScStoragePathFromUrl RCE zafiyeti. RAG ile teknik detaylar alınmalı.",
        "rag_query": "CVE-2017-7269 IIS WebDAV RCE analysis"
    },
    "openssh 7.4": {
        "cve": "CVE-2018-15473",
        "risk": "high",
        "summary": "Username enumeration zafiyeti. RAG ile bypass teknikleri sorgulanmalı.",
        "rag_query": "CVE-2018-15473 OpenSSH username enumeration"
    },
    "mysql 5.7.0": {
        "cve": "CVE-2016-6662",
        "risk": "critical",
        "summary": "MySQL privilege escalation. RAG ile exploit chain analizi yapılmalı.",
        "rag_query": "CVE-2016-6662 MySQL privilege escalation"
    }
}


class PortScannerModule(MCPTool):
    """
    MCP için tasarlanmış, nmap tabanlı profesyonel port tarama modülü.
    """

    def __init__(self):
        super().__init__(
            name="enum_port_scanner",
            description="Nmap kullanarak hedef sistem üzerinde kapsamlı ve güvenli port taraması yapar.",
            category=ToolCategory.DISCOVERY_ENUMERATION
        )

    def _is_nmap_installed(self) -> bool:
        """Nmap'in sistemde kurulu olup olmadığını kontrol eder."""
        return shutil.which("nmap") is not None

    def _parse_target_input(self, target: str) -> str:
        """
        Target input'unu parse eder ve Nmap için uygun formata çevirir.
        
        Args:
            target: Virgülle ayrılmış IP'ler, domain'ler veya tek hedef
            
        Returns:
            str: Nmap için uygun formatlanmış hedef string'i
        """
        if not target:
            return ""
            
        # Virgülle ayrılmış hedefleri ayır
        targets = [t.strip() for t in target.split(',') if t.strip()]
        
        if not targets:
            return ""
            
        # Her hedefi kontrol et ve temizle
        cleaned_targets = []
        for t in targets:
            # URL'den domain çıkar (https://example.com -> example.com)
            if t.startswith(('http://', 'https://')):
                from urllib.parse import urlparse
                parsed = urlparse(t)
                t = parsed.netloc or parsed.path
                
            # Port numarası varsa kaldır (example.com:80 -> example.com)
            if ':' in t and not t.count(':') > 1:  # IPv6 değilse
                t = t.split(':')[0]
                
            cleaned_targets.append(t)
        
        # Nmap için uygun format: boşlukla ayrılmış
        return ' '.join(cleaned_targets)

    def _generate_expert_recommendations(self, service_name: str, port: int, product: str, version: str, target: str, port_details: Dict) -> List[Dict]:
        """
        Servise özel dinamik uzman önerileri oluşturur.
        Her servis için farklı stratejiler ve araçlar önerir.
        """
        recommendations = []
        
        # Web servisleri için özel öneriler
        if service_name in ['http', 'https', 'http-proxy']:
            protocol = "https" if port == 443 or "ssl" in service_name else "http"
            url = f"{protocol}://{target}:{port}"
            
            # Teknoloji tespiti - kritik öncelik
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.CRITICAL,
                    tool_name="enum_tech_detector",
                    reason=f"🔍 WEB SERVİS ANALİZİ: Port {port}'da {product} {version} tespit edildi. Teknoloji stack'i, framework versiyonları ve potansiyel zafiyetler analiz edilmeli.",
                    params={"url": url, "deep_scan": True},
                    expert_context=f"Web servislerinde teknoloji tespiti, saldırı yüzeyini belirlemek için kritik. {product} {version} için bilinen CVE'ler kontrol edilmeli."
                )
            )
            
            # HTTP güvenlik başlıkları analizi
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="vuln_http_header_analyzer",
                    reason=f"🛡️ GÜVENLİK BAŞLIKLARI: {product} servisinin HSTS, CSP, X-Frame-Options gibi güvenlik başlıkları eksik olabilir. OWASP Top 10 uyumluluğu kontrol edilmeli.",
                    params={"url": url, "comprehensive": True},
                    expert_context=f"Modern web güvenlik standartları için kritik. {product} için önerilen güvenlik başlıkları implementasyonu gerekli."
                )
            )
            
            # Web crawling ve endpoint keşfi
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="enum_web_crawler",
                    reason=f"🕷️ ENDPOINT KEŞFİ: {product} servisinde gizli endpoint'ler, admin panelleri ve API'ler keşfedilmeli. Directory traversal ve hidden files analizi yapılmalı.",
                    params={"url": url, "depth": 3, "aggressive": True},
                    expert_context=f"Web uygulaması saldırı yüzeyinin genişletilmesi için kritik. {product} için yaygın endpoint'ler ve admin panelleri kontrol edilmeli."
                )
            )
            
            # SQL Injection ve XSS testleri
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="verify_sqli",
                    reason=f"💉 SQL INJECTION TESTİ: {product} {version} için bilinen SQL injection zafiyetleri test edilmeli. Parameterized query kullanımı kontrol edilmeli.",
                    params={"url": url, "method": "POST", "params": ["id", "user", "search"]},
                    expert_context=f"E-commerce platformları için kritik güvenlik testi. {product} için bilinen SQL injection pattern'leri uygulanmalı."
                )
            )
            
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="verify_xss",
                    reason=f"🎭 XSS TESTİ: {product} servisinde Cross-Site Scripting zafiyetleri test edilmeli. Input validation ve output encoding kontrol edilmeli.",
                    params={"url": url, "payloads": ["reflected", "stored", "dom"]},
                    expert_context=f"Kullanıcı girdisi işleyen web uygulamaları için kritik. {product} için XSS payload'ları ve bypass teknikleri test edilmeli."
                )
            )
        
        # SSH servisleri için özel öneriler
        elif service_name == 'ssh':
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="ssh_cipher_checker",
                    reason=f"🔐 SSH GÜVENLİK ANALİZİ: {product} {version} SSH servisinin cipher suite'i, key exchange algoritmaları ve authentication methodları analiz edilmeli.",
                    params={"target": target, "port": port, "version_detection": True},
                    expert_context=f"SSH servisleri için kritik güvenlik analizi. {product} {version} için önerilen cipher suite'ler ve güvenlik konfigürasyonları kontrol edilmeli."
                )
            )
            
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.MEDIUM,
                    tool_name="ssh_bruteforce_test",
                    reason=f"🔑 SSH BRUTE FORCE TESTİ: {product} servisinde weak authentication ve password policy zafiyetleri test edilmeli.",
                    params={"target": target, "port": port, "wordlist": "common_passwords"},
                    expert_context=f"SSH servisleri için authentication güvenliği testi. {product} için yaygın credential'lar ve weak password pattern'leri test edilmeli."
                )
            )
        
        # Database servisleri için özel öneriler
        elif service_name in ['mysql', 'postgresql', 'mongodb', 'redis']:
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.CRITICAL,
                    tool_name="database_security_scanner",
                    reason=f"🗄️ DATABASE GÜVENLİK ANALİZİ: {product} {version} veritabanı servisinin authentication, authorization ve encryption ayarları analiz edilmeli.",
                    params={"target": target, "port": port, "db_type": service_name, "version": version},
                    expert_context=f"Database servisleri için kritik güvenlik analizi. {product} {version} için bilinen zafiyetler ve güvenlik konfigürasyonları kontrol edilmeli."
                )
            )
            
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="database_enumeration",
                    reason=f"🔍 DATABASE ENUMERATION: {product} servisinde database schema, tables, users ve permissions keşfedilmeli.",
                    params={"target": target, "port": port, "db_type": service_name},
                    expert_context=f"Database servisleri için bilgi toplama. {product} için yaygın database enumeration teknikleri uygulanmalı."
                )
            )
        
        # FTP servisleri için özel öneriler
        elif service_name == 'ftp':
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="ftp_security_scanner",
                    reason=f"📁 FTP GÜVENLİK ANALİZİ: {product} {version} FTP servisinin anonymous access, weak authentication ve directory traversal zafiyetleri test edilmeli.",
                    params={"target": target, "port": port, "anonymous_test": True},
                    expert_context=f"FTP servisleri için kritik güvenlik analizi. {product} {version} için bilinen zafiyetler ve güvenlik konfigürasyonları kontrol edilmeli."
                )
            )
        
        # SMTP servisleri için özel öneriler
        elif service_name == 'smtp':
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.MEDIUM,
                    tool_name="smtp_security_scanner",
                    reason=f"📧 SMTP GÜVENLİK ANALİZİ: {product} {version} SMTP servisinin open relay, authentication bypass ve email spoofing zafiyetleri test edilmeli.",
                    params={"target": target, "port": port, "relay_test": True},
                    expert_context=f"SMTP servisleri için email güvenliği analizi. {product} {version} için bilinen zafiyetler ve email security konfigürasyonları kontrol edilmeli."
                )
            )
        
        # Bilinmeyen servisler için genel öneriler
        else:
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.MEDIUM,
                    tool_name="service_fingerprinting",
                    reason=f"🔍 SERVİS FİNGERPRİNTİNG: Port {port}'da {service_name} servisi tespit edildi. Detaylı servis analizi ve bilinen zafiyetler kontrol edilmeli.",
                    params={"target": target, "port": port, "service": service_name},
                    expert_context=f"Bilinmeyen servisler için güvenlik analizi. {service_name} için yaygın zafiyetler ve güvenlik konfigürasyonları araştırılmalı."
                )
            )
        
        return recommendations

    def _perform_scan(self, target: str, profile: str, reasoning_log: List[Dict[str, str]]) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Nmap taramasını subprocess kullanarak daha güvenli ve kontrol edilebilir bir şekilde çalıştırır.
        XML çıktısı alarak daha kolay ve hatasız parse etme imkanı sunar.

        Returns:
            Tuple[Optional[Dict], Optional[str]]: Başarılı ise (scan_data, None),
                                                 başarısız ise (None, error_message).
        """
        if not self._is_nmap_installed():
            # Nmap yoksa: En yaygın portlarda hızlı TCP connect fallback taraması (saf Python)
            try:
                import socket
                self._add_reasoning(reasoning_log, "fallback_scan", "Nmap bulunamadı. Python tabanlı hızlı port taraması başlatılıyor (top common ports).")
                parsed_targets = self._parse_target_input(target)
                host = parsed_targets.split()[0] if parsed_targets else target
                common_ports = [80, 443, 22, 21, 25, 110, 143, 587, 993, 995, 8080, 8443, 3306, 5432, 6379, 27017, 3389, 5900, 445, 139]
                open_tcp = {}
                for p in common_ports:
                    try:
                        with socket.create_connection((host, p), timeout=1.0):
                            open_tcp[p] = {"state": "open", "name": "unknown", "product": "", "version": "", "cpe": ""}
                    except Exception:
                        # closed/filtered - ignore
                        continue
                scan_data = {"scan": {host: {"tcp": open_tcp}}}
                return scan_data, None
            except Exception as e:
                return None, f"Nmap yok ve fallback tarama başarısız: {str(e)}"

        # Target'ı parse et - virgülle ayrılmış IP'leri düzelt
        parsed_targets = self._parse_target_input(target)
        reasoning_log.append({"phase": "target_parsing", "thought": f"Hedef parse edildi: {parsed_targets}"})

        scan_args = SCAN_PROFILES[profile]["args"]
        # -oX - : Çıktıyı XML formatında stdout'a yazdırır. Bu, en güvenilir parse yöntemidir.
        command = f"nmap {scan_args} -oX - {parsed_targets}"
        
        # Root gerektiren taramalar için kontrol
        if "-sS" in command:
            try:
                # Windows için farklı kontrol
                if os.name == 'nt':
                    # Windows'ta admin kontrolü
                    is_admin = ctypes.windll.shell32.IsUserAnAdmin()
                    if not is_admin:
                        self._add_reasoning(reasoning_log, "pre_scan_check", "⚠️ SYN scan (-sS) için admin yetkisi gerekiyor. TCP Connect scan (-sT) ile devam edilecek.")
                        command = command.replace("-sS", "-sT")
                else:
                    # Linux/Unix için root kontrolü
                    if os.geteuid() != 0:
                        self._add_reasoning(reasoning_log, "pre_scan_check", "⚠️ SYN scan (-sS) için root yetkisi gerekiyor. TCP Connect scan (-sT) ile devam edilecek.")
                        command = command.replace("-sS", "-sT")
            except Exception:
                # Hata durumunda güvenli moda geç
                self._add_reasoning(reasoning_log, "pre_scan_check", "⚠️ Yetki kontrolü başarısız. TCP Connect scan (-sT) ile devam edilecek.")
                command = command.replace("-sS", "-sT")

        self._add_reasoning(reasoning_log, "execution_start", f"Nmap komutu yürütülüyor: {command}")
        
        try:
            # Dinamik timeout - scan tipine göre ayarla - OPTIMIZE
            if profile == "quick":
                timeout_seconds = 60  # 30→60: Daha güvenli timeout
            elif profile == "default":
                timeout_seconds = 180  # 120→180: Daha kapsamlı tarama için
            elif profile == "comprehensive":
                timeout_seconds = 300  # 5 dakika
            elif profile == "aggressive":
                timeout_seconds = 600  # 10 dakika
            else:
                timeout_seconds = 120
                
            self._add_reasoning(reasoning_log, "scan_details", f"Tarama başlatılıyor: {profile} profili, timeout: {timeout_seconds}s")
            
            process = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                check=False, # Hata durumunda exception fırlatmaması için
                timeout=timeout_seconds
            )
            
            # Verbose logging
            self._add_reasoning(reasoning_log, "scan_output", f"Nmap return code: {process.returncode}")
            if process.stdout:
                self._add_reasoning(reasoning_log, "scan_output", f"Nmap stdout length: {len(process.stdout)} characters")
            if process.stderr:
                self._add_reasoning(reasoning_log, "scan_error", f"Nmap stderr: {process.stderr[:200]}...")

            if process.returncode != 0:
                # Nmap bir hata kodu ile bittiyse
                error_output = process.stderr.strip()
                if "Failed to resolve" in error_output:
                    return None, f"Hedef çözümlenemedi: {parsed_targets}. Orijinal hedef: {target}. Lütfen geçerli IP/domain formatı kullanın."
                if "Host seems down" in error_output:
                    return None, f"Hedef {parsed_targets} kapalı veya güvenlik duvarı tarafından engelleniyor. Orijinal hedef: {target}"
                if "No targets were specified" in error_output:
                    return None, f"Hedef belirtilmedi: {target}. Parse edilen hedef: {parsed_targets}. Lütfen geçerli format kullanın."
                logger.error(f"Nmap hata verdi: {error_output}")
                return None, f"Nmap çalıştırılırken hata: {error_output}. Orijinal hedef: {target}, Parse edilen: {parsed_targets}"

            # Nmap çıktısını parse etmek için python-nmap'in XML parser'ını kullanalım
            # Bu yöntem, 'nmap' kütüphanesinin scan() metodundaki bug'lardan etkilenmez.
            import nmap
            nm = nmap.PortScanner()
            
            # XML parsing'i iyileştir
            try:
                scan_data = nm.analyse_nmap_xml_scan(process.stdout)
                reasoning_log.append({"phase": "xml_parsing", "thought": "XML parsing başarılı"})
            except Exception as e:
                reasoning_log.append({"phase": "xml_parsing_error", "thought": f"XML parsing hatası: {str(e)}"})
                return None, f"XML parsing hatası: {str(e)}"
            
            if "scan" not in scan_data or not scan_data["scan"]:
                # Boş sonuç da geçerli bir sonuçtur - hedef kapalı olabilir
                reasoning_log.append({"phase": "no_open_ports", "thought": "Hedef sistemde açık port tespit edilemedi. Hedef kapalı olabilir veya firewall koruması altında olabilir. AI alternatif strateji önerebilir."})
                return {"scan": {}}, None

            reasoning_log.append({"phase": "execution_complete", "thought": "Nmap taraması başarıyla tamamlandı, sonuçlar parse ediliyor."})
            return scan_data, None

        except subprocess.TimeoutExpired:
            return None, f"Tarama zaman aşımına uğradı ({profile} profili). Daha hızlı bir profil ('quick') deneyin."
        except FileNotFoundError:
             return None, "Nmap komutu bulunamadı. Lütfen sisteminize nmap kurduğunuzdan emin olun."
        except Exception as e:
            logger.exception(f"Nmap taramasında beklenmedik bir hata oluştu: {e}")
            return None, f"Beklenmedik bir hata oluştu: {str(e)}"

    def _get_fallback_profile(self, original_profile: str) -> str:
        """AI için fallback profil önerisi"""
        fallback_map = {
            "aggressive": "comprehensive",
            "comprehensive": "default", 
            "default": "quick",
            "stealth": "quick",
            "quick": None  # Son çare yok
        }
        return fallback_map.get(original_profile, "default")

    def _analyze_and_recommend(self, target: str, scan_data: Dict, reasoning_log: List[Dict[str, str]]) -> Tuple[Dict, List]:
        """
        Parse edilmiş nmap verisini analiz eder, bulguları yapılandırır ve öneriler üretir.
        """
        reasoning_log.append({"phase": "analysis_start", "thought": "Tarama sonuçları analiz ediliyor ve riskler değerlendiriliyor."})
        
        open_ports_data = []
        recommendations = []
        hosts = list(scan_data['scan'].keys())
        
        if not hosts:
            return {"open_ports": []}, []
            
        host_data = scan_data['scan'][hosts[0]]

        if 'tcp' not in host_data:
            return {"open_ports": []}, []

        for port, port_info in host_data['tcp'].items():
            if port_info['state'] == 'open':
                service_name = port_info.get('name', 'unknown')
                product = port_info.get('product', '').lower()
                version = port_info.get('version', '').lower()
                full_version_str = f"{product} {version}".strip()
                
                port_details = {
                    "port": port,
                    "service": service_name,
                    "product": product,
                    "version": version,
                    "cpe": port_info.get('cpe', '')
                }

                # Risk ve kategori belirleme
                risk_info = {"level": "low", "description": "Bilinmeyen Servis"}
                for cat, details in SERVICE_RISK_MAP.items():
                    if port in details['ports']:
                        risk_info = {"level": details['risk'], "description": details['desc']}
                        break
                port_details["risk_info"] = risk_info

                # Bilinen zafiyetli pattern kontrolü
                for pattern, vuln_info in KNOWN_VULNERABLE_PATTERNS.items():
                    if pattern in full_version_str:
                        port_details["known_vulnerability"] = vuln_info
                        self._add_reasoning(reasoning_log, "critical_finding", f"⚠️ KRİTİK BULGU: Port {port}'da bilinen zafiyetli servis tespit edildi: {full_version_str} ({vuln_info['cve']})")
                        # Dependency scanner için öneri oluştur + RAG yönlendirmesi
                        recommendations.append(
                            self._create_recommendation(
                                priority=PriorityLevel.CRITICAL,
                                tool_name="vuln_dependency_scanner",
                                reason=f"🚨 KRİTİK CVE TESPİTİ: Port {port}'daki {product} servisi, kritik zafiyet ({vuln_info['cve']}) içeriyor. {vuln_info['summary']}",
                                params={
                                    "target": "{{final_url}}", 
                                    "cve_id": vuln_info['cve'],
                                    "rag_query": vuln_info.get('rag_query', f"CVE analysis for {vuln_info['cve']}")
                                },
                                expert_context=f"Kritik CVE tespiti: {vuln_info['cve']} - {vuln_info['summary']} Detaylı exploit analizi için RAG sistemi kullanın."
                            )
                        )
                        break
                
                open_ports_data.append(port_details)

                # Dinamik servise özel uzman önerileri
                service_recommendations = self._generate_expert_recommendations(
                    service_name, port, product, version, target, port_details
                )
                recommendations.extend(service_recommendations)


        structured_data = {
            "open_ports": sorted(open_ports_data, key=lambda x: x['port']),
            # RAG-friendly format - Rapor aşamasında analiz edilecek
            "rag_analysis_data": {
                "services_for_cve_lookup": [
                    {
                        "port": port['port'],
                        "service": port['service'],
                        "product": port['product'],
                        "version": port['version'],
                        "cve_reference": port.get('known_vulnerability', {}),
                        "rag_query_suggestion": f"CVE analysis for {port['product']} {port['version']} on port {port['port']}"
                    }
                    for port in open_ports_data
                    if port.get('product') and port.get('version')
                ],
                "critical_vulnerabilities": [
                    {
                        "cve_id": port['known_vulnerability']['cve'],
                        "service": f"{port['product']} {port['version']}",
                        "port": port['port'],
                        "risk_level": port['known_vulnerability']['risk'],
                        "rag_query_suggestion": f"Exploit analysis for {port['known_vulnerability']['cve']}"
                    }
                    for port in open_ports_data
                    if 'known_vulnerability' in port
                ],
                "scan_metadata": {
                    "target": target,
                    "scan_timestamp": time.time(),
                    "scan_type": "port_scanning",
                    "total_open_ports": len(open_ports_data),
                    "critical_vulns_found": len([p for p in open_ports_data if 'known_vulnerability' in p])
                }
            }
        }
        # Önerileri önceliğe göre sırala
        priority_map = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_recommendations = sorted(recommendations, key=lambda x: priority_map.get(x['priority'], 99))
        
        reasoning_log.append({"phase": "analysis_complete", "thought": f"{len(open_ports_data)} açık port ve {len(sorted_recommendations)} öneri ile analiz tamamlandı."})
        
        return structured_data, sorted_recommendations

    def _create_recommendation(self, priority: PriorityLevel, tool_name: str, reason: str, params: Dict[str, Any], expert_context: str = None) -> Dict[str, Any]:
        """MCP formatında öneri oluşturur"""
        recommendation = {
            "priority": priority.value,
            "tool": tool_name,
            "reason": reason,
            "params": params
        }
        
        if expert_context:
            recommendation["expert_context"] = expert_context
            
        return recommendation

    def _generate_ai_summary(self, data: Dict) -> str:
        """Analiz sonuçlarından insan tarafından okunabilir bir özet oluşturur."""
        open_ports = data.get("open_ports", [])
        if not open_ports:
            return "Hedef sistemde açık bir porta rastlanmadı. Hedef kapalı olabilir veya firewall koruması altında olabilir. AI alternatif strateji önerebilir."

        port_count = len(open_ports)
        summary = f"Hedefte toplam {port_count} adet açık port tespit ettim. "
        
        critical_findings = []
        high_risk_services = []
        
        for port in open_ports:
            if "known_vulnerability" in port:
                critical_findings.append(f"port {port['port']}'daki {port['product']} ({port['known_vulnerability']['cve']})")
            elif port['risk_info']['level'] in ['critical', 'high']:
                high_risk_services.append(f"{port['risk_info']['description']} (port {port['port']})")

        if critical_findings:
            summary += f"Özellikle, {', '.join(critical_findings)} bilinen kritik zafiyetlere sahip. "
        
        if high_risk_services:
            # Tekrarları önle
            unique_high_risk = sorted(list(set(high_risk_services)))
            summary += f"Ayrıca, {', '.join(unique_high_risk)} gibi internete açık yüksek riskli servisler dikkat çekiyor. "
            
        summary += "Bir sonraki adım olarak bu servislerin detaylı incelenmesini öneriyorum."
        return summary.strip()

    def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Modülün ana çalışma fonksiyonu.
        Girdiyi alır, taramayı yapar, analiz eder ve standart JSON çıktısını üretir.
        """
        target = params.get("target")
        profile = params.get("profile", "default")
        
        # 1. AI Düşünce Sürecini Başlat
        ai_reasoning = []
        self._add_reasoning(ai_reasoning, "initialization", f"Port tarama modülü '{target}' hedefi için '{profile}' profili ile başlatıldı.")

        # 2. Parametre Doğrulama
        if not target:
            return self._create_final_output(
                success=False,
                ai_summary="Hedef belirtilmedi.",
                ai_reasoning=ai_reasoning,
                error="Çalıştırmak için 'target' parametresi zorunludur."
            )
        if profile not in SCAN_PROFILES:
            return self._create_final_output(
                success=False,
                ai_summary="Geçersiz profil.",
                ai_reasoning=ai_reasoning,
                error=f"Geçersiz profil: '{profile}'. Kullanılabilir profiller: {list(SCAN_PROFILES.keys())}"
            )
            
        # 3. Taramayı Gerçekleştir
        scan_data, error = self._perform_scan(target, profile, ai_reasoning)
        if error:
            return self._create_final_output(
                success=False,
                ai_summary="Tarama sırasında bir hata oluştu.",
                ai_reasoning=ai_reasoning,
                error=error
            )

        # 4. Sonuçları Analiz Et ve Önerileri Oluştur
        structured_data, recommendations = self._analyze_and_recommend(target, scan_data, ai_reasoning)

        # 5. Yapay Zeka Özetini Oluştur
        ai_summary = self._generate_ai_summary(structured_data)

        # 6. Başarılı Sonuç İçin Standart JSON Çıktısını Oluştur
        return self._create_final_output(
            success=True,
            data=structured_data,
            ai_summary=ai_summary,
            ai_reasoning=ai_reasoning,
            recommendations=recommendations
        )


# === Komut Satırı Test Bloğu ===
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description="Pentagent - MCP Uyumlu Port Tarama Modülü",
        formatter_class=argparse.RawTextHelpFormatter # Profil açıklamalarını daha iyi göstermek için
    )
    parser.add_argument("target", help="Taranacak hedef (IP adresi veya alan adı).")
    
    profile_help = "Kullanılacak tarama profili:\n"
    for key, value in SCAN_PROFILES.items():
        profile_help += f"  - {key}: {value['description']}\n"
    
    parser.add_argument(
        "-p", "--profile", 
        choices=SCAN_PROFILES.keys(), 
        default="default", 
        help=profile_help
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Çıktıyı daha detaylı göstermek için (data ve reasoning alanlarını gösterir)."
    )

    args = parser.parse_args()

    # Root yetkisi uyarısı (Windows uyumluluğu için)
    try:
        # Unix/Linux sistemlerde root kontrolü
        if hasattr(os, 'geteuid') and os.geteuid() != 0:
            print("\nUYARI: Program root yetkileri olmadan çalıştırılıyor.")
            print("Bazı nmap tarama tipleri (örn: SYN Scan) root yetkisi gerektirebilir.")
            print("Modül, yetki gerektiren durumları otomatik olarak yönetmeye çalışacaktır.\n")
        elif not hasattr(os, 'geteuid'):
            # Windows sistemlerde admin kontrolü
            import ctypes
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin()
                if not is_admin:
                    print("\nUYARI: Program admin yetkileri olmadan çalıştırılıyor.")
                    print("Bazı nmap tarama tipleri admin yetkisi gerektirebilir.")
                    print("Modül, yetki gerektiren durumları otomatik olarak yönetmeye çalışacaktır.\n")
            except:
                print("\nUYARI: Sistem yetkisi kontrol edilemedi.")
                print("Modül, yetki gerektiren durumları otomatik olarak yönetmeye çalışacaktır.\n")
    except Exception as e:
        print(f"\nUYARI: Yetki kontrolü yapılamadı: {e}")
        print("Modül, yetki gerektiren durumları otomatik olarak yönetmeye çalışacaktır.\n")

    scanner = PortScannerModule()
    
    print(f"[+] Hedef: {args.target}")
    print(f"[+] Profil: {args.profile}")
    print("[+] Tarama başlatılıyor, lütfen bekleyin...")

    # Modülü çalıştır
    result = scanner.run_tool(params={"target": args.target, "profile": args.profile})

    print("\n" + "="*50)
    print("TARAMA TAMAMLANDI - MCP ÇIKTISI")
    print("="*50)

    # Sonucu güzel bir formatta yazdır
    if result['success']:
        print("\n[✅ BAŞARI DURUMU]: Tarama başarıyla tamamlandı.")
        
        print("\n--- AI Summary ---")
        print(result['ai_summary'])

        if args.verbose:
            print("\n--- AI Reasoning ---")
            for step in result['ai_reasoning']:
                print(f"  [{step['phase']}] -> {step['thought']}")

            print("\n--- Structured Data (data) ---")
            print(json.dumps(result['data'], indent=2, ensure_ascii=False))

        print("\n--- Recommendations ---")
        if result['recommendations']:
            for rec in result['recommendations']:
                print(f"  - Priority: {rec['priority'].upper()}")
                print(f"    Tool: {rec['tool']}")
                print(f"    Reason: {rec['reason']}")
                print(f"    Params: {rec['params']}")
                print("-" * 20)
        else:
            print("  Herhangi bir sonraki adım önerisi bulunamadı.")
            
    else:
        print("\n[❌ HATA DURUMU]: Tarama başarısız oldu.")
        print(f"\n--- Hata Mesajı ---")
        print(result['error'])

        if args.verbose:
            print("\n--- AI Reasoning (Hata anına kadar) ---")
            for step in result['ai_reasoning']:
                print(f"  [{step['phase']}] -> {step['thought']}")

    print("\n" + "="*50)

# MCP Tool instance
enum_port_scanner = PortScannerModule()