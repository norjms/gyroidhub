// ArtisanHub's additions to GyroidVault, copied in by convert/convert.py (gyroidhub).
//
// - AHI_BASE_PATH: the path the proxy serves this app under (for example /apps/models). The proxy strips it
//   before forwarding, so routes stay at the root; only redirects to the browser need it in front.
// - AHI_SETTING_<KEY>=value: written to system_settings at every start, so the installer, not a person in
//   the settings page, decides sign-in and features (key lowercased: AHI_SETTING_OIDC_ENABLED -> oidc_enabled).
// - AHI_SSO=1: the browser is told to sign in through the OIDC provider without showing a login dialog.
// - The library is scanned at start and whenever <library>/.rescan changes: the hub touches that file after it
//   writes models (as it does for Manyfold), so new models show within AHI_RESCAN_SECONDS (15 by default).
'use strict';

const fs = require('fs');
const path = require('path');

const BASE = (process.env.AHI_BASE_PATH || '').replace(/\/+$/, '');
const PREFIX = 'AHI_SETTING_';

function prefixed(url) {
  if (!BASE || typeof url !== 'string') return url;
  if (!url.startsWith('/') || url.startsWith('//') || url === BASE || url.startsWith(BASE + '/')) return url;
  return BASE + url;
}

function routes(app) {
  if (BASE) {
    app.use((req, res, next) => {
      const redirect = res.redirect.bind(res);
      res.redirect = function ahiRedirect(a, b) {
        if (typeof a === 'number') return redirect(a, prefixed(b));
        return redirect(prefixed(a));
      };
      next();
    });
  }
  app.get('/ahi-config.js', (req, res) => {
    const config = { sso: process.env.AHI_SSO === '1', base: BASE };
    res.set('Cache-Control', 'no-store');
    res.type('application/javascript').send('window.AHI = ' + JSON.stringify(config) + ';\n');
  });
}

function seed() {
  const { run, saveDb } = require('./database');
  const keys = [];
  for (const [name, value] of Object.entries(process.env)) {
    if (!name.startsWith(PREFIX) || name.length === PREFIX.length) continue;
    const key = name.slice(PREFIX.length).toLowerCase();
    run('INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)', [key, value], true);
    keys.push(key);
  }
  if (keys.length) {
    saveDb(true);
    // Names only: some values, such as the OIDC client secret, are secrets.
    console.log('[ArtisanHub] settings from the environment: ' + keys.sort().join(', '));
  }
}

function scan(reason) {
  try {
    const { LIBRARY_PATH } = require('./config');
    const { startScanAsync } = require('./utils/library');
    const res = startScanAsync(LIBRARY_PATH);
    const busy = res && res.alreadyRunning ? ': one is already running' : '';
    console.log('[ArtisanHub] library scan (' + reason + ')' + busy);
  } catch (e) {
    console.error('[ArtisanHub] library scan failed to start: ' + e.message);
  }
}

function watch() {
  const { LIBRARY_PATH } = require('./config');
  const marker = path.join(LIBRARY_PATH, '.rescan');
  const seconds = Math.max(5, Number(process.env.AHI_RESCAN_SECONDS || 15));
  const stamp = () => {
    try {
      return fs.statSync(marker).mtimeMs;
    } catch (e) {
      return null;
    }
  };
  let seen = stamp();
  setTimeout(() => scan('start'), 5000).unref();
  setInterval(() => {
    const now = stamp();
    if (now !== null && now !== seen) {
      seen = now;
      scan('.rescan');
    }
  }, seconds * 1000).unref();
}

function start() {
  seed();
  watch();
}

module.exports = { routes, seed, start, prefixed };
