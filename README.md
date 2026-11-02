# The Daily Brief

A personal printed morning paper, written by Claude every day and printed on your home printer.

You don't configure sections. You describe what you want in your own words, for example:

> Keep me up to date on climate tech. I'm learning German (A2), so teach me a few words and one grammar point a day. I want to get better at presentations.

Claude designs a paper around that: German words with review, a grammar box, climate headlines and a speaking exercise. It keeps the same layout every day until you change your wishes.

The paper also remembers what it has taught you. Each subject you're learning gets spaced-repetition review and running notes, so lessons build from day to day instead of starting over.

## How it works

```
Your coding agent (e.g. a Claude scheduled task at 06:30)
   │  uses the daily-brief skill (skills/daily-brief/SKILL.md)
   │  daily-brief context             wishes, saved plan, what's due for review
   │  (first run / wishes changed)    designs the paper ► state/plan.json
   │  Gmail, Calendar, HN, web       newsletters, meetings, news
   │  writes out/YYYY-MM-DD.json      today's content as generic blocks
   │  daily-brief build …             HTML ► PDF, records learning progress
   └► daily-brief deliver …           detected printer (double-sided), or just the PDF
```

The agent does the editing and writing; a small Python CLI handles the deterministic parts (state, rendering, printing). With Claude it runs on your subscription: no API key and no server. The skill is a plain `SKILL.md`, so other agents that read skills (such as Codex) can use it too.

## Requirements

