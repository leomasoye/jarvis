import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional

from tools.base_tool import BaseTool, RiskLevel
from tools.web_search import WebSearchTool
from tools.app_controller import AppControllerTool
from tools.file_manager import FileReadTool, FileWriteTool
from tools.shell_execute import ShellCommandTool
from tools.system_info import SystemInfoTool
from tools.clipboard import ClipboardTool

logger = logging.getLogger(__name__)

class ActionManager:
    """
    Gestionnaire central des actions (Étape 6).
    Parse les balises <tool_call>, évalue les risques et exécute ou demande confirmation.
    """

    def __init__(self, bridge=None) -> None:
        self.bridge = bridge
        self.tools: Dict[str, BaseTool] = {}
        self.db = None
        self.session_id: str = ""
        
        # Enregistrement des outils
        self.register_tool(WebSearchTool())
        self.register_tool(AppControllerTool())
        self.register_tool(FileReadTool())
        self.register_tool(FileWriteTool())
        self.register_tool(ShellCommandTool())
        self.register_tool(SystemInfoTool())
        self.register_tool(ClipboardTool())
        
        # État temporaire pour les actions en attente de confirmation
        self.pending_actions: Dict[str, dict] = {}
        
        if self.bridge:
            # Connecter les retours de l'UI
            pass # TODO: JS to Python slots via QWebChannel

    def set_db(self, db, session_id: str = "") -> None:
        """Injecte la base de données pour l'audit trail."""
        self.db = db
        if session_id:
            self.session_id = session_id

    def register_tool(self, tool: BaseTool) -> None:
        self.tools[tool.name] = tool
        logger.info(f"[ActionManager] Outil '{tool.name}' enregistré.")

    def parse_and_clean(self, text: str) -> tuple[list[dict], str]:
        """Extrait toutes les balises <tool_call> ou les blocs JSON isolés, et retourne le texte nettoyé."""
        calls = []
        clean_text = text
        
        # 1. Extraction classique via balise
        pattern_xml = re.compile(r'<tool_call>\s*({.*?})\s*</tool_call>', re.DOTALL | re.IGNORECASE)
        for match in pattern_xml.finditer(text):
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict) and "tool" in data and "params" in data:
                    calls.append(data)
                    clean_text = clean_text.replace(match.group(0), "")
            except json.JSONDecodeError:
                pass
                
        # 2. Extraction via fallback sur tout JSON valide
        if not calls:
            stack = []
            start = -1
            for i, char in enumerate(text):
                if char == '{':
                    if not stack:
                        start = i
                    stack.append(char)
                elif char == '}':
                    if stack:
                        stack.pop()
                        if not stack:
                            json_str = text[start:i+1]
                            try:
                                data = json.loads(json_str)
                                if isinstance(data, dict) and "tool" in data and "params" in data:
                                    calls.append(data)
                                    clean_text = clean_text.replace(json_str, "")
                            except json.JSONDecodeError:
                                pass
                                
        # 3. Sécurité anti-hallucination : 
        # Si l'IA invente elle-même la balise de retour d'outil, on coupe TOUT ce qui suit, 
        # car c'est une hallucination (elle se parle à elle-même).
        split_hallucination = re.split(r'\[RÉSULTAT DE L\'OUTIL', clean_text, flags=re.IGNORECASE)
        if len(split_hallucination) > 1:
            clean_text = split_hallucination[0]
            
        # Au cas où une balise isolée sans texte après aurait échappé au split (ex: juste la balise fermante)
        clean_text = re.sub(r'\[RÉSULTAT DE L\'OUTIL.*?\]', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
            
        return calls, clean_text.strip()

    def get_tool_documentation(self) -> str:
        """Retourne la documentation complète de tous les outils (injectée dans le prompt IA)."""
        doc = "<tools>\n"
        for t in self.tools.values():
            doc += f"  <tool name=\"{t.name}\">\n"
            doc += f"    <description>{t.description}</description>\n"
            doc += f"    <parameters>{json.dumps(t.parameters_schema, indent=2)}</parameters>\n"
            doc += "  </tool>\n"
        doc += "</tools>\n"
        doc += """
IL EST OBLIGATOIRE DE RÉPONDRE AVEC CE FORMAT EXACT :
<tool_call>
{
  "tool": "nom_de_l_outil",
  "params": { "param1": "valeur1" }
}
</tool_call>
ATTENTION : Fournis directement les valeurs dans "params". N'ajoute PAS de balises "type" ou "description" à l'intérieur.
Exemple correct : "params": {"query": "Tokyo"}
Exemple INCORRECT : "params": {"query": {"type": "string", "description": "Tokyo"}}
"""
        return doc

    def validate_and_sanitize_params(self, tool: BaseTool, raw_params: Any) -> tuple[bool, dict, str]:
        """
        Valide et assainit les paramètres fournis par le LLM.
        - Déballe les éventuelles hallucinations structurelles type {"type": "string", "value": "xyz"}.
        - Vérifie la présence des paramètres obligatoires.
        - Valide et convertit les types attendus.
        """
        if raw_params is None:
            raw_params = {}
        if not isinstance(raw_params, dict):
            return False, {}, f"Les paramètres doivent être un objet JSON (reçu: {type(raw_params).__name__})"

        cleaned = {}
        schema = getattr(tool, "parameters_schema", {}) or {}

        for param_name, param_meta in schema.items():
            if param_name not in raw_params:
                desc = param_meta.get("description", "").lower()
                is_optional = param_meta.get("optional", False) or "optionnel" in desc or "par défaut" in desc
                if not is_optional and "default" not in param_meta:
                    return False, {}, f"Paramètre obligatoire manquant : '{param_name}' pour l'outil '{tool.name}'."
                continue

            val = raw_params[param_name]
            # Déballer si le LLM a mis un objet imbriqué type {"type": ..., "value": ...} ou {"value": ...}
            if isinstance(val, dict):
                if "value" in val:
                    val = val["value"]
                elif "description" in val and len(val) == 1:
                    val = val["description"]

            expected_type = param_meta.get("type", "string")
            if expected_type == "string":
                val = str(val) if val is not None else ""
            elif expected_type == "integer":
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    return False, {}, f"Paramètre '{param_name}' invalide : entier attendu."
            elif expected_type == "boolean":
                if isinstance(val, str):
                    val = val.lower() in ("true", "1", "yes", "oui")
                else:
                    val = bool(val)

            cleaned[param_name] = val

        # Conserver les clés additionnelles
        for k, v in raw_params.items():
            if k not in cleaned:
                cleaned[k] = v

        return True, cleaned, "OK"

    def _execute_safe_call(self, tool: BaseTool, params: dict) -> tuple[str, str, int, bool]:
        """Exécute un outil SAFE avec mesure du temps et enregistrement dans l'audit."""
        logger.info(f"[ActionManager] Exécution directe (SAFE) de {tool.name}")
        t0 = time.time()
        success = True
        try:
            result = tool.execute(params)
        except Exception as e:
            result = f"Erreur lors de l'exécution de {tool.name}: {e}"
            success = False
        exec_time_ms = int((time.time() - t0) * 1000)

        if self.db:
            try:
                self.db.save_audit_log(
                    session_id=self.session_id,
                    tool_name=tool.name,
                    params=params,
                    result=str(result),
                    risk_level=tool.risk_level.value,
                    user_confirmed=False,
                    execution_time_ms=exec_time_ms,
                    success=success
                )
            except Exception as e:
                logger.error(f"[ActionManager] Erreur enregistrement audit: {e}")

        return tool.name, str(result), exec_time_ms, success

    def process_calls(self, calls: list[dict]) -> tuple[bool, Optional[str]]:
        """
        Traite une liste d'appels d'outils.
        - Valide et assainit chaque paramètre.
        - Exécute les outils SAFE (en parallèle si multiples).
        - Demande confirmation pour les outils SENSITIVE / MODERATE.
        """
        if not calls:
            return False, None

        # 1. Validation de l'existence des outils et de leurs paramètres
        prepared_calls = []
        for call in calls:
            tool_name = str(call.get("tool") or "").strip()
            raw_params = call.get("params", {})

            tool = self.tools.get(tool_name) if tool_name else None
            if not tool:
                logger.warning(f"[ActionManager] Outil inconnu : {tool_name}")
                return True, f"Erreur système : l'outil '{tool_name}' n'existe pas."

            valid, clean_params, err_msg = self.validate_and_sanitize_params(tool, raw_params)
            if not valid:
                logger.warning(f"[ActionManager] Paramètres invalides pour {tool_name} : {err_msg}")
                return True, f"Erreur de validation pour '{tool_name}' : {err_msg}"

            prepared_calls.append({"tool": tool, "params": clean_params, "raw_call": call})

        # 2. Vérifier s'il y a un outil sensible nécessitant confirmation
        sensitive_item = next((item for item in prepared_calls if item["tool"].risk_level != RiskLevel.SAFE), None)
        if sensitive_item:
            tool = sensitive_item["tool"]
            params = sensitive_item["params"]
            raw_call = sensitive_item["raw_call"]
            action_id = f"{tool.name}_{id(raw_call)}"
            self.pending_actions[action_id] = {"tool": tool, "params": params}
            logger.info(f"[ActionManager] Action {tool.name} nécessite confirmation (ID: {action_id}).")

            payload = json.dumps({
                "id": action_id,
                "tool": tool.name,
                "description": tool.description,
                "params": params,
                "risk": tool.risk_level.value
            })
            if self.bridge:
                self.bridge.action_requires_confirmation.emit(payload)
            return False, action_id

        # 3. Tous les outils sont SAFE
        if len(prepared_calls) == 1:
            item = prepared_calls[0]
            name, res, _, _ = self._execute_safe_call(item["tool"], item["params"])
            return True, f"\n[RÉSULTAT DE L'OUTIL {name}]\n{res}\n"

        # Exécution parallèle pour les outils SAFE multiples
        results_formatted = []
        with ThreadPoolExecutor(max_workers=min(4, len(prepared_calls))) as executor:
            futures = [
                executor.submit(self._execute_safe_call, item["tool"], item["params"])
                for item in prepared_calls
            ]
            for future in as_completed(futures):
                try:
                    name, res, _, _ = future.result()
                    results_formatted.append(f"[RÉSULTAT DE L'OUTIL {name}]\n{res}")
                except Exception as e:
                    results_formatted.append(f"[ERREUR OUTIL]\n{e}")

        combined_output = "\n\n" + "\n\n".join(results_formatted) + "\n"
        return True, combined_output

    def execute_pending(self, action_id: str) -> str:
        """Exécute une action après confirmation utilisateur."""
        if action_id not in self.pending_actions:
            return "Erreur : Action expirée ou introuvable."
            
        action = self.pending_actions.pop(action_id)
        tool: BaseTool = action["tool"]
        params = action["params"]
        
        logger.info(f"[ActionManager] Exécution post-confirmation de {tool.name}")
        t0 = time.time()
        success = True
        try:
            result = tool.execute(params)
        except Exception as e:
            result = f"Erreur lors de l'exécution de {tool.name}: {e}"
            success = False
        exec_time_ms = int((time.time() - t0) * 1000)

        # Journal d'audit
        if self.db:
            try:
                self.db.save_audit_log(
                    session_id=self.session_id,
                    tool_name=tool.name,
                    params=params,
                    result=str(result),
                    risk_level=tool.risk_level.value,
                    user_confirmed=True,
                    execution_time_ms=exec_time_ms,
                    success=success
                )
            except Exception as e:
                logger.error(f"[ActionManager] Erreur enregistrement audit: {e}")

        if self.bridge:
            self.bridge.action_executed_success.emit(f"Action '{tool.name}' terminée.")
            
        return result
