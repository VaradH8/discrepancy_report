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
WORKDIR /app
COPY backend/requirements.txt .
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY frontend/ ./frontend/
WORKDIR /app/backend
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
