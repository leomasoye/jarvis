/**
 * JARVIS HUD — chat.js
 * Gestion de l'affichage du chat : messages, streaming, erreurs.
 *
 * API publique (appelée depuis bridge.js et main.js) :
 *   Chat.addUserMessage(text)       Ajouter un message utilisateur
 *   Chat.startStreaming()           Créer la bulle de streaming
 *   Chat.appendToken(token)         Ajouter un token au streaming
 *   Chat.finalizeMessage(fullText)  Finaliser la bulle streaming
 *   Chat.showError(text)            Afficher une erreur dans le chat
 *   Chat.clear()                    Vider le chat et revenir à l'écran de bienvenue
 */

'use strict';

const Chat = {
  /** Bulle de streaming courante (null si pas en cours) */
  _streamEl: null,
  /** Contenu accumulé du streaming courant */
  _streamContent: '',
  /** Timestamp du début du streaming (pour la durée) */
  _streamStart: 0,

  // ── Accesseurs DOM ─────────────────────────────────────────────────────────

  get _container() {
    return document.getElementById('chat-container');
  },

  // ── Messages Utilisateur ────────────────────────────────────────────────────

  /**
   * Ajoute un message de l'utilisateur dans le chat.
   * @param {string} text
   */
  addUserMessage(text) {
    this._removeWelcomeScreen();
    const msg = this._createBubble('user', text, this._timestamp());
    this._container.appendChild(msg);
    this._scrollToBottom();
  },

  // ── Streaming Assistante ────────────────────────────────────────────────────

  /**
   * Démarre une nouvelle bulle de streaming pour la réponse IA.
   * Appelé automatiquement par appendToken() si aucune bulle n'existe.
   */
  startStreaming() {
    this._removeWelcomeScreen();
    this._streamContent = '';
    this._streamStart = Date.now();

    const msg = document.createElement('div');
    msg.className = 'message assistant streaming';
    msg.innerHTML = `
      <div class="message-bubble">
        <span class="stream-text"></span><span class="stream-cursor" aria-hidden="true">▋</span>
      </div>
    `;
    this._container.appendChild(msg);
    this._streamEl = msg;
    this._scrollToBottom();
  },

  /**
   * Ajoute un token à la bulle de streaming courante.
   * Crée automatiquement la bulle si elle n'existe pas.
   * @param {string} token
   */
  appendToken(token) {
    if (!this._streamEl) {
      this.startStreaming();
    }
    this._streamContent += token;

    const textEl = this._streamEl.querySelector('.stream-text');
    if (textEl) {
      // Rendu simplifié : sauts de ligne en <br>
      textEl.innerHTML = this._renderSimple(this._streamContent);
    }

    // Ne scroller que si on est déjà proche du bas (évite l'interruption de lecture)
    this._scrollIfNearBottom();
  },

  /**
   * Finalise la bulle de streaming.
   * Supprime le curseur, formate le texte, ajoute le timestamp.
   * @param {string} fullText - Réponse complète du LLM
   * @param {string} [modelName] - Nom du modèle utilisé
   * @param {number} [tokenCount] - Nombre de tokens approximatif
   */
  finalizeMessage(fullText, modelName = '', tokenCount = 0) {
    if (!this._streamEl) return;

    const duration = ((Date.now() - this._streamStart) / 1000).toFixed(1);
    const bubble = this._streamEl.querySelector('.message-bubble');

    if (bubble) {
      if (typeof Renderer !== 'undefined') {
        bubble.innerHTML = Renderer.renderFull(fullText);
        Renderer.renderMermaidDiagrams(bubble);
      } else {
        bubble.innerHTML = this._renderFull(fullText);
      }
    }

    this._streamEl.classList.remove('streaming');

    // Méta-info : heure + durée de génération + modèle + tokens
    const meta = document.createElement('div');
    meta.className = 'message-meta';
    
    let metaText = `${this._timestamp()} · ${duration}s`;
    if (modelName) metaText += ` · ${modelName}`;
    if (tokenCount) {
        const tokensPerSec = (tokenCount / Math.max(duration, 0.1)).toFixed(1);
        metaText += ` · ~${tokenCount} tokens (${tokensPerSec} t/s)`;
    }
    
    meta.textContent = metaText;
    this._streamEl.appendChild(meta);

    this._streamEl = null;
    this._streamContent = '';
    this._scrollToBottom();
  },

  /**
   * Ajoute un widget custom (ex: Action Card) dans le chat.
   * @param {HTMLElement} widgetEl 
   */
  addCustomWidget(widgetEl) {
    if (!this._container) return;
    this._container.appendChild(widgetEl);
    this._scrollToBottom();
  },

  // ── Erreurs ────────────────────────────────────────────────────────────────

  /**
   * Affiche un message d'erreur dans le chat.
   * Supprime la bulle de streaming si elle existe.
   * @param {string} errorText
   */
  showError(errorText) {
    // Supprimer la bulle de streaming en cours
    if (this._streamEl) {
      this._streamEl.remove();
      this._streamEl = null;
      this._streamContent = '';
    }

    const msg = document.createElement('div');
    msg.className = 'message system error-message';
    msg.innerHTML = `
      <div class="message-bubble error-bubble">
        <span class="error-icon">⚠</span>
        <span>${this._escapeHtml(errorText)}</span>
      </div>
    `;
    this._container.appendChild(msg);
    this._scrollToBottom();
  },

  // ── Gestion ────────────────────────────────────────────────────────────────

  /**
   * Vide le chat et affiche l'écran de bienvenue.
   */
  clear() {
    if (this._streamEl) {
      this._streamEl = null;
      this._streamContent = '';
    }
    const c = this._container;
    if (c) c.innerHTML = '';
    this._showWelcomeScreen();
  },

  // ── Privé ──────────────────────────────────────────────────────────────────

  /** Supprime l'écran de bienvenue s'il existe. */
  _removeWelcomeScreen() {
    const ws = document.querySelector('.welcome-screen');
    if (ws) ws.remove();
  },

  /** Affiche l'écran de bienvenue dans le container. */
  _showWelcomeScreen() {
    const c = this._container;
    if (!c) return;
    c.innerHTML = `
      <div class="welcome-screen">
        <div class="welcome-logo">JARVIS</div>
      </div>
    `;
  },

  /**
   * Crée un élément de message DOM.
   * @param {'user'|'assistant'|'system'} role
   * @param {string} html  Contenu HTML (déjà échappé ou sûr)
   * @param {string} [time]
   */
  _createBubble(role, text, time = '') {
    const msg = document.createElement('div');
    msg.className = `message ${role}`;
    msg.style.animation = 'msg-appear 0.3s ease both';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    
    if (typeof Renderer !== 'undefined') {
      bubble.innerHTML = Renderer.renderFull(text);
      Renderer.renderMermaidDiagrams(bubble);
    } else {
      bubble.innerHTML = this._renderFull(text);
    }
    
    msg.appendChild(bubble);

    if (time) {
      const meta = document.createElement('div');
      meta.className = 'message-meta';
      meta.textContent = time;
      msg.appendChild(meta);
    }
    return msg;
  },

  /**
   * Rendu simplifié pour le streaming (pas de full parse pendant la génération).
   * @param {string} text
   */
  _renderSimple(text) {
    return this._escapeHtml(text).replace(/\n/g, '<br>');
  },

  /**
   * Rendu final d'un message complet.
   * Étape 2 : texte brut avec sauts de ligne.
   * Étape 5 : sera remplacé par le renderer Markdown + Mermaid + Leaflet.
   * @param {string} text
   */
  _renderFull(text) {
    // Rendu minimal mais lisible :
    // - Sauts de ligne
    // - Gras **text** et *italique*
    // - Code inline `code`
    let html = this._escapeHtml(text);
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
    html = html.replace(/\n/g, '<br>');
    return html;
  },

  /** @param {string} str @returns {string} */
  _escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  },

  /** @returns {string} Heure locale HH:MM */
  _timestamp() {
    return new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  },

  /** Fait défiler vers le bas. */
  _scrollToBottom() {
    const c = this._container;
    if (c) c.scrollTop = c.scrollHeight;
  },

  /** Fait défiler vers le bas seulement si on est à moins de 120px du bas. */
  _scrollIfNearBottom() {
    const c = this._container;
    if (!c) return;
    const threshold = 120;
    const distFromBottom = c.scrollHeight - c.scrollTop - c.clientHeight;
    if (distFromBottom < threshold) {
      c.scrollTop = c.scrollHeight;
    }
  },
};
