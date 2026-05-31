/**
 * search.js — V2 Quick Navigation Search
 *
 * TRACE: UI → Logic → DOM
 * Component: QuickSearch
 * Mounted in: #v2-search-wrap (inside .header-controls)
 * Reads from: AppState 'versions' (array of VersionSummary)
 *
 * User actions:
 *   Type "v3"  → matches version_id "v3"  → expands accordion item, scrolls, highlights
 *   Type "r7"  → matches review_id  "r7"  → expands parent accordion, scrolls review row, highlights
 *   ↑ / ↓     → navigate dropdown items
 *   Enter      → activate highlighted item
 *   Esc        → close dropdown, clear input
 *   Click away → close dropdown
 *
 * Logic:
 *   - Index is rebuilt from AppState.get('versions') whenever 'versions' changes
 *   - Match: case-insensitive prefix match on version_id and review_id
 *   - No AI / LLM — pure string matching
 *
 * Navigation targets:
 *   - Version: #accordion-{vid} → add .expanded, scroll #v2-main, highlight header
 *   - Review:  parent accordion expanded, then .review-item[data-review-id] scrolled + highlighted
 *
 * Highlight:
 *   - Adds .qs-active-target for 1.8 s then removes (CSS handles pulse animation)
 */

'use strict';

const QuickSearch = (() => {

  // ── Internal state ────────────────────────────────────────
  /** @type {Array<{type:'version'|'review', id:string, label:string, versionId:string}>} */
  let _index       = [];
  let _activeIdx   = -1;   // keyboard-highlighted dropdown row
  let _open        = false;
  let _inputEl     = null;
  let _dropdownEl  = null;
  let _highlightTimer = null;

  // ── Index builder ─────────────────────────────────────────
  /**
   * Flatten AppState versions + their reviews into a searchable flat list.
   * Called once on mount and again whenever AppState 'versions' changes.
   */
  function _buildIndex() {
    const state    = window.AppState;
    const versions = state ? (state.get('versions') || []) : [];
    _index = [];

    versions.forEach(v => {
      const vid = (v.version_id || '').trim();
      if (!vid) return;

      _index.push({
        type:      'version',
        id:        vid,
        label:     vid + (v.label ? ' – ' + v.label : ''),
        versionId: vid,
      });

      (v.reviews || []).forEach(r => {
        const rid = (r.review_id || '').trim();
        if (!rid) return;
        _index.push({
          type:      'review',
          id:        rid,
          label:     rid + (r.persona ? ' · ' + r.persona : ''),
          versionId: vid,
        });
      });
    });
  }

  // ── Match logic ───────────────────────────────────────────
  /**
   * Return index entries whose id starts with the query (case-insensitive).
   * Empty query → empty results (don't flood the dropdown on focus).
   * @param {string} query
   * @returns {Array}
   */
  function _match(query) {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return _index.filter(entry => entry.id.toLowerCase().startsWith(q));
  }

  // ── Dropdown render ───────────────────────────────────────
  /**
   * Rebuild the dropdown list from filtered results.
   * @param {Array} results
   */
  function _renderDropdown(results) {
    if (!_dropdownEl) return;

    if (results.length === 0) {
      _dropdownEl.innerHTML =
        '<div class="qs-empty">No match — try <em>v1</em> or <em>r3</em></div>';
      _setOpen(true);
      return;
    }

    _dropdownEl.innerHTML = results.map((entry, i) => {
      const typeIcon = entry.type === 'version' ? '📄' : '🔍';
      const typeBadge = `<span class="qs-type-badge qs-type-${entry.type}">${entry.type}</span>`;
      return `
        <div class="qs-item"
             role="option"
             aria-selected="false"
             data-idx="${i}"
             data-type="${entry.type}"
             data-id="${_esc(entry.id)}"
             data-version-id="${_esc(entry.versionId)}"
             onmousedown="QuickSearch.onItemMouseDown(event,this)">
          <span class="qs-item-icon" aria-hidden="true">${typeIcon}</span>
          <span class="qs-item-label">${_escAndHighlight(entry.label, _inputEl ? _inputEl.value.trim() : '')}</span>
          ${typeBadge}
        </div>`;
    }).join('');

    _setOpen(true);
    _setActive(-1);  // reset keyboard cursor
  }

  // ── Open / close ──────────────────────────────────────────
  function _setOpen(isOpen) {
    _open = isOpen;
    if (!_dropdownEl) return;
    if (isOpen) {
      _dropdownEl.removeAttribute('hidden');
    } else {
      _dropdownEl.setAttribute('hidden', '');
      _setActive(-1);
    }
  }

  // ── Keyboard active item ──────────────────────────────────
  function _setActive(idx) {
    _activeIdx = idx;
    if (!_dropdownEl) return;
    const items = _dropdownEl.querySelectorAll('.qs-item');
    items.forEach((el, i) => {
      el.classList.toggle('qs-item-active', i === idx);
      el.setAttribute('aria-selected', String(i === idx));
    });
    // Scroll active item into view within dropdown
    if (idx >= 0 && items[idx]) {
      items[idx].scrollIntoView({ block: 'nearest' });
    }
  }

  // ── Navigation core ───────────────────────────────────────
  /**
   * Main navigation entry point.
   * Expands the correct accordion item, scrolls it into view, and
   * highlights the target element for 1.8 s.
   *
   * @param {'version'|'review'} type
   * @param {string} id         - version_id or review_id
   * @param {string} versionId  - parent version_id (same as id for version type)
   */
  function navigateTo(type, id, versionId) {
    // 1. Expand the parent accordion item
    const accordionItem = document.getElementById('accordion-' + versionId);
    if (accordionItem) {
      accordionItem.classList.add('expanded');
      const header = accordionItem.querySelector('.accordion-header');
      if (header) header.setAttribute('aria-expanded', 'true');
    }

    // 2. Resolve the DOM target to scroll to
    let target = null;
    if (type === 'version') {
      target = accordionItem;
    } else {
      // review-item inside the expanded accordion
      target = document.querySelector(
        `.review-item[data-review-id="${CSS.escape(id)}"]`
      );
    }

    // 3. Scroll target into view inside #v2-main
    //    Use a small delay so the accordion CSS max-height transition
    //    has started before we measure position (avoids scrolling to 0).
    if (target) {
      setTimeout(() => {
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        _pulseHighlight(target);
      }, 60);
    }

    // 4. Update AppState selection so context banner + sidebar sync
    const state = window.AppState;
    if (state) {
      const versions = state.get('versions') || [];
      const version  = versions.find(v => v.version_id === versionId) || null;

      if (type === 'version' && version) {
        state.selectVersion(version);
      } else if (type === 'review') {
        let review = null;
        for (const v of versions) {
          review = (v.reviews || []).find(r => r.review_id === id) || null;
          if (review) break;
        }
        if (review) state.selectReview(review);
      }
    }
  }

  // ── Pulse highlight ───────────────────────────────────────
  /**
   * Temporarily add .qs-active-target class for a visual pulse.
   * Removes itself after 1.8 s.
   * @param {HTMLElement} el
   */
  function _pulseHighlight(el) {
    clearTimeout(_highlightTimer);
    // Remove from any previous target
    document.querySelectorAll('.qs-active-target').forEach(e => {
      e.classList.remove('qs-active-target');
    });
    el.classList.add('qs-active-target');
    _highlightTimer = setTimeout(() => {
      el.classList.remove('qs-active-target');
    }, 1800);
  }

  // ── HTML helpers ──────────────────────────────────────────
  function _esc(s) {
    if (typeof s !== 'string') s = String(s == null ? '' : s);
    return s
      .replace(/&/g,  '&amp;')
      .replace(/</g,  '&lt;')
      .replace(/>/g,  '&gt;')
      .replace(/"/g,  '&quot;');
  }

  /**
   * Escape label and bold the matching prefix.
   * @param {string} label
   * @param {string} query
   * @returns {string} safe HTML
   */
  function _escAndHighlight(label, query) {
    const safe = _esc(label);
    if (!query) return safe;
    const q = _esc(query.trim());
    if (!q) return safe;
    // Bold the first occurrence of the query prefix (case-insensitive)
    const re = new RegExp('(' + q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'i');
    return safe.replace(re, '<strong class="qs-highlight">$1</strong>');
  }

  // ── Event: input ──────────────────────────────────────────
  function onInput() {
    if (!_inputEl) return;
    const q       = _inputEl.value;
    const results = _match(q);
    if (!q.trim()) {
      _setOpen(false);
      return;
    }
    _renderDropdown(results);
  }

  // ── Event: keydown on input ───────────────────────────────
  function onKeyDown(e) {
    if (!_open) {
      if (e.key === 'Escape') { _clearInput(); }
      return;
    }

    const items = _dropdownEl ? _dropdownEl.querySelectorAll('.qs-item') : [];
    const count = items.length;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        _setActive((_activeIdx + 1) % count);
        break;
      case 'ArrowUp':
        e.preventDefault();
        _setActive((_activeIdx - 1 + count) % count);
        break;
      case 'Enter':
        e.preventDefault();
        if (_activeIdx >= 0 && items[_activeIdx]) {
          _activateItem(items[_activeIdx]);
        } else if (count === 1) {
          // Auto-select the only result
          _activateItem(items[0]);
        }
        break;
      case 'Escape':
        _setOpen(false);
        _clearInput();
        break;
      default:
        break;
    }
  }

  // ── Event: mousedown on dropdown item ─────────────────────
  // mousedown fires before blur, so we can act before input loses focus
  function onItemMouseDown(event, el) {
    event.preventDefault();  // prevent input blur before we read the item
    _activateItem(el);
  }

  // ── Event: input blur ─────────────────────────────────────
  function onBlur() {
    // Delay close so onItemMouseDown can fire first
    setTimeout(() => _setOpen(false), 150);
  }

  // ── Activate a dropdown item ──────────────────────────────
  function _activateItem(el) {
    const type      = el.dataset.type;
    const id        = el.dataset.id;
    const versionId = el.dataset.versionId;
    _setOpen(false);
    _clearInput();
    navigateTo(type, id, versionId);
  }

  // ── Clear input ───────────────────────────────────────────
  function _clearInput() {
    if (_inputEl) _inputEl.value = '';
  }

  // ── Build HTML for the search widget ─────────────────────
  function _buildWidget() {
    return `
      <div class="qs-wrap" id="v2-qs-wrap" role="combobox"
           aria-expanded="false" aria-haspopup="listbox" aria-owns="v2-qs-dropdown">
        <span class="qs-icon" aria-hidden="true">⌕</span>
        <input id="v2-qs-input"
               class="qs-input"
               type="search"
               autocomplete="off"
               spellcheck="false"
               placeholder="Jump to… v3 or r7"
               aria-label="Quick navigation search"
               aria-autocomplete="list"
               aria-controls="v2-qs-dropdown"
               oninput="QuickSearch.onInput()"
               onkeydown="QuickSearch.onKeyDown(event)"
               onblur="QuickSearch.onBlur()">
        <div id="v2-qs-dropdown"
             class="qs-dropdown"
             role="listbox"
             aria-label="Search results"
             hidden>
        </div>
      </div>`;
  }

  // ── Mount ─────────────────────────────────────────────────
  /**
   * Inject the widget into #v2-search-wrap and wire up AppState.
   * Call once after DOM ready.
   */
  function mount() {
    const container = document.getElementById('v2-search-wrap');
    if (!container) return;

    container.innerHTML = _buildWidget();
    _inputEl    = document.getElementById('v2-qs-input');
    _dropdownEl = document.getElementById('v2-qs-dropdown');

    // Build initial index (versions may already be loaded)
    _buildIndex();

    // Re-index whenever versions change (renderAll rebuilds accordion DOM too)
    const state = window.AppState;
    if (state) {
      state.subscribe('versions', () => _buildIndex());
    }

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
      const wrap = document.getElementById('v2-qs-wrap');
      if (wrap && !wrap.contains(e.target)) {
        _setOpen(false);
      }
    });
  }

  // ── Public API ────────────────────────────────────────────
  return {
    mount,
    navigateTo,
    onInput,
    onKeyDown,
    onBlur,
    onItemMouseDown,
  };

})();

window.QuickSearch = QuickSearch;

// Auto-mount when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => QuickSearch.mount());
} else {
  QuickSearch.mount();
}
