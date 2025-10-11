"""
Agent Core Package - Bilişsel Pentest Ajanının Çekirdek Modülleri

Bu paket, Planner-Executor tasarım desenini kullanarak modüler bir ajan mimarisi sağlar.
Her modül belirli bir sorumluluğa sahiptir:
- state.py: Ajanın hafızası ve durum yönetimi
- planner.py: Stratejik planlama ve adaptasyon
- executor.py: Plan uygulama ve özel yetenekler
- orchestrator.py: Ana döngü yönetimi
"""

from .state import AgentState
from .planner import Planner
from .executor import Executor
from .orchestrator import AgentOrchestrator

__all__ = [
    'AgentState',
    'Planner', 
    'Executor',
    'AgentOrchestrator'
]

__version__ = "1.0.0"
__author__ = "Pentagent Team"
__description__ = "Modüler bilişsel pentest ajanı çekirdeği"
