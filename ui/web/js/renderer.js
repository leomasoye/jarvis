'use strict';

const Renderer = {
  init() {
    if (typeof mermaid !== 'undefined') {
      mermaid.initialize({
        startOnLoad: false,
        theme: 'dark',
        securityLevel: 'loose'
      });
      console.log('[Renderer] Mermaid initialisé.');
    }
  },

  /**
   * Rend le texte brut en HTML enrichi (Markdown + Mermaid).
   * @param {string} text 
   * @returns {string} html string
   */
  renderFull(text) {
    if (!text) return '';

    const mermaidBlocks = [];
    
    // 1. Extraire les balises <mermaid>
    let processedText = text.replace(/<mermaid>([\s\S]*?)<\/mermaid>/gi, (match, code) => {
      mermaidBlocks.push(code.trim());
      return `[MERMAID_BLOCK_${mermaidBlocks.length - 1}]`;
    });
    
    // Remplacement des blocs markdown ```mermaid en fallback
    processedText = processedText.replace(/```mermaid\n([\s\S]*?)\n```/gi, (match, code) => {
      mermaidBlocks.push(code.trim());
      return `[MERMAID_BLOCK_${mermaidBlocks.length - 1}]`;
    });

    // 2. Parser le Markdown
    let html = '';
    if (typeof marked !== 'undefined') {
      html = marked.parse(processedText);
    } else {
      html = processedText.replace(/\n/g, '<br>');
    }

    // 3. Purifier le HTML généré
    if (typeof DOMPurify !== 'undefined') {
      html = DOMPurify.sanitize(html);
    }

    // 4. Réinjecter les blocs Mermaid
    mermaidBlocks.forEach((code, index) => {
      const placeholder = `[MERMAID_BLOCK_${index}]`;
      const mermaidHtml = `<div class="mermaid">${this._escapeHtml(code)}</div>`;
      html = html.replace(`<p>${placeholder}</p>`, mermaidHtml);
      html = html.replace(placeholder, mermaidHtml);
    });

    return html;
  },

  /**
   * Rendu Mermaid sur les éléments du conteneur
   */
  renderMermaidDiagrams(container) {
    if (typeof mermaid !== 'undefined') {
      try {
        const nodes = container.querySelectorAll('.mermaid:not([data-processed="true"])');
        if (nodes.length > 0) {
          mermaid.run({ nodes: nodes });
        }
      } catch (e) {
        console.error('[Renderer] Erreur Mermaid:', e);
      }
    }
  },

  _escapeHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }
};
