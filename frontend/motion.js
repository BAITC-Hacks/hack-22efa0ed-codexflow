export function initializeMotion() {
  const preference = window.matchMedia?.('(prefers-reduced-motion: reduce)');
  const numberMotion = document.querySelector('.number-motion');
  const toggle = document.querySelector('#number-motion-toggle');
  let paused = false;
  function updateNumbers() {
    numberMotion.dataset.paused = String(paused || Boolean(preference?.matches));
    document.body.dataset.motionPaused = numberMotion.dataset.paused;
    toggle.hidden = Boolean(preference?.matches);
    toggle.setAttribute('aria-pressed', String(paused));
    toggle.textContent = paused ? 'Продолжить анимацию' : 'Остановить анимацию';
  }
  toggle.addEventListener('click', () => { paused = !paused; updateNumbers(); });
  preference?.addEventListener?.('change', updateNumbers);
  updateNumbers();
  if (preference?.matches || !('IntersectionObserver' in window)) return;
  const sections = [...document.querySelectorAll('#order-form, .results, footer')];
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.remove('reveal-pending');
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.08 });
  sections.forEach(section => {
    section.classList.add('scroll-reveal', 'reveal-pending');
    observer.observe(section);
    section.addEventListener('focusin', () => {
      section.classList.remove('reveal-pending');
      observer.unobserve(section);
    }, { once: true });
  });
  preference?.addEventListener?.('change', event => {
    if (!event.matches) return;
    observer.disconnect();
    sections.forEach(section => section.classList.remove('reveal-pending'));
  });
}
