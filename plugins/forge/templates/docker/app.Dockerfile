# App image for one environment: the backend image plus nginx (serving the frontend and proxying /api),
# MySQL 8.0, and Ollama (develop only), all under supervisord.
# Build order (see docker-prod): frontend and backend first, then this file.
# Build: docker build --build-arg APP_ENV=<env> -f docker/app.Dockerfile -t app-api:<env>-local .

ARG BACKEND_IMAGE=app-backend:develop-local
ARG FRONTEND_IMAGE=app-frontend:develop-local
ARG OLLAMA_VERSION=0.40.15
ARG OLLAMA_SHA256=628c018404a4206493efd38e46251c154ede5141b8b8dc85c659b3b027c47379

FROM ${FRONTEND_IMAGE} AS frontend
FROM ${BACKEND_IMAGE} AS app
ARG OLLAMA_VERSION
ARG OLLAMA_SHA256
USER root

# OS packages: nginx, supervisor, curl, and the libraries MySQL needs at run time.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl gnupg nginx supervisor xz-utils libaio1 libnuma1 libncurses6 libtinfo6 \
 && rm -rf /var/lib/apt/lists/*

# MySQL 8.0 server: pinned release tarball from dev.mysql.com, SHA-256 checked.
# Signed by MySQL Release Engineering, key BCA4 3417 C3B4 85DD 128E C6D4 B7B3 B788 A8D3 785C.
# To verify the signature by hand: gpg --verify <tarball>.asc <tarball>
ARG MYSQL_VERSION=8.0.46
ARG MYSQL_SHA256=0fcdb2e88b5bb151118420745070a34621463dd85a50e1eacd7c3aa1b9d1f4a2
RUN curl -fsSL "https://cdn.mysql.com/Downloads/MySQL-8.0/mysql-${MYSQL_VERSION}-linux-glibc2.28-x86_64.tar.xz" -o /tmp/mysql.tar.xz \
 && echo "${MYSQL_SHA256}  /tmp/mysql.tar.xz" | sha256sum -c - \
 && mkdir -p /usr/local/mysql \
 && tar -xJf /tmp/mysql.tar.xz -C /usr/local/mysql --strip-components=1 \
 && rm /tmp/mysql.tar.xz \
 && groupadd --system mysql \
 && useradd --system --gid mysql --no-create-home --shell /usr/sbin/nologin mysql \
 && mkdir -p /var/lib/mysql /run/mysqld \
 && chown mysql:mysql /var/lib/mysql /run/mysqld
ENV PATH=/usr/local/mysql/bin:${PATH}

# Ollama: pinned release, SHA-256 checked. No pipe-to-shell install.
RUN test -n "${OLLAMA_VERSION}" && test -n "${OLLAMA_SHA256}" \
 && curl -fsSL "https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-amd64.tar.zst" -o /tmp/ollama.tar.zst \
 && echo "${OLLAMA_SHA256}  /tmp/ollama.tar.zst" | sha256sum -c - \
 && apt-get update && apt-get install -y --no-install-recommends zstd && rm -rf /var/lib/apt/lists/* \
 && tar -I zstd -xf /tmp/ollama.tar.zst -C /usr/local \
 && rm /tmp/ollama.tar.zst \
 && /usr/local/bin/ollama --version

# One Linux user per service. No login shells.
RUN useradd --system --no-create-home --shell /usr/sbin/nologin ollama \
 && mkdir -p /var/lib/ollama /var/lib/app /run/nginx \
 && chown ollama:ollama /var/lib/ollama \
 && chown app:app /var/lib/app

# Frontend build output, from the frontend image
COPY --from=frontend /dist /var/www/html

COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisord.conf /etc/supervisor/supervisord.conf
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --retries=6 \
    CMD curl -fsS http://127.0.0.1/api/health >/dev/null || exit 1
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
