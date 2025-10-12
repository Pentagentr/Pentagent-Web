# -*- coding: utf-8 -*-
"""
verify_xss_http.py - Render uyumlu, bağımlılıksız XSS doğrulama (reflected) aracı
"""

import requests
import time
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from typing import Dict, Any, List
from tools.base_mcp_tool import MCPTool, ToolCategory


class VerifyXSSHTTP(MCPTool):
    def __init__(self):
        super().__init__(
            name="verify_xss_http",
            description="Bağımlılıksız reflected XSS doğrulama (HTTP yanıtında marker arar)",
            category=ToolCategory.VULNERABILITY_SCANNING
        )
        self.marker = f"pentagent_xss_{int(time.time())}"

    def _inject_param(self, url: str, parameter: str, payload: str) -> str:
        parts = list(urlparse(url))
        qs = parse_qs(parts[4], keep_blank_values=True)
        qs[parameter] = [payload]
        parts[4] = urlencode(qs, doseq=True)
        return urlunparse(parts)

    def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        url = params.get("url")
        parameter = params.get("parameter", "q")
        method = params.get("method", "GET").upper()

        if not url:
            return {"success": False, "error": "'url' zorunlu", "data": {}}

        # Zararsız proof payload'ları
        payloads = [
            f"<pentagent id='{self.marker}'>",
            f"\" autofocus data-pentagent=\"{self.marker}\"",
            f"</script><div id='{self.marker}'></div><script>",
        ]

        findings: List[Dict[str, Any]] = []
        ai_reasoning = [{"phase": "init", "thought": f"HTTP XSS probe started for {url}"}]

        headers = {"User-Agent": "Pentagent/verify_xss_http"}

        for p in payloads:
            try:
                test_url = self._inject_param(url, parameter, p)
                resp = requests.get(test_url, headers=headers, timeout=10)
                text = resp.text or ""
                if self.marker in text:
                    findings.append({
                        "parameter": parameter,
                        "payload": p,
                        "evidence": "marker_reflected_in_body"
                    })
                    break
            except Exception:
                continue

        success = len(findings) > 0
        ai_summary = (
            f"YÜKSEK RİSK! '{parameter}' parametresinde reflected XSS belirtileri bulundu."
            if success else
            "Reflected XSS kanıtı bulunamadı."
        )

        return {
            "success": True,
            "data": {"findings": findings, "target_url": url},
            "ai_summary": ai_summary,
            "ai_reasoning": ai_reasoning,
            "recommendations": []
        }


verify_xss_http = VerifyXSSHTTP()



