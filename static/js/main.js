/* ==========================================================================
   ConnectED — main.js
   Handles: sidebar mobile toggle, active nav link, alert auto-dismiss
   ========================================================================== */

(function () {
  'use strict';

  /* --------------------------------------------------------------------------
     1. SIDEBAR MOBILE TOGGLE
     - Hamburger button shows/hides sidebar on mobile
     - Clicking overlay dismisses sidebar
     - Body scroll locks while sidebar is open
  -------------------------------------------------------------------------- */
  const toggleBtn = document.getElementById('mobile-sidebar-toggle');
  const sidebar   = document.querySelector('.sidebar');

  if (toggleBtn && sidebar) {
    // Create overlay element once, insert after sidebar
    const overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    overlay.style.display = 'none';
    document.body.appendChild(overlay);

    function openSidebar() {
      sidebar.classList.add('show');
      overlay.style.display = 'block';
      document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
      sidebar.classList.remove('show');
      overlay.style.display = 'none';
      document.body.style.overflow = '';
    }

    toggleBtn.addEventListener('click', function () {
      sidebar.classList.contains('show') ? closeSidebar() : openSidebar();
    });

    overlay.addEventListener('click', closeSidebar);

    // Close sidebar on resize back to desktop
    window.addEventListener('resize', function () {
      if (window.innerWidth >= 768) {
        closeSidebar();
      }
    });
  }

  /* --------------------------------------------------------------------------
     2. ACTIVE LINK HIGHLIGHTING
     - Compares each sidebar link's href to the current page path
     - Adds .active class to the matching link
     - Handles exact match + prefix match (e.g. /challenges/detail/3/ highlights Challenges)
  -------------------------------------------------------------------------- */
  const currentPath = window.location.pathname;
  const sidebarLinks = document.querySelectorAll('.sidebar-link');

  sidebarLinks.forEach(function (link) {
    const href = link.getAttribute('href');

    // Skip placeholder links (#)
    if (!href || href === '#') return;

    // Exact match OR current path starts with the link's path
    // Give exact match higher priority to avoid /dashboard/ matching /dashboard/leaderboard/
    const isExact  = currentPath === href;
    const isPrefix = currentPath.startsWith(href) && href !== '/';

    if (isExact || isPrefix) {
      link.classList.add('active');
    }
  });

  /* --------------------------------------------------------------------------
     3. ALERT AUTO-DISMISS
     - Django flash messages (success, error, warning, info) disappear after 4s
     - Fade out animation via Bootstrap's built-in fade class
  -------------------------------------------------------------------------- */
  const alerts = document.querySelectorAll('.alert.alert-dismissible');

  alerts.forEach(function (alert) {
    setTimeout(function () {
      // Use Bootstrap's Alert.getOrCreateInstance if available, else manual fade
      if (window.bootstrap && window.bootstrap.Alert) {
        const bsAlert = window.bootstrap.Alert.getOrCreateInstance(alert);
        bsAlert.close();
      } else {
        alert.style.transition = 'opacity 0.5s ease';
        alert.style.opacity = '0';
        setTimeout(function () {
          alert.remove();
        }, 500);
      }
    }, 4000); // 4 seconds
  });

  /* --------------------------------------------------------------------------
     4. NOTIFICATION BADGE PULSE
     - Adds pulse animation class to notification badge if unread count > 0
  -------------------------------------------------------------------------- */
  const notifBadge = document.querySelector('.notification-badge');
  if (notifBadge) {
    notifBadge.classList.add('pulse-animation');
  }

})();
(function () {
  var PREFIX = 'draft:', TTL = 24 * 60 * 60 * 1000;
  var skip = /^(password|file|hidden|submit|button|reset|image)$/;

  document.querySelectorAll('[data-clear-draft]').forEach(function (el) {
    try { localStorage.removeItem(PREFIX + el.dataset.clearDraft); } catch (e) {}
  });

  document.querySelectorAll('form[data-draft]').forEach(function (form) {
    var key = PREFIX + form.dataset.draft;
    var fields = [].filter.call(form.elements, function (el) {
      return el.name && !skip.test(el.type) && !/password/i.test(el.name);
    });

    try {  // restore
      var saved = JSON.parse(localStorage.getItem(key) || 'null');
      if (saved && Date.now() - saved.t < TTL) {
        fields.forEach(function (el) {
          var v = saved.v[el.name];
          if (v === undefined) return;
          if (el.type === 'checkbox') el.checked = v;
          else if (el.type === 'radio') el.checked = (el.value === v);
          else if (el.tagName === 'SELECT') { if (el.selectedIndex <= 0) el.value = v; }
          else if (!el.value) el.value = v;   
        });
      }
    } catch (e) {}

    function saveNow() {
      var v = {};
      fields.forEach(function (el) {
        if (el.type === 'checkbox') v[el.name] = el.checked;
        else if (el.type === 'radio') { if (el.checked) v[el.name] = el.value; }
        else v[el.name] = el.value;
      });
      try { localStorage.setItem(key, JSON.stringify({ t: Date.now(), v: v })); } catch (e) {}
    }
    var timer;
    function save() { clearTimeout(timer); timer = setTimeout(saveNow, 300); }

    form.addEventListener('input', save);
    form.addEventListener('change', save);
    document.addEventListener('visibilitychange', function () { if (document.hidden) saveNow(); });
    window.addEventListener('pagehide', saveNow);   // fires right as they switch apps
  });
})();

/* OAuth popup: open a small window, update this page when it finishes */
(function () {
  var seen = 0;
  function toast(msg, ok) {
    var t = document.createElement('div');
    t.textContent = msg; t.setAttribute('role', 'status');
    t.style.cssText = 'position:fixed;left:50%;bottom:1.5rem;transform:translateX(-50%);z-index:2000;' +
      'padding:.7rem 1.1rem;border-radius:.5rem;color:#fff;font-weight:600;max-width:90vw;' +
      'box-shadow:0 8px 24px rgba(0,0,0,.25);background:' + (ok ? '#107d79' : '#b3261e');
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 4000);
  }
  function handle(d) {
    if (!d || d.type !== 'oauth-done') return;
    var now = Date.now();
    if (now - seen < 3000) return;            // both channels deliver; act once
    seen = now;
    toast(d.message, d.ok);
    if (!d.ok) return;
    var locks = document.querySelectorAll('fieldset[data-oauth-lock]');
    if (locks.length) {                        // challenge page: unlock in place, keep typed text and files
      locks.forEach(function (f) { f.disabled = false; });
      document.querySelectorAll('[data-oauth-gate]').forEach(function (el) { el.remove(); });
    } else {
      setTimeout(function () { location.reload(); }, 800);
    }
  }
  window.addEventListener('message', function (e) { if (e.origin === window.location.origin) handle(e.data); });
  var bc = ('BroadcastChannel' in window) ? new BroadcastChannel('connected-oauth') : null;
  if (bc) bc.onmessage = function (e) { handle(e.data); };

  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[data-oauth-popup]');
    if (!a) return;
    e.preventDefault();
    var u = new URL(a.href, window.location.origin);
    u.searchParams.set('popup', '1');
    var w = 600, h = 720;
    var win = window.open(u.toString(), 'oauth-popup', 'width=' + w + ',height=' + h +
      ',left=' + Math.round((screen.width - w) / 2) + ',top=' + Math.round((screen.height - h) / 2));
    if (!win) { window.location.href = a.href; return; }   // popup blocked: normal full-page flow
    win.focus();
  });
})();