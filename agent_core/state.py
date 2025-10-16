# agent_core/state.py

from typing import Dict, Any, List
from datetime import datetime

class AgentState:
    """Tüm pentest sürecinin durumunu ve hafızasını yöneten merkezi yapı."""
    
    def __init__(self, target: str, user_task: str):
        self.target = target
        self.user_task = user_task
        self.plan: List[Dict[str, Any]] = []
        self.completed_steps: List[Dict[str, Any]] = []
        self.context_summary: Dict[str, Any] = {
            "target_info": {"type": "unknown", "ip": None, "domain": target},
            "open_ports": [],
            "technologies": [],
            "vulnerabilities": [],
            "attack_vectors": [],
            "services": [],
            "subdomains": [],
            "certificates": [],
            "headers": [],
            "waf_detected": False,
            "os_info": {},
            "network_info": {}
        }
        self.start_time = datetime.now()
        self.current_step = 0
        self.total_steps = 0
        self.success_rate = 0.0
        self.execution_time = 0.0
        
        # YENİ: Raporlama için yapılandırılmış bulgular listesi
        self.findings: List[Dict[str, Any]] = []
        
        # Tool sonuçları için
        self.tool_results: List[Dict[str, Any]] = []
        
        # Keşfedilen bilgiler (dynamic orchestrator ile uyumlu)
        self.discovered_information: Dict[str, Any] = {}

    def add_completed_step(self, step_result: Dict[str, Any]):
        """Tamamlanan bir adımı geçmişe ekler."""
        step_result["timestamp"] = datetime.now().isoformat()
        step_result["step_number"] = len(self.completed_steps) + 1
        self.completed_steps.append(step_result)
        self.current_step = len(self.completed_steps)
        
        # Başarı oranını güncelle
        successful_steps = sum(1 for step in self.completed_steps 
                              if step.get("result", {}).get("success", False))
        self.success_rate = successful_steps / len(self.completed_steps) if self.completed_steps else 0.0

    def update_context(self, finding_type: str, data: Any):
        """Ajanın hafızasını yeni bulgularla günceller."""
        current_data = self.context_summary.get(finding_type)
        
        if isinstance(current_data, list):
            new_items = data if isinstance(data, list) else [data]
            for item in new_items:
                if item not in current_data:
                    current_data.append(item)
        else:
            self.context_summary[finding_type] = data
        
        print(f"🧠 Ajan Hafızası Güncellendi -> {finding_type}: {str(data)[:100]}...")

    def add_finding(self, finding_data: Dict[str, Any]):
        """
        Raporlama için yapılandırılmış bir bulguyu kaydeder.
        Bu, Analyzer tarafından doldurulacak.
        """
        # Aynı bulgunun tekrar eklenmesini önle
        # Basit bir kontrol - title ve affected_component kombinasyonunu kontrol et
        duplicate_check = False
        for existing_finding in self.findings:
            if (existing_finding.get('title') == finding_data.get('title') and
                existing_finding.get('affected_component') == finding_data.get('affected_component')):
                duplicate_check = True
                break
        
        if not duplicate_check:
            # Finding'e timestamp ekle
            finding_data['timestamp'] = datetime.now().isoformat()
            self.findings.append(finding_data)
            print(f"📄 Yeni Bulgu Rapor İçin Kaydedildi: {finding_data.get('title')}")

    def get_context_summary(self) -> Dict[str, Any]:
        """Ajanın mevcut durumunu özetler."""
        return {
            "target": self.target,
            "task": self.user_task,
            "progress": {
                "current_step": self.current_step,
                "total_steps": self.total_steps,
                "success_rate": self.success_rate,
                "elapsed_time": str(datetime.now() - self.start_time)
            },
            "findings": self.context_summary,
            "structured_findings": self.findings,  # YENİ: Rapor için yapılandırılmış bulgular
            "completed_steps": len(self.completed_steps),
            "remaining_steps": len([s for s in self.plan if s.get('status') == 'pending'])
        }

    def add_attack_vector(self, vector: Dict[str, Any]):
        """Yeni bir saldırı vektörü ekler."""
        if "attack_vectors" not in self.context_summary:
            self.context_summary["attack_vectors"] = []
        
        # Duplicate kontrolü
        if vector not in self.context_summary["attack_vectors"]:
            self.context_summary["attack_vectors"].append(vector)
            print(f"🎯 Yeni Saldırı Vektörü Eklendi: {vector.get('type', 'unknown')}")

    def get_vulnerability_summary(self) -> Dict[str, Any]:
        """Tespit edilen zafiyetleri kategorize eder."""
        vulnerabilities = self.context_summary.get("vulnerabilities", [])
        
        summary = {
            "total": len(vulnerabilities),
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,  # YENİ: Bilgilendirme seviyesi
            "by_type": {}
        }
        
        for vuln in vulnerabilities:
            severity = vuln.get("severity", "unknown").lower()
            vuln_type = vuln.get("type", "unknown")
            
            if severity in summary:
                summary[severity] += 1
            
            if vuln_type not in summary["by_type"]:
                summary["by_type"][vuln_type] = 0
            summary["by_type"][vuln_type] += 1
        
        return summary

    def get_findings_summary(self) -> Dict[str, Any]:
        """
        YENİ: Rapor için yapılandırılmış bulguların özetini döndürür.
        """
        summary = {
            "total": len(self.findings),
            "by_severity": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0
            },
            "with_cve": 0,
            "findings": self.findings
        }
        
        for finding in self.findings:
            severity = finding.get("severity", "").lower()
            if severity in ["kritik", "critical"]:
                summary["by_severity"]["critical"] += 1
            elif severity in ["yüksek", "high"]:
                summary["by_severity"]["high"] += 1
            elif severity in ["orta", "medium"]:
                summary["by_severity"]["medium"] += 1
            elif severity in ["düşük", "low"]:
                summary["by_severity"]["low"] += 1
            elif severity in ["bilgilendirme", "info", "information"]:
                summary["by_severity"]["info"] += 1
            
            if finding.get("cve_id"):
                summary["with_cve"] += 1
        
        return summary

    def to_dict(self) -> Dict[str, Any]:
        """AgentState'i JSON serializable dictionary'e çevirir"""
        return {
            "target": self.target,
            "user_task": self.user_task,
            "plan": self.plan,
            "completed_steps": self.completed_steps,
            "context_summary": self.context_summary,
            "start_time": self.start_time.isoformat(),
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "success_rate": self.success_rate,
            "execution_time": self.execution_time,
            "findings": self.findings,
            "tool_results": self.tool_results
        }