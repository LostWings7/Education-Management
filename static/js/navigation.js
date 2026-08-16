/**
 * Education Management Portal - Navigation & Layout Controller
 */

export function initNavigation() {
  // 1. User Profile Dropdown Menu
  const userMenuTrigger = document.getElementById('userMenuTrigger');
  const userDropdown = document.getElementById('userDropdown');

  if (userMenuTrigger && userDropdown) {
    userMenuTrigger.addEventListener('click', function (e) {
      e.stopPropagation();
      userDropdown.classList.toggle('show');
    });

    document.addEventListener('click', function (e) {
      if (!userDropdown.contains(e.target) && !userMenuTrigger.contains(e.target)) {
        userDropdown.classList.remove('show');
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && userDropdown.classList.contains('show')) {
        userDropdown.classList.remove('show');
      }
    });
  }

  // 2. Responsive Mobile Sidebar Toggle
  const sidebarToggle = document.getElementById('sidebarToggle');
  const portalSidebar = document.getElementById('portalSidebar');

  if (sidebarToggle && portalSidebar) {
    sidebarToggle.addEventListener('click', function (e) {
      e.stopPropagation();
      portalSidebar.classList.toggle('open');
    });

    document.addEventListener('click', function (e) {
      if (window.innerWidth <= 768 && !portalSidebar.contains(e.target) && e.target !== sidebarToggle) {
        portalSidebar.classList.remove('open');
      }
    });
  }

  // 3. Lucide Icons re-render helper
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}
