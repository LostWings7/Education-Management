/**
 * Education Management Portal - Universal Evidence Inspector Controller
 * Signature Explainability & Mathematical Transparency Drawer
 */

export function initEvidenceInspector() {
  const inspectorDrawer = document.getElementById('evidenceInspectorDrawer');
  const closeInspectorBtn = document.getElementById('closeInspectorBtn');
  const explainBtns = document.querySelectorAll('.explain-btn');

  if (!inspectorDrawer) return;

  function openInspector(data) {
    const titleEl = document.getElementById('inspectorMetricTitle');
    const valueEl = document.getElementById('inspectorMetricValue');
    const serviceEl = document.getElementById('inspectorService');
    const formulaEl = document.getElementById('inspectorFormula');
    const summaryEl = document.getElementById('inspectorSummary');

    if (titleEl) titleEl.textContent = data.title || 'Metric Explanation';
    if (valueEl) valueEl.textContent = data.value || '';
    if (serviceEl) serviceEl.textContent = data.service || 'Authoritative Computing Engine';
    if (formulaEl) formulaEl.textContent = data.formula || 'Deterministic OLS Regression / Matrix Projection';
    if (summaryEl) summaryEl.textContent = data.summary || 'Authoritative data grounded in immutable academic event records.';

    inspectorDrawer.style.display = 'flex';
    inspectorDrawer.setAttribute('aria-hidden', 'false');
  }

  function closeInspector() {
    inspectorDrawer.style.display = 'none';
    inspectorDrawer.setAttribute('aria-hidden', 'true');
  }

  explainBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const data = {
        title: btn.getAttribute('data-title'),
        value: btn.getAttribute('data-value'),
        service: btn.getAttribute('data-service'),
        formula: btn.getAttribute('data-formula'),
        summary: btn.getAttribute('data-summary')
      };
      openInspector(data);
    });
  });

  if (closeInspectorBtn) {
    closeInspectorBtn.addEventListener('click', closeInspector);
  }

  inspectorDrawer.addEventListener('click', (e) => {
    if (e.target === inspectorDrawer) {
      closeInspector();
    }
  });

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && inspectorDrawer.style.display === 'flex') {
      closeInspector();
    }
  });

  // 1-Click Copilot Synthesis Trigger
  const askCopilotBtn = document.getElementById('askCopilotSynthesisBtn');
  if (askCopilotBtn) {
    askCopilotBtn.addEventListener('click', () => {
      const metric = document.getElementById('inspectorMetricTitle')?.textContent || 'this academic metric';
      const prompt = `Synthesize plain-language study recommendations for ${metric}.`;
      window.location.href = `/portal/student/ai/copilot/?prompt=${encodeURIComponent(prompt)}`;
    });
  }
}
