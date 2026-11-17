#!/usr/bin/env bash
# 把 nba_proxy.py 部署到 Cloud Run。從 repo 根目錄執行：
#
#   PROJECT=你的-gcp-project-id ./deploy/cloudrun/deploy.sh
#
# 第一次之前要做的事（各一次）：
#   gcloud auth login
#   gcloud config set project 你的-gcp-project-id
#   gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
#
# 費用上限由 --max-instances 1 決定，見同目錄 README.md。
set -euo pipefail

PROJECT="${PROJECT:?請設 PROJECT=你的-gcp-project-id}"
REGION="${REGION:-us-central1}"          # 免費額度適用的 Tier 1 區域
SERVICE="${SERVICE:-nba-proxy}"

# 沒給 TOKEN 就自己產一個，部署完會印出來。App 端要帶同一個。
TOKEN="${TOKEN:-$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"

# gcloud run deploy --source 只認 source 根目錄的 Dockerfile（沒有 --dockerfile 旗標），
# 所以備一個只有兩個檔案的暫存目錄當 build context。
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp "$HERE/Dockerfile" "$ROOT/scripts/nba_proxy.py" "$STAGE/"

echo "部署 $SERVICE 到 $PROJECT / $REGION"

gcloud run deploy "$SERVICE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --source "$STAGE" \
  --allow-unauthenticated \
  --set-env-vars "PROXY_TOKEN=$TOKEN" \
  --max-instances 1 \
  --min-instances 0 \
  --concurrency 80 \
  --cpu 1 \
  --memory 512Mi \
  --timeout 30s

URL="$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" \
        --format='value(status.url)')"

cat <<MSG

部署完成。

  網址   $URL
  token  $TOKEN

把這兩個記下來，App 端要用。測一下：

  curl -s "$URL/healthz"
  curl -s -H "X-Proxy-Token: $TOKEN" "$URL/scoreboard" | head -c 300

沒帶 token 應該回 401：

  curl -s "$URL/scoreboard"

⚠️ 如果 /scoreboard 回 {"error":"upstream_status","status":403}，表示 cdn.nba.com
   擋掉了 Google Cloud 的 IP。那不是你設定錯，是這條路在 GCP 走不通 ——
   改用你家的電腦（住宅 IP）或 Azure。見 README.md 最後一節。
MSG
