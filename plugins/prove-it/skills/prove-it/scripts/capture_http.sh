#!/usr/bin/env sh
# capture_http.sh - capture proof that an HTTP endpoint behaves as claimed.
#
# Records status, final URL after redirects, timing, cache headers, a body
# snippet, and the result of every text assertion, into .prove-it/.
# Exits 0 only if every expectation held.
#
# Usage:
#   capture_http.sh URL [--expect-text STR]... [--expect-status N] [--method M]
#                       [--data BODY] [--header 'K: V']... [--out DIR]
#                       [--timeout S] [--no-follow] [--insecure] [--bust]
#
# Examples:
#   capture_http.sh https://example.com/pricing --expect-text "Pro plan"
#   capture_http.sh https://api.example.com/v1/ping --expect-status 204
#   capture_http.sh https://example.com/api/health --expect-text "$(git rev-parse --short HEAD)"

set -u

URL=""
METHOD=""
DATA=""
OUT=".prove-it"
TIMEOUT=30
FOLLOW="-L"
INSECURE=""
BUST=0
EXPECT_STATUS=""
HEADERS_FILE=$(mktemp)
EXPECT_FILE=$(mktemp)
trap 'rm -f "$HEADERS_FILE" "$EXPECT_FILE"' EXIT

die() { printf '%s\n' "$*" >&2; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --expect-text)   [ $# -ge 2 ] || die "--expect-text needs a value"; printf '%s\n' "$2" >> "$EXPECT_FILE"; shift 2 ;;
    --expect-status) [ $# -ge 2 ] || die "--expect-status needs a value"; EXPECT_STATUS="$2"; shift 2 ;;
    --method)        [ $# -ge 2 ] || die "--method needs a value"; METHOD="$2"; shift 2 ;;
    --data)          [ $# -ge 2 ] || die "--data needs a value"; DATA="$2"; shift 2 ;;
    --header)        [ $# -ge 2 ] || die "--header needs a value"; printf '%s\n' "$2" >> "$HEADERS_FILE"; shift 2 ;;
    --out)           [ $# -ge 2 ] || die "--out needs a value"; OUT="$2"; shift 2 ;;
    --timeout)       [ $# -ge 2 ] || die "--timeout needs a value"; TIMEOUT="$2"; shift 2 ;;
    --no-follow)     FOLLOW=""; shift ;;
    --insecure)      INSECURE="-k"; shift ;;
    --bust)          BUST=1; shift ;;
    -h|--help)       sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)              die "unknown option: $1" ;;
    *)               [ -z "$URL" ] || die "only one URL allowed (got '$1')"; URL="$1"; shift ;;
  esac
done

[ -n "$URL" ] || die "usage: capture_http.sh URL [options]  (--help for more)"
command -v curl >/dev/null 2>&1 || die "curl not found - cannot capture HTTP evidence"

if [ "$BUST" -eq 1 ]; then
  case "$URL" in
    *\?*) URL="${URL}&_proveit=$(date +%s)" ;;
    *)    URL="${URL}?_proveit=$(date +%s)" ;;
  esac
fi

mkdir -p "$OUT"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
SLUG=$(printf '%s' "$URL" | sed -e 's#^https\{0,1\}://##' -e 's#[^A-Za-z0-9]#-#g' | cut -c1-60)
BASE="$OUT/http-$SLUG-$STAMP"
BODY="$BASE.body"
HDRS="$BASE.headers"
JSON="$BASE.json"

# JSON string escaping, in pure sed: backslash, quote, control chars, newlines.
esc() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/\t/\\t/g' -e 's/\r/\\r/g' \
    | awk 'BEGIN{ORS=""} NR>1{print "\\n"} {print}'
}

set -- -sS $FOLLOW $INSECURE --max-time "$TIMEOUT" -o "$BODY" -D "$HDRS" \
       -w '%{http_code}\t%{url_effective}\t%{time_total}\t%{num_redirects}\t%{size_download}\t%{content_type}'
[ -n "$METHOD" ] && set -- "$@" -X "$METHOD"
[ -n "$DATA" ]   && set -- "$@" --data-binary "$DATA"
while IFS= read -r h; do [ -n "$h" ] && set -- "$@" -H "$h"; done < "$HEADERS_FILE"
set -- "$@" "$URL"

