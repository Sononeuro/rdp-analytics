import Phaser from 'phaser';

/**
 * Phase 1 placeholder scene: shows a deep-blue background with the title and
 * a build tag so we can confirm the bundle, service worker, and manifest are
 * wired up before later phases drop in the real Title/Preload/Overworld.
 */
export class BootScene extends Phaser.Scene {
  constructor() {
    super({ key: 'BootScene' });
  }

  create(): void {
    const { width, height } = this.scale;

    this.cameras.main.setBackgroundColor('#0b1d3a');

    const cx = width / 2;
    const cy = height / 2;

    this.add
      .text(cx, cy - 48, 'BELLWETHER', {
        fontFamily: 'system-ui, sans-serif',
        fontSize: '48px',
        color: '#f4f6fb',
        fontStyle: 'bold',
      })
      .setOrigin(0.5)
      .setLetterSpacing(6);

    this.add
      .text(cx, cy + 4, 'Cre-8 Chronicles', {
        fontFamily: 'system-ui, sans-serif',
        fontSize: '22px',
        color: '#9fb6dc',
      })
      .setOrigin(0.5)
      .setLetterSpacing(2);

    this.add
      .text(cx, cy + 56, 'Phase 1 — scaffold online', {
        fontFamily: 'system-ui, sans-serif',
        fontSize: '14px',
        color: '#7a8fb0',
      })
      .setOrigin(0.5);

    const buildTag = `build ${import.meta.env.MODE} · ${new Date().toISOString().slice(0, 10)}`;
    this.add
      .text(width - 12, height - 10, buildTag, {
        fontFamily: 'system-ui, sans-serif',
        fontSize: '11px',
        color: '#3e567e',
      })
      .setOrigin(1, 1);

    // Gentle pulse on the subtitle so we can visually verify the render loop is
    // running on every target device.
    const subtitle = this.children.list.find(
      (c): c is Phaser.GameObjects.Text =>
        c instanceof Phaser.GameObjects.Text && c.text === 'Cre-8 Chronicles',
    );
    if (subtitle && !this.sys.game.device.os.iPhone) {
      this.tweens.add({
        targets: subtitle,
        alpha: { from: 0.6, to: 1 },
        duration: 1400,
        yoyo: true,
        repeat: -1,
        ease: 'Sine.easeInOut',
      });
    }
  }
}
