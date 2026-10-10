import logging
import subprocess
import os
import difflib
import winreg
import shutil
from typing import Any, Dict
from tools.base_tool import BaseTool, RiskLevel

logger = logging.getLogger(__name__)

class AppControllerTool(BaseTool):
    name = "app_controller"
    description = "Ouvre une application installée sur le PC (ex: spotify, chrome, word)."
    risk_level = RiskLevel.SAFE
    parameters_schema = {
        "app_name": {
            "type": "string",
            "description": "Le nom flou ou exact de l'application à lancer (ex: spotify, chrome, word)."
        }
    }

    def _find_in_start_menu(self, app_name: str) -> str:
        import os
        import difflib
        
        search_target = app_name.lower().strip()
        
        # Dictionnaire d'alias pour les applications les plus courantes
        aliases = {
            "vs code": "visual studio code",
            "vscode": "visual studio code",
            "word": "word",
            "excel": "excel",
            "powerpoint": "powerpoint",
            "chrome": "google chrome",
            "edge": "microsoft edge",
            "lol": "league of legends",
            "csgo": "counter-strike",
            "cs2": "counter-strike",
            "vlc": "vlc media player"
        }
        if search_target in aliases:
            search_target = aliases[search_target]
            
        appdata = os.environ.get('APPDATA', '')
        programdata = os.environ.get('PROGRAMDATA', '')
        userprofile = os.environ.get('USERPROFILE', '')
        public = os.environ.get('PUBLIC', '')
        
        dirs_to_scan = []
        if appdata:
            dirs_to_scan.append(os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs"))
        if programdata:
            dirs_to_scan.append(os.path.join(programdata, r"Microsoft\Windows\Start Menu\Programs"))
        if userprofile:
            dirs_to_scan.append(os.path.join(userprofile, r"Desktop"))
        if public:
            dirs_to_scan.append(os.path.join(public, r"Desktop"))
            
        all_shortcuts = {} # name_without_ext -> full_path
        
        for d in dirs_to_scan:
            if not os.path.exists(d): continue
            for root, _, files in os.walk(d):
                for file in files:
                    if file.lower().endswith('.lnk'):
                        name_without_ext = os.path.splitext(file)[0].lower()
                        all_shortcuts[name_without_ext] = os.path.join(root, file)

        # 1. Exact match
        if search_target in all_shortcuts:
            return all_shortcuts[search_target]

        # 2. Substring match
        for name, path in all_shortcuts.items():
            if search_target in name or name in search_target:
                return path

        # 3. Fuzzy match (difflib) avec un seuil bas pour capter "vs code" -> "visual studio code"
        matches = difflib.get_close_matches(search_target, all_shortcuts.keys(), n=1, cutoff=0.4)
        if matches:
            return all_shortcuts[matches[0]]
            
        return None

    def _find_in_registry(self, app_name: str) -> str:
        registry_hives = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
        ]
        
        search_target = app_name.lower().strip()
        search_target_exe = search_target if search_target.endswith(".exe") else f"{search_target}.exe"
        
        for hive, path in registry_hives:
            try:
                with winreg.OpenKey(hive, path) as key:
                    num_subkeys = winreg.QueryInfoKey(key)[0]
                    for i in range(num_subkeys):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            if search_target_exe == subkey_name.lower() or search_target in subkey_name.lower():
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    default_val, _ = winreg.QueryValueEx(subkey, None)
                                    if default_val:
                                        return str(default_val)
                        except OSError:
                            continue
            except FileNotFoundError:
                continue
                
        return None

    def execute(self, params: Dict[str, Any]) -> str:
        app_name = params.get("app_name")
        if not app_name:
            return "Erreur : 'app_name' est requis."

        logger.info(f"[AppController] Tentative de lancement : {app_name}")
        
        # 1. Native Windows command (PATH / shell)
        if shutil.which(app_name):
            try:
                subprocess.Popen([app_name], shell=True)
                return f"Application '{app_name}' lancée avec succès via les commandes natives."
            except Exception as e:
                logger.error(f"[AppController] Erreur commande native: {e}")

        # 2. Scanner le Menu Démarrer
        lnk_path = self._find_in_start_menu(app_name)
        if lnk_path:
            try:
                os.startfile(lnk_path)
                return f"Application '{app_name}' lancée avec succès via le Menu Démarrer."
            except Exception as e:
                logger.error(f"[AppController] Erreur Start Menu: {e}")

        # 3. Chercher dans le Registre Windows
        exe_path = self._find_in_registry(app_name)
        # Check if exe_path doesn't have quotes and exists
        if exe_path:
            exe_path = exe_path.strip('"')
            if os.path.exists(exe_path):
                try:
                    subprocess.Popen([exe_path])
                    return f"Application '{app_name}' lancée avec succès via le Registre."
                except Exception as e:
                    logger.error(f"[AppController] Erreur Registre: {e}")

        # Si l'application n'est toujours pas trouvée
        return "Application introuvable. Demande à l'utilisateur s'il veut que tu cherches dans un dossier spécifique ou s'il connaît le nom exact de l'exécutable."
