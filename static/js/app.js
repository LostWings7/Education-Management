/**
 * Education Management Portal - Core Application Utilities & UI Controllers
 * Self-contained bundle supporting standard script tags and all modern browsers.
 */

(function () {
  'use strict';

  // ==========================================================================
  // 1. Navigation & Layout Controller
  // ==========================================================================
  function initNavigation() {
    // User Profile Dropdown Menu
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

    // Mobile Sidebar Toggle
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

    // Lucide Icons Render
    if (window.lucide && typeof window.lucide.createIcons === 'function') {
      window.lucide.createIcons();
    }
  }

  // ==========================================================================
  // 2. Universal Command Palette (Ctrl+K / Cmd+K)
  // ==========================================================================
  function initCommandPalette() {
    const searchModal = document.getElementById('globalSearchModal');
    const searchInput = document.getElementById('globalSearchInput');
    const searchResults = document.getElementById('globalSearchResults');
    const searchTriggerBtn = document.getElementById('searchTriggerBtn');
    const searchCloseKbd = document.getElementById('searchCloseKbd');

    if (!searchModal) return;

    function openSearch() {
      searchModal.style.display = 'flex';
      setTimeout(function () {
        if (searchInput) searchInput.focus();
      }, 50);
    }

    function closeSearch() {
      searchModal.style.display = 'none';
      if (searchInput) searchInput.value = '';
      if (searchResults) {
        searchResults.innerHTML = `
          <div style="padding: 2.5rem; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
            Type 2 or more characters to search academic entities...
          </div>
        `;
      }
    }

    if (searchTriggerBtn) searchTriggerBtn.addEventListener('click', openSearch);
    if (searchCloseKbd) searchCloseKbd.addEventListener('click', closeSearch);

    window.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (searchModal.style.display === 'flex') {
          closeSearch();
        } else {
          openSearch();
        }
      } else if (e.key === 'Escape' && searchModal.style.display === 'flex') {
        closeSearch();
      }
    });

    searchModal.addEventListener('click', function (e) {
      if (e.target === searchModal) {
        closeSearch();
      }
    });

    let searchTimeout = null;
    if (searchInput) {
      searchInput.addEventListener('input', function (e) {
        const val = e.target.value.trim();
        clearTimeout(searchTimeout);
        if (val.length < 2) {
          searchResults.innerHTML = `
            <div style="padding: 2.5rem; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
              Type 2 or more characters to search academic entities...
            </div>
          `;
          return;
        }

        searchTimeout = setTimeout(function () {
          fetch('/portal/api/search/?q=' + encodeURIComponent(val))
            .then(function (res) { return res.json(); })
            .then(function (data) {
              if (data.success && data.results && data.results.length > 0) {
                let html = '';
                data.results.forEach(function (item) {
                  html += `
                    <a href="${item.url}" style="padding: 0.85rem 1.25rem; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; text-decoration: none; color: inherit; transition: background 0.15s ease;">
                      <div>
                        <div style="font-weight: 600; font-size: 0.9rem; color: var(--text-primary);">${item.title}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.15rem;">${item.subtitle || ''}</div>
                      </div>
                      <span class="badge ${item.badge_class || 'badge-neutral'}">${item.category}</span>
                    </a>
                  `;
                });
                searchResults.innerHTML = html;
              } else {
                searchResults.innerHTML = `
                  <div style="padding: 2.5rem; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
                    No matching academic records found.
                  </div>
                `;
              }
            })
            .catch(function () {
              searchResults.innerHTML = `
                <div style="padding: 2.5rem; text-align: center; color: var(--color-danger); font-size: 0.85rem;">
                  Unable to complete search request.
                </div>
              `;
            });
        }, 200);
      });
    }
  }

  // ==========================================================================
  // 3. Universal "Why?" Evidence Inspector Drawer
  // ==========================================================================
  function initEvidenceInspector() {
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

    explainBtns.forEach(function (btn) {
      btn.addEventListener('click', function (e) {
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

    inspectorDrawer.addEventListener('click', function (e) {
      if (e.target === inspectorDrawer) {
        closeInspector();
      }
    });

    window.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && inspectorDrawer.style.display === 'flex') {
        closeInspector();
      }
    });

    // 1-Click Copilot Synthesis Trigger
    const askCopilotBtn = document.getElementById('askCopilotSynthesisBtn');
    if (askCopilotBtn) {
      askCopilotBtn.addEventListener('click', function () {
        const titleEl = document.getElementById('inspectorMetricTitle');
        const metric = titleEl ? titleEl.textContent : 'this academic metric';
        const prompt = 'Synthesize plain-language study recommendations for ' + metric + '.';
        window.location.href = '/portal/student/ai/copilot/?prompt=' + encodeURIComponent(prompt);
      });
    }
  }

  // ==========================================================================
  // 4. Interactive Architecture Flow Modal
  // ==========================================================================
  function initArchitectureFlow() {
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

    archModal.addEventListener('click', function (e) {
      if (e.target === archModal) {
        closeModal();
      }
    });

    window.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && archModal.style.display === 'flex') {
        closeModal();
      }
    });

    flowNodes.forEach(function (node) {
      node.addEventListener('click', function () {
        flowNodes.forEach(function (n) {
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

  // ==========================================================================
  // 5. Toast Notifications & Dismissible Alerts
  // ==========================================================================
  function showToast(message, type, duration) {
    type = type || 'info';
    duration = duration || 4000;

    let container = document.getElementById('portalToastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'portalToastContainer';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
      <div style="flex: 1; font-size: 0.85rem; font-weight: 500;">${message}</div>
      <button type="button" class="btn-ghost" style="padding: 0.2rem; cursor: pointer; color: var(--text-muted);">&times;</button>
    `;

    const closeBtn = toast.querySelector('button');
    closeBtn.addEventListener('click', function () {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(function () { toast.remove(); }, 200);
    });

    container.appendChild(toast);

    setTimeout(function () {
      if (toast.parentElement) {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(function () { toast.remove(); }, 200);
      }
    }, duration);
  }

  function initAlerts() {
    const alertCloseBtns = document.querySelectorAll('.alert-close');
    alertCloseBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        const alert = btn.closest('.alert, .toast');
        if (alert) {
          alert.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
          alert.style.opacity = '0';
          alert.style.transform = 'translateY(-4px)';
          setTimeout(function () { alert.remove(); }, 200);
        }
      });
    });
  }

  // ==========================================================================
  // 6. Scroll Reveals & Microinteractions
  // ==========================================================================
  function initInteractions() {
    const reveals = document.querySelectorAll('.reveal-on-scroll');
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.15 });

      reveals.forEach(function (el) { observer.observe(el); });
    } else {
      reveals.forEach(function (el) { el.classList.add('revealed'); });
    }

    document.querySelectorAll('.copilot-prompt-pill').forEach(function (pill) {
      pill.addEventListener('click', function () {
        const prompt = pill.getAttribute('data-prompt');
        const chatInput = document.getElementById('copilot-chat-input');
        if (chatInput) {
          chatInput.value = prompt;
          chatInput.focus();
        } else {
          window.location.href = '/portal/student/ai/copilot/?prompt=' + encodeURIComponent(prompt);
        }
      });
    });
  }

  // Expose Global Namespace
  window.EduPortal = {
    showToast: showToast,
    initNavigation: initNavigation,
    initCommandPalette: initCommandPalette,
    initEvidenceInspector: initEvidenceInspector,
    initArchitectureFlow: initArchitectureFlow
  };

  // Run on DOM Ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initNavigation();
      initCommandPalette();
      initEvidenceInspector();
      initArchitectureFlow();
      initAlerts();
      initInteractions();
    });
  } else {
    initNavigation();
    initCommandPalette();
    initEvidenceInspector();
    initArchitectureFlow();
    initAlerts();
    initInteractions();
  }

})();
