/**
 * JARVIS HUD — bridge.js v2
 * Fonctions JS <-> Python via QWebChannel.
 * Consulter contexte_projet.md §7.1.
 */

'use strict';

const Bridge = {
  _jarvis: null,

  /** @param {object} jarvisObj - L'objet Python exposé par QWebChannel */
  init(jarvisObj) {
    this._jarvis = jarvisObj;
    console.log('[Bridge] Connexion QWebChannel établie.');

    // ── Signaux Python → JS ────────────────────────────────────────────────

    // Statut de l'IA
    jarvisObj.update_status.connect((status) => {
      if (typeof UI !== 'undefined') UI.setStatus(status);
      // Activer/désactiver la saisie selon le statut
      if (typeof UI !== 'undefined') UI.setInputEnabled(status === 'idle' || status === 'error');
    });

    // Notifications (toasts)
    jarvisObj.show_notification.connect((title, message) => {
      let type = 'info';
      if (title.includes('Erreur') || title.includes('erreur')) type = 'error';
      else if (title.includes('pret') || title.includes('operat') || title.includes('OK')) type = 'success';
      if (typeof UI !== 'undefined') UI.showNotification(title, message, type);
    });

    // Info modèle
    jarvisObj.update_model_info.connect((modelName, modelType) => {
      if (typeof UI !== 'undefined') UI.setModelInfo(modelName, modelType);
    });

    // Modèles disponibles
    jarvisObj.models_list_ready.connect((jsonStr) => {
      try {
        const models = JSON.parse(jsonStr);
        if (typeof UI !== 'undefined') UI.buildModelsMenu(models);
      } catch (e) {
        console.error("[Bridge] Erreur parsing models_list_ready:", e);
      }
    });

    // Message utilisateur injecté par Python (ex: STT)
    jarvisObj.add_user_message_ui.connect((text) => {
      if (typeof Chat !== 'undefined') Chat.addUserMessage(text);
    });

    // Streaming token par token
    jarvisObj.send_token.connect((token) => {
      if (typeof Chat !== 'undefined') Chat.appendToken(token);
    });

    // Réponse complète (finalisation)
    jarvisObj.send_message_complete.connect((fullText, modelName, tokenCount) => {
      if (typeof Chat !== 'undefined') Chat.finalizeMessage(fullText, modelName, tokenCount);
      if (typeof UI !== 'undefined') UI.setInputEnabled(true);
    });

    // Erreurs LLM
    jarvisObj.llm_error.connect((err) => {
      if (typeof Chat !== 'undefined') Chat.showError(err);
      if (typeof UI !== 'undefined') UI.setStatus('error');
    });

    // Stats système
    jarvisObj.update_system_stats.connect((cpu, ram) => {
      if (typeof UI !== 'undefined') UI.updateSystemStats(cpu, ram);
    });

    // Niveau audio en temps réel
    jarvisObj.audio_level_update.connect((level) => {
      if (typeof UI !== 'undefined') UI.updateAudioLevel(level);
    });

    // Directive de rendu (Étape 5)
    jarvisObj.send_render_directive.connect((type, content) => {
      // TODO Étape 5
    });

    // Confirmation d'action PC (Étape 6)
    jarvisObj.action_requires_confirmation.connect((actionJson) => {
      if (typeof ActionCard !== 'undefined') {
        ActionCard.render(actionJson);
      }
    });
  },

  // ── Méthodes JS → Python ──────────────────────────────────────────────────

  /** @param {string} message */
  sendMessage(message) {
    if (!this._ensureConnected()) return;
    this._jarvis.on_user_message(message);
  },

  cancelMessage() {
    if (!this._ensureConnected()) return;
    this._jarvis.on_cancel_message();
  },

  toggleVoice() {
    if (!this._ensureConnected()) return;
    this._jarvis.on_toggle_voice();
  },

  toggleModel() {
    if (!this._ensureConnected()) return;
    this._jarvis.on_toggle_model();
  },

  /** @param {string} mode */
  changeModel(mode) {
    if (!this._ensureConnected()) return;
    this._jarvis.on_change_model(mode);
  },

  fetchModels() {
    if (!this._ensureConnected()) return;
    this._jarvis.on_fetch_models();
  },

  clearContext() {
    if (!this._ensureConnected()) return;
    this._jarvis.on_clear_context();
  },

  /** @param {string} actionId */
  confirmAction(actionId) {
    if (!this._ensureConnected()) return;
    this._jarvis.on_confirm_action(actionId);
  },

  /** @param {string} actionId */
  cancelAction(actionId) {
    if (!this._ensureConnected()) return;
    this._jarvis.on_cancel_action(actionId);
  },

  minimize() {
    if (!this._ensureConnected()) return;
    this._jarvis.on_minimize_window();
  },

  close() {
    if (!this._ensureConnected()) return;
    this._jarvis.on_close_window();
  },

  /** @param {string} msg */
  log(msg) {
    if (this._jarvis) this._jarvis.on_js_log(msg);
  },

  // ── Utilitaires ────────────────────────────────────────────────────────────

  _ensureConnected() {
    if (!this._jarvis) {
      console.warn('[Bridge] Appel avant connexion QWebChannel.');
      return false;
    }
    return true;
  },

  get isConnected() { return this._jarvis !== null; },
};
