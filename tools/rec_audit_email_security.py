#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
rec_audit_email_security.py - Pentagent Projesi için MCP Uyumlu E-posta Güvenlik Denetim Aracı

Amaç: 
Bu araç, bir alan adının e-posta güvenlik yapılandırmalarını (SPF, DMARC, DKIM) 
derinlemesine analiz eder ve güvenlik zafiyetlerini tespit eder. E-posta spoofing,
phishing ve diğer e-posta tabanlı saldırılara karşı koruma durumunu değerlendirir.

Temel Felsefeye Uygunluk:
- Keşfet & Tespit Et: E-posta güvenlik kayıtlarını analiz ederek zafiyetleri tespit eder
- Kanıtla: SPF/DMARC/DKIM yapılandırma hatalarını somut kanıtlarla gösterir
- RAG Girdisi Sağla: Tüm e-posta güvenlik analizlerini yapılandırılmış formatta sunar
- Otonom Ajanı Yönlendir: E-posta güvenlik zafiyetlerine yönelik öneriler sunar
"""

import asyncio
import re
import json
import logging
from typing import Dict, Any, List, Optional
import dns.resolver
import dns.exception

# PentagentTool base class'ını import et
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RecAuditEmailSecurityTool(MCPTool):
    """E-posta güvenlik kayıtlarını analiz eder ve zafiyetleri tespit eder."""
    
    def __init__(self):
        super().__init__(
            name="rec_audit_email_security",
            description="E-posta güvenlik kayıtlarını (SPF, DMARC, DKIM) analiz ederek güvenlik zafiyetlerini tespit eder.",
            category=ToolCategory.RECONNAISSANCE
        )
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = 3
        self.resolver.lifetime = 6

    async def _query_record(self, domain: str, record_type: str) -> List[str]:
        """Belirtilen türde DNS kaydını sorgular."""
        try:
            answers = self.resolver.resolve(domain, record_type)
            return [str(rdata) for rdata in answers]
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
            return []
        except Exception as e:
            logger.warning(f"Error querying {record_type} for {domain}: {e}")
            return []

    async def _analyze_spf(self, domain: str) -> Dict:
        """SPF kaydını analiz eder."""
        txt_records = await self._query_record(domain, 'TXT')
        spf_record = next((r.strip('"') for r in txt_records if r.lower().startswith('"v=spf1')), None)
        if not spf_record:
            return {"found": False, "policy": "none", "warning": "No SPF record found."}
        
        policy = "strong (-all)"
        warning = None
        if "~all" in spf_record:
            policy = "weak (~all)"
            warning = "SPF policy is 'softfail', which is not a strong protection."
        elif "?all" in spf_record or " all" in spf_record and "-all" not in spf_record and "~all" not in spf_record:
            policy = "none (?all or +all)"
            warning = "SPF policy provides no protection against spoofing."

        return {"found": True, "record": spf_record, "policy": policy, "warning": warning}

    async def _analyze_dmarc(self, domain: str) -> Dict:
        """DMARC kaydını analiz eder."""
        dmarc_domain = f"_dmarc.{domain}"
        txt_records = await self._query_record(dmarc_domain, 'TXT')
        dmarc_record = next((r.strip('"') for r in txt_records if r.lower().startswith('"v=dmarc1')), None)
        if not dmarc_record:
            return {"found": False, "policy": "none", "warning": "No DMARC record found."}

        policy_match = re.search(r'p=([a-z]+)', dmarc_record)
        policy = policy_match.group(1) if policy_match else "none"
        warning = "DMARC policy is 'none', which is only for monitoring." if policy == "none" else None
        return {"found": True, "record": dmarc_record, "policy": policy, "warning": warning}

    async def _analyze_dkim(self, domain: str) -> Dict:
        """DKIM kayıtlarını analiz eder."""
        dkim_selectors = ['default', 'google', 'k1', 'selector1', 'selector2']
        dkim_found = []
        
        for selector in dkim_selectors:
            dkim_domain = f"{selector}._domainkey.{domain}"
            txt_records = await self._query_record(dkim_domain, 'TXT')
            dkim_record = next((r.strip('"') for r in txt_records if r.lower().startswith('"v=dkim1')), None)
            if dkim_record:
                dkim_found.append({"selector": selector, "record": dkim_record})
        
        if not dkim_found:
            return {"found": False, "warning": "No DKIM records found."}
        
        return {"found": True, "records": dkim_found}

    async def _check_mx_records(self, domain: str) -> Dict:
        """MX kayıtlarını kontrol eder."""
        mx_records = await self._query_record(domain, 'MX')
        if not mx_records:
            return {"found": False, "warning": "No MX records found - domain cannot receive email."}
        
        return {"found": True, "records": mx_records}

    async def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """E-posta güvenlik analizini gerçekleştirir."""
        domain = params.get("domain")
        if not domain:
            return self._create_final_output(
                success=False,
                ai_summary="Domain parametresi eksik.",
                error="Domain parametresi eksik."
            )

        ai_reasoning_log = []
        self._add_reasoning(ai_reasoning_log, "initialization", f"E-posta güvenlik analizi '{domain}' için başlatıldı.")

        try:
            # E-posta güvenlik kayıtlarını analiz et
            spf_analysis = await self._analyze_spf(domain)
            dmarc_analysis = await self._analyze_dmarc(domain)
            dkim_analysis = await self._analyze_dkim(domain)
            mx_analysis = await self._check_mx_records(domain)

            self._add_reasoning(ai_reasoning_log, "analysis", "E-posta güvenlik kayıtları analiz edildi.")

            # Zafiyetleri tespit et
            vulnerabilities = []
            if not spf_analysis["found"]:
                vulnerabilities.append({"type": "missing_spf", "severity": "high", "description": "SPF record is missing"})
            elif spf_analysis.get("warning"):
                vulnerabilities.append({"type": "weak_spf", "severity": "medium", "description": spf_analysis["warning"]})

            if not dmarc_analysis["found"]:
                vulnerabilities.append({"type": "missing_dmarc", "severity": "high", "description": "DMARC record is missing"})
            elif dmarc_analysis.get("warning"):
                vulnerabilities.append({"type": "weak_dmarc", "severity": "medium", "description": dmarc_analysis["warning"]})

            if not dkim_analysis["found"]:
                vulnerabilities.append({"type": "missing_dkim", "severity": "medium", "description": "DKIM records are missing"})

            if not mx_analysis["found"]:
                vulnerabilities.append({"type": "missing_mx", "severity": "low", "description": "MX records are missing"})

            self._add_reasoning(ai_reasoning_log, "vulnerability_detection", f"{len(vulnerabilities)} e-posta güvenlik zafiyeti tespit edildi.")

            # Öneriler oluştur
            recommendations = []
            for vuln in vulnerabilities:
                if vuln["type"] == "missing_spf":
                    recommendations.append(
                        self._create_recommendation(
                            priority=PriorityLevel.HIGH,
                            tool_name="email_spoofing_tester",
                            reason="SPF kaydı eksik. E-posta spoofing saldırıları mümkün olabilir.",
                            params={"domain": domain, "vulnerability": "missing_spf"}
                        )
                    )
                elif vuln["type"] == "missing_dmarc":
                    recommendations.append(
                        self._create_recommendation(
                            priority=PriorityLevel.HIGH,
                            tool_name="email_phishing_tester",
                            reason="DMARC kaydı eksik. Phishing saldırıları engellenemeyebilir.",
                            params={"domain": domain, "vulnerability": "missing_dmarc"}
                        )
                    )

            # AI Summary oluştur
            if vulnerabilities:
                high_vulns = [v for v in vulnerabilities if v["severity"] == "high"]
                medium_vulns = [v for v in vulnerabilities if v["severity"] == "medium"]
                ai_summary = f"'{domain}' için e-posta güvenlik analizi tamamlandı. {len(high_vulns)} yüksek, {len(medium_vulns)} orta seviye zafiyet tespit edildi."
            else:
                ai_summary = f"'{domain}' için e-posta güvenlik analizi tamamlandı. Kritik bir zafiyet tespit edilmedi."

            self._add_reasoning(ai_reasoning_log, "completion", "E-posta güvenlik analizi başarıyla tamamlandı.")

            return self._create_final_output(
                success=True,
                data={
                    "domain": domain,
                    "spf_analysis": spf_analysis,
                    "dmarc_analysis": dmarc_analysis,
                    "dkim_analysis": dkim_analysis,
                    "mx_analysis": mx_analysis,
                    "vulnerabilities": vulnerabilities
                },
                ai_summary=ai_summary,
                ai_reasoning=ai_reasoning_log,
                recommendations=recommendations
            )

        except Exception as e:
            logger.error(f"E-posta güvenlik analizi sırasında hata: {e}", exc_info=True)
            return self._create_final_output(
                success=False,
                ai_summary="E-posta güvenlik analizi sırasında bir hata oluştu.",
                ai_reasoning=ai_reasoning_log,
                error=str(e)
            )

async def main():
    """Test fonksiyonu"""
    tool = RecAuditEmailSecurityTool()
    test_params = {"domain": "example.com"}
    
    print("--- E-posta Güvenlik Analizi Test ---")
    result = await tool.run_tool(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=True))

if __name__ == "__main__":
    asyncio.run(main())