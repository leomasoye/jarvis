import os
import sys
from pathlib import Path

def create_startup_shortcut():
    """
    Crée un raccourci Windows (.lnk) dans le dossier de démarrage pour lancer JARVIS silencieusement avec son icône.
    """
    if sys.platform != "win32":
        print("L'installation au démarrage n'est supportée que sous Windows.")
        return

    jarvis_dir = Path(__file__).parent.resolve()
    main_script = jarvis_dir / "main.py"
    
    pythonw_exe = Path(sys.executable).parent / "pythonw.exe"
    if not pythonw_exe.exists():
        pythonw_exe = Path(sys.executable)

    icon_path = jarvis_dir / "assets" / "icon.ico"

    startup_dir = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    shortcut_path = startup_dir / "JARVIS.lnk"

    # Création d'un script VBS temporaire pour générer le vrai raccourci .lnk
    vbs_script = jarvis_dir / "create_shortcut.vbs"
    vbs_content = f'''
Set WshShell = CreateObject("WScript.Shell")
Set Shortcut = WshShell.CreateShortcut("{shortcut_path}")
Shortcut.TargetPath = "{pythonw_exe}"
Shortcut.Arguments = """{main_script}"""
Shortcut.WorkingDirectory = "{jarvis_dir}"
Shortcut.IconLocation = "{icon_path}"
Shortcut.WindowStyle = 7
Shortcut.Save
'''
    
    try:
        vbs_script.write_text(vbs_content.strip(), encoding="utf-8")
        os.system(f'cscript //nologo "{vbs_script}"')
        vbs_script.unlink(missing_ok=True)
        
        # Supprimer l'ancien script .vbs s'il existe
        old_vbs = startup_dir / "LaunchJarvis.vbs"
        if old_vbs.exists():
            old_vbs.unlink()
            
        print(f"Installation réussie ! JARVIS se lancera avec son icône au démarrage.")
        print(f"Raccourci créé : {shortcut_path}")
    except Exception as e:
        print(f"Erreur lors de la création du raccourci de démarrage : {e}")

if __name__ == "__main__":
    create_startup_shortcut()
