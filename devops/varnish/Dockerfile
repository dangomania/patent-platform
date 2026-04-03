# syntax=docker/dockerfile:1
FROM varnish:7.6

LABEL maintainer="Yosuke Kawasaki <you.kawasaki@gmail.com>" \
      org.label-schema.name="patent-platform-varnish" \
      org.label-schema.description="patent_platform Varnish image." \
      org.label-schema.vendor="Yosuke Kawasaki"

COPY etc/varnish.vcl /etc/varnish/default.vcl
