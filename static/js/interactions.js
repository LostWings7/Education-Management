/**
 * Education Management Portal - Scroll Reveals, Counters & Microinteractions
 */

export function initInteractions() {
  // 1. Scroll-triggered reveal animations
  const reveals = document.querySelectorAll('.reveal-on-scroll');
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });

    reveals.forEach(el => observer.observe(el));
  } else {
    reveals.forEach(el => el.classList.add('revealed'));
  }

  // 2. Copilot prompt pill clicks
  document.querySelectorAll('.copilot-prompt-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      const prompt = pill.getAttribute('data-prompt');
      const chatInput = document.getElementById('copilot-chat-input');
      if (chatInput) {
        chatInput.value = prompt;
        chatInput.focus();
      } else {
        window.location.href = `/portal/student/ai/copilot/?prompt=${encodeURIComponent(prompt)}`;
      }
    });
  });
}
