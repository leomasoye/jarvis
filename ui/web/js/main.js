/**
 * JARVIS HUD — main.js v2
 * Point d'entrée JavaScript — Étape 2.
 *
 * Nouveautés :
 *  - initUserInteractions() active l'input + send/stop buttons
 *  - handleSend() : affiche le message utilisateur + envoie à Python
 *  - handleStop() : annule la génération
 *  - Mode démonstration amélioré
 */

'use strict';

// ── Bootstrap ─────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  UI.startClock();
  UI.setStatus('init');
  UI.setInputEnabled(false);  // Désactivé jusqu'à la connexion bridge

  if (typeof Renderer !== 'undefined') {
    Renderer.init();
  }

  // Afficher l'écran de bienvenue
  Chat._showWelcomeScreen();

  // Lancer la séquence de boot puis connecter le bridge
  UI.runBootSequence().then(initBridge);
});

// ── Connexion QWebChannel ──────────────────────────────────────────────────────

function initBridge() {
  if (typeof qt === 'undefined' || !qt.webChannelTransport) {
    console.warn('[Main] QWebChannel non disponible — mode démonstration activé.');
    activateDemoMode();
    return;
  }

  new QWebChannel(qt.webChannelTransport, (channel) => {
    const jarvisObj = channel.objects.jarvis;
    if (!jarvisObj) {
      console.error('[Main] Objet "jarvis" introuvable dans le channel.');
      return;
    }

    Bridge.init(jarvisObj);
    initUserInteractions();
    
    // Récupérer la liste des modèles Ollama
    Bridge.fetchModels();

    console.log('[Main] Jarvis HUD opérationnel.');
    Bridge.log('HUD opérationnel — Étape 2 validée.');
  });
}

// ── Interactions Utilisateur ────────────────────────────────────────────────────

function initUserInteractions() {
  const input    = document.getElementById('message-input');
  const sendBtn  = document.getElementById('send-btn');
  const stopBtn  = document.getElementById('stop-btn');
  const voiceBtn = document.getElementById('voice-btn');
  const clearBtn = document.getElementById('clear-btn');
  const closeBtn = document.getElementById('close-btn');

  // ── Fermeture ─────────────────────────────────────────────────────────────
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      if (window.confirm("Voulez-vous vraiment éteindre le système JARVIS ?")) {
        Bridge.close();
      }
    });
  }

  // ── Envoi de message ──────────────────────────────────────────────────────

  function handleSend() {
    const text = input?.value.trim();
    if (!text) return;

    // Affichage immédiat côté JS
    Chat.addUserMessage(text);

    // Vider l'input et désactiver pendant la génération
    input.value = '';
    UI.setInputEnabled(false);

    // Envoyer à Python
    Bridge.sendMessage(text);
  }

  if (sendBtn) sendBtn.addEventListener('click', handleSend);

  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    });
    // Focus automatique sur l'input
    input.focus();
  }

  // ── Arrêt de la génération ────────────────────────────────────────────────

  if (stopBtn) {
    stopBtn.addEventListener('click', () => {
      Bridge.cancelMessage();
      UI.setInputEnabled(true);
    });
  }

  // ── Vocal (Étape 4) ───────────────────────────────────────────────────────

  if (voiceBtn) {
    voiceBtn.addEventListener('click', () => {
      Bridge.toggleVoice();
      voiceBtn.classList.toggle('active');
    });
  }

  // ── Effacer le contexte ───────────────────────────────────────────────────

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      Bridge.clearContext();
      Chat.clear();
    });
  }

  const modelDropdownContainer = document.getElementById('model-dropdown-container');
  const modelBadge = document.getElementById('model-badge');

  if (modelBadge && modelDropdownContainer) {
    modelBadge.addEventListener('click', (e) => {
      e.stopPropagation();
      modelDropdownContainer.classList.toggle('open');
      const isOpen = modelDropdownContainer.classList.contains('open');
      modelBadge.setAttribute('aria-expanded', isOpen);
    });

    // Fermer si clic ailleurs
    document.addEventListener('click', () => {
      modelDropdownContainer.classList.remove('open');
      modelBadge.setAttribute('aria-expanded', 'false');
    });
    
    // Les clics sur les items sont gérés par UI.buildModelsMenu
  }
}

/** Bascule entre modèle rapide et avancé via Python. */
function _toggleModel() {
  Bridge.toggleModel();
}

// ── Mode Démonstration ─────────────────────────────────────────────────────────

function activateDemoMode() {
  UI.setStatus('idle');
  UI.setModelInfo('demo-mode', 'FAST');
  UI.setInputEnabled(true);

  // Dans le mode démo, le send affiche juste un echo local
  const sendBtn = document.getElementById('send-btn');
  const input   = document.getElementById('message-input');

  if (sendBtn) {
    sendBtn.addEventListener('click', () => {
      const text = input?.value.trim();
      if (!text) return;
      Chat.addUserMessage(text);
      input.value = '';
      // Simuler une réponse
      setTimeout(() => {
        Chat.startStreaming();
        const demo = 'Mode démonstration : ouvrez ce fichier via PyQt6 pour activer le bridge Python et Ollama.';
        let i = 0;
        const interval = setInterval(() => {
          if (i < demo.length) {
            Chat.appendToken(demo[i++]);
          } else {
            clearInterval(interval);
            Chat.finalizeMessage(demo);
          }
        }, 20);
      }, 800);
    });
  }

  setTimeout(() => {
    UI.showNotification('Mode Démonstration', 'Ouvrez via PyQt6 pour activer le bridge Python.', 'warn');
  }, 600);
}
