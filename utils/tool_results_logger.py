#!/usr/bin/env python3
"""
Tool Results Logger - Araç sonuçlarını JSON olarak kaydetme ve gösterme
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class ToolResultsLogger:
    """Araç sonuçlarını JSON formatında kaydetme ve yönetme"""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = f"session_{self.session_id}.json"
        self.results_dir = "pentest_results"
        
        # Results dizinini oluştur
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
        
        self.session_data = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "target": None,
            "user_task": None,
            "tool_results": [],
            "ai_decisions": [],
            "discovered_information": {},
            "final_analysis": {},
            "execution_summary": {},
            "end_time": None
        }
    
    def log_tool_result(self, tool_name: str, params: Dict[str, Any], 
                       result: Dict[str, Any], ai_reasoning: str, target: str):
        """Araç sonucunu kaydet"""
        tool_result = {
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "params": params,
            "result": result,
            "ai_reasoning": ai_reasoning,
            "target": target,
            "success": result.get("success", False)
        }
        
        self.session_data["tool_results"].append(tool_result)
        
        # Her sonuç sonrası dosyayı güncelle
        self._save_session()
        
        logger.info(f"Tool result logged: {tool_name}")
    
    def log_ai_decision(self, decision_type: str, decision: Dict[str, Any], 
                       context: str = ""):
        """AI kararını kaydet"""
        ai_decision = {
            "timestamp": datetime.now().isoformat(),
            "decision_type": decision_type,
            "decision": decision,
            "context": context
        }
        
        self.session_data["ai_decisions"].append(ai_decision)
        self._save_session()
        
        logger.info(f"AI decision logged: {decision_type}")
    
    def log_session_summary(self, target: str, user_task: str, final_results: Dict[str, Any]):
        """Session özetini kaydet"""
        self.session_data["target"] = target
        self.session_data["user_task"] = user_task
        self.session_data["discovered_information"] = final_results.get("discovered_information", {})
        self.session_data["final_analysis"] = final_results.get("final_analysis", {})
        self.session_data["execution_summary"] = final_results.get("execution_summary", {})
        self.session_data["end_time"] = datetime.now().isoformat()
        
        self._save_session()
        
        logger.info(f"Session summary logged for target: {target}")
    
    def _save_session(self):
        """Session verilerini dosyaya kaydet"""
        file_path = os.path.join(self.results_dir, self.session_file)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.session_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Session save error: {e}")
    
    def get_current_session_file(self) -> str:
        """Mevcut session dosyasının yolunu döndür"""
        return os.path.join(self.results_dir, self.session_file)
    
    def print_tool_result(self, tool_name: str, result: Dict[str, Any]):
        """Araç sonucunu güzel formatta yazdır"""
        print(f"\n{'='*60}")
        print(f"🔧 TOOL SONUCU: {tool_name}")
        print(f"{'='*60}")
        
        if result.get("success", False):
            print(f"✅ Durum: BAŞARILI")
            print(f"📊 Özet: {result.get('summary', 'Sonuç alındı')}")
            
            data = result.get("data", {})
            if data:
                print(f"\n📋 DETAYLI VERİLER:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            
            recommendations = result.get("recommendations", [])
            if recommendations:
                print(f"\n💡 ÖNERİLER:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"   {i}. {rec.get('title', 'Öneri')}")
                    print(f"      {rec.get('description', 'Açıklama yok')}")
        else:
            print(f"❌ Durum: BAŞARISIZ")
            print(f"🚨 Hata: {result.get('error', 'Bilinmeyen hata')}")
        
        print(f"{'='*60}\n")
    
    def print_final_analysis(self, analysis: Dict[str, Any]):
        """Final analizi güzel formatta yazdır"""
        print(f"\n{'='*80}")
        print(f"📊 FİNAL GÜVENLİK ANALİZİ")
        print(f"{'='*80}")
        
        # Risk seviyesi
        risk_level = analysis.get("risk_level", "Bilinmiyor")
        risk_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(risk_level.lower(), "⚪")
        print(f"{risk_emoji} Risk Seviyesi: {risk_level.upper()}")
        
        # Güvenlik açıkları
        vulnerabilities = analysis.get("security_vulnerabilities", [])
        if vulnerabilities:
            print(f"\n🚨 TESPİT EDİLEN GÜVENLİK AÇIKLARI ({len(vulnerabilities)} adet):")
            for i, vuln in enumerate(vulnerabilities, 1):
                severity = vuln.get("severity", "Bilinmiyor")
                severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(severity.lower(), "⚪")
                print(f"   {i}. {severity_emoji} {vuln.get('type', 'Bilinmiyor')} - {severity.upper()}")
                print(f"      📝 {vuln.get('description', 'Açıklama yok')}")
                if vuln.get('cvss_score'):
                    print(f"      📊 CVSS: {vuln.get('cvss_score')}")
        
        # Öneriler
        recommendations = analysis.get("recommendations", [])
        if recommendations:
            print(f"\n💡 ÖNCELİKLİ ÖNERİLER:")
            for i, rec in enumerate(recommendations, 1):
                priority = rec.get("priority", "Bilinmiyor")
                priority_emoji = {"immediate": "🔴", "short_term": "🟠", "long_term": "🟡"}.get(priority.lower(), "⚪")
                print(f"   {i}. {priority_emoji} {rec.get('description', 'Öneri yok')}")
        
        # Executive Summary
        exec_summary = analysis.get("executive_summary", "")
        if exec_summary:
            print(f"\n📋 YÖNETİCİ ÖZETİ:")
            print(f"   {exec_summary}")
        
        print(f"{'='*80}\n")

# Global logger instance
_logger_instance = None

def get_logger() -> ToolResultsLogger:
    """Global logger instance'ı al"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ToolResultsLogger()
    return _logger_instance

def log_tool_result(tool_name: str, params: Dict[str, Any], result: Dict[str, Any], 
                   ai_reasoning: str, target: str):
    """Araç sonucunu kaydet (global fonksiyon)"""
    logger = get_logger()
    logger.log_tool_result(tool_name, params, result, ai_reasoning, target)
    logger.print_tool_result(tool_name, result)

def log_ai_decision(decision_type: str, decision: Dict[str, Any], context: str = ""):
    """AI kararını kaydet (global fonksiyon)"""
    logger = get_logger()
    logger.log_ai_decision(decision_type, decision, context)

def log_session_summary(target: str, user_task: str, final_results: Dict[str, Any]):
    """Session özetini kaydet (global fonksiyon)"""
    logger = get_logger()
    logger.log_session_summary(target, user_task, final_results)
    logger.print_final_analysis(final_results.get("final_analysis", {}))

def get_current_session_file() -> str:
    """Mevcut session dosyasının yolunu al (global fonksiyon)"""
    logger = get_logger()
    return logger.get_current_session_file()
