/**
 * Education Management Portal - Toast Notification Manager
 */

export function showToast(message, type = 'info', duration = 4000) {
  let container = document.getElementById('portalToastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'portalToastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.setAttribute('role', 'alert');
  toast.innerHTML = `
    <div style="flex: 1; font-size: 0.85rem; font-weight: 500;">${message}</div>
    <button type="button" class="btn-ghost" style="padding: 0.2rem; cursor: pointer; color: var(--text-muted);">&times;</button>
  `;

  const closeBtn = toast.querySelector('button');
  closeBtn.addEventListener('click', () => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 200);
  });

  container.appendChild(toast);

  setTimeout(() => {
    if (toast.parentElement) {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 200);
    }
  }, duration);
}

export function initAlerts() {
  const alertCloseBtns = document.querySelectorAll('.alert-close');
  alertCloseBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const alert = btn.closest('.alert');
      if (alert) {
        alert.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-4px)';
        setTimeout(() => alert.remove(), 200);
      }
    });
  });
}
