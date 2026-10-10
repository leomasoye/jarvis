# JARVIS — Document d'Architecture & Feuille de Contexte
> **Version** : 1.1
> **Date** : 2026-08-18
> **Statut** : Référence Canonique — À consulter SYSTÉMATIQUEMENT avant tout développement
> **Matériel cible** : PC Windows — GPU NVIDIA RTX 3060 (6 Go VRAM), CPU multi-cœur, RAM ≥ 16 Go

---

## Table des matières

1. [Vision & Cahier des Charges](#1-vision--cahier-des-charges)
2. [Contraintes Matérielles & Optimisation](#2-contraintes-matérielles--optimisation)
3. [Choix Techniques (Stack)](#3-choix-techniques-stack)
4. [Architecture Globale du Système](#4-architecture-globale-du-système)
5. [Structure des Dossiers](#5-structure-des-dossiers)
6. [Architecture de la Mémoire IA](#6-architecture-de-la-mémoire-ia)
7. [Protocole de Communication Interne](#7-protocole-de-communication-interne)
8. [Rendu Dynamique & Balises Spéciales](#8-rendu-dynamique--balises-spéciales)
9. [Système d'Actions PC Cadré (Agentic Layer)](#9-système-dactions-pc-cadré-agentic-layer)
10. [Plan de Développement — Étapes 1 à 6](#10-plan-de-développement--étapes-1-à-6)
11. [Règles de Développement & Conventions](#11-règles-de-développement--conventions)

---

## 1. Vision & Cahier des Charges

### 1.1 Objectif Principal

Jarvis est un **assistant IA 100% local**, fonctionnant hors ligne, sous forme d'application de bureau autonome (Desktop App). Il est conçu pour être un véritable copilote personnel : capable de comprendre la voix, de raisonner, de générer du code, de produire des visualisations dynamiques, et de maintenir une mémoire persistante entre les sessions.

**Il n'est PAS** un site web, une extension navigateur, ou une application cloud.

### 1.2 Principes Fondateurs

| Principe | Description |
|---|---|
| **100% Local** | Aucune donnée ne sort du PC. Pas d'API externe. Pas de connexion cloud. |
| **Temps-réel** | Réponses vocales et textuelles sans latence perceptible. |
| **Visualisation Dynamique** | L'IA produit du contenu visuel interactif (diagrammes, cartes, graphiques). |
| **Mémoire Persistante** | Jarvis se souvient des conversations passées et des préférences utilisateur. |
| **Extensible** | Architecture modulaire permettant d'ajouter de nouveaux outils (tools) facilement. |
| **Actions Cadrées** | Jarvis peut agir sur le PC (mail, fichiers, apps) uniquement avec confirmation explicite de l'utilisateur pour les actions sensibles. |

### 1.3 Fonctionnalités Requises (MVP)

- [ ] **F-01** : Interface graphique de type HUD — sombre, futuriste, épurée.
- [ ] **F-02** : Reconnaissance vocale via Faster-Whisper (optimisé CPU/RAM).
- [ ] **F-03** : Synthèse vocale (TTS) via Piper — ultra-rapide sur CPU.
- [ ] **F-04** : Chat textuel avec streaming des réponses de l'IA.
- [ ] **F-05** : Rendu de diagrammes Mermaid depuis le texte de l'IA (balise `<mermaid>`).
- [ ] **F-06** : Affichage de cartes Leaflet.js depuis un JSON (balise `<map>`).
- [ ] **F-07** : Mémoire conversationnelle persistante (court-terme + long-terme).
- [ ] **F-08** : Sélection dynamique du modèle IA (rapide vs. complexe).
- [ ] **F-09** : System prompt configurable via un fichier dédié.
- [ ] **F-10** : Panneau de configuration accessible depuis l'interface.

### 1.4 Fonctionnalités d'Actions PC (Agentic Layer)

- [ ] **F-11** : Envoi d'e-mails via compte SMTP local (avec prévisualisation + confirmation obligatoire).
- [ ] **F-12** : Gestion de fichiers et dossiers (créer, lire, déplacer, supprimer — avec confirmation pour suppression).
- [ ] **F-13** : Exécution de commandes système et scripts (shell restreint, liste blanche de commandes autorisées).
- [ ] **F-14** : Contrôle d'applications (ouvrir/fermer Chrome, VSCode, Notepad, etc.).
- [ ] **F-15** : Planificateur de tâches (créer des rappels ou tâches différées via Windows Task Scheduler).
- [ ] **F-16** : Système de permissions granulaires — l'utilisateur active/désactive chaque catégorie d'action.

---

## 2. Contraintes Matérielles & Optimisation

### 2.1 GPU — RTX 3060 (6 Go VRAM)

La VRAM est la ressource la plus précieuse et la plus contrainte du système.

| Modèle | VRAM estimée | Utilisation |
|---|---|---|
| `llama3.2:3b` | ~2.5 Go | Conversations vocales rapides, réponses courtes |
| `qwen2.5:7b` | ~5.0 Go | Tâches complexes, code, tool calling, schémas |

> RÈGLE ABSOLUE : Un seul modèle est chargé en VRAM à la fois. Ollama gère l'unload automatiquement, mais le sélecteur de modèle de Jarvis doit anticiper cela.

### 2.2 CPU & RAM

- **Faster-Whisper** tourne exclusivement sur CPU (modèle `small` ou `medium`). Il est exécuté dans un **thread dédié** pour ne pas bloquer l'UI.
- **Piper TTS** tourne sur CPU. La génération audio est streamed (chunk par chunk) pour minimiser la latence perçue.
- **ChromaDB / SQLite** : Opérations I/O sur disque, pas de contrainte majeure.

### 2.3 Stratégie de Priorité des Ressources

```
Priorité 1 (VRAM)   : Modèle Ollama actif
Priorité 2 (CPU)    : Piper TTS (bloquant pour l'utilisateur)
Priorité 3 (CPU)    : Faster-Whisper (background thread)
Priorité 4 (CPU)    : Interface PyQt6 / Chromium (QtWebEngine)
Priorité 5 (Disque) : ChromaDB, SQLite, logs
```

---

## 3. Choix Techniques (Stack)

### 3.1 Application Desktop

| Composant | Technologie | Justification |
|---|---|---|
| **Framework UI** | `PyQt6` | Maturité, contrôle fin, support natif Windows |
| **Moteur Web intégré** | `PyQt6-WebEngine` (Chromium) | Exécute JS, supporte Mermaid.js, Leaflet.js, animations CSS avancées |
| **Communication UI <-> Python** | `QWebChannel` + `PyQt6.QtWebChannel` | Bridge JS <-> Python bidirectionnel, temps-réel |
| **Rendu HTML/CSS/JS** | Vanilla HTML5 + CSS3 + JS (ES6+) | Contrôle total, pas de dépendance framework inutile |

### 3.2 Intelligence Artificielle

| Composant | Technologie | Version / Modèle |
|---|---|---|
| **Backend LLM** | Ollama | Dernière version stable |
| **Modèle Vocal (rapide)** | `llama3.2:3b` | Interactions courtes, commandes vocales |
| **Modèle Avancé (complexe)** | `qwen2.5:7b` | Code, tool calling, diagrammes, raisonnement |
| **Client Python Ollama** | `ollama` (lib officielle) | Stream natif, async compatible |

### 3.3 Audio

| Composant | Technologie | Justification |
|---|---|---|
| **Reconnaissance Vocale (STT)** | `faster-whisper` | 4x plus rapide que Whisper original, CPU-optimized |
| **Modèle Whisper** | `small` ou `medium` | Balance vitesse / précision sur CPU |
| **Capture Microphone** | `sounddevice` + `numpy` | Faible latence, VAD (Voice Activity Detection) |
| **Synthèse Vocale (TTS)** | `piper-tts` | Ultra-rapide, 100% offline, voix naturelles |
| **Playback Audio** | `sounddevice` | Cohérence avec la capture |

### 3.4 Mémoire & Persistance

| Composant | Technologie | Usage |
|---|---|---|
| **Mémoire Court-terme** | Liste Python en RAM | Historique de la session en cours (dernier N tours) |
| **Mémoire Long-terme** | `ChromaDB` | Embeddings vectoriels des conversations passées |
| **Base de données structurée** | `SQLite` (via `sqlite3`) | Historique complet, préférences, profil utilisateur |
| **Embeddings locaux** | `sentence-transformers` (all-MiniLM-L6-v2) | Génération d'embeddings sur CPU, ~90 Mo |

### 3.5 Dépendances Python (requirements.txt prévisionnel)

```txt
# Core UI
PyQt6>=6.6.0
PyQt6-WebEngine>=6.6.0
PyQt6-Qt6>=6.6.0

# LLM
ollama>=0.3.0

# STT
faster-whisper>=1.0.0
sounddevice>=0.4.6
numpy>=1.24.0

# TTS
piper-tts>=1.2.0

# Memory
chromadb>=0.5.0
sentence-transformers>=3.0.0

# Utils
python-dotenv>=1.0.0
pydantic>=2.0.0
aiofiles>=23.0.0
```

---

## 4. Architecture Globale du Système

```
+------------------------------------------------------------------+
|                    JARVIS DESKTOP APPLICATION                    |
|                                                                  |
|  +------------------------------------------------------------+  |
|  |                    PyQt6 Main Window                       |  |
|  |                                                            |  |
|  |   +---------------------------------------------------------+  |
|  |   |          QWebEngineView (Chromium)                    |  |
|  |   |                                                       |  |
|  |   |  +--------------+  +----------------------------+    |  |
|  |   |  |  HUD Panel   |  |   Dynamic Content Panel    |    |  |
|  |   |  |  (chat UI)   |  |  (Mermaid / Leaflet / ...) |    |  |
|  |   |  +--------------+  +----------------------------+    |  |
|  |   |                                                       |  |
|  |   |  JavaScript <------ QWebChannel ------> Python       |  |
|  |   +---------------------------------------------------------+  |
|  |                                                            |  |
|  |  +----------+  +-------------+  +------------------+     |  |
|  |  |AudioThread|  | LLMManager  |  |  MemoryManager   |     |  |
|  |  | STT + TTS |  |  (Ollama)   |  | Chroma + SQLite  |     |  |
|  |  +----------+  +-------------+  +------------------+     |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  |                   Ollama Daemon (local)                    |  |
|  |            llama3.2:3b  |  qwen2.5:7b                     |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

### 4.1 Flux de Données — Interaction Vocale

```
[Microphone]
     |
     v
[sounddevice] --> [VAD] --> [Faster-Whisper] --> [Texte transcrit]
                                                          |
                                                          v
                                               [MemoryManager.get_context()]
                                                          |
                                                          v
                                               [LLMManager.stream(prompt)]
                                               (modele: llama3.2:3b)
                                                          |
                                          +--------------+|
                                          v               v
                                  [QWebChannel]    [Piper TTS]
                                  (affichage UI)   (audio output)
```

### 4.2 Flux de Données — Tâche Complexe (code/schema)

```
[Input texte / voix]
     |
     v
[LLMManager.stream(prompt, model="qwen2.5:7b")]
     |
     v
[ResponseParser] --> detecte balises speciales
     |
     +--> <mermaid>...</mermaid>  --> JS: renderMermaid()
     +--> <map>JSON</map>         --> JS: renderLeaflet()
     +--> <code lang="...">       --> JS: renderCode() avec syntax highlight
     +--> texte brut              --> JS: appendMessage()
```

---

## 5. Structure des Dossiers

```
PROJET JARVIS/
|
+-- contexte_projet.md          <- CE FICHIER (feuille de contexte)
|
+-- main.py                     <- Point d'entrée de l'application
+-- requirements.txt            <- Dépendances Python
+-- .env                        <- Variables d'environnement (chemins, configs)
+-- .gitignore
|
+-- config/
|   +-- settings.py             <- Classe de configuration centralisée
|   +-- system_prompt.txt       <- System prompt de Jarvis (modifiable)
|   +-- models.json             <- Définition des modèles et leurs capacités
|
+-- core/
|   +-- __init__.py
|   +-- app.py                  <- Classe principale PyQt6 Application
|   +-- window.py               <- Fenêtre principale (MainWindow)
|   +-- bridge.py               <- QWebChannel bridge JS <-> Python
|
+-- ai/
|   +-- __init__.py
|   +-- llm_manager.py          <- Gestion Ollama, sélection modèle, streaming
|   +-- response_parser.py      <- Détection et extraction des balises spéciales
|   +-- tool_manager.py         <- Définition et dispatch des tools (function calling)
|
+-- audio/
|   +-- __init__.py
|   +-- audio_thread.py         <- Thread dédié audio (QThread)
|   +-- stt.py                  <- Faster-Whisper STT wrapper
|   +-- tts.py                  <- Piper TTS wrapper
|   +-- vad.py                  <- Voice Activity Detection
|
+-- memory/
|   +-- __init__.py
|   +-- memory_manager.py       <- Orchestrateur mémoire (court + long terme)
|   +-- short_term.py           <- Buffer de conversation en RAM
|   +-- long_term.py            <- ChromaDB vector store
|   +-- database.py             <- SQLite : historique complet + profil user
|
+-- ui/
|   +-- web/                    <- Interface HTML/CSS/JS servie dans QtWebEngine
|   |   +-- index.html          <- Page principale du HUD
|   |   +-- css/
|   |   |   +-- main.css        <- Design system, variables CSS, thème sombre
|   |   |   +-- components.css  <- Composants UI (chat, boutons, panels)
|   |   |   +-- animations.css  <- Animations et transitions
|   |   +-- js/
|   |   |   +-- main.js         <- Point d'entrée JS, init QWebChannel
|   |   |   +-- bridge.js       <- Fonctions de communication avec Python
|   |   |   +-- chat.js         <- Gestion du chat (affichage messages, stream)
|   |   |   +-- renderer.js     <- Rendu dynamique (Mermaid, Leaflet, code)
|   |   |   +-- ui.js           <- Interactions UI (boutons, animations)
|   |   +-- assets/
|   |       +-- fonts/
|   |       +-- icons/
|   |       +-- libs/           <- Toutes les librairies JS (LOCAL, AUCUN CDN)
|   |           +-- mermaid.min.js
|   |           +-- leaflet.js
|   |           +-- marked.min.js
|   |           +-- highlight.min.js
|   +-- widgets/
|       +-- system_tray.py
|
+-- tools/                      <- Modules de tools appelables par l'IA
|   +-- __init__.py
|   +-- base_tool.py            <- Classe abstraite BaseTool (interface commune)
|   +-- file_system.py          <- Lecture/écriture/suppression de fichiers locaux
|   +-- web_search.py           <- Recherche web (future extension)
|   +-- system_info.py          <- Infos système (CPU, RAM, GPU)
|   +-- email_sender.py         <- Envoi d'e-mails via SMTP (Gmail, Outlook, local)
|   +-- app_controller.py       <- Ouverture/fermeture d'applications Windows
|   +-- shell_executor.py       <- Exécution de commandes shell (liste blanche)
|   +-- task_scheduler.py       <- Création de tâches planifiées Windows
|
+-- data/
|   +-- chromadb/               <- Base vectorielle ChromaDB (auto-généré)
|   +-- jarvis.db               <- Base SQLite (auto-générée)
|   +-- piper_models/           <- Modèles voix Piper téléchargés
|
+-- logs/
    +-- jarvis.log              <- Logs applicatifs rotatifs
```

---

## 6. Architecture de la Mémoire IA

Jarvis implémente un système de mémoire à **trois niveaux**, inspiré des architectures cognitives humaines.

### 6.1 Niveau 1 — Mémoire de Contexte (Court-terme, session)

- **Support** : Liste Python en RAM (`deque` avec `maxlen`)
- **Contenu** : Les N derniers échanges (user + assistant) de la session courante
- **TTL** : Session uniquement. Perdue à la fermeture.
- **Taille recommandée** : 20 derniers tours (40 messages)
- **Usage** : Injectée directement dans le prompt Ollama à chaque requête

```python
# Exemple de structure
short_term_memory = deque([
    {"role": "user",      "content": "Bonjour Jarvis"},
    {"role": "assistant", "content": "Bonjour ! Comment puis-je vous aider ?"},
    # ...
], maxlen=40)
```

### 6.2 Niveau 2 — Mémoire Épisodique (Long-terme, vectorielle)

- **Support** : ChromaDB (base vectorielle locale, fichiers sur disque)
- **Contenu** : Résumés de conversations passées, faits importants, embeddings
- **Modèle d'embedding** : `sentence-transformers/all-MiniLM-L6-v2` (~90 Mo, CPU)
- **Stratégie** : À la fin de chaque session, un résumé est généré par l'IA et stocké
- **Récupération** : RAG (Retrieval-Augmented Generation) — top-K résultats par similarité cosinus injectés dans le prompt

```python
# Flux de stockage (fin de session)
summary = llm.summarize(short_term_memory)
embedding = embedder.encode(summary)
chromadb.add(document=summary, embedding=embedding, metadata={"date": ..., "topics": [...]})

# Flux de récupération (début de requête)
relevant_memories = chromadb.query(query_embedding, n_results=3)
context = build_prompt(relevant_memories, short_term_memory, user_input)
```

### 6.3 Niveau 3 — Mémoire Déclarative (Structurée, SQLite)

- **Support** : SQLite via `sqlite3`
- **Contenu** : Historique complet non modifié, profil utilisateur, préférences

```sql
-- Tables principales
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    timestamp DATETIME,
    role TEXT,           -- 'user' | 'assistant'
    content TEXT,
    model_used TEXT,
    tokens_used INTEGER
);

CREATE TABLE user_profile (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME
);

CREATE TABLE memories (
    id INTEGER PRIMARY KEY,
    summary TEXT,
    chroma_id TEXT,      -- référence vers ChromaDB
    session_date DATE,
    topics TEXT          -- JSON array de topics
);
```

### 6.4 Construction du Prompt Final

```
[SYSTEM PROMPT]          <- config/system_prompt.txt
[PROFIL UTILISATEUR]     <- SQLite user_profile (nom, préférences)
[MÉMOIRES PERTINENTES]   <- Top-3 ChromaDB (résumés des sessions passées)
[HISTORIQUE RÉCENT]      <- Short-term memory (20 derniers tours)
[MESSAGE UTILISATEUR]    <- Input courant
```

---

## 7. Protocole de Communication Interne

### 7.1 Bridge Python <-> JavaScript (QWebChannel)

Le bridge est l'épine dorsale de la communication entre le backend Python et le frontend JS dans le WebEngine.

**Python -> JS** (appels Python vers l'interface) :
```python
self.bridge.send_token.emit("token_text")           # streaming token par token
self.bridge.send_message_complete.emit(full_text)   # message complet
self.bridge.send_render_directive.emit("mermaid", diagram_code)
self.bridge.update_status.emit("thinking")          # état de l'IA
```

**JS -> Python** (actions utilisateur) :
```javascript
jarvis.send_user_message(text);      // envoyer un message texte
jarvis.toggle_voice_input();         // activer/désactiver micro
jarvis.change_model("qwen2.5:7b");  // changer de modèle
jarvis.clear_context();              // vider le contexte
```

### 7.2 Signaux PyQt6

```python
# AudioThread -> MainController
stt_transcription_ready = pyqtSignal(str)
tts_playback_started    = pyqtSignal()
tts_playback_finished   = pyqtSignal()

# LLMManager -> MainController
llm_token_received      = pyqtSignal(str)
llm_response_complete   = pyqtSignal(str)
llm_error               = pyqtSignal(str)

# MainController -> Bridge -> JS
bridge_send_token       = pyqtSignal(str)
bridge_send_directive   = pyqtSignal(str, str)
```

---

## 8. Rendu Dynamique & Balises Spéciales

### 8.1 Balise `<mermaid>` — Diagrammes

Syntaxe dans la réponse IA :
```
<mermaid>
graph TD
    A[Début] --> B{Condition}
    B -->|Oui| C[Résultat 1]
    B -->|Non| D[Résultat 2]
</mermaid>
```
Rendu : Mermaid.js (local) génère un SVG interactif inline.

### 8.2 Balise `<map>` — Cartes Géographiques

Syntaxe dans la réponse IA :
```
<map>
{
  "center": [48.8566, 2.3522],
  "zoom": 12,
  "markers": [
    {"lat": 48.8566, "lng": 2.3522, "label": "Paris Centre"},
    {"lat": 48.8738, "lng": 2.2950, "label": "Tour Eiffel"}
  ]
}
</map>
```
Rendu : Leaflet.js (local) affiche une carte interactive.

### 8.3 Blocs de Code

Syntaxe : Markdown standard ```python etc.
Rendu : Highlight.js (local) + bouton "Copier" auto-généré.

### 8.4 Texte Brut / Markdown

Tout texte hors balises spéciales est rendu via `marked.js` (local).

### 8.5 Bibliothèques JS (toutes locales, aucun CDN)

| Bibliothèque | Fichier local | Usage |
|---|---|---|
| `mermaid.js` | `ui/web/assets/libs/mermaid.min.js` | Diagrammes |
| `leaflet.js` | `ui/web/assets/libs/leaflet.js` | Cartes |
| `marked.js` | `ui/web/assets/libs/marked.min.js` | Markdown |
| `highlight.js` | `ui/web/assets/libs/highlight.min.js` | Colorisation code |

---

## 9. Système d'Actions PC Cadré (Agentic Layer)

Jarvis peut exécuter des actions réelles sur le PC de l'utilisateur. Ce système repose sur un **modèle de permissions strict** pour garantir la sécurité et la confiance.

### 9.1 Philosophie de Sécurité

Le principe fondateur de l'agentic layer est : **"Jarvis propose, l'utilisateur dispose"**.

| Niveau de risque | Exemples | Comportement |
|---|---|---|
| **SAFE** (risque nul) | Lire un fichier, afficher l'heure, ouvrir une app | Exécution directe, pas de confirmation |
| **MODERATE** (risque faible) | Créer un fichier, ouvrir un email, lancer un script | Aperçu affiché dans le HUD + bouton "Confirmer" |
| **SENSITIVE** (risque élevé) | Envoyer un email, supprimer un fichier, modifier le registre | Confirmation obligatoire + résumé clair de l'action |
| **BLOCKED** (interdit) | Accès à des chemins système critiques, exécution de code arbitraire | Refus systématique, non configurable |

### 9.2 Flux d'une Action PC

```
[Utilisateur] : "Envoie un mail à Jean pour reporter le meeting"
     |
     v
[LLM - qwen2.5:7b] -> génère un tool call JSON :
{
  "tool": "email_sender",
  "params": {
    "to": "jean@example.com",
    "subject": "Report du meeting",
    "body": "Bonjour Jean, je dois reporter notre meeting..."
  }
}
     |
     v
[ActionManager.validate(tool_call)]
     |
     +--> Niveau SENSITIVE détecté
     |
     v
[Bridge -> JS] : affiche une "Action Card" dans le HUD
+------------------------------------------+
| JARVIS souhaite effectuer l'action :      |
| Envoyer un e-mail                         |
| A : jean@example.com                      |
| Sujet : Report du meeting                 |
| [VOIR LE CORPS DU MAIL] [MODIFIER]        |
|           [ANNULER]  [CONFIRMER]          |
+------------------------------------------+
     |
     +--> [Confirmer] -> [EmailSender.execute()] -> Succes/Erreur -> HUD
     +--> [Annuler]   -> Action abandonnée, message dans le chat
```

### 9.3 Catalogue des Actions Disponibles

#### 9.3.1 Gestion des E-mails (`email_sender.py`)

- **Protocoles supportés** : SMTP (Gmail App Password, Outlook, serveur SMTP local)
- **Actions** : Composer, prévisualiser, envoyer
- **Configuration** : Credentials stockés dans `.env` (jamais hardcodés dans le code)
- **Niveau de risque** : SENSITIVE (confirmation obligatoire)

```python
# Exemple de tool definition pour Ollama function calling
email_tool = {
    "type": "function",
    "function": {
        "name": "send_email",
        "description": "Envoie un e-mail au nom de l'utilisateur",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Adresse email du destinataire"},
                "subject": {"type": "string", "description": "Objet du mail"},
                "body": {"type": "string", "description": "Corps du mail en texte brut ou HTML"}
            },
            "required": ["to", "subject", "body"]
        }
    }
}
```

#### 9.3.2 Gestion des Fichiers (`file_system.py`)

- **Actions SAFE** : `read_file`, `list_directory`, `get_file_info`
- **Actions MODERATE** : `create_file`, `create_directory`, `write_file`
- **Actions SENSITIVE** : `delete_file`, `move_file`
- **Chemins BLOQUÉS** : `C:\Windows\*`, `C:\System32\*`, fichiers `.exe`, `.dll`, `.sys`
- **Racine par défaut** : `%USERPROFILE%` (personnalisable dans config)

#### 9.3.3 Exécution Shell (`shell_executor.py`)

- **Mode** : Liste blanche de commandes autorisées, définie dans `config/allowed_commands.json`
- **Niveau de risque** : MODERATE à SENSITIVE selon la commande
- **Exemples autorisés** : `ipconfig`, `ping`, `dir`, `python`, `git status`
- **Toujours bloqués** : `rm -rf`, `format`, `del /f /s /q`, `reg delete`, toute commande avec `| curl`, `| wget`
- **Timeout** : 30 secondes max par commande
- **Isolation** : Exécution dans un subprocess avec capture stdout/stderr

```json
// config/allowed_commands.json (exemple)
{
  "whitelist": [
    {"cmd": "ipconfig", "risk": "SAFE"},
    {"cmd": "ping", "risk": "SAFE"},
    {"cmd": "git", "risk": "MODERATE"},
    {"cmd": "python", "risk": "MODERATE"},
    {"cmd": "npm", "risk": "MODERATE"}
  ]
}
```

#### 9.3.4 Contrôle d'Applications (`app_controller.py`)

- **Actions** : Ouvrir une application par nom, fermer une application
- **Niveau de risque** : SAFE pour l'ouverture, MODERATE pour la fermeture
- **Mapping configurable** : `config/apps.json` associe les noms naturels aux executables

```json
// config/apps.json (exemple)
{
  "chrome": "chrome.exe",
  "vscode": "code.exe",
  "notepad": "notepad.exe",
  "explorateur": "explorer.exe"
}
```

#### 9.3.5 Planificateur de Tâches (`task_scheduler.py`)

- **Backend** : Windows Task Scheduler (via `schtasks` ou bibliothèque `win32api`)
- **Actions** : Créer un rappel, lister les tâches Jarvis, supprimer une tâche
- **Niveau de risque** : MODERATE
- **Format** : L'IA génère une description en langage naturel, Jarvis la convertit en tâche planifiée

### 9.4 Système de Permissions (config/permissions.json)

L'utilisateur contrôle finement ce que Jarvis peut faire via un fichier de config et un panneau UI :

```json
// config/permissions.json
{
  "email": {
    "enabled": true,
    "require_confirmation": true,
    "smtp_profile": "gmail"
  },
  "file_system": {
    "enabled": true,
    "allowed_roots": ["C:\\Users\\leoma\\Documents", "C:\\Users\\leoma\\Desktop"],
    "require_confirmation_on_delete": true
  },
  "shell": {
    "enabled": false,
    "whitelist_file": "config/allowed_commands.json"
  },
  "app_control": {
    "enabled": true,
    "apps_config": "config/apps.json"
  },
  "task_scheduler": {
    "enabled": true,
    "require_confirmation": true
  }
}
```

### 9.5 Nouveaux Signaux PyQt6 pour les Actions

```python
# ActionManager -> Bridge -> JS
action_requires_confirmation = pyqtSignal(dict)   # affiche l'Action Card
action_executed_success      = pyqtSignal(str)     # feedback succès
action_executed_error        = pyqtSignal(str)     # feedback erreur
action_cancelled             = pyqtSignal(str)     # action annulée par l'user

# JS -> ActionManager (depuis l'Action Card)
jsbridge.confirm_action(action_id)   # utilisateur confirme
jsbridge.cancel_action(action_id)    # utilisateur annule
jsbridge.edit_action(action_id, new_params)  # utilisateur modifie les params
```

### 9.6 Variables d'Environnement — Actions PC (.env)

```env
# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votre.email@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # App Password Gmail, jamais le mot de passe principal
SMTP_FROM_NAME=Jarvis

# File System
FS_ALLOWED_ROOTS=C:\Users\leoma\Documents;C:\Users\leoma\Desktop
FS_MAX_FILE_SIZE_MB=50

# Shell
SHELL_TIMEOUT_SECONDS=30
SHELL_ENABLED=false

# Permissions
PERMISSIONS_CONFIG=config/permissions.json
```

---

## 10. Plan de Développement — Étapes 1 à 6

### Étape 1 — Fondations & Squelette de l'Application
**Objectif** : Application qui démarre, affiche une fenêtre HUD, et prouve que le bridge fonctionne.

**Livrables** :
- [ ] `main.py` : Point d'entrée, init PyQt6 Application
- [ ] `core/app.py` : Classe Application
- [ ] `core/window.py` : MainWindow avec QWebEngineView plein écran
- [ ] `core/bridge.py` : QWebChannel setup, signaux de base
- [ ] `ui/web/index.html` : Page HUD de base (sans fonctionnalités)
- [ ] `ui/web/css/main.css` : Design system complet (thème sombre, variables CSS)
- [ ] `config/settings.py` : Configuration centralisée
- [ ] **Test** : Python envoie "Hello World" -> JS l'affiche dans le HUD

---

### Étape 2 — Intégration LLM & Chat Textuel
**Objectif** : Chat textuel fonctionnel avec streaming Ollama.

**Livrables** :
- [ ] `ai/llm_manager.py` : Client Ollama, streaming, sélection de modèle
- [ ] `ai/response_parser.py` : Détection des balises spéciales (regex)
- [ ] `config/system_prompt.txt` : System prompt Jarvis initial
- [ ] `config/models.json` : Config des modèles disponibles
- [ ] `ui/web/js/chat.js` : Affichage des messages, streaming token par token
- [ ] `ui/web/js/bridge.js` : Fonctions JS d'appel Python
- [ ] `memory/short_term.py` : Buffer de contexte court-terme
- [ ] **Test** : Saisir un message texte -> réponse streamée token par token dans le HUD

---

### Étape 3 — Mémoire Persistante
**Objectif** : Jarvis se souvient entre les sessions.

**Livrables** :
- [ ] `memory/database.py` : SQLite schema, fonctions CRUD
- [ ] `memory/long_term.py` : ChromaDB init, add, query
- [ ] `memory/memory_manager.py` : Orchestrateur, construction du prompt complet
- [ ] Logique de résumé de session (appel LLM à la fermeture)
- [ ] **Test** : Dire "Je m'appelle Léo" -> fermer -> rouvrir -> demander "Comment je m'appelle ?" -> Jarvis répond correctement

---

### Étape 4 — Audio (STT + TTS)
**Objectif** : Interactions vocales complètes.

**Livrables** :
- [ ] `audio/vad.py` : Voice Activity Detection
- [ ] `audio/stt.py` : Wrapper Faster-Whisper (modèle `small`, compute_type="int8")
- [ ] `audio/tts.py` : Wrapper Piper TTS (voix FR ou EN selon config)
- [ ] `audio/audio_thread.py` : QThread dédié, gestion états (listening/speaking/idle)
- [ ] Intégration dans le bridge (bouton micro dans l'UI)
- [ ] Bouton push-to-talk ET mode VAD continu (configurable)
- [ ] **Test** : Parler -> transcription -> réponse IA -> lecture vocale de la réponse

---

### Étape 5 — Rendu Dynamique & Outils IA
**Objectif** : Visualisations dynamiques et tool calling.

**Livrables** :
- [ ] `ui/web/js/renderer.js` : Moteur de rendu (Mermaid, Leaflet, Highlight.js)
- [ ] Téléchargement et intégration locale de toutes les libs JS
- [ ] `ai/tool_manager.py` : Définition des tools, dispatch function calling
- [ ] `tools/file_system.py` : Tool lecture/écriture fichiers
- [ ] `tools/system_info.py` : Tool infos système
- [ ] **Test** : Demander "Fais-moi un diagramme de flux" -> Mermaid s'affiche
- [ ] **Test** : Demander "Montre Paris sur une carte" -> Leaflet s'affiche

---

### Étape 6 — Actions PC & Agentic Layer
**Objectif** : Jarvis peut agir sur le PC de manière sécurisée et cadrée.

**Livrables** :
- [ ] `tools/base_tool.py` : Classe abstraite `BaseTool` avec interface commune (nom, description, risk_level, execute)
- [ ] `ai/action_manager.py` : Orchestrateur d'actions — reçoit les tool calls LLM, valide les permissions, déclenche la confirmation UI
- [ ] `tools/email_sender.py` : Envoi SMTP avec preview HTML dans le HUD
- [ ] `tools/file_system.py` : CRUD fichiers avec filtrage des chemins interdits
- [ ] `tools/shell_executor.py` : Shell restreint avec liste blanche
- [ ] `tools/app_controller.py` : Ouverture/fermeture d'apps Windows
- [ ] `tools/task_scheduler.py` : Tâches planifiées Windows
- [ ] `ui/web/js/action_card.js` : Composant JS "Action Card" (prévisualisation + boutons Confirmer/Modifier/Annuler)
- [ ] `config/permissions.json` : Fichier de permissions par défaut
- [ ] `config/allowed_commands.json` : Liste blanche des commandes shell autorisées
- [ ] `config/apps.json` : Mapping noms naturels -> executables
- [ ] Panneau de gestion des permissions dans l'UI (activer/désactiver chaque catégorie)
- [ ] **Test** : Dire "Envoie un mail à jean@example.com pour le meeting" -> Action Card apparaît -> Confirmer -> Mail envoyé
- [ ] **Test** : Dire "Ouvre Chrome" -> Chrome s'ouvre sans confirmation (action SAFE)
- [ ] **Test** : Dire "Supprime le fichier test.txt sur le Bureau" -> Confirmation demandée avant suppression

---

## 11. Règles de Développement & Conventions

### 10.1 Règles Générales

1. **Lire ce fichier avant tout** — Toujours consulter `contexte_projet.md` avant de coder.
2. **Pas de CDN** — Toutes les librairies JS sont dans `ui/web/assets/libs/`.
3. **Un modèle à la fois** — Ne jamais charger deux modèles Ollama simultanément.
4. **Threads séparés** — Audio (STT+TTS) et LLM tournent dans des QThreads dédiés. Jamais dans le thread principal.
5. **Signaux PyQt6** — La communication cross-thread se fait UNIQUEMENT via des signaux PyQt6.
6. **Configuration centralisée** — Toutes les constantes dans `config/settings.py`. Jamais de "magic strings".
7. **Logging** — Utiliser le module `logging` Python partout. Niveau DEBUG en dev, INFO en prod.
8. **Sécurité actions PC** — Tout tool qui modifie l'état du système (fichier, email, shell) DOIT passer par `ActionManager.validate()`. Aucun tool ne s'exécute directement sans validation.
9. **Jamais de credentials dans le code** — Les informations SMTP, mots de passe, tokens sont UNIQUEMENT dans `.env`. Le `.env` est dans `.gitignore`.
10. **Liste blanche, pas liste noire** — Pour le shell et les chemins fichiers, on autorise une liste restreinte d'actions connues et sûres. On ne tente pas de bloquer tous les cas dangereux (approche fragile).

### 10.2 Conventions de Nommage

| Élément | Convention | Exemple |
|---|---|---|
| Classes Python | `PascalCase` | `LLMManager`, `AudioThread` |
| Fonctions/méthodes Python | `snake_case` | `get_context()`, `send_token()` |
| Signaux PyQt6 | `snake_case` | `token_received`, `stt_ready` |
| Fichiers Python | `snake_case` | `llm_manager.py`, `audio_thread.py` |
| Variables JS | `camelCase` | `chatContainer`, `renderMermaid` |
| Classes CSS | `kebab-case` | `.message-bubble`, `.hud-panel` |
| Variables CSS | `--kebab-case` | `--color-accent`, `--font-primary` |

### 10.3 Style de Code Python

- **Python 3.11+** minimum
- **Type hints** obligatoires sur toutes les fonctions publiques
- **Docstrings** sur les classes et méthodes publiques
- Préférer `async/await` pour les appels Ollama (via `asyncio`)
- Limiter les fichiers à 300 lignes max

### 10.4 Variables d'Environnement (.env)

```env
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_FAST=llama3.2:3b
OLLAMA_MODEL_ADVANCED=qwen2.5:7b

# Audio
WHISPER_MODEL_SIZE=small
WHISPER_COMPUTE_TYPE=int8
PIPER_MODEL_PATH=data/piper_models/fr_FR-upmc-medium.onnx
AUDIO_SAMPLE_RATE=16000
VAD_THRESHOLD=0.5

# Memory
CHROMA_DB_PATH=data/chromadb
SQLITE_DB_PATH=data/jarvis.db
SHORT_TERM_MAX_TURNS=20

# App
APP_LOG_LEVEL=DEBUG
APP_THEME=dark
```

---

*Document créé le 2026-08-18 — Dernière mise à jour : 2026-08-18 (v1.1 — Ajout Agentic Layer)*
*Architecte : Antigravity (Google DeepMind)*
*Ce document est la référence canonique du projet Jarvis. Toute décision technique doit être cohérente avec ce document.*
