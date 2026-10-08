#!/usr/bin/env sh
# Builds app/static/tailwind.css (committed, so the app works offline on a LAN with no CDN).
set -e
cd "$(dirname "$0")"
printf '@tailwind base;@tailwind components;@tailwind utilities;' > /tmp/ctf-tw-in.css
npx tailwindcss -c tailwind.config.js -i /tmp/ctf-tw-in.css -o ../app/static/tailwind.css --minify
