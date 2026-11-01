# The Daily Brief

A personal printed morning paper, written by Claude every day and printed on your home printer.

You decide what's in it. Pick from built-in sections, such as headlines, trends in topics you follow, takeaways from newsletters in your inbox, vocabulary with spaced repetition, a short lesson, a quote, speaking and writing drills or a reflection question. Or describe your own sections in plain language, like "on this day in history" or "a chess puzzle". Arrange them over one double-sided sheet.

The paper remembers what it has taught you: `state/progress.json` tracks the words you've learned and when they're due for review, and records past lessons and prompts so nothing repeats.

## How it works

```
Claude desktop app, scheduled task (e.g. 06:30)
   │  follows prompts/daily-brief.md
   │  uv run daily-brief context      what's due for review, what not to repeat
   │  Gmail connector + web search    newsletters, news, trends
   │  writes out/YYYY-MM-DD.json
   │  uv run daily-brief build …      HTML ► PDF, records progress
   └► uv run daily-brief deliver …    lp ► your printer (double-sided)
```

Claude does the research and writing; a small Python CLI handles the deterministic parts (state, rendering, printing). It runs on your Claude subscription: no API key and no server.

## Requirements

- macOS or Linux
- [uv](https://docs.astral.sh/uv/)
- WeasyPrint's system libraries: `brew install pango` (macOS) or `apt install libpango-1.0-0 libpangoft2-1.0-0` (Debian/Ubuntu)
- A printer set up on your computer (`lpstat -p` lists it). Double-sided output needs a printer with automatic duplex.
- The [Claude desktop app](https://claude.ai/download), to run the daily scheduled task
- Optional: the Gmail connector in Claude, for the "From your inbox" column

## Setup

```bash
git clone https://github.com/pranaymodukuru/daily-brief && cd daily-brief
uv sync
cp config.example.yaml config.yaml
```

Edit `config.yaml`; see [Make it yours](#make-it-yours) below. At minimum, set `reader.about` and `delivery.printer` (your printer's name from `lpstat -p`).

Check that rendering and printing work with the sample edition:

```bash
uv run daily-brief build examples/sample-edition.json --no-record   # writes out/2026-01-01.pdf
uv run daily-brief deliver out/2026-01-01.pdf                       # prints it
```

## Make it yours

Everything lives in `config.yaml` (see [config.example.yaml](config.example.yaml)):

- **`reader`:** who the paper is for and what they care about. Every section is written for this person.
- **`instructions`:** tone and style for the whole paper.
- **`paper.pages`:** the layout. Each page has a `left` and `right` column of section ids, in order. Two pages make one double-sided sheet.
- **`sections`:** options for each section, such as `topics`, `count` and `focus`.

| Built-in section | What it prints | Key options |
|---|---|---|
| `headlines` | News from the last 1–2 days | `topics`, `count` |
| `trends` | What's changing in each topic | `topics`, `points` |
| `newsletters` | One takeaway per newsletter (Gmail connector) | `query`, `lookback_days` |
| `quote` | A real, attributed quote | `focus` |
| `vocabulary` | New words plus spaced-repetition review | `new_per_day`, `max_review`, `focus` |
| `phrase` | An idiom or useful phrase | |
| `lesson` | A short practical lesson | `themes` |
| `speaking` | A timed speaking prompt with a structure | `seconds`, `focus` |
| `drill` | Sentences to improve, answers the next day | `focus` |
| `pronunciation` | A tricky phrase and a tip | |
| `reflection` | A question, with lines to write on | |
| `checklist` | Your daily habits, to tick off | `items` |

**Custom sections:** use any id you like, with `type: custom`:

```yaml
sections:
  chess:
    type: custom
    title: "Puzzle"
    instructions: "A mate-in-two chess puzzle in algebraic notation, solution printed tomorrow."
```

Then add `chess` to a page. Any section that isn't on a page is skipped.

## Schedule it

In the Claude desktop app, open **Code → Scheduled → New task**, choose a daily time (for example 06:30), and use this prompt with your own path:

> Produce and print today's edition of "The Daily Brief". Work in the repository `/path/to/daily-brief` (cd there first). Read `prompts/daily-brief.md` and follow its steps exactly. Never invent news: every headline must come from a newsletter you read or a web result from the last 2 days. Only read email, never send or change it. If today's edition is already in `state/progress.json`, don't print it again.

**When it runs**
- **App open and computer awake at the scheduled time:** it prints then.
- **App closed, or computer asleep or off:** it runs as soon as the app is open and the computer is awake again, so you never miss an edition. It just arrives later.
- **Printer off or out of paper:** the PDF stays in `out/` and the run reports the error.

**Have it ready before you wake up (macOS).** Keep the app open and let the Mac wake itself a few minutes earlier:

```bash
sudo pmset repeat wakeorpoweron MTWRFSU 06:25:00    # undo: sudo pmset repeat cancel
```

## Ideas

- **Language or speaking practice:** combine `vocabulary`, `speaking`, `drill` and `pronunciation`, then practise the speaking prompt with Claude's voice mode and ask for feedback.
- **Focused news:** a front page of `headlines` and `newsletters` only, with a `trends` column for the industry you work in.
- **Family edition:** custom sections for a riddle, a fun fact and the weather, written for kids.

## Manual use

```bash
uv run daily-brief context                          # JSON the agent writes from
uv run daily-brief build out/2026-01-01.json        # render PDF + record progress
uv run daily-brief build out/… --no-record          # render only
uv run daily-brief build out/… --layout compact     # one-page edition
uv run daily-brief deliver out/2026-01-01.pdf       # print (or email, see below)
```

## Privacy

`config.yaml`, `state/` and `out/` are gitignored: your profile, progress and editions stay on your machine.

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
