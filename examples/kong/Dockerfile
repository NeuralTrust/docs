# Kong image with the NeuralTrust TrustGuard plugin.
# Works with Kong Gateway Enterprise (kong/kong-gateway) and Kong OSS (kong). Tested on
# kong/kong-gateway:3.14 and kong:3.9.4 / kong:3.4.
ARG KONG_IMAGE=kong/kong-gateway:3.14
FROM ${KONG_IMAGE}
COPY kong/plugins/neuraltrust-trustguard /usr/local/share/lua/5.1/kong/plugins/neuraltrust-trustguard
ENV KONG_PLUGINS=bundled,neuraltrust-trustguard
# Prompts with a long history exceed nginx's default 8k body buffer. Kong 3.6+ reads larger
# bodies from disk, older versions cannot; with this setting every version keeps them in memory.
ENV KONG_NGINX_HTTP_CLIENT_BODY_BUFFER_SIZE=10m
