# JARVIS — Just A Rather Very Intelligent System

> **Assistant IA de bureau 100% local, autonome, vocal et agentique pour Windows.**  
> Conçu pour fonctionner hors ligne sans aucune dépendance vers des API cloud externes, avec une interface HUD cyberpunk immersive, une mémoire cognitive persistante et un contrôle sécurisé du système d'exploitation.

---

![Plateforme](https://img.shields.io/badge/Plateforme-Windows%2010%20%7C%2011-blue?style=for-the-badge&logo=windows)
![Python](https://img.shields.io/badge/Python-3.11%2B-brightgreen?style=for-the-badge&logo=python)
![PyQt6](https://img.shields.io/badge/UI-PyQt6%20%2B%20WebEngine-darkblue?style=for-the-badge&logo=qt)
![Ollama](https://img.shields.io/badge/LLM-Ollama%20(Local)-orange?style=for-the-badge&logo=ollama)
![Sécurité](https://img.shields.io/badge/Confidentialité-100%25%20Local%20%2F%20Offline-red?style=for-the-badge)

---

## 📑 Table des Matières

1. [Vision & Philosophie](#-vision--philosophie)
2. [Matériel Cible & Optimisations](#-matériel-cible--optimisations)
3. [Tout ce que JARVIS sait faire (Fonctionnalités Détaillées)](#-tout-ce-que-jarvis-sait-faire)
   - [1. Dialogue & Raisonnement Local (LLM)](#1-dialogue--raisonnement-local-llm)
   - [2. Interaction Vocale Complète (STT & TTS)](#2-interaction-vocale-complète-stt--tts)
   - [3. Système de Mémoire Cognitive à 3 Niveaux](#3-système-de-mémoire-cognitive-à-3-niveaux)
   - [4. Interface Graphique HUD Futuriste](#4-interface-graphique-hud-futuriste)
   - [5. Moteur de Rendu Dynamique](#5-moteur-de-rendu-dynamique)
   - [6. Couche Agentique & Actions PC Sécurisées](#6-couche-agentique--actions-pc-sécurisées)
4. [Architecture Technique & Flux de Données](#-architecture-technique--flux-de-données)
5. [Structure du Projet](#-structure-du-projet)
6. [Installation & Démarrage](#-installation--démarrage)
7. [Configuration (.env)](#-configuration-env)
8. [Raccourcis & Utilisation](#-raccourcis--utilisation)
9. [Feuille de Route (Roadmap Étapes 1 à 6)](#-feuille-de-route-roadmap)

---

## 🌟 Vision & Philosophie

JARVIS est conçu comme un véritable **copilote personnel autonome**, inspiré de la science-fiction mais ancré dans une architecture logicielle moderne, robuste et strictement locale.

* **🛡️ 100% Local & Privé** : Aucune donnée, aucune frappe de clavier, aucun enregistrement vocal ni aucun fichier n'est envoyé vers des serveurs tiers ou des API cloud.
* **⚡ Latence Minimale** : Réponses vocales et écrites en temps réel grâce au streaming natif des tokens et à la synthèse audio par morceaux.
* **🧠 Continuité Cognitive** : JARVIS ne repart pas de zéro à chaque session ; il retient qui vous êtes, vos préférences et le contexte de vos projets passés.
* **🔒 Action Sécurisée ("L'IA propose, l'utilisateur dispose")** : JARVIS peut interagir avec le système d'exploitation Windows (applications, fichiers, scripts, emails), mais toute action potentiellement sensible requiert une confirmation visuelle explicite via une *Action Card*.
* **🎭 Identité & Persona** : Poli, concis, direct, doué d'un humour pince-sans-rire occasionnel, appelant son utilisateur *"Monsieur Masoyé"*, sans jamais mentionner qu'il est un LLM ou un script.

---

## 💻 Matériel Cible & Optimisations

Le projet est calibré pour offrir des performances maximales sur une machine grand public performante :

* **GPU cible** : NVIDIA GeForce RTX 3060 (6 Go VRAM) ou équivalent.
* **CPU & RAM** : Processeur multi-cœurs (Intel/AMD) + 16 Go de RAM minimum.
* **Gestion stricte de la VRAM (Règle d'or)** : Un seul modèle de langage est chargé en mémoire graphique à la fois.
  * **Modèle Rapide** : `llama3.2:latest` (3B) ~ 2.5 Go VRAM (dialogue instantané, commandes rapides).
  * **Modèle Avancé** : `qwen2.5:latest` (7B) ~ 5.0 Go VRAM (code, raisonnement poussé, outils, diagrammes).
* **Décharge CPU** : La transcription audio (`Faster-Whisper` en `int8`), la synthèse vocale (`Piper`) et les calculs d'embeddings vectoriels (`sentence-transformers`) s'exécutent sur CPU pour préserver l'intégralité de la VRAM pour le LLM.

---

## 🎯 Tout ce que JARVIS sait faire

### 1. Dialogue & Raisonnement Local (LLM)

* **Streaming temps-réel** : Affichage fluide des réponses mot par mot dans l'interface sans temps de blocage.
* **Routage intelligent des modèles** :
  * Mode **AUTO** : Sélectionne automatiquement le modèle rapide pour les discussions simples ou le modèle avancé pour les tâches complexes.
  * Basculement manuel possible à tout instant via un badge cliquable dans le HUD.
* **Préchargement en mémoire** : Démarrage en tâche de fond du modèle dès le lancement pour éliminer le délai de première réponse.
* **Respect strict des faits** : Le système prompt interdit d'inventer des informations non vérifiées ; lorsqu'un doute subsiste, JARVIS déclenche automatiquement un outil de recherche ou avoue sobrement son ignorance.

---

### 2. Interaction Vocale Complète (STT & TTS)

* **Reconnaissance vocale (STT - Speech-to-Text)** :
  * Propulsée par `Faster-Whisper` (modèle `small` quantifié en `int8`).
  * 4x plus rapide que Whisper standard, s'exécute dans un thread d'arrière-plan sans figer l'interface.
  * Détection d'activité vocale (VAD) via `sounddevice` et `numpy` pour filtrer les silences.
* **Synthèse vocale neuronale (TTS - Text-to-Speech)** :
  * Propulsée par `Piper-TTS` avec voix française naturelle (`fr_FR-upmc-medium`).
  * Génération quasi-instantanée sur CPU.
  * Lecture vocale automatique des réponses générées par JARVIS.
* **Bouton Micro interactif** : Activation / désactivation d'un clic dans la barre inférieure du HUD.

---

### 3. Système de Mémoire Cognitive à 3 Niveaux

JARVIS intègre une architecture cognitive inspirée du cerveau humain pour assurer un apprentissage continu sans saturer la fenêtre de contexte :

```
┌─────────────────────────────────────────────────────────────┐
│                      PROMPT ASSEMBLE                        │
│  [System Prompt + Persona]                                  │
│  + [Profil Utilisateur & Préférences] (SQLite)              │
│  + [Souvenirs Pertinents RAG] (ChromaDB - Top-3 K-NN)       │
│  + [Buffer de Session en cours] (RAM - Derniers 20 tours)   │
│  + [Message Courant de l'Utilisateur]                       │
└─────────────────────────────────────────────────────────────┘
```

1. **Mémoire de Contexte (Court-terme - RAM)** :
   * Buffer circulaire conservant les 20 derniers échanges (40 messages).
   * Réponse directe et contextualisée au cours de la session active.
2. **Mémoire Épisodique (Long-terme - ChromaDB)** :
   * Base de données vectorielle locale (`data/chromadb`).
   * À la fermeture de l'application, JARVIS génère automatiquement un résumé des faits saillants de la session.
   * Embeddings locaux générés par `all-MiniLM-L6-v2` (~90 Mo sur CPU).
   * Injection via RAG (Retrieval-Augmented Generation) des souvenirs les plus proches par similarité cosinus.
3. **Mémoire Déclarative & Structurée (SQLite)** :
   * Fichier de base de données local `data/jarvis.db`.
   * Historique complet de toutes les conversations, horodatages, jetons consommés et métadonnées.
   * Table de profil utilisateur (nom, préférences de réponse, configurations).

---

### 4. Interface Graphique HUD Futuriste

Une application de bureau native propulsée par **PyQt6** et **QtWebEngine (Chromium)** :

* **Esthétique Cyberpunk / Iron Man** : Palette sombre (`#060810`), accents néon cyan et ambre, grille holographique animée, lignes de balayage CRT et lueur diffuse.
* **Cœur IA Réactif** : Sphère centrale à anneaux concentriques animés dont le rythme et l'apparence réagissent aux états du système (*Initialisation*, *En attente*, *Réflexion*, *Écoute*, *Parole*).
* **Monitoring Matériel en Temps Réel** : Jauges de charge CPU et RAM rafraîchies toutes les 2 secondes via `psutil`.
* **Horloge Dynamique & Statut Système** : Indicateur textuel et lumineux de l'état actuel de l'assistant.
* **Contrôles Utiles** :
  * Bouton d'interruption immédiate de la génération (Stop).
  * Bouton de réinitialisation du contexte conversationnel (Poubelle).
  * Système de notifications visuelles "Toast" non intrusives.

---

### 5. Moteur de Rendu Dynamique

JARVIS ne produit pas uniquement du texte brut, il sait matérialiser ses explications visuellement :

* **📊 Diagrammes Mermaid.js** : Tout bloc encadré par `<mermaid>...</mermaid>` est automatiquement converti en SVG interactif inline (diagrammes de flux, séquences, architectures, diagrammes de classes).
* **🗺️ Cartes Interactives Leaflet.js** : Tout bloc balisé `<map>{...}</map>` génère une carte géographique interactive avec zoom, centrage et marqueurs.
* **💻 Blocs de Code Formatés** : Coloration syntaxique via `highlight.js` avec détection automatique du langage et bouton de copie en un clic dans le presse-papiers.
* **📝 Markdown Intégral** : Titres, listes, citations, tableaux, textes en gras/italique rendus via `marked.js` et désinfectés par `DOMPurify`.
* **🔒 100% Hors-Ligne** : Toutes les bibliothèques JS sont stockées localement dans `ui/web/assets/libs/` sans aucun appel à des CDN distants.

---

### 6. Couche Agentique & Actions PC Sécurisées

JARVIS dispose d'un **Agentic Layer** capable de manipuler votre ordinateur pour exécuter des ordres en langage naturel, sous un protocole de sécurité strict :

#### Matrice des Niveaux de Risque

| Niveau | Impact | Comportement |
|---|---|---|
| **🟢 SAFE** | Lecture seule, lancement d'app | Exécution directe et silencieuse |
| **🟡 MODERATE** | Création de fichier, scripts légers | Notification ou prévisualisation |
| **🔴 SENSITIVE** | Écriture/suppression de fichier, shell, envoi d'email | **Action Card obligatoire** (Validation utilisateur) |
| **⛔ BLOCKED** | Fichiers système critiques, `rmdir /s`, registre | **Interdiction totale et inconditionnelle** |

#### Catalogue des Outils Implémentés & Disponibles

1. **🚀 Lancement d'Applications (`app_controller`)** :
   * Ouvre n'importe quel logiciel installé (Spotify, VS Code, Google Chrome, Word, Excel, etc.).
   * Recherche multicouche : alias usuels, scan récursif du Menu Démarrer / Bureau, et interrogation du Registre Windows (`App Paths`).
2. **🌐 Recherche Web en Temps Réel (`web_search`)** :
   * Recherche en direct via DuckDuckGo (`ddgs`) sans API payante.
   * Détection intelligente des requêtes temporelles (actualités, météo, scores sportifs, cours boursiers).
   * Retourne des résumés riches (titres, extraits pertinents, sources).
3. **📁 Gestion du Système de Fichiers (`file_manager`)** :
   * **`file_read`** : Lecture du contenu textuel d'un fichier local (avec protection contre les fichiers volumineux > 20 000 caractères).
   * **`file_write`** : Création ou modification de fichiers (code source, notes, scripts) avec création automatique des dossiers parents.
4. **⚡ Exécution de Commandes Shell (`shell_execute`)** :
   * Exécution de commandes PowerShell sécurisées avec timeout de 30 secondes pour prévenir tout gel.
   * Capture séparée de `stdout` et `stderr`.
5. **📧 Gestionnaire d'Emails (`email_sender` - Prévu/Spécifié)** :
   * Composition et envoi via SMTP local ou distant (Gmail App Password, Outlook).
   * Prévisualisation complète du destinataire, de l'objet et du corps avant validation.
6. **⏰ Planificateur de Tâches (`task_scheduler` - Prévu/Spécifié)** :
   * Définition de rappels et de tâches différées via le Planificateur de tâches Windows (`schtasks`).

#### L'Action Card : L'Homme au Centre de la Décision

Lorsqu'une action sensible est demandée (ex. : *"Écris ce code dans main.py"* ou *"Exécute cette commande"*), JARVIS ne l'exécute pas à l'aveugle :
1. Une **Action Card** apparaît dans le HUD avec l'explication et les paramètres exacts.
2. L'utilisateur peut **Confirmer**, **Modifier les paramètres** ou **Annuler**.
3. Le résultat de l'opération est réinjecté dans la boucle de réflexion de JARVIS.

---

## 🏗️ Architecture Technique & Flux de Données

```
+-------------------------------------------------------------------------+
|                       APPLICATION DESKTOP JARVIS                        |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                     Fenêtre Principale PyQt6                      |  |
|  |                                                                   |  |
|  |   +------------------------------------------------------------+  |  |
|  |   |                QWebEngineView (Chromium)                   |  |  |
|  |   |                                                            |  |  |
|  |   |   +------------------------+  +-------------------------+  |  |  |
|  |   |   |   HUD & Chat Panel     |  |  Panneau Dynamique      |  |  |  |
|  |   |   |   (Messages, Actions)  |  |  (Mermaid, Leaflet)     |  |  |  |
|  |   |   +------------------------+  +-------------------------+  |  |  |
|  |   |                                                            |  |  |
|  |   |   JavaScript <═════════ QWebChannel ═════════> Python      |  |  |
|  |   +------------------------------------------------------------+  |  |
|  |                                                                   |  |
|  |   +---------------+  +-------------------+  +------------------+  |  |
|  |   |  AudioThread  |  |    LLMManager     |  |  MemoryManager   |  |  |
|  |   |  (STT + TTS)  |  |  (Ollama Stream)  |  | (Chroma + SQLite)|  |  |
|  |   +---------------+  +-------------------+  +------------------+  |  |
|  |          |                     |                      |           |  |
|  |          |            +------------------+            |           |  |
|  |          |            |  ActionManager   |            |           |  |
|  |          |            | (Tools Agentics) |            |           |  |
|  |          |            +------------------+            |           |  |
|  +-------------------------------------------------------------------+  |
|                                                                         |
|  +-------------------------------------------------------------------+  |
|  |                      Services Locaux Machine                      |  |
|  |   • Serveur Ollama (llama3.2 / qwen2.5)                           |  |
|  |   • Moteur Faster-Whisper (CPU int8)                              |  |
|  |   • Moteur Piper TTS (CPU onnx)                                   |  |
|  |   • Base ChromaDB & SQLite sur disque SSD                         |  |
|  +-------------------------------------------------------------------+  |
+-------------------------------------------------------------------------+
```

---

## 📂 Structure du Projet

```text
PROJET JARVIS/
│
├── main.py                     # Point d'entrée de l'application
├── setup_startup.py            # Script d'installation du lancement automatique au boot
├── requirements.txt            # Dépendances Python du projet
├── contexte_projet.md          # Cahier des charges et architecture de référence
├── README.md                   # Documentation complète du projet
├── .env.example                # Exemple de configuration des variables d'environnement
├── .env                        # Variables locales (ignoré par git)
│
├── ai/                         # Intelligence Artificielle & Logique Agentique
│   ├── llm_manager.py          # Gestionnaire Ollama, streaming et auto-routage
│   ├── action_manager.py       # Orchestration des outils et validation de sécurité
│   └── response_parser.py      # Détection des balises (<tool_call>, <mermaid>, etc.)
│
├── audio/                      # Pipeline Audio Vocal
│   ├── audio_thread.py         # Thread dédié asynchrone (QThread)
│   ├── stt.py                  # Reconnaissance vocale Faster-Whisper
│   ├── tts.py                  # Synthèse vocale Piper-TTS
│   └── vad.py                  # Détection d'activité vocale (Voice Activity Detection)
│
├── config/                     # Configuration et Prompts
│   ├── settings.py             # Classe de configuration centralisée (chemins, ports)
│   ├── system_prompt.txt       # Instructions système strictes données à JARVIS
│   ├── persona.md              # Définition du caractère et du ton de l'assistant
│   └── models.json             # Définition des capacités et VRAM des modèles
│
├── core/                       # Cœur de l'application Desktop
│   ├── app.py                  # Classe QApplication personnalisée
│   ├── window.py               # Fenêtre principale native (PyQt6 + WebEngine)
│   ├── bridge.py               # Pont de communication bidirectionnel QWebChannel
│   ├── ollama_service.py       # Surveillance et démarrage automatique du daemon Ollama
│   └── system_monitor.py       # Mesure en continu des ressources CPU / RAM
│
├── memory/                     # Système de Mémoire Cognitive
│   ├── memory_manager.py       # Orchestrateur des 3 niveaux de mémoire
│   ├── short_term.py           # Contexte immédiat de session (RAM deque)
│   ├── long_term.py            # Base vectorielle RAG (ChromaDB)
│   └── database.py             # Base relationnelle d'historique (SQLite)
│
├── tools/                      # Boîte à outils Agentiques
│   ├── base_tool.py            # Classe abstraite et énumération des niveaux de risque
│   ├── app_controller.py       # Recherche et lancement d'applications Windows
│   ├── web_search.py           # Recherche Web & actualités via DuckDuckGo
│   ├── file_manager.py         # Lecture et écriture sécurisées de fichiers
│   └── shell_execute.py        # Exécution de commandes PowerShell
│
├── ui/                         # Interface Graphique Web-in-Desktop
│   └── web/
│       ├── index.html          # Structure HTML du HUD
│       ├── css/                # Feuilles de styles (main, components, animations)
│       ├── js/                 # Logique client (bridge, chat, ui, renderer, action_card)
│       └── assets/             # Polices, icônes et bibliothèques JS locales (Mermaid, Leaflet)
│
├── data/                       # Données persistantes locales (générées automatiquement)
│   ├── chromadb/               # Base vectorielle ChromaDB
│   ├── jarvis.db               # Base SQLite
│   └── piper_models/           # Fichiers de voix ONNX pour Piper
│
└── logs/                       # Journaux d'exécution rotatifs
    └── jarvis.log
```

---

## 🚀 Installation & Démarrage

### 1. Prérequis Système

* **Système d'exploitation** : Windows 10 ou Windows 11 (64-bit).
* **Python** : Version 3.11 ou supérieure.
* **Ollama** : Installé sur la machine ([https://ollama.com](https://ollama.com)).
* **Modèles Ollama** :
  ```powershell
  ollama pull llama3.2:latest
  ollama pull qwen2.5:latest
  ```

### 2. Installation des dépendances

Dans un terminal PowerShell (ou invite de commande) à la racine du projet :

```powershell
# Créer et activer un environnement virtuel (recommandé)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Installer les dépendances
pip install -r requirements.txt
```

### 3. Configuration initiale

Copiez le fichier d'exemple et ajustez les réglages si nécessaire :

```powershell
cp .env.example .env
```

### 4. Lancement de JARVIS

```powershell
python main.py
```

> **Note** : Si Ollama n'est pas déjà lancé, JARVIS tente automatiquement de démarrer le service en arrière-plan.

### 5. Démarrage Automatique avec Windows (Optionnel)

Pour que JARVIS démarre silencieusement en arrière-plan à chaque ouverture de session Windows avec son icône dédiée :

```powershell
python setup_startup.py
```

---

## ⚙️ Configuration (.env)

| Variable | Description | Valeur par défaut |
|---|---|---|
| `OLLAMA_BASE_URL` | URL de l'API locale Ollama | `http://localhost:11434` |
| `OLLAMA_MODEL_FAST` | Modèle pour les requêtes vocales/rapides | `llama3.2:latest` |
| `OLLAMA_MODEL_ADVANCED` | Modèle pour le code et les outils | `qwen2.5:latest` |
| `WHISPER_MODEL_SIZE` | Taille du modèle Faster-Whisper | `small` |
| `WHISPER_COMPUTE_TYPE` | Type de calcul CPU pour Whisper | `int8` |
| `PIPER_MODEL_PATH` | Chemin vers le modèle ONNX de Piper | `data/piper_models/fr_FR-upmc-medium.onnx` |
| `SHORT_TERM_MAX_TURNS` | Nombre d'échanges conservés en RAM | `20` |
| `APP_LOG_LEVEL` | Niveau de verbosité des logs | `DEBUG` ou `INFO` |

---

## ⌨️ Raccourcis & Utilisation

* **Entrée** : Envoyer le message saisi dans le champ texte.
* **Bouton Micro** : Déclencher l'écoute vocale.
* **Bouton Stop (Carré rouge)** : Stopper immédiatement la génération en cours du LLM.
* **Bouton Poubelle** : Vider l'historique de la session active (réinitialisation du contexte).
* **F5** : Recharger l'interface graphique (utile en développement).
* **F12** : Ouvrir les Outils de Développement Chromium (DevTools) pour inspecter l'interface et la console.

---

## 🗺️ Feuille de Route (Roadmap)

Le développement de JARVIS est articulé en 6 étapes majeures :

* [x] **Étape 1 — Fondations & Squelette** : Application PyQt6, fenêtre maximisée, pont bidirectionnel QWebChannel, design system HUD sombre.
* [x] **Étape 2 — Intégration LLM & Chat** : Connexion Ollama, streaming fluide des tokens, routage dynamique de modèles, mémoire court-terme.
* [x] **Étape 3 — Mémoire Cognitive Persistante** : Base relationnelle SQLite, vector store ChromaDB (RAG), synthèse automatique en fin de session.
* [x] **Étape 4 — Pipeline Audio (STT & TTS)** : Détection d'activité vocale (VAD), reconnaissance vocale Faster-Whisper sur CPU, synthèse vocale Piper-TTS.
* [x] **Étape 5 — Moteur Visuel & Monitoring** : Rendu des diagrammes Mermaid, cartes géographiques Leaflet, surveillance en direct du CPU/RAM.
* [x] **Étape 6 — Couche Agentique (Actions PC Cadrées)** :
  * [x] Gestionnaire central d'actions (`ActionManager`) et parsing des `<tool_call>`.
  * [x] Composant HUD *Action Card* (Confirmation / Modification / Annulation).
  * [x] Contrôleur d'applications Windows (`app_controller`).
  * [x] Recherche Web et actualités DuckDuckGo (`web_search`).
  * [x] Gestionnaire de fichiers (`file_read`, `file_write`).
  * [x] Exécution de commandes Shell (`shell_execute`).
  * [ ] Connecteur d'envoi d'e-mails sécurisé (`email_sender`).
  * [ ] Planificateur de rappels et tâches Windows (`task_scheduler`).

---

## 📄 Licence & Confidentialité

Projet développé pour un usage personnel strict.  
**Garantie de confidentialité** : 100% du code, des modèles et des données s'exécutent en vase clos sur votre machine locale. Aucune télémétrie n'est transmise à l'extérieur.