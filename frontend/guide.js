// Local handbook: no messages, remote requests, storage or AI calls.
export function initializeGuide() {
  const toggle = document.querySelector('#guide-toggle');
  const panel = document.querySelector('#guide-panel');
  const title = document.querySelector('#guide-title');
  const close = () => {
    panel.hidden = true;
    toggle.setAttribute('aria-expanded', 'false');
    toggle.focus();
  };
  toggle.addEventListener('click', () => {
    if (!panel.hidden) { close(); return; }
    panel.hidden = false;
    toggle.setAttribute('aria-expanded', 'true');
    title.focus({ preventScroll: true });
  });
  document.querySelector('#guide-close').addEventListener('click', close);
  panel.addEventListener('keydown', event => {
    if (event.key === 'Escape') { event.preventDefault(); close(); }
  });
  toggle.hidden = false;
}