- macOS or Linux
- [uv](https://docs.astral.sh/uv/)
- WeasyPrint's system libraries: `brew install pango` (macOS) or `apt install libpango-1.0-0 libpangoft2-1.0-0` (Debian/Ubuntu)
- Optional: a printer set up on your computer. It's found automatically (`daily-brief printers` shows which); without one, each edition is saved as a PDF. Double-sided output needs a printer with automatic duplex.
- A coding agent: Claude Code (the [Claude desktop app](https://claude.ai/download) can run it as a daily scheduled task) or another agent that reads `SKILL.md` skills
- Optional: the Gmail connector in Claude, for the "From your inbox" column

## Install (local)

```bash
git clone https://github.com/pranaymodukuru/daily-brief && cd daily-brief
./install.sh
```

`install.sh` puts the `daily-brief` command on your PATH (with `uv tool install`), links the skill into the skills folder of each agent it finds (`~/.claude/skills`, `~/.codex/skills`, `~/.agents/skills`) and creates your home folder, `~/.daily-brief`, with a `config.yaml`. Run it again after a `git pull`; `./install.sh --uninstall` removes the command and links but keeps your paper.

**Or as a Claude Code plugin**, instead of the skill links (use one or the other, so the skill isn't loaded twice):

```
/plugin marketplace add /path/to/daily-brief
/plugin install daily-brief@daily-brief
```

On first use the skill installs the `daily-brief` command itself if it's missing.

Edit `~/.daily-brief/config.yaml` and write your `wishes` (see [Make it yours](#make-it-yours)), or just ask your agent for "today's daily brief" and it asks you what you want. Check that rendering and printing work with the sample edition:

```bash
daily-brief printers                                          # which printer would be used
daily-brief build examples/sample-edition.json --no-record    # writes ~/.daily-brief/out/2026-01-01.pdf
daily-brief deliver ~/.daily-brief/out/2026-01-01.pdf         # prints it, or keeps the PDF
```

**Where your data lives.** Config, state and editions are in the home folder: `$DAILY_BRIEF_HOME` if set, else the current folder if it has a `config.yaml` (so a checkout set up the old way keeps working), else `~/.daily-brief`.

## Make it yours

Everything lives in `config.yaml` (see [config.example.yaml](src/daily_brief/config.example.yaml)):

- **`wishes`:** what you want from the paper, in plain language: interests, things you're learning and at what level, habits, tone, what to leave out.
- **`reader`:** your name and the language the paper is written in.
- **`sources.newsletters`:** optional. A Gmail search for newsletters to summarise (needs the Gmail connector).
- **`sources.calendar`:** optional. Puts today's meetings (time and title) on the front page (needs the Google Calendar connector).
- **`sources.hackernews`:** optional. Today's Hacker News front page, fetched by `daily-brief hn` (no account needed).
- **`sources.weather`:** optional. A one-line forecast under the masthead (`place`; Open-Meteo, no account needed).
- **`sources.feeds`:** optional. RSS/Atom feeds, e.g. AI company blogs, read by `daily-brief feeds` (the most reliable source for launches).
- **`sources.inbox`:** optional. A Gmail search for personal emails; the paper lists the ones needing a reply or with a deadline, as short actions without sensitive details.
- **`paper.pages`:** how many printed pages; 2 makes one double-sided sheet.
- **`delivery`:** `mode: auto` (the default) prints on `printer`, or on the detected one when that's empty (system default first, fax and PDF queues skipped), and only saves the PDF if there's none. `lp` always prints and fails if the printer isn't there; `none` never prints.

**The plan.** On the first run, Claude turns your wishes into a plan, saved as `state/plan.json`: which sections, in what order, with what purpose. Every edition follows that plan, so the paper feels familiar. Edit your wishes and the next run redesigns it. To force a redesign without changing them, delete `state/plan.json`.

**Learning.** Anything you're learning becomes a subject in `state/progress.json`, such as "German" or "English vocabulary". New terms come back for review after 1, 3, 7 and 21 days and so on, and a short note per subject records where the lessons left off.

**Layout.** A page is either two columns (`left`/`right`) or a stack of rows, each with its own columns and optional widths, for example one row per subject.

**Building blocks.** Each section is printed as one of a few generic blocks: news (with optional lead stories and source stamps), stat (number of the day), list, text, terms, prompt (boxed exercise), quote, lines (space to write), checklist, agenda (today's meetings), exercise (numbered items with answer lines), diagram (a figure Claude draws as SVG, e.g. for a machine-learning concept) and sudoku (generated in code, with yesterday's solution). They're defined in [`blocks.html.j2`](src/daily_brief/templates/blocks.html.j2), so new kinds of content need no code changes.

**Footer.** Each page shows its number, the model that wrote the paper, the paper's size in tokens, and how many tokens the run used with an approximate cost at Anthropic API list prices. The numbers come from Claude Code's own transcript of the run. On a Claude subscription you don't pay per token, so the cost shows what the run would cost on the API. Use `build --no-usage` to leave it out.

## Schedule it

In the Claude desktop app, open **Code → Scheduled → New task**, choose a daily time (for example 06:30), and use this prompt:

> Produce and print today's edition of "The Daily Brief" with the daily-brief skill, following its steps exactly. Never invent news: every headline must come from a newsletter you read or a web result from the last 2 days. Only read email, never send or change it. If today's edition is already in `state/progress.json`, don't print it again.

**When it runs**
- **App open and computer awake at the scheduled time:** it prints then.
- **App closed, or computer asleep or off:** it runs as soon as the app is open and the computer is awake again, so you never miss an edition. It just arrives later.
- **No printer found:** the edition is saved as a PDF in `out/`.
- **Printer off or out of paper:** the PDF stays in `out/` and the run reports the error. (A printer that's switched off can still look available, so the PDF is always kept.)

**Have it ready before you wake up (macOS).** Keep the app open and let the Mac wake itself a few minutes earlier:

```bash
sudo pmset repeat wakeorpoweron MTWRFSU 06:25:00    # undo: sudo pmset repeat cancel
```

## Ideas for wishes

- *"I'm learning Spanish (B1). Give me five words with review, one grammar point, and a short news story in simple Spanish."*
- *"Help me become a better public speaker: one technique a day and a 60-second speaking prompt I can practise with Claude's voice mode."*
- *"Front page: the most important world news and AI news. Back page: a chess puzzle with yesterday's solution."*
- *"For my 10-year-old: a fun fact, a riddle, a new word and a drawing prompt."*

## Manual use

```bash
daily-brief context                                 # JSON the agent writes from
daily-brief build out/2026-01-01.json               # render PDF + record progress (a rebuild replaces the day's record)
daily-brief build out/… --no-record                 # render only
daily-brief build out/… --layout compact            # one-page edition
daily-brief deliver out/2026-01-01.pdf              # print, keep or email it (see below)
```

## Privacy

Everything personal lives in your home folder (`~/.daily-brief` by default), outside the repo. In a checkout, `config.yaml`, `state/` and `out/` are gitignored: your profile, progress and editions stay on your machine.

## Later: cloud and email delivery (experimental)

Not needed for the local setup above. Parked for a future version that runs without your computer.

The idea: a Claude cloud routine produces the edition and emails a compact one-page PDF to the printer's email address (many printers have one, e.g. HP ePrint). Progress would live in Google Drive rather than in the repo.

What exists today:
- `delivery.mode: email` renders the compact one-page layout (about 20 KB) and `daily-brief deliver` sends it over SMTP to `delivery.email_to`. Credentials come from environment variables, never from the repo:

  ```bash
  export SMTP_HOST=smtp.gmail.com      # default; or e.g. smtp-relay.brevo.com
  export SMTP_PORT=587                 # default
  export SMTP_USER=...                 # SMTP login
  export SMTP_PASSWORD=...             # app password / SMTP key (macOS: or Keychain, see deliver.py)
  export SMTP_FROM=...                 # optional sender, if it differs from the login
  ```

What's been learned so far:
- **Email-to-print services may ignore duplex.** HP ePrint does, both in the PDF and in the printer's own default, which is why email editions are one page.
- **Don't send the PDF through the Gmail connector:** attachments go through the model as base64, which costs about 29k tokens for 22 KB. The script sends it instead.
- Gmail app passwords need 2-step verification. Relays such as Brevo need IP blocking turned off to work from the cloud.
- Cloud environment variables are not a secret store. Use a send-only credential (for example a Brevo SMTP key), never your main mailbox's password.

Still to do: Google Drive sync for `config.yaml` and `progress.json`, the cloud routine itself, and a check that the sandbox allows outbound SMTP.
