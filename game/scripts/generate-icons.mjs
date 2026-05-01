/**
 * Renders placeholder PWA icons from public/favicon.svg into public/icons/.
 *
 * Runs as a prebuild and predev hook so the PWA manifest always finds the
 * icon files. Custom art will replace these files later — keep filenames
 * stable.
 */
import { mkdir, readFile, writeFile, access } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');
const srcSvg = path.join(root, 'public', 'favicon.svg');
const outDir = path.join(root, 'public', 'icons');

const TARGETS = [
  { name: 'icon-192.png', size: 192, padding: 0 },
  { name: 'icon-512.png', size: 512, padding: 0 },
  // Maskable icons need a safe zone (~10% inset on each side).
  { name: 'icon-maskable-192.png', size: 192, padding: 0.1 },
  { name: 'icon-maskable-512.png', size: 512, padding: 0.1 },
  { name: 'apple-touch-icon-180.png', size: 180, padding: 0.05 },
];

async function fileExists(p) {
  try {
    await access(p);
    return true;
  } catch {
    return false;
  }
}

async function main() {
  let sharp;
  try {
    ({ default: sharp } = await import('sharp'));
  } catch {
    console.warn(
      '[generate-icons] sharp is not installed; skipping icon generation. ' +
        'Run `npm install` to install it. The PWA manifest will still load, ' +
        'but icons will 404 until icons are produced.',
    );
    return;
  }

  await mkdir(outDir, { recursive: true });
  const svg = await readFile(srcSvg);

  for (const target of TARGETS) {
    const dest = path.join(outDir, target.name);
    if (process.env.SKIP_IF_EXISTS === '1' && (await fileExists(dest))) continue;

    const inset = Math.round(target.size * target.padding);
    const inner = target.size - inset * 2;

    const innerPng = await sharp(svg, { density: 384 })
      .resize(inner, inner, { fit: 'contain', background: { r: 11, g: 29, b: 58, alpha: 1 } })
      .png()
      .toBuffer();

    await sharp({
      create: {
        width: target.size,
        height: target.size,
        channels: 4,
        background: { r: 11, g: 29, b: 58, alpha: 1 },
      },
    })
      .composite([{ input: innerPng, top: inset, left: inset }])
      .png({ compressionLevel: 9 })
      .toFile(dest);

    console.log(`[generate-icons] wrote ${path.relative(root, dest)}`);
  }
}

main().catch((err) => {
  console.error('[generate-icons] failed:', err);
  process.exitCode = 1;
});
