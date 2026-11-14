# CLAUDE.md

Instructions for every Claude Code session in this repo. Read them and follow them.

## About this repo

- Team **Smooth Operators**: Roy, Shai, Noa. NASA Space Apps Challenge 2026, Haifa (Technion), Nov 14–15.
- Challenge: **Dancing with the SARs**: an interactive app that tracks and visualizes surface change using NISAR radar data.
- **`docs/01-Competition.md` is the source of truth for the hackathon:** rules, dates, deadlines, schedule, support, free tools,
  what to submit, judging, prizes, the full challenge statement and all official resources.
- `docs/02-Submission-guide.md`: form fields, AI watermark rules, demo limits, final checklist.
- `docs/03-Citation-and-AI.md`: how to credit data, tools and papers, and how to disclose AI use.
- Diagrams in docs: use Mermaid code blocks (GitHub renders them). Add one only where a flow or structure is clearer as a picture.

## What we are building toward

Let the submission and the judging criteria guide every design and development decision.

**What to submit:** one solution that includes all six parts, in English, by **Nov 15, 23:59**:
1. High-Level Summary: what we built, why it matters, how it answers the challenge
2. Project Demo: 7 slides or a 30-second video
3. Final Project Link: public, linked to our Git repo
4. Project Details: how it works, tools used, limitations
5. Data & AI Disclosure: NASA data, other data, AI tools used
6. References: links to all data sources and external tools

- Partial is OK. For anything unfinished, write what we intended to do.
- The pitch deck goes to the Haifa organizers by email at 18:00 on Nov 15. Aim to submit on the site by 22:00.

**Judging criteria:** Impact · Creativity · Validity (scientific and technical correctness) · Relevance (to the challenge) · Presentation.
- Judges look for **problem → NASA data → method → clear result**.
- We must show **why the solution is accurate and scientific**, and how it answers the problem.
- Prefer a focused, demoable MVP over a big system we can't finish.
- NASA data is required for global judging.
- Extra Haifa prizes to keep in mind: **Dual-Use Innovation** (advances space exploration and also benefits Earth) and **best use of Canadian Space Agency (CSA) data**.

## UI and writing style

- Keep it short. UI text, docs and replies: fewer words, no long explanations, unless someone asks for detail.
- Keep the user in one place. Show results on the map/globe in context (a panel over the map, layers draped in place),
  not on a separate page that loses scale and location.

## Keeping the records

These files feed the Disclosure, References and Summary parts of the submission. Update them as you go, without being asked,
and commit them with the related change. How to write each credit line: `docs/03-Citation-and-AI.md`.

- **`docs/04-Sources-and-tools.md`: what we used.** Add a line the first time we use something new: a data source, library,
  service, AI tool, or a reference we relied on. This includes things the user tells you they used outside the repo.
- **`ACKNOWLEDGMENTS.md`: credits and licences.** Whenever we rely on someone else's data, code, API, map tiles, library or paper,
  add it there too (with its licence / credit line), in the same commit. Bundled third-party code keeps its licence file next to it.
- **AI use:** code or data made with AI is stated in the README and commit trailers; AI-made images and videos carry a visible watermark.
- At the end, write the Disclosure, References and Summary parts from these files plus the git history.

## Who is working

- Three people, each running their own Claude Code on their own local clone: **Roy**, **Shai**, **Noa**.
- Find out who your user is from `git config user.name`. If it isn't clearly Roy, Shai or Noa, ask once.
- Everyone may edit any file in the repo, including this one.

## Repo layout

- Build in modules. Each area of work lives in its own top-level folder, e.g. backend, frontend, data, scripts.
- Create a folder only when there is real work for it. No empty placeholder folders.
- Folder structure follows the architecture. Pick names that say what the module does, and keep related code together.
- We split the work by area, and each person mostly works in one area. Clear boundaries mean fewer conflicts.
- Before creating a new top-level folder, propose it to your user. The team should agree on the structure.

Current files and folders:

- `docs/`: markdown notes. Name files `NN-Topic.md`, numbered from 01.
- `Glossary.md`: every abbreviation we use. When a doc introduces a new abbreviation, add it here in the same commit.
  **Keep it in strict A-Z order** (insert in place, never append at the end).
