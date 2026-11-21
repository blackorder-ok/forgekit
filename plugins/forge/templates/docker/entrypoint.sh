#!/bin/sh
# Runs as root once per container start, then supervisord starts each service as its own user.
set -eu

: "${APP_ENV:?APP_ENV must be set}"
SECRETS="/app/secrets/application-${APP_ENV}-secrets.properties"
if [ ! -f "$SECRETS" ]; then
    echo "[ENTRY] missing secrets file: application-${APP_ENV}-secrets.properties" >&2
    exit 1
fi

# Read one key from the properties file. Only the key name is ever printed.
readKey() {
    grep -E "^$1=" "$SECRETS" | head -n 1 | cut -d= -f2- | tr -d '\r'
}

DB_NAME="$(grep -E '^database\.name=' /app/config/application.properties /app/config/application-"${APP_ENV}".properties | tail -n 1 | cut -d= -f2- | tr -d '\r')"
DB_PASSWORD="$(readKey database.password)"
if [ -z "$DB_PASSWORD" ]; then
    echo "[ENTRY] database.password is empty in the secrets file" >&2
    exit 1
fi

SOCKET=/run/mysqld/mysqld.sock
mkdir -p /run/mysqld
chown mysql:mysql /run/mysqld

# First start only: create the MySQL data directory. Root has no password here,
# but MySQL listens on the local socket only during this setup step.
if [ ! -d /var/lib/mysql/mysql ]; then
    echo "[ENTRY] initialising MySQL data directory"
    mysqld --initialize-insecure --user=mysql --datadir=/var/lib/mysql
fi

# Every start: bring MySQL up with networking off, create the app database and user, then stop it.
runuser -u mysql -- mysqld --user=mysql --datadir=/var/lib/mysql --skip-networking --socket="$SOCKET" &
i=0
until mysqladmin --socket="$SOCKET" -uroot ping >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -gt 60 ]; then
        echo "[ENTRY] MySQL did not start for setup" >&2
        exit 1
    fi
    sleep 1
done

mysql --socket="$SOCKET" -uroot <<EOF
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS 'app'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
CREATE USER IF NOT EXISTS 'app'@'127.0.0.1' IDENTIFIED BY '${DB_PASSWORD}';
ALTER USER 'app'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
ALTER USER 'app'@'127.0.0.1' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO 'app'@'localhost';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO 'app'@'127.0.0.1';
FLUSH PRIVILEGES;
EOF

mysqladmin --socket="$SOCKET" -uroot shutdown
# Wait for the setup instance to exit before supervisord starts the real one.
i=0
while [ -S "$SOCKET" ] && [ "$i" -lt 60 ]; do
    i=$((i + 1))
    sleep 1
done

mkdir -p /var/lib/ollama/models
chown -R ollama:ollama /var/lib/ollama
chown -R app:app /var/lib/app

exec "$@"
