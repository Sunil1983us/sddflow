## Feature Drift Check (multi-session safety)

`manifest.project.feature` is one value in one shared file, not a per-chat
setting. If a second chat session — another window open on the same project
folder, or a teammate editing `manifest.yml` directly — switches it while
*this* conversation is still active, every later command in this
conversation would silently start reading and writing the new feature's
`.specify/features/{feature}/` folder instead of the one this conversation
has actually been working on. Nothing crashes; it just quietly does the
wrong thing, which is worse.

**Guard against it.** Once this conversation has established which feature
it's working on — you generated or read a document for it, or the user
named it explicitly — compare that against `project.feature` every time a
command re-reads `manifest.yml`. If the two now disagree, **STOP before
reading or writing any document** and ask: "manifest.yml's active feature
is now **{new}**, but this conversation has been working on **{previous}**
— did you (or another session) intend to switch? Reply with which one to
continue, or confirm **{new}** is correct." Proceed only after the user
answers. This has no effect on a fresh conversation's first command in a
session — there is nothing yet to contradict, so whatever `project.feature`
already says is simply where this conversation starts.

For genuinely parallel work on two features at once, two chats sharing one
`manifest.yml` is not the right setup regardless of this check — recommend
a separate working copy per feature (e.g. `git worktree add`), each with
its own `.specify/manifest.yml`. See HOW-TO-USE.md → "Working on Multiple
Features."

**When you do intentionally switch `project.feature`** (not a drift — the
user asked to move to a different feature), three fields move together,
not just one: `project.feature` (the folder-path pointer), `project.
context_file` (that feature's own context doc), and — once a project has
more than one feature — `project.feature_display_name` (see CLAUDE.md
"`{Feature Name}` convention"). Leaving `feature_display_name` stale means
the new feature's documents, Confluence pages, and Jira Epic all carry the
previous feature's name — a real collision (Confluence page titles must be
unique), not just a cosmetic mismatch.
