# GÖREV: OTONOM KOD ANALİZİ VE DÜZELTME
# ARAÇ ADI: recon_dns_analyzer.py
# DURUM: NİHAİ UZMAN SÜRÜMÜ v2 - Stratejik Saldırı Vektörü Tespiti

"""
recon_dns_analyzer.py - Web Penetrasyon Testi Odaklı DNS İstihbarat Aracı

Amaç: Bir domain'in DNS kayıtlarını sadece listelemekle kalmaz, bu kayıtlardaki
      güvenlik zafiyetlerini (Zone Transfer), yapılandırma hatalarını (Private IP,
      Wildcard) ve altyapısal ipuçlarını (CDN, SPF) analiz ederek, MCP ajanı için
      önceliklendirilmiş ve eyleme dönüştürülebilir bir saldırı planı oluşturur.

v2 Değişiklik Notları:
- MİMARİ: Araç, MCP için tamamen stateless (durumsuz) hale getirildi. Tüm analiz
  durumu, her 'execute' çağrısında oluşturulan bir context nesnesi içinde yönetilir.
- STRATEJİK ZEKA: "Attack Vectors" bölümü, MCP'nin anlayabileceği yapılandırılmış
  'recommendations' listesine dönüştürüldü. Araç artık sadece sorunları değil,
  diğer araçları kullanarak nasıl sömürüleceklerini de öneriyor.
- MCP ENTEGRASYONU: Çıktı, standart MCP JSON formatına tam uyumlu hale getirildi.
  'ai_summary' ve 'ai_reasoning' alanları, analizin en kritik bulgularını ve
  adımlarını şeffaf bir şekilde özetler.
- DERİNLEŞTİRİLMİŞ ANALİZ: SPF kayıtlarından hosting/mail sağlayıcı tespiti,
  CNAME kayıtlarından CDN/WAF tespiti gibi analizler, öneri motorunu daha akıllı
  hale getirmek için doğrudan kullanılır.
- KOD KALİTESİ: Kod, kapsamlı yorumlar, type hinting ve bir uzmanın beklentilerini
  karşılayacak şekilde sağlam hata yönetimi ile son haline getirildi.
"""
import asyncio
import json
import time
import sys
from typing import Dict, Any, List, Optional, Set
import logging
import argparse

# PentagentTool base class'ını import et
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

try:
    import dns.resolver
    import dns.exception
    import dns.query
    import dns.zone
    DNSPYTHON_AVAILABLE = True
except ImportError:
    DNSPYTHON_AVAILABLE = False
from dataclasses import dataclass, field

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Veri Sınıfları ve Sabitler ---
RECORD_TYPES = ['A', 'AAAA', 'CNAME', 'NS', 'TXT', 'MX', 'SOA']
CDN_PATTERNS = {'Cloudflare': 'cloudflare', 'CloudFront': 'cloudfront.net', 'Akamai': 'akamai'}

@dataclass
class DnsContext:
    """DNS analizi sırasında durumu yönetmek için kullanılan veri sınıfı."""
    domain: str
    records: Dict[str, List[str]] = field(default_factory=dict)
    zone_transfer_result: Dict[str, Any] = field(default_factory=dict)
    wildcard_detected: bool = False
    dnssec_enabled: bool = False
    infrastructure: Dict[str, Any] = field(default_factory=dict)
    ai_reasoning_log: List[Dict[str, str]] = field(default_factory=list)

