#!/usr/bin/env bash
# Wdrożenie na VPS: w katalogu repo na serwerze git pull, potem przebudowa i restart kontenerów.
# Użycie: ./deploy.sh (w .env: VPS_HOSTNAME, VPS_PASSWORD, VPS_PATH; opcjonalnie VPS_USER).
set -euo pipefail
cd "$(dirname "$0")"

[[ -f .env ]] || { echo "Brak pliku .env (cp .env.example .env)." >&2; exit 1; }

# Czytamy tylko VPS_*, bez `source`: reszta .env to konfiguracja aplikacji, nie skrypt.
env_get() { grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- || true; }

VPS_HOSTNAME=$(env_get VPS_HOSTNAME)
SSHPASS=$(env_get VPS_PASSWORD)
VPS_PATH=$(env_get VPS_PATH)
VPS_USER=$(env_get VPS_USER)
VPS_USER=${VPS_USER:-root}
for name in VPS_HOSTNAME VPS_PASSWORD VPS_PATH; do
  value=$(env_get "$name")
  [[ -n $value ]] || { echo "Ustaw $name w .env." >&2; exit 1; }
done
# Hasło bez sshpass: OpenSSH >= 8.4 pyta program z SSH_ASKPASS. Pomocnik czyta hasło ze zmiennej,
# więc nie ma go w `ps` ani w pliku; sam pomocnik znika po zakończeniu skryptu.
export SSHPASS
ASKPASS=$(mktemp)
trap 'rm -f "$ASKPASS"' EXIT
printf '#!/bin/sh\nprintf "%%s\\n" "$SSHPASS"\n' > "$ASKPASS"
chmod 700 "$ASKPASS"
export SSH_ASKPASS=$ASKPASS SSH_ASKPASS_REQUIRE=force DISPLAY=${DISPLAY:-:0}

# VPS_HOSTNAME może już zawierać użytkownika (root@1.2.3.4); wtedy VPS_USER jest pomijany.
case $VPS_HOSTNAME in
  *@*) TARGET=$VPS_HOSTNAME ;;
  *) TARGET="$VPS_USER@$VPS_HOSTNAME" ;;
esac
# accept-new: pierwsze połączenie zapisuje klucz hosta bez pytania (pomocnik odpowiada tylko na hasło).
SSH=(ssh -o StrictHostKeyChecking=accept-new "$TARGET")

echo "==> $TARGET:$VPS_PATH: git pull, przebudowa kontenerów"
# --ff-only: lokalne zmiany na serwerze zatrzymują wdrożenie zamiast tworzyć merge.
"${SSH[@]}" "set -e
  cd '$VPS_PATH'
  git pull --ff-only
  git log -1 --oneline
  # Grupa docker.sock dla otel-collectora (receiver docker_stats); na Linuksie to zwykle grupa docker, nie 0.
  export DOCKER_GID=\$(stat -c %g /var/run/docker.sock)
  docker compose up -d --build --remove-orphans
  docker compose ps
  curl -fsS --retry 10 --retry-connrefused --retry-delay 3 http://localhost:8080/health && echo"

echo "==> Gotowe: http://${VPS_HOSTNAME#*@}:8080"