- `data/` (when needed): local data files only. Git ignores it, so it is never committed.
- `LICENSE`: MIT (our code). NASA data keeps its own terms and credit (see `ACKNOWLEDGMENTS.md`).
- `ACKNOWLEDGMENTS.md`: third-party data, imagery, software and papers we use, with their licences and credit lines.
- `index.html`: the site's entry page (served by Vercel).
- `.vercelignore`: allowlist of what goes to the site (see Deployment).

## Git workflow

- Everyone pushes straight to `main`. No PRs.
- Once per clone, make sure `git config pull.rebase true` is set. Check and set it at the start if it isn't.
- Before you start work, and before every push: `git pull`.
- Make small, focused commits and push often.
- **Never** force-push (`git push --force` / `-f`). Never rewrite history that is already pushed.
- Commit only what the user asked to change. Don't sweep in unrelated files.

## Commit messages

- Start every commit title with the user's name in brackets: `[Roy]`, `[Shai]` or `[Noa]`.
  The name comes from `git config user.name` of the clone, never from who is mentioned in the change.
- Example: `[Shai] Add GUNW download script`
- Keep the title short and say what changed.
- Commits Claude helped with end with the `Co-Authored-By: Claude ...` trailer (it is our AI disclosure).
- The commit author email is public. Use your GitHub noreply address (`ID+user@users.noreply.github.com`)
  in `git config user.email`, not a personal email.

## Free-text team files

- Shared notes files (e.g. `docs/ideas.md`) are edited by all three of us.
- Start each entry with a header line naming who and when, then the text:

  ```
  **Roy, 14.11.26 19:33:00 says:** ...
  ```

- Date format: `DD.MM.YY HH:MM:SS`, local time. Get the real time from the system (e.g. `date`). Don't guess it.
- Add new entries. Don't rewrite or delete other people's entries.

## Conflicts

- If a `git pull` gives a conflict, the person whose push failed fixes it.
- **Simple conflict**, where both changes can obviously be kept (e.g. different lines, two new entries): resolve it, then tell the user what you did.
- **Real conflict**, where both people changed the same thing differently: **stop and flag it.** Don't pick a side.
  - Find who made the other change from the `[NAME]` in that commit's title (`git log`).
  - Tell your user to check with that person before resolving. Example: "Conflict in `backend/api.py` with Roy's commit `[Roy] ...`. Check with Roy before resolving."

## Data

- NISAR files (HDF5, often hundreds of MB) go in `data/`, which git ignores. Never commit them.
- Commit the **scripts** that download or produce data, not the data itself.
- If a file looks large (over ~10 MB), don't commit it. Ask first.

## Public repo: keep private things out

The repo is public and judges will read it. Everything committed stays in the history forever, even if deleted later.

- **Secrets:** never commit passwords, tokens, API keys, NASA Earthdata logins.
  - Each person keeps their own secrets in a local `.env` file, which git ignores.
  - If a needed variable is missing, add its name (with no value) to `.env.example`. Ask the user to put the real value in their own `.env`.
- **Personal details:** no personal emails, phone numbers, home addresses, ID numbers or private links. Names in the README are fine.
  Public organizer contacts (e.g. the Haifa organizers' email) are fine.
- **Dev and hosting details:** don't write our development URLs or Vercel project/team names or IDs anywhere in the repo
  (code, docs, README, comments). The `.vercel/` folder stays git-ignored.
  The final public URL (our GoDaddy domain) goes in the README only when we submit.
- **Local tool files:** `.claude/settings.local.json`, `CLAUDE.local.md`, editor folders stay git-ignored.
- **Before every commit:** look at `git diff --staged` for any of the above. If something private was already pushed,
  stop and tell the user (rotate the secret; don't rewrite history on your own).

## Deployment (Vercel)

- The site deploys from `main` on every push. Vercel serves the repo root as a static site; `index.html` at the root is the entry page.
- **`.vercelignore` is an allowlist:** it ignores everything, then un-ignores only what the site needs.
  When you add a file or folder the site must serve, add a `!path` line there in the same commit.
- Never let `docs/`, `data/`, scripts, `.env*` or other non-site files into the deployment.
- If we add a build step later (e.g. a framework in its own folder), update `.vercelignore` and this section together.
