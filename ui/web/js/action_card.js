'use strict';

const ActionCard = {
  /**
   * Crée et affiche une Action Card dans le chat.
   * @param {string} jsonPayload 
   */
  render(jsonPayload) {
    try {
      const data = JSON.parse(jsonPayload);
      const actionId = data.id;
      const toolName = data.tool;
      const description = data.description;
      const params = data.params;
      const risk = data.risk;

      const card = document.createElement('div');
      card.className = `action-card risk-${risk.toLowerCase()}`;
      card.id = `action-card-${actionId}`;

      let paramsHtml = '';
      for (const [k, v] of Object.entries(params)) {
        paramsHtml += `<li><strong>${k}:</strong> ${v}</li>`;
      }

      card.innerHTML = `
        <div class="action-header">
          <span class="action-icon">🛡️</span>
          <strong>Autorisation requise</strong>
        </div>
        <div class="action-body">
          <p>JARVIS souhaite exécuter l'action suivante :</p>
          <p class="action-desc">${description}</p>
          <ul class="action-params">${paramsHtml}</ul>
        </div>
        <div class="action-footer">
          <button class="btn btn-cancel" onclick="ActionCard.cancel('${actionId}')">Annuler</button>
          <button class="btn btn-confirm" onclick="ActionCard.confirm('${actionId}')">Confirmer</button>
        </div>
      `;

      if (typeof Chat !== 'undefined') {
        Chat.addCustomWidget(card);
      }
    } catch (e) {
      console.error('[ActionCard] Erreur lors du rendu:', e);
    }
  },

  confirm(actionId) {
    this._disableCard(actionId);
    if (typeof Bridge !== 'undefined') {
      Bridge.confirmAction(actionId);
    }
  },

  cancel(actionId) {
    this._disableCard(actionId);
    if (typeof Bridge !== 'undefined') {
      Bridge.cancelAction(actionId);
    }
  },

  _disableCard(actionId) {
    const card = document.getElementById(`action-card-${actionId}`);
    if (card) {
      const buttons = card.querySelectorAll('button');
      buttons.forEach(b => {
        b.disabled = true;
        b.style.opacity = '0.5';
      });
    }
  }
};
