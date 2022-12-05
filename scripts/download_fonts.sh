#!/bin/sh
set -e

# Download google fonts
while IFS= read -r fontname; do
  FONTNAME_URL=$(echo "${fontname}" | tr " " "+")
  FONTNAME_FS=$(echo "${fontname}" | tr "[:upper:]" "[:lower:]" | tr " " "_")
  wget https://fonts.google.com/download?family=${FONTNAME_URL} -O /tmp/${FONTNAME_FS}.zip
  mkdir -p /usr/share/fonts/ttf-${FONTNAME_FS}/
  unzip /tmp/${FONTNAME_FS}.zip -d /usr/share/fonts/ttf-${FONTNAME_FS}/
  if [[ ${FONTNAME_FS} = 'roboto_serif' ]]; then
    mv /usr/share/fonts/ttf-${FONTNAME_FS}/ /tmp/roboto_serif_all/
    mv /tmp/roboto_serif_all/static/RobotoSerif/ /usr/share/fonts/ttf-${FONTNAME_FS}/
    rm -rf /tmp/roboto_serif_all/
  fi
  rm -f /tmp/${FONTNAME_FS}.zip
done << EOF
Roboto
Roboto Serif
Lato
Tinos
Exo
Source Code Pro
Roboto Mono
Courier Prime
EOF
# Fonts installed with alpine apk: 
# Noto: Noto Sans, Noto Serif, Noto Mono
# Open Sans

# Update font cache
fc-cache -f