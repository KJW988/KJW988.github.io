/* Two horizontal bodies: a driven highlighter, and a heavier inertial word.
 * No animation keyframes. Impulse contact, compliant pull and damped docking
 * are integrated at 240 Hz; rendering is independent of display refresh rate.
 * This is a stylized UI model, not a simulation of a literal highlighter pen.
 */
'use strict';
(() => {
  const STEP = 1 / 240;
  const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
  function create(gap, travel) {
    return { gap, travel, x: 0, v: 0, u: 0, w: 0, t: 0,
      attached: false, contacts: 0, firstContact: null, quiet: 0 };
  }
  function advance(s, dt = STEP) {
    const mass = 1.45;
    const target = s.t < .07 ? -Math.min(4, s.travel * .06)
      : s.t < .42 ? s.gap + s.travel : 0;
    let markerForce = 220 * (target - s.x) - 28 * s.v;
    let wordForce = -3.5 * s.w;
    if (s.attached) {
      // A compliant connection transfers the pull, not an imposed position.
      // The word keeps its own momentum when the marker starts to return.
      const anchor = Math.max(0, s.x - s.gap);
      const anchorVelocity = s.x > s.gap ? s.v : 0;
      const tension = 180 * (s.u - anchor) + 15 * (s.w - anchorVelocity);
      wordForce -= tension;
      if (s.x > s.gap) markerForce += tension;
      // The attachment returns to its original spacing near the home position.
      // Add smoothly increasing damping instead of abruptly stopping the word.
      const dock = clamp((s.gap - s.x) / Math.max(2, s.gap), 0, 1);
      wordForce -= 18 * dock * dock * (3 - 2 * dock) * s.w;
    }
    s.v += markerForce * dt;
    s.w += wordForce / mass * dt;
    s.x += s.v * dt;
    s.u += s.w * dt;
    const penetration = s.x - s.gap - s.u;
    if (penetration > 0) {
      // Resolve the actual edges, then exchange momentum with low restitution.
      const inverseMass = 1 + 1 / mass;
      s.x -= penetration / inverseMass;
      s.u += penetration / (mass * inverseMass);
      const closingSpeed = s.v - s.w;
      if (closingSpeed > 0) {
        const impulse = 1.10 * closingSpeed / inverseMass;
        s.v -= impulse;
        s.w += impulse / mass;
        s.contacts += 1;
      }
      if (!s.attached) s.firstContact = s.t;
      s.attached = true;
    }
    s.t += dt;
    const slow = Math.max(Math.abs(s.x), Math.abs(s.u)) < .035
      && Math.max(Math.abs(s.v), Math.abs(s.w)) < .22;
    s.quiet = s.t > .85 && slow ? s.quiet + dt : 0;
    return s;
  }
  // The same integrator can be tested without a browser or network connection.
  if (typeof module === 'object' && module.exports) module.exports = { STEP, create, advance };
  if (typeof document === 'undefined') return;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const hover = matchMedia('(hover: hover) and (pointer: fine)');
  document.querySelectorAll('.moves-pair').forEach(pair => {
    const mark = pair.querySelector('.moves-mark');
    const us = pair.querySelector('.moves-us');
    if (!mark || !us) return;
    let state = null, raf = 0, lastTime = 0, accumulator = 0;
    mark.setAttribute('role', 'button');
    mark.setAttribute('tabindex', '0');
    mark.setAttribute('aria-label', document.documentElement.lang === 'ko'
      ? 'Moves Us. 모션 재생' : 'Play the Moves Us motion');
    function stop() {
      cancelAnimationFrame(raf); raf = 0; state = null; lastTime = 0; accumulator = 0;
      pair.classList.remove('is-moving');
      pair.style.removeProperty('--marker-x');
      pair.style.removeProperty('--us-x');
    }
    function frame(now) {
      if (!state) return;
      if (!lastTime) lastTime = now;
      accumulator += clamp((now - lastTime) / 1000, 0, .05);
      lastTime = now;
      while (accumulator >= STEP) {
        advance(state); accumulator -= STEP;
      }
      if (![state.x, state.v, state.u, state.w].every(Number.isFinite)
          || state.t > 5 || state.quiet > .075) {
        stop(); pair.dispatchEvent(new Event('movesmotionend')); return;
      }
      pair.style.setProperty('--marker-x', state.x.toFixed(3) + 'px');
      pair.style.setProperty('--us-x', state.u.toFixed(3) + 'px');
      raf = requestAnimationFrame(frame);
    }
    function play() {
      if (reduced.matches || state) return;
      const a = mark.getBoundingClientRect();
      const b = us.getBoundingClientRect();
      const outer = pair.parentElement.getBoundingClientRect();
      const fontSize = parseFloat(getComputedStyle(mark).fontSize) || 48;
      const room = Math.max(0, Math.min(outer.right, document.documentElement.clientWidth - 12) - b.right - 8);
      const travel = Math.min(64, fontSize * .95, room * .72);
      if (travel < 3) return;
      const gap = Math.max(0, b.left - a.right);
      state = create(gap, travel);
      pair.classList.add('is-moving');
      raf = requestAnimationFrame(frame);
    }
    // The stationary word is the trigger: a moving box cannot re-enter itself.
    mark.addEventListener('pointerenter', () => { if (hover.matches) play(); });
    mark.addEventListener('click', play);
    mark.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); play(); }
    });
    window.addEventListener('resize', stop, { passive: true });
    document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
    reduced.addEventListener('change', stop);
  });
})();
