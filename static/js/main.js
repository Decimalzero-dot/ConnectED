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