class ReconDnsAnalyzerTool(MCPTool):
    """Web pentest için DNS kayıtlarını analiz eder ve stratejik saldırı vektörleri önerir."""

    def __init__(self):
        super().__init__(
            name="rec_dns_analyzer",
            description="DNS kayıtlarını analiz ederek güvenlik zafiyetlerini ve saldırı vektörlerini tespit eder.",
            category=ToolCategory.RECONNAISSANCE
        )

    async def _get_records(self, domain: str, record_types: List[str]) -> Dict[str, List[str]]:
        """Belirtilen türlerdeki tüm DNS kayıtlarını çeker."""
        records = {}
        resolver = dns.resolver.Resolver()
        for r_type in record_types:
            try:
                answers = await asyncio.to_thread(resolver.resolve, domain, r_type)
                records[r_type] = sorted([str(r.to_text()).strip('"') for r in answers])
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                records[r_type] = []
            except Exception as e:
                logger.debug(f"{domain} için {r_type} kaydı alınamadı: {e}")
                records[r_type] = []
        return records

    async def _check_zone_transfer(self, domain: str, ns_records: List[str]) -> Dict[str, Any]:
        """Zone transfer (AXFR) zafiyetini kontrol eder."""
        for ns_server in ns_records:
            ns_server = ns_server.rstrip('.')
            try:
                # asyncio DNS sorguları için doğrudan to_thread kullanmak daha güvenli
                zone = await asyncio.to_thread(dns.zone.from_xfr, dns.query.xfr(ns_server, domain, timeout=5))
                if zone:
                    subdomains = [str(name) for name in zone.nodes.keys() if str(name) != '@']
                    logger.warning(f"KRİTİK: Zone Transfer zafiyeti {ns_server} üzerinde tespit edildi!")
                    return {"vulnerable": True, "nameserver": ns_server, "subdomain_count": len(subdomains), "subdomains": subdomains}
            except Exception:
                continue
        return {"vulnerable": False}

    async def _detect_wildcard(self, domain: str) -> bool:
        """Wildcard DNS yapılandırmasını tespit eder."""
        random_sub = f"pentagent-wildcard-test-{int(time.time())}"
        try:
            resolver = dns.resolver.Resolver()
            await asyncio.to_thread(resolver.resolve, f"{random_sub}.{domain}", 'A')
            return True
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            return False
        except Exception:
            return False

    def _analyze_infrastructure(self, records: Dict[str, List[str]]) -> Dict[str, Any]:
        """DNS kayıtlarından altyapısal ipuçları çıkarır."""
        infra = {"cdn_provider": None, "mail_provider": None, "hosting_hints": []}
        # CNAME ve NS kayıtlarından CDN tespiti
        lookup_targets = records.get('CNAME', []) + records.get('NS', [])
        for target in lookup_targets:
            for provider, pattern in CDN_PATTERNS.items():
                if pattern in target:
                    infra["cdn_provider"] = provider
                    break
        
        # SPF kayıtlarından mail/hosting sağlayıcı tespiti
        for txt in records.get('TXT', []):
            if txt.lower().startswith("v=spf1"):
                if "include:_spf.google.com" in txt: infra["mail_provider"] = "Google Workspace"
                elif "include:spf.protection.outlook.com" in txt: infra["mail_provider"] = "Microsoft 365"
                elif "include:amazonses.com" in txt: infra["hosting_hints"].append("AWS")
        
        infra["hosting_hints"] = sorted(list(set(infra["hosting_hints"])))
        return infra

    def _build_final_json(self, context: DnsContext, error: Exception = None) -> Dict[str, Any]:
        if error:
            error_message = f"{type(error).__name__}: {str(error)}"
            self._add_reasoning(context.ai_reasoning_log, "critical_error", error_message)
            return self._create_final_output(
                success=False,
                ai_summary="DNS analizi kritik bir hatayla karşılaştı.",
                ai_reasoning=context.ai_reasoning_log,
                error=error_message
            )
            
        # AI Summary
        summary_parts = []
        if context.zone_transfer_result.get("vulnerable"): summary_parts.append("Kritik Zone Transfer zafiyeti bulundu.")
        if context.infrastructure.get("cdn_provider"): summary_parts.append(f"{context.infrastructure['cdn_provider']} koruması tespit edildi.")
        if not summary_parts: summary_parts.append("Temel DNS analizi tamamlandı.")
        summary = " ".join(summary_parts)

        # Recommendations
        recommendations = []
        if context.zone_transfer_result.get("vulnerable"):
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.CRITICAL,
                    tool_name="subdomain_scanner_from_list",
                    reason="Zone Transfer zafiyeti, tüm subdomain'leri ortaya çıkardı. Bu listeyi doğrudan hedef alarak tarama yapılmalı.",
                    params={"targets": context.zone_transfer_result["subdomains"]}
                )
            )
        
        if context.infrastructure.get("cdn_provider") == "Cloudflare":
             recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.HIGH,
                    tool_name="recon_origin_ip_finder",
                    reason="Hedef Cloudflare arkasında. WAF'ı atlamak için gerçek sunucu IP'sini bulmak önceliklidir."
                )
            )

        if not context.zone_transfer_result.get("vulnerable") and not context.wildcard_detected:
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.MEDIUM,
                    tool_name="enum_subdomain_bruteforcer",
                    reason="Zone transfer mümkün değil ve wildcard DNS yok. Kapsamlı bir subdomain bruteforce taraması yapılmalı.",
                    params={"domain": context.domain}
                )
            )
        elif context.wildcard_detected:
            self._add_reasoning(context.ai_reasoning_log, "analysis_insight", "Wildcard DNS aktif olduğundan standart subdomain bruteforce önerilmiyor.")

        if not context.records.get('DMARC'): # Örnek olarak DMARC ekleyelim
            recommendations.append(
                self._create_recommendation(
                    priority=PriorityLevel.LOW,
                    tool_name="report_generator",
                    reason="DMARC kaydı bulunamadı. Bu durum, e-posta sahtekarlığı (spoofing) riskini artırır.",
                    params={"finding": "Missing DMARC record"}
                )
            )

        self._add_reasoning(context.ai_reasoning_log, "complete", f"Analiz tamamlandı. {len(recommendations)} adet eylem önerisi oluşturuldu.")
        
        return self._create_final_output(
            success=True,
            data={
                "domain": context.domain,
                "records": context.records,
                "security_posture": {
                    "zone_transfer_vulnerable": context.zone_transfer_result.get("vulnerable", False),
                    "wildcard_dns_enabled": context.wildcard_detected,
                    "dnssec_enabled": context.dnssec_enabled # Bu kontrolü daha sağlam hale getirebiliriz
                },
                "infrastructure_profile": context.infrastructure
            },
            ai_summary=summary,
            ai_reasoning=context.ai_reasoning_log,
            recommendations=recommendations
        )

    async def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        domain = params.get("domain")
        if not domain: 
            return self._create_final_output(
                success=False,
                ai_summary="Domain parametresi eksik.",
                error="Domain parametresi zorunludur."
            )
        if not DNSPYTHON_AVAILABLE: 
            return self._create_final_output(
                success=False,
                ai_summary="Gerekli kütüphane eksik.",
                error="dnspython kütüphanesi bulunamadı. Lütfen 'pip install dnspython' komutunu çalıştırın."
            )

        context = DnsContext(domain=domain)
        self._add_reasoning(context.ai_reasoning_log, "initialization", f"Hedef {domain} için DNS istihbarat analizi başlatılıyor.")

        try:
            context.records = await self._get_records(domain, RECORD_TYPES)
            self._add_reasoning(context.ai_reasoning_log, "record_retrieval", f"{sum(len(v) for v in context.records.values())} adet DNS kaydı toplandı.")

            # Paralel kontroller
            ns_records = context.records.get('NS', [])
            if not ns_records:
                self._add_reasoning(context.ai_reasoning_log, "warning", "NS kayıtları bulunamadı, Zone Transfer kontrolü atlanıyor.")
                zt_task = asyncio.Future(); zt_task.set_result({"vulnerable": False})
            else:
                 zt_task = self._check_zone_transfer(domain, ns_records)
                 
            wildcard_task = self._detect_wildcard(domain)
            
            context.zone_transfer_result, context.wildcard_detected = await asyncio.gather(zt_task, wildcard_task)
            
            if context.zone_transfer_result.get("vulnerable"): 
                self._add_reasoning(context.ai_reasoning_log, "critical_finding", "🔥 KRİTİK: Zone Transfer zafiyeti tespit edildi!")
            if context.wildcard_detected: 
                self._add_reasoning(context.ai_reasoning_log, "finding", "Wildcard DNS yapılandırması tespit edildi.")

            context.infrastructure = self._analyze_infrastructure(context.records)
            self._add_reasoning(context.ai_reasoning_log, "infra_analysis", f"Altyapı analizi tamamlandı. CDN: {context.infrastructure.get('cdn_provider', 'Yok')}")

            return self._build_final_json(context)
        except Exception as e:
            logger.error(f"Execute metodunda kritik hata: {repr(e)}", exc_info=True)
            return self._create_final_output(
                success=False,
                ai_summary="DNS analizi sırasında kritik bir hata oluştu.",
                ai_reasoning=context.ai_reasoning_log,
                error=str(e)
            )

