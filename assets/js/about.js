'use strict';
// Both languages are fully rendered; JavaScript only remembers the preference.
document.querySelectorAll('.language').forEach(link => {
  link.addEventListener('click', () => {
    try { localStorage.setItem('research-language', link.hreflang); } catch (_) {}
    const destination = new URL(link.href);
    destination.hash = location.hash;
    link.href = destination.href;
  });
});
// Refresh a previous Chirpy installation after a deployment.
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistration('/').then(registration => {
    if (registration) registration.update().catch(() => {});
  }).catch(() => {});
}
