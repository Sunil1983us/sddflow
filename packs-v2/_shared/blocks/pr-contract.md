- Estimate before every task.
- If > max_lines_per_pr → SPLIT A/B/C → confirm → one at a time.
- After task, per manifest.workflow_mode:
  - github: state files + lines + "PR ready" → wait for go.
  - local: run build/test/lint/coverage locally → report ✅/❌ per check →
    state files + lines + "Task accepted" → wait for go.
