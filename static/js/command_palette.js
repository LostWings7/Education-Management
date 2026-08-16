/**
 * Education Management Portal - Universal Command Palette (Ctrl+K / Cmd+K)
 */

export function initCommandPalette() {
  const searchModal = document.getElementById('globalSearchModal');
  const searchInput = document.getElementById('globalSearchInput');
  const searchResults = document.getElementById('globalSearchResults');
  const searchTriggerBtn = document.getElementById('searchTriggerBtn');
  const searchCloseKbd = document.getElementById('searchCloseKbd');

  if (!searchModal) return;

  function openSearch() {
    searchModal.style.display = 'flex';
    setTimeout(() => {
      if (searchInput) searchInput.focus();
    }, 50);
  }

  function closeSearch() {
    searchModal.style.display = 'none';
    if (searchInput) searchInput.value = '';
    if (searchResults) {
      searchResults.innerHTML = `
        <div style="padding: 2rem; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
          Type 2 or more characters to search students, courses, assignments, or actions...
        </div>
      `;
    }
  }

  if (searchTriggerBtn) searchTriggerBtn.addEventListener('click', openSearch);
  if (searchCloseKbd) searchCloseKbd.addEventListener('click', closeSearch);

  window.addEventListener('keydown', (e) => {
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

  searchModal.addEventListener('click', (e) => {
    if (e.target === searchModal) {
      closeSearch();
    }
  });

  let searchTimeout = null;
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const val = e.target.value.trim();
      clearTimeout(searchTimeout);
      if (val.length < 2) {
        searchResults.innerHTML = `
          <div style="padding: 2rem; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
            Type 2 or more characters to search...
          </div>
        `;
        return;
      }

      searchTimeout = setTimeout(() => {
        fetch(`/portal/api/search/?q=${encodeURIComponent(val)}`)
          .then(res => res.json())
          .then(data => {
            if (data.success && data.results && data.results.length > 0) {
              let html = '';
              data.results.forEach(item => {
                html += `
                  <a href="${item.url}" class="command-result-item" style="padding: 0.85rem 1.25rem; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; text-decoration: none; color: inherit; transition: background 0.15s ease;">
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
                <div style="padding: 2rem; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
                  No matching academic records found.
                </div>
              `;
            }
          })
          .catch(() => {
            searchResults.innerHTML = `
              <div style="padding: 2rem; text-align: center; color: var(--color-danger); font-size: 0.85rem;">
                Unable to complete search request.
              </div>
            `;
          });
      }, 200);
    });
  }
}
