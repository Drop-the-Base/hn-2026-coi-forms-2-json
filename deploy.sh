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
# sshpass -e czyta hasło ze zmiennej SSHPASS, więc nie widać go w `ps`.
export SSHPASS

command -v sshpass >/dev/null || {
  echo "Brak sshpass. Zainstaluj: brew install hudochenkov/sshpass/sshpass (macOS) albo sudo apt install sshpass (Debian/Ubuntu)." >&2
  exit 1
}

# VPS_HOSTNAME może już zawierać użytkownika (root@1.2.3.4); wtedy VPS_USER jest pomijany.
case $VPS_HOSTNAME in
  *@*) TARGET=$VPS_HOSTNAME ;;
  *) TARGET="$VPS_USER@$VPS_HOSTNAME" ;;
esac
# accept-new: pierwsze połączenie zapisuje klucz hosta bez pytania (sshpass nie odpowie na prompt).
SSH=(sshpass -e ssh -o StrictHostKeyChecking=accept-new "$TARGET")

echo "==> $TARGET:$VPS_PATH: git pull, przebudowa kontenerów"
# --ff-only: lokalne zmiany na serwerze zatrzymują wdrożenie zamiast tworzyć merge.
"${SSH[@]}" "set -e
  cd '$VPS_PATH'
  git pull --ff-only
  git log -1 --oneline
  docker compose up -d --build --remove-orphans
  docker compose ps
  curl -fsS --retry 10 --retry-connrefused --retry-delay 3 http://localhost:8080/health && echo"

echo "==> Gotowe: http://${VPS_HOSTNAME#*@}:8080"
