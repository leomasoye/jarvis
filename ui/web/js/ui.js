/**
 * JARVIS HUD — ui.js
 * Contrôleur de l'interface graphique.
 * Gère les mises à jour DOM, animations, notifications, horloge.
 */

'use strict';

const UI = {
  // ── Références DOM ─────────────────────────────────────────────────────

  get statusDot()     { return document.getElementById('status-dot'); },
  get statusText()    { return document.getElementById('status-text'); },
  get modelName()     { return document.getElementById('model-name'); },
  get modelType()     { return document.getElementById('model-type'); },
  get clock()         { return document.getElementById('clock'); },
  get notifContainer(){ return document.getElementById('notifications'); },
  get chatContainer() { return document.getElementById('chat-container'); },
  get loadingScreen() { return document.getElementById('loading-screen'); },
  get loadingText()   { return document.getElementById('loading-text'); },
  get loadingBar()    { return document.getElementById('loading-progress'); },
  get thinkingIndicator() { return document.getElementById('thinking-indicator'); },

  // ── Contrôle de la saisie ────────────────────────────────────────────────

  /**
   * Active ou désactive la zone de saisie et permute send/stop buttons.
   * @param {boolean} enabled  true = input actif, false = génération en cours
   */
  setInputEnabled(enabled) {
    const input   = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const stopBtn = document.getElementById('stop-btn');

    if (input) {
      input.disabled = !enabled;
      input.placeholder = enabled
        ? 'Écrivez votre message… (Entrée pour envoyer)'
        : 'JARVIS génère une réponse…';
      if (enabled) setTimeout(() => input.focus(), 50);
    }
    if (sendBtn) sendBtn.classList.toggle('hidden', !enabled);
    if (stopBtn) stopBtn.classList.toggle('hidden', enabled);
  },

  // ── Statut ─────────────────────────────────────────────────────────────

  /**
   * Met à jour le statut affiché dans le header.
   * @param {'idle'|'thinking'|'speaking'|'listening'|'error'} status
   */
  setStatus(status) {
    const dot = this.statusDot;
    const text = this.statusText;
    if (!dot || !text) return;

    const configs = {
      idle:      { label: 'EN ATTENTE',  cls: '' },
      thinking:  { label: 'ANALYSE...',  cls: 'thinking' },
      speaking:  { label: 'PARLE',       cls: 'speaking' },
      listening: { label: 'ÉCOUTE',      cls: 'listening' },
      error:     { label: 'ERREUR',      cls: 'error' },
      init:      { label: 'INITIALISATION', cls: '' },
    };

    // Jouer un son simple
    if (this.Audio) {
      this.Audio.playStatusSound(status);
    }

    const cfg = configs[status] || configs.idle;
    text.textContent = cfg.label;
    dot.className = 'status-dot' + (cfg.cls ? ` ${cfg.cls}` : '');

    // Afficher / masquer l'indicateur de réflexion
    if (this.thinkingIndicator) {
      this.thinkingIndicator.classList.toggle('hidden', status !== 'thinking');
    }

    // Mettre à jour la puce IA dans la sidebar
    const aiStatus = document.querySelector('.ai-status-text');
    if (aiStatus) {
      const aiLabels = {
        idle: 'EN ATTENTE', thinking: 'ANALYSE', speaking: 'PARLE',
        listening: 'ÉCOUTE', error: 'ERREUR', init: 'BOOT',
      };
      aiStatus.textContent = aiLabels[status] || 'EN ATTENTE';
    }
  },

  // ── Modèle Info ────────────────────────────────────────────────────────

  /**
   * Met à jour l'affichage du modèle dans le header.
   * @param {string} name  Nom du modèle (ex: "llama3.2:3b")
   * @param {string} type  Type : "FAST" ou "ADV"
   */
  setModelInfo(name, type) {
    if (this.modelName) this.modelName.textContent = name;
    if (this.modelType) {
      this.modelType.textContent = type;
    }
  },

  /**
   * Construit dynamiquement le menu déroulant des modèles.
   * @param {Array<{name: string, param_size: string}>} models 
   */
  buildModelsMenu(models) {
    const menu = document.getElementById('model-dropdown-menu');
    if (!menu) return;
    
    // Garder le bouton AUTO
    menu.innerHTML = `
      <div class="dropdown-item" data-model="auto" role="menuitem" tabindex="0">
        <span class="model-type">AUTO</span>
        <span class="model-name">Routage automatique</span>
      </div>
    `;

    models.forEach(m => {
      const item = document.createElement('div');
      item.className = 'dropdown-item';
      item.setAttribute('data-model', m.name);
      item.setAttribute('role', 'menuitem');
      item.setAttribute('tabindex', '0');
      
      item.innerHTML = `
        <span class="model-type">${m.param_size || '?B'}</span>
        <span class="model-name">${m.name}</span>
      `;
      
      menu.appendChild(item);
    });

    // Réattacher les événements de clic sur tous les items
    const items = menu.querySelectorAll('.dropdown-item');
    const modelDropdownContainer = document.getElementById('model-dropdown-container');
    const modelBadge = document.getElementById('model-badge');

    items.forEach(item => {
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        if (modelDropdownContainer) modelDropdownContainer.classList.remove('open');
        if (modelBadge) modelBadge.setAttribute('aria-expanded', 'false');
        
        const mode = item.getAttribute('data-model');
        if (mode && typeof Bridge !== 'undefined') {
          Bridge.changeModel(mode);
        }
      });
    });
  },

  // ── Audio Level ─────────────────────────────────────────────────────────

  /**
   * Met à jour l'apparence du bouton micro en fonction du volume RMS.
   * @param {number} level RMS audio entre 0.0 et 1.0
   */
  updateAudioLevel(level) {
    const voiceBtn = document.getElementById('voice-btn');
    if (!voiceBtn || !voiceBtn.classList.contains('active')) {
      if (voiceBtn) {
        voiceBtn.style.transform = '';
        voiceBtn.style.boxShadow = '';
      }
      return;
    }
    
    // Le RMS d'une voix parlée normale est souvent entre 0.01 et 0.1
    // On amplifie la valeur pour l'effet visuel
    const visualIntensity = Math.min(level * 10, 1.0);
    
    const scale = 1.0 + (visualIntensity * 0.3); // max 1.3
    const glowRadius = 15 + (visualIntensity * 25); // 15px to 40px
    const glowOpacity = 0.5 + (visualIntensity * 0.5);
    
    voiceBtn.style.transform = `scale(${scale})`;
    voiceBtn.style.boxShadow = `0 0 ${glowRadius}px rgba(0, 255, 204, ${glowOpacity})`;
  },

  // ── Stats Système ──────────────────────────────────────────────────────

  /**
   * Met à jour les barres CPU et RAM dans la sidebar.
   * @param {number} cpu 
   * @param {number} ram 
   */
  updateSystemStats(cpu, ram) {
    const cpuFill = document.getElementById('cpu-fill');
    const cpuVal = document.getElementById('cpu-val');
    const ramFill = document.getElementById('ram-fill');
    const ramVal = document.getElementById('ram-val');

    if (cpuFill) cpuFill.style.width = cpu + '%';
    if (cpuVal) cpuVal.textContent = cpu + '%';
    
    if (ramFill) ramFill.style.width = ram + '%';
    if (ramVal) ramVal.textContent = ram + '%';
  },

  // ── Notifications (Toasts) ─────────────────────────────────────────────

  /**
   * Affiche une notification toast dans le coin supérieur droit.
   * Se ferme automatiquement après 5 secondes.
   * @param {string} title    Titre du toast
   * @param {string} message  Corps du toast
   * @param {'info'|'success'|'warn'|'error'} [type='info']
   */
  showNotification(title, message, type = 'info') {
    const icons = { info: 'ℹ', success: '✓', warn: '⚠', error: '✕' };
    const icon = icons[type] || icons.info;

    // Jouer un son pour la notification
    if (this.Audio) {
      if (type === 'error') {
        this.Audio.playBeep(200, 'sawtooth', 0.3, 0.1);
      } else if (type === 'success') {
        this.Audio.playBeep(600, 'sine', 0.1, 0.05);
        setTimeout(() => this.Audio.playBeep(800, 'sine', 0.2, 0.05), 100);
      } else {
        this.Audio.playBeep(500, 'sine', 0.15, 0.03);
      }
    }

    const toast = document.createElement('div');
    toast.className = 'notification-toast';
    toast.innerHTML = `
      <div class="toast-icon">${icon}</div>
      <div class="toast-body">
        <div class="toast-title">${this._escapeHtml(title)}</div>
        <div class="toast-message">${this._escapeHtml(message)}</div>
      </div>
    `;

    this.notifContainer.appendChild(toast);

    // Fermeture automatique après 5s
    const closeDelay = 5000;
    const closeTimeout = setTimeout(() => this._closeToast(toast), closeDelay);

    // Fermeture au clic
    toast.addEventListener('click', () => {
      clearTimeout(closeTimeout);
      this._closeToast(toast);
    });
  },

  /** @param {HTMLElement} toast */
  _closeToast(toast) {
    if (!toast.isConnected) return;
    toast.classList.add('closing');
    toast.addEventListener('animationend', () => toast.remove(), { once: true });
  },

  // ── Chat ───────────────────────────────────────────────────────────────

  /**
   * Ajoute un message dans la zone de chat.
   * @param {'user'|'assistant'|'system'} role
   * @param {string} content
   * @param {string} [meta]  Métadonnée affichée en dessous (ex: modèle, heure)
   */
  addMessage(role, content, meta = '') {
    // Supprimer l'écran de bienvenue s'il existe
    const welcome = document.querySelector('.welcome-screen');
    if (welcome) welcome.remove();

    const msg = document.createElement('div');
    msg.className = `message ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = content;
    msg.appendChild(bubble);

    if (meta) {
      const metaEl = document.createElement('div');
      metaEl.className = 'message-meta';
      metaEl.textContent = meta;
      msg.appendChild(metaEl);
    }

    this.chatContainer.appendChild(msg);
    this._scrollToBottom();
    return msg;
  },

  /** Fait défiler la zone de chat vers le bas. */
  _scrollToBottom() {
    const c = this.chatContainer;
    if (c) c.scrollTop = c.scrollHeight;
  },

  // ── Séquence de Boot ───────────────────────────────────────────────────

  /**
   * Anime l'écran de chargement avec des messages progressifs.
   * @returns {Promise<void>}
   */
  async runBootSequence() {
    const steps = [
      { msg: 'CHARGEMENT DU MOTEUR IA...', pct: 20, delay: 300 },
      { msg: 'CONNEXION AU BRIDGE PYTHON...', pct: 50, delay: 400 },
      { msg: 'INITIALISATION DE L\'INTERFACE...', pct: 75, delay: 350 },
      { msg: 'DÉMARRAGE DES MODULES...', pct: 90, delay: 300 },
      { msg: 'SYSTÈME PRÊT.', pct: 100, delay: 200 },
    ];

    for (const step of steps) {
      await this._delay(step.delay);
      if (this.loadingText) this.loadingText.textContent = step.msg;
      if (this.loadingBar) this.loadingBar.style.width = `${step.pct}%`;
    }

    await this._delay(400);
    this._hideLoadingScreen();
  },

  _hideLoadingScreen() {
    const ls = this.loadingScreen;
    if (!ls) return;
    ls.classList.add('fade-out');
    setTimeout(() => ls.remove(), 550);
  },

  // ── Horloge ────────────────────────────────────────────────────────────

  /** Démarre la mise à jour de l'horloge toutes les secondes. */
  startClock() {
    const update = () => {
      const el = this.clock;
      if (!el) return;
      const now = new Date();
      el.textContent = now.toLocaleTimeString('fr-FR', {
        hour: '2-digit', minute: '2-digit', second: '2-digit',
      });
    };
    update();
    setInterval(update, 1000);
  },

  // ── Utilitaires ────────────────────────────────────────────────────────

  /** @param {number} ms */
  _delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); },

  /** @param {string} str */
  _escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  },

  // ── Audio Feedback ───────────────────────────────────────────────────────
  
  Audio: {
    ctx: null,
    
    init() {
      if (!this.ctx) {
        this.ctx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (this.ctx.state === 'suspended') {
        this.ctx.resume();
      }
    },
    
    /**
     * Génère un simple "beep" synthétique
     * @param {number} freq 
     * @param {string} type 'sine', 'square', 'sawtooth', 'triangle'
     * @param {number} duration en secondes
     * @param {number} vol de 0.0 à 1.0
     */
    playBeep(freq, type, duration, vol=0.05) {
      try {
        this.init();
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        
        osc.type = type;
        osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
        
        gain.gain.setValueAtTime(vol, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);
        
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        
        osc.start();
        osc.stop(this.ctx.currentTime + duration);
      } catch (e) {
        console.warn("Impossible de jouer le son:", e);
      }
    },
    
    /**
     * Joue un pattern sonore selon le statut
     * @param {string} status 
     */
    playStatusSound(status) {
      // Pour éviter de bloquer si l'utilisateur n'a pas encore interagi
      // (bien que dans QWebEngine, l'autoplay soit souvent toléré)
      
      switch(status) {
        case 'thinking':
          this.playBeep(600, 'sine', 0.1, 0.05);
          setTimeout(() => this.playBeep(800, 'sine', 0.2, 0.05), 150);
          break;
        case 'listening':
          this.playBeep(400, 'sine', 0.1, 0.05);
          setTimeout(() => this.playBeep(600, 'sine', 0.1, 0.05), 100);
          setTimeout(() => this.playBeep(800, 'sine', 0.3, 0.05), 200);
          break;
        case 'idle':
          this.playBeep(400, 'sine', 0.1, 0.02);
          setTimeout(() => this.playBeep(300, 'sine', 0.2, 0.02), 150);
          break;
        case 'init':
          this.playBeep(800, 'sine', 0.1, 0.05);
          setTimeout(() => this.playBeep(1200, 'sine', 0.4, 0.05), 150);
          break;
        case 'error':
          this.playBeep(150, 'sawtooth', 0.3, 0.1);
          setTimeout(() => this.playBeep(150, 'sawtooth', 0.4, 0.1), 350);
          break;
      }
    }
  },
};
