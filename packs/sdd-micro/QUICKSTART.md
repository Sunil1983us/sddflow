# Quickstart — SDD Micro

5 minutes, start to first task.

## 1. Get the pack into your project

```bash
pip install sddflow
mkdir hello-world && cd hello-world
git init
sdd init --pack sdd-micro
```

Answer the 3 prompts (project name, feature name, which AI tool). This
fills `.specify/manifest.yml` and creates an empty
`.specify/contexts/{feature}.md`.

*(No CLI? Unzip the pack into your project folder instead and fill
`.specify/manifest.yml` by hand — see README.md.)*

## 2. Describe what you're building

Either write a couple of sentences in `.specify/contexts/{feature}.md`,
or just tell the agent directly — no file required for something this
small:

```
/specify
A CLI script in Python that prints "Hello, world!" and accepts an
optional --name flag to greet someone by name. No dependencies, run
with `python greet.py`.
```

## 3. Confirm the constitution (GATE-1)

The agent generates `constitution.md` Part 2 — a short DRAFT with the
tech stack (Python, no framework, `python greet.py` to run) and any
ground rules. Read it, edit anything wrong, then say:

```
confirmed
```

## 4. Generate tasks

```
/task
```

Produces a short, flat `tasks.md` — e.g. TASK-001 "scaffold greet.py with
argparse", TASK-002 "add tests for default and --name cases".

## 5. Implement

```
/implement
```

The agent does TASK-001, runs its verification step, reports the result,
and waits for "next" before moving to TASK-002. Repeat until done.

That's it — no BRD, no sign-off meeting, no Jira board. For a project
this size, `constitution.md` + `tasks.md` + the code itself *is* the
documentation.

## Next

- Bigger project than you thought? See README.md → "Outgrowing sdd-micro"
- Want to know why even a 50-line script has a constitution? See
  `WHY-SDD.md`
