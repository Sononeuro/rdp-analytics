import { registerSW } from 'virtual:pwa-register';

/**
 * Registers the Workbox-generated service worker and shows a lightweight,
 * accessible in-game prompt when a new build is available. The real in-game
 * UI for this comes online later; for now we use a minimal DOM banner so we
 * can validate the update flow end-to-end on Vercel previews.
 */
export function registerServiceWorker(): void {
  if (typeof window === 'undefined') return;
  if (!('serviceWorker' in navigator)) return;

  const updateSW = registerSW({
    immediate: false,
    onNeedRefresh() {
      showUpdateBanner(() => {
        void updateSW(true);
      });
    },
    onOfflineReady() {
      showTransientToast('Ready to play offline.');
    },
    onRegisteredSW(swUrl) {
      // eslint-disable-next-line no-console
      console.info('[pwa] service worker registered:', swUrl);
    },
    onRegisterError(error) {
      console.error('[pwa] service worker registration failed:', error);
    },
  });
}

function showUpdateBanner(onAccept: () => void): void {
  const existing = document.getElementById('pwa-update-banner');
  if (existing) existing.remove();

  const banner = document.createElement('div');
  banner.id = 'pwa-update-banner';
  banner.setAttribute('role', 'status');
  banner.setAttribute('aria-live', 'polite');
  Object.assign(banner.style, bannerBaseStyle, {
    bottom: 'calc(16px + env(safe-area-inset-bottom, 0px))',
  } satisfies Partial<CSSStyleDeclaration>);

  const label = document.createElement('span');
  label.textContent = 'A new version of Bellwether is available.';
  label.style.flex = '1';

  const reloadBtn = document.createElement('button');
  reloadBtn.type = 'button';
  reloadBtn.textContent = 'Reload';
  Object.assign(reloadBtn.style, buttonStyle);
  reloadBtn.addEventListener('click', () => {
    banner.remove();
    onAccept();
  });

  const dismissBtn = document.createElement('button');
  dismissBtn.type = 'button';
  dismissBtn.textContent = 'Later';
  dismissBtn.setAttribute('aria-label', 'Dismiss update prompt');
  Object.assign(dismissBtn.style, { ...buttonStyle, background: 'transparent' });
  dismissBtn.addEventListener('click', () => banner.remove());

  banner.appendChild(label);
  banner.appendChild(reloadBtn);
  banner.appendChild(dismissBtn);
  document.body.appendChild(banner);
}

function showTransientToast(message: string): void {
  const toast = document.createElement('div');
  toast.setAttribute('role', 'status');
  toast.textContent = message;
  Object.assign(toast.style, bannerBaseStyle, {
    bottom: 'calc(16px + env(safe-area-inset-bottom, 0px))',
    opacity: '0',
    transition: 'opacity 240ms ease',
  } satisfies Partial<CSSStyleDeclaration>);
  document.body.appendChild(toast);
  requestAnimationFrame(() => {
    toast.style.opacity = '1';
  });
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 320);
  }, 2400);
}

const bannerBaseStyle: Partial<CSSStyleDeclaration> = {
  position: 'fixed',
  left: '50%',
  transform: 'translateX(-50%)',
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  padding: '12px 16px',
  borderRadius: '12px',
  background: 'rgba(11, 29, 58, 0.95)',
  color: '#f4f6fb',
  boxShadow: '0 6px 24px rgba(0, 0, 0, 0.35)',
  font: '14px system-ui, sans-serif',
  zIndex: '9999',
  maxWidth: 'calc(100vw - 32px)',
};

const buttonStyle: Partial<CSSStyleDeclaration> = {
  appearance: 'none',
  border: '1px solid rgba(244, 246, 251, 0.25)',
  borderRadius: '8px',
  padding: '8px 12px',
  background: 'rgba(244, 246, 251, 0.1)',
  color: '#f4f6fb',
  font: '600 13px system-ui, sans-serif',
  cursor: 'pointer',
  minHeight: '44px',
  minWidth: '44px',
};