METRICS=$(curl "$@" 2>"$BASE.curlerr") || {
  CURLERR=$(cat "$BASE.curlerr" 2>/dev/null)
  printf 'NOT PROVEN - request failed: %s\n' "$CURLERR" >&2
  printf '{\n  "url": "%s",\n  "captured_at": "%s",\n  "verdict": "NOT PROVEN",\n  "error": "%s"\n}\n' \
    "$(esc "$URL")" "$STAMP" "$(esc "$CURLERR")" > "$JSON"
  printf 'evidence: %s\n' "$JSON" >&2
  exit 1
}
rm -f "$BASE.curlerr"

STATUS=$(printf '%s' "$METRICS" | cut -f1)
FINAL=$(printf '%s' "$METRICS" | cut -f2)
TIME=$(printf '%s' "$METRICS" | cut -f3)
REDIRS=$(printf '%s' "$METRICS" | cut -f4)
SIZE=$(printf '%s' "$METRICS" | cut -f5)
CTYPE=$(printf '%s' "$METRICS" | cut -f6)

# Redact secrets in the stored headers, both sent and received.
sed -i.bak -E 's/^([Aa]uthorization|[Cc]ookie|[Ss]et-[Cc]ookie|[^:]*([Tt]oken|[Kk]ey|[Ss]ecret)[^:]*):.*/\1: [redacted by prove-it]/' "$HDRS" 2>/dev/null || true
rm -f "$HDRS.bak"

cache_header() {
  grep -i -m1 "^$1:" "$HDRS" 2>/dev/null | sed -e "s/^[^:]*: *//" | tr -d '\r\n'
}
CACHE=""
for h in cf-cache-status x-vercel-cache x-nextjs-cache x-cache age; do
  v=$(cache_header "$h")
  [ -n "$v" ] && CACHE="$CACHE$h=$v "
done

FAIL=0
MATCHED=""
MISSING=""
while IFS= read -r want; do
  [ -n "$want" ] || continue
  if grep -qF -- "$want" "$BODY" 2>/dev/null; then
    MATCHED="$MATCHED  \"$(esc "$want")\","
  else
    MISSING="$MISSING  \"$(esc "$want")\","
    FAIL=1
  fi
done < "$EXPECT_FILE"

if [ -n "$EXPECT_STATUS" ]; then
  [ "$STATUS" = "$EXPECT_STATUS" ] || FAIL=1
else
  case "$STATUS" in 2*|3*) ;; *) FAIL=1 ;; esac
fi

VERDICT="PROVEN"
[ "$FAIL" -eq 0 ] || VERDICT="NOT PROVEN"

SNIPPET=$(head -c 600 "$BODY" 2>/dev/null | tr -d '\000')

{
  printf '{\n'
  printf '  "tool": "capture_http.sh",\n'
  printf '  "captured_at": "%s",\n' "$STAMP"
  printf '  "url": "%s",\n' "$(esc "$URL")"
  printf '  "final_url": "%s",\n' "$(esc "$FINAL")"
  printf '  "method": "%s",\n' "$(esc "${METHOD:-GET}")"
  printf '  "status": %s,\n' "${STATUS:-0}"
  printf '  "expected_status": "%s",\n' "$(esc "${EXPECT_STATUS:-2xx/3xx}")"
  printf '  "redirects": %s,\n' "${REDIRS:-0}"
  printf '  "time_total_s": %s,\n' "${TIME:-0}"
  printf '  "bytes": %s,\n' "${SIZE:-0}"
  printf '  "content_type": "%s",\n' "$(esc "$CTYPE")"
  printf '  "cache_headers": "%s",\n' "$(esc "${CACHE% }")"
  printf '  "matched": [%s],\n' "$(printf '%s' "${MATCHED%,}")"
  printf '  "missing": [%s],\n' "$(printf '%s' "${MISSING%,}")"
  printf '  "body_snippet": "%s",\n' "$(esc "$SNIPPET")"
  printf '  "body_file": "%s",\n' "$(esc "$BODY")"
  printf '  "headers_file": "%s",\n' "$(esc "$HDRS")"
  printf '  "verdict": "%s"\n' "$VERDICT"
  printf '}\n'
} > "$JSON"

printf '%s  status=%s  %ss  %sB  %s\n' "$VERDICT" "$STATUS" "$TIME" "$SIZE" "${CACHE:-no-cache-headers}"
[ -n "$MISSING" ] && printf 'missing text: %s\n' "$(printf '%s' "${MISSING%,}")"
printf 'evidence: %s\n' "$JSON"
exit "$FAIL"
