# -*- coding: utf-8 -*-
"""
service_fingerprinting.py - Basit servis parmak izi çıkarma aracı (bağımlılıksız)

Amaç:
- Belirtilen hedef ve port için TCP bağlantısı kurup banner yakalamaya çalışır
- HTTP servisleri için HEAD isteği ile server bilgisi toplamaya çalışır
- MCPTool arayüzü ile uyumlu, hafif ve Render uyumlu
"""

import socket
import ssl
import json
import logging
from typing import Dict, Any
from tools.base_mcp_tool import MCPTool, ToolCategory

logger = logging.getLogger(__name__)


class ServiceFingerprintingTool(MCPTool):
    def __init__(self):
        super().__init__(
            name="service_fingerprinting",
            description="Belirtilen portta banner ve temel servis bilgisi toplar (bağımlılıksız).",
            category=ToolCategory.DISCOVERY_ENUMERATION
        )

    def _banner_grab(self, host: str, port: int, use_tls: bool = False) -> str:
        try:
            sock = socket.create_connection((host, port), timeout=2.0)
            if use_tls:
                context = ssl.create_default_context()
                sock = context.wrap_socket(sock, server_hostname=host)
            sock.settimeout(2.0)
            try:
                data = sock.recv(1024)
                if data:
                    return data.decode(errors='ignore')
            finally:
                sock.close()
        except Exception as e:
            logger.debug(f"Banner grab failed: {e}")
        return ""

    def _http_head(self, host: str, port: int, use_tls: bool = False) -> Dict[str, str]:
        try:
            proto = "https" if use_tls else "http"
            request = f"HEAD / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
            sock = socket.create_connection((host, port), timeout=3.0)
            if use_tls:
                context = ssl.create_default_context()
                sock = context.wrap_socket(sock, server_hostname=host)
            sock.sendall(request.encode())
            response = b""
            sock.settimeout(3.0)
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            sock.close()
            text = response.decode(errors='ignore')
            headers = {}
            for line in text.split("\r\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    headers[k.strip()] = v.strip()
            return {
                "protocol": proto,
                "server": headers.get("Server", ""),
                "powered_by": headers.get("X-Powered-By", ""),
                "status": text.split("\r\n", 1)[0] if text else ""
            }
        except Exception as e:
            logger.debug(f"HTTP HEAD failed: {e}")
            return {}

    def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        host = params.get("target") or params.get("host")
        port = int(params.get("port", 80))

        if not host:
            return {
                "success": False,
                "error": "'target' zorunlu",
                "data": {}
            }

        result: Dict[str, Any] = {
            "host": host,
            "port": port,
            "banner": "",
            "http_info": {}
        }

        # Banner (plain / TLS)
        result["banner"] = self._banner_grab(host, port, use_tls=False) or self._banner_grab(host, port, use_tls=True)

        # HTTP/HTTPS HEAD
        if port in (80, 8080, 8000):
            result["http_info"] = self._http_head(host, port, use_tls=False)
        elif port in (443, 8443):
            result["http_info"] = self._http_head(host, port, use_tls=True)

        return {
            "success": True,
            "data": result,
            "ai_summary": f"{host}:{port} için temel servis parmak izi çıkarıldı.",
            "ai_reasoning": [
                {"phase": "fingerprint", "thought": "Banner ve HTTP başlıkları toplandı"}
            ],
            "recommendations": []
        }


service_fingerprinting = ServiceFingerprintingTool()


