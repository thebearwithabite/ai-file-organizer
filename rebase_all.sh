#!/bin/bash
export PATH=/opt/homebrew/bin:$PATH
cd /tmp/ai-file-org-fix
git config user.email "jeeves@openclaw.ai"
git config user.name "Jeeves"

# Fetch all branches
gh pr list --state open --json headRefName -q '.[].headRefName' | while read branch; do
  git fetch origin "$branch" 2>/dev/null
done

BRANCHES=(
  "sentinel-fix-argument-injection-17365958814891074486"
  "fix/security-lfi-openfile-6484926735015329438"
  "bolt/perf-staging-monitor-batching-8401238821667072562"
  "palette/header-accessibility-154469823728066491"
  "palette-ux-improvements-4869494028608771941"
  "bolt-dedup-optimization-2370780502246104527"
  "bolt/optimize-tagging-connection-reuse-16315524214069553426"
  "bolt/optimize-batch-content-extraction-15207826938807937234"
)

PRS=(80 81 83 82 79 78 76 75)

for i in "${!BRANCHES[@]}"; do
  branch="${BRANCHES[$i]}"
  pr="${PRS[$i]}"
  echo "========================================"
  echo "PR #$pr — Branch: $branch"
  echo "========================================"
  
  git checkout main 2>/dev/null
  git checkout -B "rebase-$branch" "origin/$branch" 2>&1
  
  # Try rebase
  if git rebase origin/main 2>&1; then
    echo "✅ Rebase clean for PR #$pr"
    git push origin "rebase-$branch:$branch" --force 2>&1
    echo "✅ Force-pushed PR #$pr"
  else
    echo "❌ Conflicts in PR #$pr"
    # Show conflicting files
    git diff --name-only --diff-filter=U 2>/dev/null
    git rebase --abort 2>/dev/null
  fi
  
  git checkout main 2>/dev/null
  echo ""
done
