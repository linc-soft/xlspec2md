# xlspec2md 単一イメージ: エンジン + Web UI + LibreOffice(EMF→PNG)
#
# 標準ビルド:
#   docker build -t xlspec2md .
#
# 中国大陸ネットワーク/NAS 環境向け（ミラー指定）:
#   docker build \
#     --build-arg APT_MIRROR=mirrors.aliyun.com \
#     --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
#     --build-arg NPM_REGISTRY=https://registry.npmmirror.com \
#     -t xlspec2md .

# ---- Stage 1: フロントエンドビルド ----
FROM node:20-slim AS frontend
ARG NPM_REGISTRY=""
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN if [ -n "$NPM_REGISTRY" ]; then npm config set registry "$NPM_REGISTRY"; fi \
    && npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: ランタイム ----
# bookworm を固定（latest(trixie) は apt パッケージ構成が変わるリスクがあるため）
FROM python:3.12-slim-bookworm

ARG APT_MIRROR=""
ARG PIP_INDEX_URL=""

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    XLSPEC2MD_DATA=/data

# apt ミラー差し替え（deb822 形式(bookworm+) と従来形式の両対応）+ LibreOffice + 日本語フォント
RUN set -eux; \
    if [ -n "$APT_MIRROR" ]; then \
      if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
      else \
        sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list; \
      fi; \
    fi; \
    apt-get update -o Acquire::Retries=5 -o Acquire::http::Timeout=60; \
    apt-get install -y --no-install-recommends \
        libreoffice-core libreoffice-calc libreoffice-draw \
        fonts-noto-cjk fontconfig; \
    rm -rf /var/lib/apt/lists/*; \
    fc-cache -f

WORKDIR /srv
COPY pyproject.toml README.md ./
COPY src ./src
RUN if [ -n "$PIP_INDEX_URL" ]; then pip config set global.index-url "$PIP_INDEX_URL"; fi \
    && pip install --no-cache-dir -e . fastapi "uvicorn[standard]" python-multipart

# フロントエンド産物（FastAPI が静的配信）
COPY --from=frontend /app/dist ./frontend/dist

VOLUME ["/data"]
EXPOSE 8000
CMD ["python", "-m", "xlspec2md.web.app"]
