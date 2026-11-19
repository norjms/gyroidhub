# gyroidhub: a GyroidVault release, converted for OpenPrintHQ by convert/convert.py.
#
# The release comes from upstream.env (passed as build arguments by artisan-hub-deploy's build/release.sh):
# the tag is fetched and must be the commit named there, so a moved tag fails the build instead of changing
# what is built.

FROM python:3.12-alpine AS convert
ARG GYROIDVAULT_REPO
ARG GYROIDVAULT_VERSION
ARG GYROIDVAULT_COMMIT
RUN apk add --no-cache git
RUN test -n "$GYROIDVAULT_VERSION" && test -n "$GYROIDVAULT_COMMIT" \
 && git clone -q --depth 1 --branch "$GYROIDVAULT_VERSION" "$GYROIDVAULT_REPO" /src \
 && test "$(git -C /src rev-parse HEAD)" = "$GYROIDVAULT_COMMIT" \
 && rm -rf /src/.git /src/screenshots
COPY convert /convert
RUN python3 /convert/convert.py /src

FROM node:22-alpine
ARG GYROIDVAULT_VERSION
WORKDIR /app
COPY --from=convert /src/package*.json ./
# better-sqlite3 builds from source on Alpine; the compilers are removed again in the same layer.
RUN apk add --no-cache --virtual .build python3 make g++ \
 && npm ci --omit=dev \
 && apk del .build \
 && npm cache clean --force
COPY --from=convert /src/ ./
COPY LICENSE /app/LICENSE.gyroidhub
RUN mkdir -p /app/data/uploads
ENV NODE_ENV=production PORT=3000 LIBRARY_PATH=/library
LABEL org.opencontainers.image.title="gyroidhub" \
      org.opencontainers.image.description="OpenPrintHQ's model library, built from GyroidVault ${GYROIDVAULT_VERSION}" \
      org.opencontainers.image.licenses="AGPL-3.0-only" \
      org.opencontainers.image.version="${GYROIDVAULT_VERSION}"
EXPOSE 3000
VOLUME ["/app/data"]
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=6 \
  CMD wget -qO- http://127.0.0.1:3000/healthz >/dev/null || exit 1
CMD ["/app/ahi-start.sh"]
