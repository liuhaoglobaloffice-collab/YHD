#!/bin/bash
# Usage: ./push_create_pr.sh <REMOTE_URL> [--draft]
# Example: ./push_create_pr.sh git@github.com:org/repo.git --draft

set -euo pipefail
REMOTE_URL="$1"
DRAFT_FLAG=""
if [ "${2-}" = "--draft" ]; then
  DRAFT_FLAG="--draft"
fi

# Ensure branch name
BRANCH="metrics/persist-staging"
BASE_BRANCH="staging"

# Add remote if not exists
if ! git remote | grep -q origin; then
  git remote add origin "$REMOTE_URL"
fi

# Push branch
git push -u origin "$BRANCH"

# Create PR using gh if available
if command -v gh >/dev/null 2>&1; then
  gh pr create --base "$BASE_BRANCH" --head "$BRANCH" --title "metrics: persist provider metrics to DB (staging) + integration test" --body-file .changes/PR_BODY.md $DRAFT_FLAG
else
  echo "gh CLI not found; please create a PR manually using the repo UI and use .changes/PR_BODY.md as the description."
fi
