#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/app}"
OUT="${1:-/app/solution.patch}"
EDITABLE="2phase_nsa/binary_plan/rewrite_policy.py"
OUT_REL=""
case "$OUT" in
  "$APP_DIR"/*) OUT_REL="${OUT#"$APP_DIR"/}" ;;
esac

if [[ ! -d "$APP_DIR/.git" ]]; then
  echo "Git checkout not found at $APP_DIR" >&2
  exit 2
fi

outside=()
while IFS= read -r -d '' path; do
  [[ -n "$OUT_REL" && "$path" == "$OUT_REL" ]] && continue
  [[ "$path" == "submit.sh" ]] && continue
  [[ "$path" == "$EDITABLE" ]] || outside+=("$path")
done < <(
  {
    git -C "$APP_DIR" diff --name-only -z HEAD --
    git -C "$APP_DIR" ls-files --others --exclude-standard -z
  }
)

if (( ${#outside[@]} )); then
  echo "ERROR: changes outside the editable surface:" >&2
  printf '  %q\n' "${outside[@]}" >&2
  exit 3
fi

git -C "$APP_DIR" diff --binary --no-color HEAD -- "$EDITABLE" > "$OUT"
echo "Wrote $OUT ($(wc -c < "$OUT" | tr -d ' ') bytes)."
