#!/usr/bin/env python3
"""
Subdomain Bruteforce Tool - Subdomain'leri bruteforce ile bulma
Gerçek penetrasyon test uzmanları için kritik araç
"""

import asyncio
import aiohttp
import re
import json
import logging
from typing import Dict, Any, Set, List, Optional
from datetime import datetime
from tools.base_mcp_tool import MCPTool, ToolCategory

logger = logging.getLogger(__name__)

class SubdomainBruteforceModule(MCPTool):
    """Subdomain bruteforce modülü"""
    
    def __init__(self):
        super().__init__(
            name="enum_subdomain_bruteforcer",
            description="Subdomain'leri bruteforce teknikleri ile bulur. Yaygın kelimeler, sayılar ve kombinasyonlar kullanır.",
            category=ToolCategory.RECONNAISSANCE
        )
        self.version = "1.0.0-MCP"
        self.reasoning_log = []
    
    async def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """MCP ajanı tarafından çağrılacak ana fonksiyon."""
        try:
            # Hem 'domain' hem de 'target' parametresini kabul et
            domain = params.get("domain") or params.get("target")
            if not domain:
                raise ValueError("Gerekli 'domain' veya 'target' parametresi eksik.")
            
            # URL'den domain çıkar
            if domain.startswith("http"):
                from urllib.parse import urlparse
                domain = urlparse(domain).netloc
            
            scan_type = params.get("scan_type", "comprehensive")
            timeout = params.get("timeout", 60)
            threads = params.get("threads", 20)
            
            self._add_reasoning(self.reasoning_log, "initialization", f"Subdomain bruteforce '{domain}' için başlatılıyor.")
            
            # Ana tarama mantığını çalıştır
            scan_result = await self._bruteforce_subdomains(domain, scan_type, timeout, threads)
            
            self._add_reasoning(self.reasoning_log, "analysis_complete", "Subdomain bruteforce tamamlandı.")
            
            return self._create_final_output(
                success=True,
                data=scan_result,
                ai_summary=self._generate_ai_summary(scan_result),
                recommendations=self._generate_mcp_recommendations(scan_result)
            )
            
        except Exception as e:
            logger.error(f"Subdomain bruteforce'da hata: {e}", exc_info=True)
            self._add_reasoning(self.reasoning_log, "error", f"Araç çalıştırılırken kritik bir hata oluştu: {e}")
            return self._create_final_output(
                success=False,
                data={},
                ai_summary=f"Araç çalıştırılırken kritik bir hata oluştu: {e}",
                recommendations=[],
                error=str(e)
            )
    
    async def _bruteforce_subdomains(self, domain: str, scan_type: str, timeout: int, threads: int) -> Dict[str, Any]:
        """Ana subdomain bruteforce fonksiyonu."""
        found_subdomains = set()
        techniques_used = []
        
        # Wordlist oluştur
        wordlist = self._generate_wordlist(domain, scan_type)
        
        self._add_reasoning(self.reasoning_log, "wordlist_generation", f"{len(wordlist)} kelime ile wordlist oluşturuldu.")
        
        # Bruteforce işlemini başlat
        async with aiohttp.ClientSession() as session:
            # Paralel bruteforce
            semaphore = asyncio.Semaphore(threads)
            tasks = []
            
            for subdomain in wordlist:
                task = self._check_subdomain(session, subdomain, domain, semaphore, timeout)
                tasks.append(task)
            
            # Tüm görevleri çalıştır
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Sonuçları topla
            for result in results:
                if isinstance(result, dict) and result.get("found"):
                    found_subdomains.add(result["subdomain"])
                    techniques_used.append("DNS Bruteforce")
        
        # Subdomain'leri analiz et
        analyzed_subdomains = self._analyze_subdomains(found_subdomains, domain)
        
        return {
            "subdomains": analyzed_subdomains,
            "total_found": len(analyzed_subdomains),
            "wordlist_size": len(wordlist),
            "techniques_used": list(set(techniques_used)),
            "ai_reasoning": self.reasoning_log
        }

    def _generate_wordlist(self, domain: str, scan_type: str) -> List[str]:
        """Domain'e özel wordlist oluştur"""
        base_words = [
            # Yaygın subdomain'ler
            "www", "mail", "ftp", "admin", "api", "dev", "test", "staging", "prod", "production",
            "blog", "shop", "store", "app", "mobile", "cdn", "static", "assets", "img", "images",
            "js", "css", "fonts", "downloads", "files", "docs", "help", "support", "status",
            "monitor", "stats", "analytics", "tracking", "metrics", "logs", "backup", "backups",
            "db", "database", "mysql", "postgres", "redis", "cache", "memcache", "elastic",
            "search", "solr", "lucene", "kibana", "grafana", "prometheus", "alertmanager",
            "jenkins", "ci", "cd", "git", "gitlab", "github", "bitbucket", "svn", "hg",
            "docker", "k8s", "kubernetes", "helm", "terraform", "ansible", "puppet", "chef",
            "nagios", "zabbix", "cacti", "munin", "collectd", "telegraf", "influxdb",
            "rabbitmq", "kafka", "zookeeper", "consul", "etcd", "vault", "nomad",
            "nginx", "apache", "tomcat", "jetty", "glassfish", "wildfly", "jboss",
            "php", "python", "ruby", "node", "java", "go", "rust", "scala", "clojure",
            "wordpress", "drupal", "joomla", "magento", "prestashop", "opencart",
            "laravel", "symfony", "codeigniter", "cakephp", "yii", "zend", "phalcon",
            "django", "flask", "fastapi", "tornado", "bottle", "cherrypy", "pyramid",
            "rails", "sinatra", "hanami", "grape", "padrino", "cuba", "roda",
            "express", "koa", "hapi", "sails", "meteor", "next", "nuxt", "gatsby",
            "spring", "struts", "hibernate", "mybatis", "jpa", "jdbc", "jsp", "servlet",
            "react", "vue", "angular", "ember", "backbone", "knockout", "jquery",
            "bootstrap", "foundation", "bulma", "tailwind", "materialize", "semantic",
            "aws", "azure", "gcp", "digitalocean", "linode", "vultr", "heroku", "netlify",
            "cloudflare", "maxcdn", "keycdn", "bunnycdn", "fastly", "incapsula", "sucuri",
            "mailgun", "sendgrid", "mandrill", "postmark", "sparkpost", "ses", "sns",
            "stripe", "paypal", "square", "braintree", "authorize", "adyen", "klarna",
            "google", "facebook", "twitter", "linkedin", "instagram", "youtube", "tiktok",
            "slack", "discord", "teams", "zoom", "skype", "whatsapp", "telegram",
            "salesforce", "hubspot", "pipedrive", "zendesk", "freshdesk", "intercom",
            "mixpanel", "amplitude", "segment", "hotjar", "fullstory", "logrocket",
            "sentry", "bugsnag", "rollbar", "airbrake", "honeybadger", "raygun",
            "datadog", "newrelic", "appdynamics", "dynatrace", "splunk", "sumo",
            "elasticsearch", "logstash", "kibana", "beats", "filebeat", "metricbeat",
            "prometheus", "grafana", "alertmanager", "thanos", "cortex", "victoriametrics",
            "consul", "etcd", "zookeeper", "eureka", "nacos", "apollo", "discovery",
            "kong", "nginx", "haproxy", "traefik", "envoy", "istio", "linkerd",
            "redis", "memcached", "hazelcast", "ignite", "caffeine", "guava",
            "rabbitmq", "kafka", "pulsar", "nats", "zeromq", "activemq", "artemis",
            "postgresql", "mysql", "mariadb", "oracle", "sqlserver", "sqlite", "h2",
            "mongodb", "cassandra", "dynamodb", "couchdb", "riak", "neo4j", "arango",
            "influxdb", "timescaledb", "clickhouse", "bigquery", "redshift", "snowflake",
            "hadoop", "spark", "hive", "pig", "hbase", "kafka", "storm", "flink",
            "tensorflow", "pytorch", "keras", "scikit", "pandas", "numpy", "matplotlib",
            "jupyter", "zeppelin", "databricks", "sagemaker", "mlflow", "kubeflow",
            "jenkins", "gitlab", "github", "bitbucket", "azure", "circleci", "travis",
            "docker", "kubernetes", "helm", "terraform", "ansible", "puppet", "chef",
            "vagrant", "packer", "consul", "vault", "nomad", "serf", "raft",
            "prometheus", "grafana", "alertmanager", "thanos", "cortex", "victoriametrics",
            "jaeger", "zipkin", "opentelemetry", "honeycomb", "lightstep", "datadog",
            "newrelic", "appdynamics", "dynatrace", "splunk", "sumo", "loggly",
            "papertrail", "logentries", "logdna", "humio", "elastic", "kibana",
            "fluentd", "fluentbit", "logstash", "beats", "filebeat", "metricbeat",
            "packetbeat", "heartbeat", "auditbeat", "functionbeat", "journalbeat",
            "winlogbeat", "osquerybeat", "cloudbeat", "agentbeat", "communitybeat"
        ]
        
        # Domain'e özel kelimeler ekle
        domain_words = domain.split('.')[0]
        if len(domain_words) > 3:
            base_words.extend([
                domain_words,
                domain_words + "api",
                domain_words + "app",
                domain_words + "dev",
                domain_words + "test",
                domain_words + "staging",
                domain_words + "prod"
            ])
        
        # Sayılar ekle
        numbers = [str(i) for i in range(0, 100)]
        
        # Kombinasyonlar oluştur
        wordlist = set(base_words)
        
        if scan_type == "comprehensive":
            # Daha kapsamlı wordlist
            wordlist.update(numbers)
            wordlist.update([f"{word}{num}" for word in base_words[:50] for num in numbers[:10]])
            wordlist.update([f"{num}{word}" for word in base_words[:50] for num in numbers[:10]])
        
        return list(wordlist)[:1000]  # Maksimum 1000 kelime

    async def _check_subdomain(self, session: aiohttp.ClientSession, subdomain: str, domain: str, semaphore: asyncio.Semaphore, timeout: int) -> Dict[str, Any]:
        """Tek bir subdomain'i kontrol et"""
        async with semaphore:
            full_domain = f"{subdomain}.{domain}"
            try:
                # DNS A kaydı kontrol et
                import dns.resolver
                a_records = dns.resolver.resolve(full_domain, 'A')
                if a_records:
                    return {
                        "found": True,
                        "subdomain": full_domain,
                        "ip": str(a_records[0]),
                        "method": "DNS_A"
                    }
            except:
                pass
            
            try:
                # DNS CNAME kaydı kontrol et
                cname_records = dns.resolver.resolve(full_domain, 'CNAME')
                if cname_records:
                    return {
                        "found": True,
                        "subdomain": full_domain,
                        "cname": str(cname_records[0]),
                        "method": "DNS_CNAME"
                    }
            except:
                pass
            
            return {"found": False, "subdomain": full_domain}

    def _analyze_subdomains(self, subdomains: Set[str], domain: str) -> List[Dict[str, Any]]:
        """Subdomain'leri analiz et ve risk seviyesi belirle"""
        analyzed_subdomains = []
        for subdomain in subdomains:
            risk_level = self._determine_risk_level(subdomain, domain)
            analyzed_subdomains.append({
                "subdomain": subdomain,
                "risk_level": risk_level,
                "confidence": "high",
                "method": "bruteforce"
            })
        return analyzed_subdomains

    def _determine_risk_level(self, subdomain: str, domain: str) -> str:
        """Subdomain'in risk seviyesini belirle"""
        high_risk_keywords = ["admin", "api", "dev", "test", "staging", "backup", "db", "database", "mail", "ftp"]
        medium_risk_keywords = ["www", "blog", "shop", "store", "app", "mobile", "cdn", "static"]
        
        subdomain_lower = subdomain.lower()
        
        for keyword in high_risk_keywords:
            if keyword in subdomain_lower:
                return "high"
        
        for keyword in medium_risk_keywords:
            if keyword in subdomain_lower:
                return "medium"
        
        return "low"

    def _generate_ai_summary(self, scan_result: Dict[str, Any]) -> str:
        """İnsan tarafından okunabilir bir özet oluşturur."""
        subdomains = scan_result.get('subdomains', [])
        if not subdomains:
            return "Hiçbir subdomain bruteforce ile tespit edilemedi."
        
        high_risk_count = len([s for s in subdomains if s.get('risk_level') == 'high'])
        medium_risk_count = len([s for s in subdomains if s.get('risk_level') == 'medium'])
        wordlist_size = scan_result.get('wordlist_size', 0)
        
        summary = f"{len(subdomains)} subdomain bruteforce ile tespit edildi. "
        summary += f"{high_risk_count} tanesi yüksek risk, {medium_risk_count} tanesi orta risk seviyesinde. "
        summary += f"{wordlist_size} kelime ile tarama yapıldı."
        
        return summary

    def _generate_mcp_recommendations(self, scan_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """MCP formatında öneriler oluşturur."""
        recommendations = []
        
        subdomains = scan_result.get('subdomains', [])
        if subdomains:
            recommendations.append({
                "title": "Subdomain Port Taraması",
                "description": f"Tespit edilen {len(subdomains)} subdomain üzerinde port taraması yapın",
                "priority": "high"
            })
            
            high_risk = [s for s in subdomains if s.get('risk_level') == 'high']
            if high_risk:
                recommendations.append({
                    "title": "Yüksek Riskli Subdomain'ler",
                    "description": f"{len(high_risk)} yüksek riskli subdomain'i öncelikle test edin",
                    "priority": "critical"
                })
            
            recommendations.append({
                "title": "Web Uygulama Testi",
                "description": "Tespit edilen subdomain'lerde web uygulama güvenlik testleri yapın",
                "priority": "high"
            })
            
            recommendations.append({
                "title": "Teknoloji Tespiti",
                "description": "Her subdomain için teknoloji tespiti yapın",
                "priority": "medium"
            })
        else:
            recommendations.append({
                "title": "Alternatif Teknikler",
                "description": "Pasif subdomain enumeration tekniklerini deneyin",
                "priority": "medium"
            })
        
        return recommendations

# MCP Tool instance
enum_subdomain_bruteforcer = SubdomainBruteforceModule()
