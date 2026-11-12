#!/bin/sh
# gyroidhub's start: when AHI_CA_PEM holds the installation's own certificate authority (a hub used only at
# home), Node trusts it, so signing in through Authelia under the hub's name works; then GyroidVault starts.
set -e
if [ -n "${AHI_CA_PEM:-}" ]; then
  printf '%s\n' "$AHI_CA_PEM" > /tmp/ahi-ca.pem
  export NODE_EXTRA_CA_CERTS=/tmp/ahi-ca.pem
fi
exec node server/index.js
