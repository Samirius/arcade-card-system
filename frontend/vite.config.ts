import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { PrimeVueResolver } from '@primevue/auto-import-resolver'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

export default defineConfig({
  plugins: [
    vue(),
    Components({
      resolvers: [
        PrimeVueResolver(),
      ],
    }),
    // --- Cashier PWA scaffold ---
    // Enables the cashier surface (/cashier/*) to be installed as a PWA and
    // to keep serving its own shell/assets when the device briefly loses
    // connectivity (e.g. a spotty arcade-floor Wi-Fi). This is a SCAFFOLD
    // ONLY: it registers a service worker that precaches the app shell and
    // exposes the update lifecycle, but it does NOT itself make API calls
    // work offline — that's what `src/lib/offlineQueue.ts` is for (queues
    // mutating card actions in IndexedDB and drains them on reconnect).
    //
    // `registerType: 'autoUpdate'` means a new service worker activates and
    // takes over automatically on the next navigation once a new build is
    // deployed, rather than waiting for the user to close every tab.
    //
    // `workbox.navigateFallbackDenylist` excludes `/api/*` so navigation
    // fallback routing never accidentally serves the cached index.html in
    // place of a real (failed) API response — GET API calls should fail
    // loudly when offline, not silently resolve to HTML.
    VitePWA({
      registerType: 'autoUpdate',
      // Only the cashier surface is the intended PWA install target today;
      // the manifest/icons below still apply app-wide because Vite serves a
      // single SPA shell, but scope can be tightened later if the
      // admin/portal surfaces should NOT be installable.
      includeAssets: ['favicon.ico'],
      manifest: {
        name: 'سندباد — Cashier',
        short_name: 'Sindbad Cashier',
        description: 'Arcade card top-up and charge terminal (cashier PWA)',
        start_url: '/cashier',
        scope: '/',
        display: 'standalone',
        background_color: '#ffffff',
        theme_color: '#1e293b',
        // NOTE: no icon files exist in `public/` yet at authoring time — add
        // real 192x192 / 512x512 PNGs under `public/pwa/` and reference them
        // here before shipping. Left commented so the manifest is valid but
        // incomplete rather than pointing at 404s.
        icons: [
          // { src: '/pwa/icon-192.png', sizes: '192x192', type: 'image/png' },
          // { src: '/pwa/icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
      workbox: {
        navigateFallbackDenylist: [/^\/api\//],
        // Runtime caching left minimal on purpose — this scaffold precaches
        // the built app shell (JS/CSS/HTML) via Workbox defaults. Deciding
        // which GET API responses (if any) are safe to cache-then-revalidate
        // is a product/security decision (balances are financial data — do
        // not cache them optimistically without explicit sign-off) and is
        // deliberately left to the founder rather than guessed here.
        runtimeCaching: [],
      },
      devOptions: {
        // Service workers are disabled in `npm run dev` by default in this
        // plugin; flip to `true` locally only if you need to test install/
        // offline behavior against the dev server.
        enabled: false,
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: true,
    port: 3000,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
