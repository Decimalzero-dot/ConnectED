/* ConnectED guided tour: no dependencies. Steps are matched by sidebar link addresses. */
(function () {
  'use strict';
  var root = document.getElementById('cx-tour');
  if (!root) return;

  var role = root.dataset.role;
  var autoPending = root.dataset.auto === '1';
  var HOME_PATHS = ['/dashboard/', '/dashboard/employer/', '/management/', '/management/campus/'];

  var NOTIFS = { sel: 'a[href="/notifications/"]', title: 'Notifications',
    text: 'Updates land here. The number shows what you haven\'t opened yet.' };
  function settings(text) { return { sel: 'a[href^="/accounts/settings/"]', title: 'Settings', text: text }; }
  var REVIEW = { sel: 'a[href="/challenges/review/"]', title: 'Review queue',
    text: 'Submissions waiting for you. Open one to see the challenge brief next to the student\'s work.' };

  var STEPS = {
    student: [
      { sel: 'a[href="/dashboard/"]', title: 'Home', text: 'Your starting point: your progress and shortcuts.' },
      { sel: 'a[href="/challenges/"]', title: 'Challenges', text: 'Practical tasks at your level. Try the ones marked Guided first: each has a Start here guide and hints you can open one at a time.' },
      { sel: 'a[href="/dashboard/leaderboard/"]', title: 'Leaderboard', text: 'Points come from work a reviewer has passed. Focus on learning and the ranking follows.' },
      { sel: 'a[data-tour="portfolio"]', optional: true, title: 'My Portfolio', text: 'This is the page employers see: your passed challenges, scores and reviewer feedback. You choose in Settings whether it is public.' },
      NOTIFS,
      settings('Connect GitHub, set your year and details, choose which emails you get, and replay this tour any time from the Account tab.')
    ],
    campus_admin: [
      { sel: 'a[href="/management/campus/"]', title: 'Admin panel', text: 'Your campus at a glance: students, pending reviews and recent submissions.' },
      REVIEW,
      { sel: 'a[href="/management/campus/challenges/create/"]', optional: true, title: 'New challenge', text: 'Create challenges for your students. Add Start here links and hints so beginners are not lost.' },
      { sel: 'a[href="/management/employer-interests/"]', optional: true, title: 'Employer interests', text: 'Employers ask about your students here. You decide what gets forwarded.' },
      NOTIFS,
      settings('Your details, email preferences, and a replay of this tour.')
    ],
    super_admin: [
      { sel: 'a[href="/management/"]', title: 'Super admin', text: 'Platform overview: universities, campus admins and totals.' },
      { sel: 'a[href="/management/employers/"]', optional: true, title: 'Employers', text: 'Verify or reject employer accounts before they can browse students.' },
      { sel: 'a[href="/management/sponsorships/"]', optional: true, title: 'Sponsorships', text: 'Sponsorship enquiries from employers, with a status you can update.' },
      REVIEW,
      NOTIFS,
      settings('Your details, email preferences, and a replay of this tour.')
    ],
    employer: [
      { sel: 'a[href="/dashboard/employer/"]', title: 'Home', text: 'Your requests and where each one stands.' },
      { sel: 'a[href="/dashboard/leaderboard/"]', title: 'Browse students', text: 'Students ranked by reviewed work. Open a portfolio to see the evidence, then express interest. Requests go to the student\'s campus admin, who decides whether to forward them.' },
      { sel: 'a[href="/challenges/sponsor/"]', title: 'Sponsor challenges', text: 'Want challenges in your field? Tell us what you would sponsor.' },
      NOTIFS,
      settings('Your company details and a replay of this tour.')
    ]
  };

  var steps = [], i = 0, shield, spot, card, prevFocus, marked = false;

  function make(tag, cls) { var n = document.createElement(tag); n.className = cls; return n; }

  // A target counts as visible if it takes up space AND is horizontally on screen.
  // (The mobile sidebar is only moved off-screen with a transform, so a plain
  // "has a box" check would wrongly point the spotlight at empty space.)
  function visible(n) {
    if (!n.getClientRects().length) return false;
    var r = n.getBoundingClientRect();
    return r.right > 0 && r.left < window.innerWidth;
  }
  function findEl(step) {
    var all = document.querySelectorAll(step.sel);
    for (var k = 0; k < all.length; k++) if (visible(all[k])) return all[k];
    return null;
  }

  function markDone() {
    if (marked || !autoPending) return;
    marked = true;
    fetch(root.dataset.doneUrl, {
      method: 'POST', credentials: 'same-origin', keepalive: true,
      headers: { 'X-CSRFToken': root.dataset.csrf }
    }).catch(function () {});
  }

  function build() {
    shield = make('div', 'cx-tour-shield');
    spot = make('div', 'cx-tour-spot');
    card = make('div', 'cx-tour-card');
    card.setAttribute('role', 'dialog');
    card.setAttribute('aria-modal', 'true');
    card.setAttribute('aria-labelledby', 'cx-tour-title');
    card.innerHTML =
      '<p class="cx-tour-count"></p><h3 id="cx-tour-title" class="cx-tour-title"></h3>' +
      '<p class="cx-tour-text"></p><div class="cx-tour-dots" aria-hidden="true"></div>' +
      '<div class="cx-tour-actions"><button type="button" class="cx-tour-skip" data-act="skip">Skip tour</button>' +
      '<span><button type="button" class="cx-tour-back" data-act="back">Back</button>' +
      '<button type="button" class="cx-tour-next" data-act="next"></button></span></div>';
    document.body.appendChild(shield);
    document.body.appendChild(spot);
    document.body.appendChild(card);
    card.addEventListener('click', onCardClick);
    document.addEventListener('keydown', onKey, true);
    window.addEventListener('resize', reposition);
    window.addEventListener('scroll', reposition, true);
  }

  function reposition() {
    if (!card) return;
    var s = steps[i], t = s && findEl(s), r = t ? t.getBoundingClientRect() : null;
    if (r) {
      var pad = 6;
      spot.style.display = 'block';
      spot.style.left = (r.left - pad) + 'px';
      spot.style.top = (r.top - pad) + 'px';
      spot.style.width = (r.width + pad * 2) + 'px';
      spot.style.height = (r.height + pad * 2) + 'px';
      shield.classList.remove('is-dim');
    } else {                       // target not on screen (e.g. collapsed mobile sidebar): centred card
      spot.style.display = 'none';
      shield.classList.add('is-dim');
    }
    var gap = 16, cw = card.offsetWidth, ch = card.offsetHeight, vw = window.innerWidth, vh = window.innerHeight;
    var x, y;
    if (!r) { x = (vw - cw) / 2; y = (vh - ch) / 2; }
    else if (r.right + gap + cw <= vw) { x = r.right + gap; y = r.top + r.height / 2 - ch / 2; }
    else if (r.bottom + gap + ch <= vh) { x = r.left; y = r.bottom + gap; }
    else { x = r.left; y = r.top - ch - gap; }
    card.style.left = Math.max(12, Math.min(x, vw - cw - 12)) + 'px';
    card.style.top = Math.max(12, Math.min(y, vh - ch - 12)) + 'px';
  }

  function show() {
    var s = steps[i];
    card.querySelector('.cx-tour-count').textContent = 'Step ' + (i + 1) + ' of ' + steps.length;
    card.querySelector('.cx-tour-title').textContent = s.title;
    card.querySelector('.cx-tour-text').textContent = s.text;
    card.querySelector('.cx-tour-dots').innerHTML =
      steps.map(function (_, n) { return '<i class="' + (n === i ? 'on' : '') + '"></i>'; }).join('');
    card.querySelector('[data-act=back]').hidden = i === 0;
    card.querySelector('[data-act=next]').textContent = i === steps.length - 1 ? 'Finish' : 'Next';
    var t = findEl(s);
    if (t) t.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    reposition();
    card.querySelector('[data-act=next]').focus({ preventScroll: true });
  }

  function onCardClick(e) {
    var b = e.target.closest('[data-act]');
    if (!b) return;
    var a = b.dataset.act;
    if (a === 'skip') end();
    else if (a === 'back' && i > 0) { i--; show(); }
    else if (a === 'next') {
      if (i === steps.length - 1) end();
      else { i++; markDone(); show(); }
    }
  }

  function onKey(e) {
    if (!card) return;
    if (e.key === 'Escape') { e.preventDefault(); end(); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); card.querySelector('[data-act=next]').click(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); card.querySelector('[data-act=back]').click(); }
    else if (e.key === 'Tab') {            // keep keyboard focus inside the card
      var f = Array.prototype.filter.call(card.querySelectorAll('button'), function (n) { return !n.hidden; });
      var first = f[0], last = f[f.length - 1];
      if (!card.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
      else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  }

  function end() {
    markDone();
    [shield, spot, card].forEach(function (n) { if (n) n.remove(); });
    document.removeEventListener('keydown', onKey, true);
    window.removeEventListener('resize', reposition);
    window.removeEventListener('scroll', reposition, true);
    card = spot = shield = null;
    if (prevFocus && prevFocus.focus) prevFocus.focus({ preventScroll: true });
  }

  function start(manual) {
    if (card) return;
    steps = (STEPS[role] || STEPS.student).filter(function (s) {
      return !(s.optional && !document.querySelector(s.sel));
    });
    // Auto-start only if the sidebar links exist in the page (hidden is fine; mobile gets centred cards)
    var present = steps.filter(function (s) { return document.querySelector(s.sel); }).length;
    if (!steps.length || (!manual && present < 2)) return;
    i = 0;
    prevFocus = document.activeElement;
    build();
    show();
  }

  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-tour-start]')) { e.preventDefault(); start(true); }
  });

  function boot() {
    if (new URLSearchParams(location.search).get('tour') === '1') setTimeout(function () { start(true); }, 400);
    else if (autoPending && HOME_PATHS.indexOf(location.pathname) !== -1) setTimeout(function () { start(false); }, 900);
  }
  if (document.readyState === 'complete') boot(); else window.addEventListener('load', boot);
})();