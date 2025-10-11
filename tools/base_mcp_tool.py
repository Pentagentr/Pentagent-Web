"""
Pentagent Base Tool - Mevcut Araçlar için Uyumlu Temel Sınıf

Bu modül, mevcut Pentagent araçlarının yapısına uygun olarak tasarlanmış
temel sınıfı tanımlar. Mevcut araçların kullandığı MCPTool formatını koruyarak,
standartlaştırılmış çıktı formatı ve yardımcı metodlar sağlar.

Mevcut Araç Yapısı:
- MCPTool base class'ından miras alır
- run_tool() metodunu kullanır (sync)
- reasoning_log listesi ile akıl yürütme
- recommendations dictionary formatında
- _create_final_output() ile çıktı formatlama

Bu base class, mevcut araçları bozmadan standartlaştırma sağlar.
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Günlükleme yapılandırması
logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """
    Pentagent ekosistemi için araç kategorilerinin numaralandırması.
    """
    RECONNAISSANCE = "reconnaissance"
    DISCOVERY_ENUMERATION = "discovery_enumeration"
    VULNERABILITY_SCANNING = "vulnerability_scanning"
    VULNERABILITY_VERIFICATION = "vulnerability_verification"
    API_SECURITY = "api_security"
    CLOUD_SECURITY = "cloud_security"
    THREAT_INTELLIGENCE = "threat_intelligence"


class PriorityLevel(Enum):
    """
    Araç önerileri için öncelik seviyelerinin numaralandırması.
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ToolRecommendation:
    """
    Araç önerileri için veri sözleşmesi.
    """
    priority: PriorityLevel
    tool_name: str
    reason: str
    params: Dict[str, Any]


class MCPTool(ABC):
    """
    Mevcut Pentagent araçları için uyumlu temel sınıf.
    
    Bu sınıf, mevcut araçların yapısını koruyarak standartlaştırma sağlar.
    Tüm araçlar bu sınıftan miras alır ve run_tool metodunu uygular.
    """
    
    def __init__(self, name: str, description: str, category: ToolCategory = None) -> None:
        """
        MCP aracını başlat.
        
        Args:
            name (str): Araç için benzersiz tanımlayıcı
            description (str): Aracın amacının açıklaması
            category (ToolCategory, optional): Aracın kategorisi
        """
        # İsim doğrulama
        if not name or not isinstance(name, str) or not name.strip():
            raise ValueError("Araç ismi boş olmayan bir string olmalı")
        
        # Açıklama doğrulama
        if not description or not isinstance(description, str) or not description.strip():
            raise ValueError("Araç açıklaması boş olmayan bir string olmalı")
        
        # Doğrulanmış özellikleri sakla
        self.name = name.strip()
        self.description = description.strip()
        self.category = category
        self.version = "1.0.0"
        self.created_at = datetime.now()
        
        # Araç başlatmasını günlükle
        logger.info(f"🔧 {self.name} başlatıldı")
    
    @abstractmethod
    def run_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aracı sağlanan parametrelerle yürüt.
        
        Bu, her aracın MUTLAKA uygulaması gereken ana yürütme metodudur.
        Mevcut araçların yapısına uygun olarak sync olarak tasarlanmıştır.
        
        Args:
            params (Dict[str, Any]): Araç yürütmesi için gerekli parametreler
        
        Returns:
            Dict[str, Any]: Standartlaştırılmış sonuç sözlüğü
        
        Raises:
            NotImplementedError: Alt sınıf tarafından uygulanmazsa
        """
        pass
    
    def _add_reasoning(self, reasoning_log: List[Dict[str, str]], phase: str, thought: str) -> None:
        """
        Akıl yürütme günlüğüne yapılandırılmış giriş ekle.
        
        Args:
            reasoning_log (List[Dict[str, str]]): Eklenecek akıl yürütme günlüğü
            phase (str): Yürütme aşaması
            thought (str): Günlüğe kaydedilecek düşünce
        """
        reasoning_log.append({
            "phase": phase,
            "thought": thought,
            "timestamp": datetime.now().isoformat()
        })
    
    def _create_recommendation(self, priority: PriorityLevel, tool_name: str, reason: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Araç önerisi oluştur.
        
        Args:
            priority (PriorityLevel): Öneri için öncelik seviyesi
            tool_name (str): Önerilen aracın adı
            reason (str): Önerinin nedeni
            params (Dict[str, Any], optional): Önerilen araç için parametreler
        
        Returns:
            Dict[str, Any]: Öneri sözlüğü
        """
        if params is None:
            params = {}
        
        return {
            "priority": priority.value,
            "tool": tool_name,
            "reason": reason,
            "params": params
        }
    
    def _create_final_output(self, 
                           success: bool = True,
                           data: Dict[str, Any] = None,
                           ai_summary: str = None,
                           ai_reasoning: List[Dict[str, str]] = None,
                           recommendations: List[Dict[str, Any]] = None,
                           error: str = None) -> Dict[str, Any]:
        """
        Standartlaştırılmış final çıktı formatı oluştur.
        
        Mevcut araçların kullandığı format ile uyumlu olarak tasarlanmıştır.
        
        Args:
            success (bool): Yürütmenin başarılı olup olmadığı
            data (Dict[str, Any], optional): Araç sonuçları
            ai_summary (str, optional): AI özeti
            ai_reasoning (List[Dict[str, str]], optional): Akıl yürütme günlüğü
            recommendations (List[Dict[str, Any]], optional): Öneriler
            error (str, optional): Hata mesajı
        
        Returns:
            Dict[str, Any]: Standartlaştırılmış çıktı sözlüğü
        """
        # Varsayılan değerleri başlat
        if data is None:
            data = {}
        if ai_reasoning is None:
            ai_reasoning = []
        if recommendations is None:
            recommendations = []
        
        # AI özeti oluştur (sağlanmamışsa)
        if ai_summary is None:
            if not success:
                ai_summary = f"{self.name} yürütmesi başarısız"
            elif not data:
                ai_summary = f"{self.name} başarıyla yürütüldü ancak veri döndürmedi"
            else:
                ai_summary = f"{self.name} başarıyla yürütüldü"
        
        # Standartlaştırılmış çıktı oluştur
        return {
            "success": success,
            "data": data,
            "ai_summary": ai_summary,
            "ai_reasoning": ai_reasoning,
            "recommendations": recommendations,
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "tool_name": self.name,
            "tool_version": self.version,
            "tool_category": self.category.value if self.category else "unknown"
        }
