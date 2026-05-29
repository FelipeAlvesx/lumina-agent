#!/bin/sh
# Aplica o patch @lid na Evolution API.
# Executado como serviço one-shot pelo patcher no docker-compose.

set -e

i=0
while [ $i -lt 10 ]; do
  if docker exec lumina_evolution echo ok >/dev/null 2>&1; then
    break
  fi
  echo "[patcher] Aguardando evolution... tentativa $((i+1))/10"
  i=$((i + 1))
  sleep 3
done

echo "[patcher] Aplicando patch @lid..."

docker exec lumina_evolution sed -i \
  's/!isWA.exists \&\& !(0, baileys_1.isJidGroup)(isWA.jid) \&\& !isWA.jid.includes(.@broadcast.)/!isWA.exists \&\& !(0, baileys_1.isJidGroup)(isWA.jid) \&\& !isWA.jid.includes('\''@broadcast'\'') \&\& !isWA.jid.includes('\''@lid'\'')/g' \
  /evolution/dist/src/api/services/channels/whatsapp.baileys.service.js

echo "[patcher] Reiniciando evolution para aplicar patch..."
docker restart lumina_evolution

echo "[patcher] Patch @lid aplicado com sucesso!"
