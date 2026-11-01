"""daily-brief: the deterministic half of the daily brief.

The agent (Claude, following prompts/daily-brief.md) does the research and
writing; these commands handle state, rendering and printing.

  daily-brief context              print what today's edition needs (JSON)
  daily-brief build CONTENT.json   validate, render PDF, record progress
  daily-brief print PDF            send a PDF to the configured printer
  daily-brief deliver PDF          print or email it, per delivery.mode
  daily-brief hn [--top N]         today's Hacker News front page (JSON)
  daily-brief weather              today's forecast for sources.weather (JSON)
  daily-brief feeds [--hours N]    recent posts from sources.feeds (JSON)
"""

import argparse
import calendar
import json
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from daily_brief import deliver, render, state, weather

ROOT = Path.cwd()
BLOCK_KINDS = {"news", "list", "text", "terms", "prompt", "quote", "lines", "checklist",
               "agenda", "exercise", "sudoku"}


def load_config() -> dict:
    path = ROOT / "config.yaml"
    if not path.exists():
        sys.exit("config.yaml not found: copy config.example.yaml and edit it")
    return yaml.safe_load(path.read_text())


def cmd_context(args, cfg):
    st = state.load(ROOT / "state" / "progress.json")
    plan_path = ROOT / "state" / "plan.json"
    plan = json.loads(plan_path.read_text()) if plan_path.exists() else None
    ctx = state.context(st, plan, cfg, date.today())
    ctx["config"] = cfg
    print(json.dumps(ctx, indent=2, ensure_ascii=False))


def validate(content: dict) -> list[str]:
    errors = [f"missing '{k}'" for k in ("date", "pages") if k not in content]
    for n, page in enumerate(content.get("pages", []), 1):
        for col in ("left", "right"):
            for b in page.get(col) or []:
                if b.get("kind") not in BLOCK_KINDS:
                    errors.append(f"page {n} {col}: unknown block kind {b.get('kind')!r}")
    return errors


def cmd_build(args, cfg):
    content = json.loads(Path(args.content).read_text())
    if errors := validate(content):
        sys.exit("invalid content: " + "; ".join(errors))
    layout = args.layout or ("compact" if cfg["delivery"]["mode"] == "email" else "full")
    pdf = ROOT / "out" / f"{content['date']}.pdf"
    pages = render.to_pdf(content, cfg, pdf, layout)
    if not args.no_record:
        path = ROOT / "state" / "progress.json"
        st = state.record(state.load(path), content, date.fromisoformat(content["date"]))
        state.save(path, st)
    print(f"{pdf} ({layout}, {pages} pages, {pdf.stat().st_size // 1024} KB)")


def cmd_hn(args, cfg):
    """Front-page stories, most points first, so the agent needn't browse HN."""
    url = f"https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage={args.top}"
    with urllib.request.urlopen(url, timeout=20) as r:
        hits = json.load(r)["hits"]
    stories = [{
        "title": h["title"],
        "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
        "points": h.get("points", 0),
        "comments": h.get("num_comments", 0),
        "posted": h["created_at"][:16].replace("T", " "),
        "discussion": f"https://news.ycombinator.com/item?id={h['objectID']}",
    } for h in hits]
    stories.sort(key=lambda x: -x["points"])
    print(json.dumps(stories, indent=2, ensure_ascii=False))


def cmd_weather(args, cfg):
    w = (cfg.get("sources") or {}).get("weather")
    if not w:
        sys.exit("sources.weather is not set in config.yaml")
    print(json.dumps(weather.forecast(w), indent=2, ensure_ascii=False))


def cmd_feeds(args, cfg):
    """Posts from the configured RSS/Atom feeds in the last N hours, newest first."""
    import feedparser

    feeds = (cfg.get("sources") or {}).get("feeds") or []
    if not feeds:
        sys.exit("sources.feeds is not set in config.yaml")
    cutoff = datetime.now(timezone.utc).timestamp() - args.hours * 3600
    posts = []
    for f in feeds:
        parsed = feedparser.parse(f["url"], agent="Mozilla/5.0 daily-brief")
        if parsed.bozo and not parsed.entries:
            print(f"feeds: could not read {f['name']}: {parsed.bozo_exception}", file=sys.stderr)
            continue
        for e in parsed.entries:
            t = e.get("published_parsed") or e.get("updated_parsed")
            if not t or calendar.timegm(t) < cutoff:
                continue
            posts.append({
                "source": f["name"],
                "title": e.get("title", "").strip(),
                "link": e.get("link", ""),
                "published": datetime.fromtimestamp(calendar.timegm(t), timezone.utc).astimezone().strftime("%d %b %H:%M"),
                "ts": calendar.timegm(t),
                "summary": " ".join(e.get("summary", "").split())[:400],
            })
    posts.sort(key=lambda x: -x["ts"])
    for x in posts:
        del x["ts"]
    print(json.dumps(posts, indent=2, ensure_ascii=False))


def cmd_print(args, cfg):
    d = cfg["delivery"]
    cmd = ["lp"]
    if d.get("printer"):
        cmd += ["-d", d["printer"]]
    if d.get("duplex", True):
        cmd += ["-o", "sides=two-sided-long-edge"]
    cmd += ["-o", "media=A4", "-t", "The Daily Brief", args.pdf]
    subprocess.run(cmd, check=True)


def cmd_deliver(args, cfg):
    """Deliver per config: lp prints locally, email sends over SMTP, none keeps the PDF."""
    mode = cfg["delivery"]["mode"]
    if mode == "none":
        print(f"delivery off: PDF saved at {args.pdf}")
        return
    if mode == "lp":
        return cmd_print(args, cfg)
    pdf = Path(args.pdf)
    subject = f"{(cfg.get('paper') or {}).get('title', 'The Daily Brief')}, {pdf.stem}"
    print(deliver.send(pdf, cfg["delivery"]["email_to"], subject, dry_run=args.dry_run))


def main():
    p = argparse.ArgumentParser(prog="daily-brief")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("context")
    b = sub.add_parser("build")
    b.add_argument("content")
    b.add_argument("--no-record", action="store_true", help="render only, don't update progress")
    b.add_argument("--layout", choices=list(render.LAYOUTS), help="default: compact for email delivery, else full")
    pr = sub.add_parser("print")
    pr.add_argument("pdf")
    dl = sub.add_parser("deliver", help="print (lp) or email (SMTP), per delivery.mode")
    dl.add_argument("pdf")
    dl.add_argument("--dry-run", action="store_true", help="build the email but don't send it")
    hn = sub.add_parser("hn", help="today's Hacker News front page as JSON")
    hn.add_argument("--top", type=int, default=30)
    sub.add_parser("weather", help="today's forecast for sources.weather as JSON")
    fd = sub.add_parser("feeds", help="recent posts from sources.feeds as JSON")
    fd.add_argument("--hours", type=int, default=48)
    args = p.parse_args()
    cmds = {"context": cmd_context, "build": cmd_build, "print": cmd_print, "deliver": cmd_deliver, "hn": cmd_hn,
            "weather": cmd_weather, "feeds": cmd_feeds}
    cmds[args.cmd](args, load_config())
