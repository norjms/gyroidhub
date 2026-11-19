# gyroidhub

OpenPrintHQ's model library: [GyroidVault](https://github.com/TeeCodeDev/GyroidVault), converted to run inside
an OpenPrintHQ installation. It browses the hub's model library with a 3D preview, under the hub's name at
`/apps/models/`, signed in through the hub's own sign-in, and looks like the rest of OpenPrintHQ.

This repository holds no copy of GyroidVault. It holds the steps that turn a GyroidVault **release** into
gyroidhub, and the build applies them to the release named in `upstream.env`:

| File | What it is |
|---|---|
| `upstream.env` | The GyroidVault release built: its tag and the commit the tag must point at. |
| `convert/convert.py` | The conversion, as a script: relative URLs for a base path, sign-in and settings from the environment, the OpenPrintHQ look and name. Each edit names the exact text it changes and stops the build if a release no longer has it. |
| `convert/files/` | Files added to the release: `server/ahi.js` and `public/css/ahi-theme.css`. |
| `Dockerfile` | Fetches the release, checks its commit, runs the conversion, and builds the image. |
| `.github/workflows/upstream-watch.yml` | Checks daily for a new GyroidVault release and opens a pull request moving `upstream.env` to it, saying whether the conversion still applies. |

## Keeping up with GyroidVault

1. A new release appears; the watch opens a pull request `GyroidVault vX.Y.Z`.
2. If it says the conversion failed, fix the named anchor in `convert/convert.py` on that branch.
3. Build both architectures with `build/release.sh gyroidhub <branch>` in openprinthq-deploy, open it, and
   merge the pull request. The installer then pins the new image by digest.

Only published releases are taken; pre-releases, drafts, branches and nightly builds never are.

## Running it

The installer runs it. The settings it uses:

| Variable | Meaning |
|---|---|
| `AHI_BASE_PATH` | The path it is served under, such as `/apps/models`. A proxy may forward the path whole or strip it. |
| `AHI_SSO=1` | Sign in through the OIDC provider directly, without a login dialog. |
| `AHI_SETTING_<KEY>` | Written to GyroidVault's settings at every start, for example `AHI_SETTING_OIDC_ISSUER_URL`. |
| `LIBRARY_PATH` | The model library, `/library` by default. |

## Licence

GyroidVault is free software under the GNU Affero General Public License, version 3, and so is gyroidhub:
see `LICENSE`. Every page links to GyroidVault and to this source.