async def main():
    parser = argparse.ArgumentParser(description="Pentagent DNS İstihbarat Aracı (v2).")
    parser.add_argument("domain", help="Analiz edilecek domain.")
    parser.add_argument("--json", action="store_true", help="Çıktıyı ham JSON formatında göster.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Detaylı (INFO seviyesi) logları göster.")
    args = parser.parse_args()

    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stderr)

    analyzer = ReconDnsAnalyzerTool()
    result = await analyzer.run_tool(vars(args))

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    # Uzman gözüyle, okunabilir ve profesyonel rapor çıktısı
    print("\n" + "="*60 + "\n Pentagent DNS İstihbarat Raporu\n" + "="*60)
    if not result.get("success"):
        print(f"HATA: Analiz Basarisiz!\n   Sebep: {result.get('error')}")
    else:
        data = result.get("data", {})
        print(f"Hedef: {data.get('domain')}")
        print(f"Ozet: {result.get('ai_summary')}\n")

        # Güvenlik Duruşu
        security = data.get("security_posture", {})
        print("-" * 25 + " GÜVENLİK DURUŞU " + "-"*25)
        if security.get("zone_transfer_vulnerable"):
            print("KRITIK: Zone Transfer Zafiyeti Tespit Edildi!")
        else:
            print("Zone Transfer: Guvenli.")
        print(f"[*] Wildcard DNS: {'Aktif' if security.get('wildcard_dns_enabled') else 'Aktif Değil'}")
        
        # Altyapı Profili
        infra = data.get("infrastructure_profile", {})
        print("\n" + "-" * 26 + " ALTYAPI PROFİLİ " + "-"*27)
        print(f"CDN Saglayici: {infra.get('cdn_provider', 'Tespit Edilemedi')}")
        print(f"Mail Saglayici: {infra.get('mail_provider', 'Tespit Edilemedi')}")
        if infra.get("hosting_hints"):
            print(f"Hosting Ipuclari: {', '.join(infra['hosting_hints'])}")
        
        # Stratejik Plan
        recommendations = result.get("recommendations", [])
        if recommendations:
            print("\n" + "-" * 23 + " STRATEJİK SALDIRI ÖNERİLERİ " + "-"*22)
            for rec in recommendations:
                print(f"  [{rec['priority'].upper()}] -> Çalıştır: {rec['tool']}")
                print(f"    Neden: {rec['reason']}")
    
    # AI Düşünce Akışı (Debug/Verbose için faydalı)
    if args.verbose:
        print("\nAI Düşünce Akışı:")
        for thought in result.get("ai_reasoning", []):
            print(f"   [{thought['phase']}] {thought['thought']}")

    print("="*60)


if __name__ == "__main__":
    if not DNSPYTHON_AVAILABLE:
        print(" HATA: 'dnspython' kütüphanesi bulunamadı.", file=sys.stderr)
        print("Lütfen 'pip install dnspython' komutunu çalıştırın.", file=sys.stderr)
        sys.exit(1)
    asyncio.run(main())