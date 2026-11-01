# Daily Brief: agent instructions

You are writing today's edition of a personal printed morning paper. Its
contents, order and tone are defined entirely by `config.yaml`; follow it.
Work in the repository root.

## 1. Load context

Run `uv run daily-brief context`. It returns JSON with:
- `config`: the reader (`reader.about`), global `instructions`, page layout and per-section options
- `sections`: the sections to produce, in print order: `{id, type, page, options}`
- `edition`, `today`
- `review_words`: vocabulary due for spaced-repetition review today (use ALL of them)
- `known_words`: never introduce one of these as a new word
- `recent_lessons`, `recent_speaking_prompts`: don't repeat these
- `yesterday_drill_answers`: print these as today's `answer_key`

Produce **only** the sections listed in `sections`. Write everything for the
reader described in `config.reader`, in `config.reader.language`, following
`config.instructions` and each section's `options` (`focus`, `topics`, counts…).

## 2. Gather (only for sections that need it)

- **newsletters** (Gmail connector): search Gmail with
  `{options.query} newer_than:{options.lookback_days}d`. Read up to 6 of the
  newest threads. For each, give one useful takeaway in your own words. Never
  reproduce newsletter text. If Gmail is unavailable, leave the list empty.
- **headlines / trends** (web search): for each topic in `options.topics`,
  search for news from the last 24–48 hours. Choose `options.count` (default 4)
  substantive headlines, and `options.points` (default 2) trend points per topic
  that say what is changing. Prefer reputable sources and name them briefly.
  Don't repeat stories already covered by newsletter takeaways.
- **Never invent news.** If fresh news is thin, print fewer items.

## 3. Write

Built-in section types and the content they need:

| type | content key | shape |
|---|---|---|
| headlines | `headlines` | `[{"topic", "title", "summary" (2–3 sentences), "source"}]` |
| trends | `trends` | `[{"area", "points": [..]}]` |
| newsletters | `newsletters` | `[{"name", "takeaway" (1–2 sentences)}]` |
| quote | `quote` | `{"text", "author"}`: real and correctly attributed, on `options.focus` if set |
| vocabulary | `words`, `review_words` | words: `options.new_per_day` × `{"word", "pos", "ipa", "meaning", "example", "use_it"}`; review: one `{"word", "meaning", "prompt"}` per due word, where the prompt makes the reader produce it |
| phrase | `phrase` | `{"text", "meaning", "example"}`: an idiom or useful phrase |
| lesson | `lesson` | `{"title", "body" (90–120 words), "try_it"}`: rotate through `options.themes` |
| speaking | `speaking` | `{"prompt", "structure": [3–4 steps], "time"}`: `options.seconds` (default 60) |
| drill | `drill`, `answer_key` | `{"instruction", "sentences": [3], "answers": [3]}`; answers print tomorrow |
| pronunciation | `pronunciation` | `{"text", "tip"}` |
| reflection | `reflection` | one question (string) |
| checklist | none | printed from `options.items` |

A section with `type: custom` stores its content under its own id as
`{"body": "...", "items": ["..."]}` (either or both), written according to
its `options.instructions`.

## 4. Assemble

Write `out/{today}.json`:

```json
{
  "date": "YYYY-MM-DD", "edition": 1,
  "greeting": "one warm, specific line for today",
  "...": "one key per section, as in the table above"
}
```

## 5. Build and check

Run `uv run daily-brief build out/{today}.json --no-record`. It prints the
PDF path, layout, page count and size. The `full` layout must have as many
pages as `config.paper.pages`; the `compact` layout (email delivery) must be 1
page. If it overflows, shorten the longest sections and rebuild. When it fits,
run `uv run daily-brief build out/{today}.json` (without `--no-record`) to
save progress.

## 6. Deliver

Run `uv run daily-brief deliver out/{today}.pdf`. It prints locally or emails
the PDF over SMTP, depending on `config.delivery.mode`. Never pass the PDF
through a connector. If delivery fails, keep the PDF and report the error in
one line.

## 7. Report

End with 3 lines: whether it was delivered, the edition number, and one line
on what's in it.
