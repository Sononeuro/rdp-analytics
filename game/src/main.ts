import Phaser from 'phaser';
import { BootScene } from '@scenes/BootScene';
import { registerServiceWorker } from '@pwa/registerSW';

const PARENT_ID = 'game';
const BACKGROUND = '#0b1d3a';

const config: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  parent: PARENT_ID,
  backgroundColor: BACKGROUND,
  pixelArt: true,
  roundPixels: true,
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH,
    width: 960,
    height: 540,
  },
  fps: { target: 60, min: 30, smoothStep: true },
  input: {
    activePointers: 3,
    smoothFactor: 0.2,
  },
  render: {
    antialias: false,
    powerPreference: 'high-performance',
  },
  scene: [BootScene],
  audio: {
    disableWebAudio: false,
  },
  banner: false,
};

function hideBootFallback(): void {
  const el = document.getElementById('boot-fallback');
  if (el) el.classList.add('hide');
}

function start(): void {
  const game = new Phaser.Game(config);
  game.events.once(Phaser.Core.Events.READY, hideBootFallback);

  // Pause audio when tab is hidden, per spec.
  document.addEventListener('visibilitychange', () => {
    if (!game.sound) return;
    if (document.hidden) game.sound.mute = true;
    else game.sound.mute = false;
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', start, { once: true });
} else {
  start();
}

registerServiceWorker();
