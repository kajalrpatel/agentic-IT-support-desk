#!/bin/sh
set -eu
printf 'window.SMARTDESK_CONFIG = ' > /usr/share/nginx/html/config.js
jq -n --arg apiBase "${API_BASE:-}" --arg oidcAuthority "${OIDC_AUTHORITY:-}" --arg oidcClientId "${OIDC_CLIENT_ID:-}" '{apiBase:$apiBase,oidcAuthority:$oidcAuthority,oidcClientId:$oidcClientId,oidcScope:"openid profile email"}' >> /usr/share/nginx/html/config.js
printf ';\n' >> /usr/share/nginx/html/config.js
