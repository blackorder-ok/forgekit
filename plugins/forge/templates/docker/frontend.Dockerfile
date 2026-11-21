# Frontend build. Output: a scratch image holding /dist, copied into the app image.
# Build: docker build --target artifact -f docker/frontend.Dockerfile -t app-frontend:<env>-local .
# Build context is the repo root.

ARG NODE_IMAGE=node:20-bookworm-slim

FROM ${NODE_IMAGE} AS build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build && test -f dist/index.html

FROM scratch AS artifact
COPY --from=build /src/dist /dist
