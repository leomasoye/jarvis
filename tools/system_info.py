"""
JARVIS — Outil de surveillance et d'informations système (SystemInfoTool).
Utilise psutil pour remonter l'utilisation CPU, RAM, disque, batterie et processus.
"""
import logging
from typing import Any, Dict
import psutil

from tools.base_tool import BaseTool, RiskLevel

logger = logging.getLogger(__name__)


class SystemInfoTool(BaseTool):
    name = "system_info"
    description = (
        "Fournit les métriques et statistiques matérielles en temps réel du PC : "
        "CPU, mémoire RAM, espace disque, statut de la batterie et processus les plus actifs."
    )
    risk_level = RiskLevel.SAFE
    parameters_schema = {
        "metric": {
            "type": "string",
            "description": "Information spécifique demandée : 'all', 'cpu', 'memory', 'disk', 'processes', 'battery'. Par défaut 'all'."
        }
    }

    def execute(self, params: Dict[str, Any]) -> str:
        metric = (params.get("metric") or "all").lower().strip()
        lines = []

        try:
            # 1. CPU
            if metric in ("all", "cpu"):
                cpu_pct = psutil.cpu_percent(interval=0.1)
                cpu_count = psutil.cpu_count(logical=True)
                lines.append(f"• CPU : {cpu_pct:.1f}% d'utilisation ({cpu_count} cœurs logiques)")

            # 2. RAM
            if metric in ("all", "memory", "ram"):
                mem = psutil.virtual_memory()
                used_gb = mem.used / (1024 ** 3)
                total_gb = mem.total / (1024 ** 3)
                lines.append(f"• RAM : {mem.percent}% ({used_gb:.1f} Go / {total_gb:.1f} Go)")

            # 3. Disque
            if metric in ("all", "disk", "storage"):
                disk = psutil.disk_usage("C:\\" if hasattr(psutil, "disk_usage") else "/")
                free_gb = disk.free / (1024 ** 3)
                total_gb = disk.total / (1024 ** 3)
                lines.append(f"• Disque principal : {disk.percent}% utilisé ({free_gb:.1f} Go libres sur {total_gb:.1f} Go)")

            # 4. Batterie
            if metric in ("all", "battery"):
                battery = psutil.sensors_battery()
                if battery:
                    status = "en charge" if battery.power_plugged else "sur batterie"
                    lines.append(f"• Batterie : {battery.percent}% ({status})")
                elif metric == "battery":
                    lines.append("• Batterie : Aucune batterie détectée (ordinateur fixe)")

            # 5. Processus actifs
            if metric in ("all", "processes", "apps"):
                top_procs = []
                for p in psutil.process_iter(['name', 'memory_percent', 'cpu_percent']):
                    try:
                        name = p.info['name']
                        mem_p = p.info['memory_percent'] or 0.0
                        if name and name.lower() not in ("system idle process", "system"):
                            top_procs.append((name, mem_p))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                top_procs.sort(key=lambda x: x[1], reverse=True)
                top_names = [f"{name} ({mem_p:.1f}% RAM)" for name, mem_p in top_procs[:4]]
                if top_names:
                    lines.append(f"• Processus principaux : {', '.join(top_names)}")

            if not lines:
                return f"Métrique inconnue : '{metric}'. Métriques valides : all, cpu, memory, disk, processes, battery."

            return "État actuel du système :\n" + "\n".join(lines)

        except Exception as e:
            logger.error(f"[SystemInfoTool] Erreur : {e}")
            return f"Erreur lors de la récupération des informations système : {e}"
