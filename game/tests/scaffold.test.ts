import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';

/**
 * Phase 1 sanity checks. Real coverage of the engine arrives in Phase 2+.
 * These exist so `npm test` has something to run on a clean clone and so
 * configuration regressions (missing manifest icon, broken tsconfig, etc.)
 * fail loudly rather than silently.
 */

const root = path.resolve(__dirname, '..');

describe('phase 1 scaffold', () => {
  it('package.json declares the locked stack', () => {
    const pkg = JSON.parse(readFileSync(path.join(root, 'package.json'), 'utf8')) as {
      dependencies: Record<string, string>;
      devDependencies: Record<string, string>;
    };
    expect(pkg.dependencies.phaser).toMatch(/^\^?3\./);
    expect(pkg.devDependencies.typescript).toMatch(/^\^?5\./);
    expect(pkg.devDependencies.vite).toMatch(/^\^?5\./);
    expect(pkg.devDependencies['vite-plugin-pwa']).toBeDefined();
    expect(pkg.devDependencies.vitest).toBeDefined();
  });

  it('tsconfig is in strict mode', () => {
    const ts = JSON.parse(readFileSync(path.join(root, 'tsconfig.json'), 'utf8')) as {
      compilerOptions: Record<string, unknown>;
    };
    expect(ts.compilerOptions.strict).toBe(true);
    expect(ts.compilerOptions.noUnusedLocals).toBe(true);
    expect(ts.compilerOptions.noUnusedParameters).toBe(true);
  });

  it('index.html uses dvh units and safe-area insets', () => {
    const html = readFileSync(path.join(root, 'index.html'), 'utf8');
    expect(html).toContain('100dvh');
    expect(html).toContain('env(safe-area-inset');
    expect(html).toContain('viewport-fit=cover');
  });
});
