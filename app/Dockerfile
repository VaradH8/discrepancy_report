# ---- Stage 1: build LibreDWG (DWG->DXF converter) ----
FROM ubuntu:24.04 AS dwgbuild
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential autoconf automake libtool texinfo curl ca-certificates pkg-config git && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN curl -sL https://codeload.github.com/LibreDWG/libredwg/tar.gz/refs/tags/0.13.3 -o lib.tgz && \
    tar xzf lib.tgz && mv libredwg-0.13.3 libredwg
WORKDIR /src/libredwg
# jsmn submodule header (not in the tarball)
RUN mkdir -p jsmn && curl -sL https://raw.githubusercontent.com/zserge/jsmn/master/jsmn.h -o jsmn/jsmn.h
RUN ( ./autogen.sh || true ) && ./configure --disable-bindings --disable-python && \
    make -j"$(nproc)" CFLAGS="-O0 -g0" && make install && ldconfig

# ---- Stage 2: app ----
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip ca-certificates && rm -rf /var/lib/apt/lists/*
# bring the compiled converter + library over
COPY --from=dwgbuild /usr/local/bin/dwg2dxf /usr/local/bin/dwg2dxf
COPY --from=dwgbuild /usr/local/lib/libredwg.* /usr/local/lib/
RUN ldconfig

# Optional: ODA File Converter — the preferred DWG decoder (reads every AutoCAD
# version, so it handles files LibreDWG can't). Enable by passing the Linux .deb
# URL: --build-arg ODA_URL=https://.../ODAFileConverter_..._lnxX64_..._25.x.deb
# (grab it from https://www.opendesign.com/guestfiles/oda_file_converter after
# accepting their licence). When unset, the image uses LibreDWG only. ODA is a
# Qt GUI app, so it runs headless through xvfb.
ARG ODA_URL=""
RUN if [ -n "$ODA_URL" ]; then \
      apt-get update && \
      apt-get install -y --no-install-recommends xvfb curl ca-certificates libxcb-util1 && \
      curl -fL "$ODA_URL" -o /tmp/oda.deb && \
      apt-get install -y --no-install-recommends /tmp/oda.deb && \
      rm -f /tmp/oda.deb && rm -rf /var/lib/apt/lists/* && \
      # Ubuntu 22/24 ship libxcb-util.so.1; ODA's Qt build wants .so.0 (per ODA docs)
      ln -sf /usr/lib/x86_64-linux-gnu/libxcb-util.so.1 /usr/lib/x86_64-linux-gnu/libxcb-util.so.0 && \
      command -v ODAFileConverter ; \
    else echo "ODA_URL not set -> DWG conversion uses LibreDWG only"; fi

WORKDIR /app
COPY backend/requirements.txt .
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY frontend/ ./frontend/
WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
