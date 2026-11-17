# nba_proxy.py 的 Cloud Run 映像。
# 刻意保持極小：只要 Python + curl_cffi，沒有 web framework。
#
# build context 是 deploy.sh 準備的暫存目錄（裡面只有這個 Dockerfile 和 nba_proxy.py），
# 不是 repo 根目錄 —— 這樣 repo 根目錄不用擺 Dockerfile，上傳的東西也最少。
FROM python:3.12-slim

# curl_cffi 有預編好的 wheel，所以不需要編譯工具鏈。
# 這支就是整個方案的關鍵：它能偽裝 Chrome 的 TLS 指紋，過得了 cdn.nba.com 的檢查。
RUN pip install --no-cache-dir --disable-pip-version-check curl_cffi==0.17.0

WORKDIR /app
COPY nba_proxy.py /app/nba_proxy.py

# 不要用 root 跑。
RUN useradd --create-home --uid 10001 proxy
USER proxy

# Cloud Run 會用環境變數 PORT 告訴容器要聽哪裡；本機直接跑時預設 8080。
ENV PORT=8080
EXPOSE 8080

CMD ["python", "-u", "/app/nba_proxy.py"]
