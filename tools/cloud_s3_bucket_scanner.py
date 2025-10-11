#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pentagent - Cloud S3 Bucket Scanner
Görev: Hedef domaine ilişkili AWS S3 bucket'larını keşfeder,
erişim izinlerini analiz eder ve halka açık hassas verileri tespit eder.
Bu araç, MCP ajanına bulut tabanlı saldırı vektörleri için kanıtlar sunar.
"""

import boto3
import requests
import json
import logging
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from botocore.exceptions import ClientError
from botocore.config import Config
import datetime

# PentagentTool base class'ını import et
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.base_mcp_tool import MCPTool, ToolCategory, PriorityLevel

# Logging yapılandırması
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SensitiveFileFinding:
    """Bir bucket içinde bulunan hassas bir dosyayı temsil eder."""
    key: str
    size_bytes: int
    last_modified: str
    matched_pattern: str

@dataclass
class BucketFinding:
    """Tek bir S3 bucket'ı için toplanan teknik bulguları temsil eder."""
    bucket_name: str
    bucket_url: str
    region: Optional[str]
    exists: bool = False
    is_public: bool = False
    allows_listing: bool = False
    allows_upload: bool = False
    sensitive_files: Optional[List[SensitiveFileFinding]] = None

class CloudS3Scanner(MCPTool):
    """
    AWS S3 bucket'larını keşfeden ve analiz eden, MCP ile entegre profesyonel araç.
    """

    def __init__(self):
        super().__init__(
            name="cloud_s3_bucket_scanner",
            description="Hedef domaine ilişkili AWS S3 bucket'larını keşfeder ve erişim izinlerini analiz eder.",
            category=ToolCategory.CLOUD_SECURITY
        )
        
        self.regions = [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'eu-west-1', 
            'eu-west-2', 'eu-central-1', 'ap-southeast-1', 'ap-southeast-2', 
            'ap-northeast-1', 'sa-east-1'
        ]
        
        self.sensitive_patterns = {
            # Kritik Öncelikli (Credentials, Keys)
            "critical_credentials": [r'\.pem$', r'\.key$', r'id_rsa$', r'\.p12$', r'\.pfx$'],
            "critical_configs": [r'\.env$', r'credentials', r'\.htpasswd$', r'wp-config\.php$'],
            # Yüksek Öncelikli (Kod, Veritabanı)
            "high_backups": [r'\.sql(\.gz)?$', r'\.dump$', r'\.bak$', r'backup.*\.(zip|tar\.gz|tgz|7z)$'],
            "high_source_code": [r'\.git/config$'],
            # Orta Öncelikli (Hassas Dokümanlar)
            "medium_documents": [r'password.*\.(txt|csv|json)$', r'secret.*\.(txt|csv|json)$'],
            "medium_logs": [r'\.log$', r'\.bash_history$', r'\.zsh_history$']
        }
        
        self.s3_config = Config(signature_version='UNSIGNED', retries={'max_attempts': 2})

    def _generate_permutations(self, domain: str) -> List[str]:
        """Verilen domain için potansiyel S3 bucket isimleri oluşturur."""
        domain_parts = domain.split('.')
        company_name = domain_parts[-2] if len(domain_parts) > 1 else domain_parts[0]

        keywords = [
            'assets', 'backup', 'backups', 'cdn', 'config', 'data', 'db', 
            'dev', 'prod', 'public', 's3', 'stage', 'static', 'test', 'uploads', 'www'
        ]
        
        patterns = [
            f"{company_name}",
            f"{company_name}-prod",
            f"{company_name}-dev",
            f"assets-{company_name}",
            f"{domain}",
            f"{domain.replace('.', '-')}",
        ]
        
        for keyword in keywords:
            patterns.append(f"{company_name}-{keyword}")
            patterns.append(f"{keyword}-{company_name}")
            patterns.append(f"{company_name}.{keyword}")

        return list(set(p.lower() for p in patterns))

    def _get_bucket_region(self, bucket_name: str) -> Optional[str]:
        """Bir bucket'ın bölgesini HTTP başlıklarından veya API çağrısıyla tespit eder."""
        try:
            response = requests.head(f"https://{bucket_name}.s3.amazonaws.com", timeout=5, allow_redirects=False)
            if 'x-amz-bucket-region' in response.headers:
                return response.headers['x-amz-bucket-region']
            # Yönlendirme durumunda bölgeyi URL'den al
            if response.status_code in [301, 307] and 'Location' in response.headers:
                match = re.search(r's3\.([a-z0-9-]+)\.amazonaws\.com', response.headers['Location'])
                if match:
                    return match.group(1)
        except requests.RequestException:
            pass

        # Alternatif olarak tüm bölgeleri dene
        for region in self.regions:
            try:
                response = requests.head(f"https://{bucket_name}.s3.{region}.amazonaws.com", timeout=3)
                if response.status_code < 400:
                    return region
            except requests.RequestException:
                continue
        return None

    def _check_bucket(self, bucket_name: str, ai_reasoning_log: List[Dict]) -> Optional[BucketFinding]:
        """Tek bir S3 bucket'ının varlığını ve erişim izinlerini kontrol eder."""
        try:
            region = self._get_bucket_region(bucket_name)
            if not region:
                return None
            
            ai_reasoning_log.append({"phase": "discovery", "thought": f"Potansiyel bucket '{bucket_name}' için bölge tespiti yapıldı: {region}."})
            
            s3_client = boto3.client('s3', region_name=region, config=self.s3_config)
            bucket_url = f"https://{bucket_name}.s3.amazonaws.com"
            finding = BucketFinding(bucket_name=bucket_name, bucket_url=bucket_url, region=region, exists=True)

            # 1. Listeleyebilme (Public Read) Kontrolü
            try:
                s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
                finding.is_public = True
                finding.allows_listing = True
                ai_reasoning_log.append({"phase": "critical_finding", "thought": f"⚠️ '{bucket_name}' bucket'ı halka açık olarak listelenebiliyor!"})
            except ClientError as e:
                if e.response['Error']['Code'] not in ['AccessDenied', 'NoSuchBucket']:
                    logger.debug(f"'{bucket_name}' listeleme hatası: {e}")

            # 2. Yükleme Yapabilme (Public Write) Kontrolü
            try:
                acl = s3_client.get_bucket_acl(Bucket=bucket_name)
                for grant in acl.get('Grants', []):
                    grantee = grant.get('Grantee', {})
                    uri = grantee.get('URI', '')
                    if ('AllUsers' in uri or 'AuthenticatedUsers' in uri) and grant['Permission'] in ['WRITE', 'FULL_CONTROL']:
                        finding.is_public = True
                        finding.allows_upload = True
                        ai_reasoning_log.append({"phase": "critical_finding", "thought": f"⚠️ '{bucket_name}' bucket'ına halka açık yazma izni ({grant['Permission']}) tespit edildi!"})
                        break
            except ClientError:
                pass 

            # 3. Eğer listelenebiliyorsa, hassas dosyaları ara
            if finding.allows_listing:
                finding.sensitive_files = self._find_sensitive_files_in_bucket(s3_client, bucket_name, ai_reasoning_log)

            if finding.is_public:
                return finding
            
            return None # Halka açık değilse raporlamaya gerek yok

        except Exception as e:
            logger.error(f"'{bucket_name}' taranırken beklenmedik hata: {e}")
            return None

    def _find_sensitive_files_in_bucket(self, s3_client: Any, bucket_name: str, ai_reasoning_log: List[Dict], max_files: int = 200) -> List[SensitiveFileFinding]:
        """Halka açık bir bucket içinde hassas dosya desenlerini arar."""
        sensitive_files_found = []
        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=bucket_name)
            
            files_scanned = 0
            for page in page_iterator:
                if 'Contents' not in page:
                    continue
                for obj in page['Contents']:
                    if files_scanned >= max_files:
                        ai_reasoning_log.append({"phase": "analysis", "thought": f"'{bucket_name}' içinde dosya tarama limiti ({max_files}) aşıldı."})
                        return sensitive_files_found

                    key = obj.get('Key', '')
                    for category, patterns in self.sensitive_patterns.items():
                        for pattern in patterns:
                            if re.search(pattern, key, re.IGNORECASE):
                                finding = SensitiveFileFinding(
                                    key=key,
                                    size_bytes=obj.get('Size', 0),
                                    last_modified=obj.get('LastModified', datetime.datetime.now()).isoformat(),
                                    matched_pattern=f"{category}:{pattern}"
                                )
                                sensitive_files_found.append(finding)
                                ai_reasoning_log.append({"phase": "sensitive_data", "thought": f"🚨 Hassas dosya bulundu: '{key}' (Desen: {pattern})"})
                                break 
                    files_scanned += 1
        except ClientError as e:
            ai_reasoning_log.append({"phase": "error", "thought": f"'{bucket_name}' içeriği okunurken hata: {e.response['Error']['Code']}"})
        
        return sensitive_files_found

    def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aracın ana giriş noktası. Verilen domaine göre S3 taraması yapar
        ve sonucu standart MCP JSON formatında döndürür.
        """
        target_domain = params.get("domain")
        threads = params.get("threads", 20)
        
        if not target_domain:
            return self._create_final_output(
                success=False,
                ai_summary="Hedef domain parametresi eksik.",
                error="Hedef 'domain' parametresi eksik."
            )

        ai_reasoning_log = []
        self._add_reasoning(ai_reasoning_log, "initialization", f"cloud_s3_scanner aracı '{target_domain}' hedefi için başlatıldı.")
        self._add_reasoning(ai_reasoning_log, "preparation", f"{threads} iş parçacığı ile çalışılacak.")
        
        error_message = None
        findings: List[BucketFinding] = []
        
        try:
            permutations = self._generate_permutations(target_domain)
            self._add_reasoning(ai_reasoning_log, "preparation", f"Hedef domain için {len(permutations)} adet potansiyel bucket ismi oluşturuldu.")

            with ThreadPoolExecutor(max_workers=threads) as executor:
                future_to_bucket = {executor.submit(self._check_bucket, p, ai_reasoning_log): p for p in permutations}
                for future in as_completed(future_to_bucket):
                    try:
                        result = future.result()
                        if result:
                            findings.append(result)
                    except Exception as exc:
                        bucket_name = future_to_bucket[future]
                        logger.warning(f"'{bucket_name}' taranırken bir hata oluştu: {exc}")

            self._add_reasoning(ai_reasoning_log, "analysis_complete", f"Tarama tamamlandı. {len(findings)} adet halka açık bucket bulundu.")
            
            return self._create_mcp_output(
                target_domain=target_domain,
                findings=findings,
                ai_reasoning_log=ai_reasoning_log
            )

        except Exception as e:
            logger.critical(f"S3 tarama aracında kritik hata: {e}", exc_info=True)
            error_message = f"Beklenmedik bir hata oluştu: {str(e)}"
            return self._create_final_output(
                success=False,
                ai_summary="S3 bucket taraması bir hata nedeniyle başarısız oldu.",
                ai_reasoning=ai_reasoning_log,
                error=error_message
            )

    def _create_mcp_output(self, 
                           target_domain: str = None, 
                           findings: List[BucketFinding] = None,
                           ai_reasoning_log: List[Dict] = None,
                           success: bool = True,
                           error: str = None) -> Dict[str, Any]:
        """
        Toplanan verileri, projemizin standart JSON formatına dönüştürür.
        """
        if findings is None: findings = []
        if ai_reasoning_log is None: ai_reasoning_log = []
        
        if not success:
            ai_summary = "S3 bucket taraması bir hata nedeniyle başarısız oldu."
        elif not findings:
            ai_summary = f"'{target_domain}' için yapılan taramada halka açık herhangi bir S3 bucket'ı bulunamadı."
        else:
            total_findings = len(findings)
            sensitive_count = sum(1 for f in findings if f.sensitive_files)
            writable_count = sum(1 for f in findings if f.allows_upload)
            summary_parts = [f"'{target_domain}' için {total_findings} adet halka açık S3 bucket'ı tespit ettim."]
            if sensitive_count > 0:
                summary_parts.append(f"{sensitive_count} tanesinde potansiyel hassas veri bulundu.")
            if writable_count > 0:
                summary_parts.append(f"{writable_count} tanesi halka açık yazma iznine sahip.")
            ai_summary = " ".join(summary_parts)

        recommendations = []
        for finding in findings:
            if finding.sensitive_files:
                recommendations.append(
                    self._create_recommendation(
                        priority=PriorityLevel.HIGH,
                        tool_name="cloud_data_downloader",
                        reason=f"'{finding.bucket_name}' bucket'ında potansiyel hassas dosyalar tespit edildi. İçerik analizi için indirilmesi önerilir.",
                        params={"bucket_name": finding.bucket_name, "region": finding.region}
                    )
                )
            if finding.allows_upload:
                 recommendations.append(
                    self._create_recommendation(
                        priority=PriorityLevel.CRITICAL,
                        tool_name="poc_file_uploader",
                        reason=f"'{finding.bucket_name}' bucket'ı halka açık yazma iznine sahip. Bu durum, zararlı yazılım barındırma veya web sitesi tahrifatı için kullanılabilir. PoC ile kanıtlanmalı.",
                        params={"bucket_name": finding.bucket_name, "region": finding.region}
                    )
                )
        
        return self._create_final_output(
            success=success,
            data={
                "target_domain": target_domain,
                "findings": [asdict(f) for f in findings]
            },
            ai_summary=ai_summary,
            ai_reasoning=ai_reasoning_log,
            recommendations=recommendations,
            error=error
        )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Cloud S3 Bucket Scanner")
    parser.add_argument("domain", help="Target domain to scan")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    scanner = CloudS3Scanner()
    result = scanner.run_tool({"domain": args.domain})
    
    print(json.dumps(result, indent=4, ensure_ascii=True))
