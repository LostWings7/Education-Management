/**
 * Education Management Portal - Interactive Architecture Flow Controller
 */

export function initArchitectureFlow() {
  const archModal = document.getElementById('architectureFlowModal');
  const archBtn = document.getElementById('architectureFlowBtn');
  const closeArchModalBtn = document.getElementById('closeArchModalBtn');
  const flowNodes = document.querySelectorAll('.flow-node');
  const flowNodeDetailBox = document.getElementById('flowNodeDetailBox');

  if (!archModal) return;

  function openModal() {
    archModal.style.display = 'flex';
    archModal.setAttribute('aria-hidden', 'false');
  }

  function closeModal() {
    archModal.style.display = 'none';
    archModal.setAttribute('aria-hidden', 'true');
  }

  if (archBtn) archBtn.addEventListener('click', openModal);
  if (closeArchModalBtn) closeArchModalBtn.addEventListener('click', closeModal);

  archModal.addEventListener('click', (e) => {
    if (e.target === archModal) {
      closeModal();
    }
  });

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && archModal.style.display === 'flex') {
      closeModal();
    }
  });

  flowNodes.forEach(node => {
    node.addEventListener('click', () => {
      flowNodes.forEach(n => {
        n.style.borderColor = 'var(--border-color)';
        n.style.backgroundColor = 'var(--bg-surface-secondary)';
      });
      node.style.borderColor = '#38bdf8';
      node.style.backgroundColor = 'rgba(56, 189, 248, 0.08)';

      if (flowNodeDetailBox) {
        flowNodeDetailBox.style.display = 'block';
        document.getElementById('flowNodeName').textContent = node.getAttribute('data-name');
        document.getElementById('flowNodeType').textContent = node.getAttribute('data-type');
        document.getElementById('flowNodeService').textContent = node.getAttribute('data-service');
        document.getElementById('flowNodeInputs').textContent = node.getAttribute('data-inputs');
        document.getElementById('flowNodeOutputs').textContent = node.getAttribute('data-outputs');
      }
    });
  });
}
