'use strict';
// No email is sent, no external service is called automatically, and mailto
// preferences are never changed. The visitor chooses how to contact the author.
(() => {
  const contact = document.getElementById('contact-email');
  const copy = document.getElementById('copy-email');
  const fallback = document.getElementById('email-copy-fallback');
  const status = document.getElementById('email-status');
  if (!contact || !copy || !fallback || !status) return;
  const email = contact.dataset.email;
  if (!email) return;
  const korean = document.documentElement.lang === 'ko';
  copy.addEventListener('click', async () => {
    copy.disabled = true;
    status.textContent = '';
    try {
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        throw new Error('Clipboard unavailable');
      }
      await navigator.clipboard.writeText(email);
      fallback.hidden = true;
      status.textContent = korean ? '이메일 주소를 복사했어요.' : 'Email address copied.';
    } catch (_) {
      fallback.hidden = false;
      fallback.value = email;
      fallback.focus();
      fallback.select();
      fallback.setSelectionRange(0, email.length);
      status.textContent = korean
        ? '자동 복사가 허용되지 않았어요. 선택된 주소를 직접 복사해 주세요.'
        : 'Automatic copying is unavailable. Copy the selected address manually.';
    } finally {
      copy.disabled = false;
    }
  });
  copy.hidden = false;
})();
