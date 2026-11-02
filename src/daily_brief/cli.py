"""daily-brief: the deterministic half of the daily brief.

The agent (following skills/daily-brief/SKILL.md) does the research and
writing; these commands handle state, rendering and printing.

Your config, state and editions live in the brief's home folder:
$DAILY_BRIEF_HOME, else the current folder if it has a config.yaml, else
~/.daily-brief.

  daily-brief init                 create the home folder and config.yaml
  daily-brief home                 print the home folder's path
  daily-brief printers             list print queues and the one that would be used
  daily-brief context              print what today's edition needs (JSON)
  daily-brief build CONTENT.json   validate, render PDF, record progress
  daily-brief print PDF            send a PDF to the configured or detected printer
  daily-brief deliver PDF          print, email or just keep it, per delivery.mode
  daily-brief hn [--top N]         today's Hacker News front page (JSON)
  daily-brief weather              today's forecast for sources.weather (JSON)
  daily-brief feeds [--hours N]    recent posts from sources.feeds (JSON)
"""

import argparse
import calendar
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from daily_brief import deliver, printers, render, state, usage, weather



def _home() -> Path:
    if env := os.environ.get("DAILY_BRIEF_HOME"):
        return Path(env).expanduser()
    if (Path.cwd() / "config.yaml").exists():
        return Path.cwd()  # a repo checkout or a folder you set up yourself
    return Path.home() / ".daily-brief"


ROOT = _home()
EXAMPLE_CONFIG = Path(__file__).parent / "config.example.yaml"
BLOCK_KINDS = {"news", "list", "text", "terms", "prompt", "quote", "lines", "checklist",
               "agenda", "exercise", "sudoku", "stat"}


def load_config() -> dict:
    path = ROOT / "config.yaml"
    if not path.exists():
        sys.exit(f"no config.yaml in {ROOT}: run `daily-brief init` and edit it")
    return yaml.safe_load(path.read_text())


def cmd_context(args, cfg):
    st = state.load(ROOT / "state" / "progress.json")
    plan_path = ROOT / "state" / "plan.json"
    plan = json.loads(plan_path.read_text()) if plan_path.exists() else None
    ctx = state.context(st, plan, cfg, date.today())
    ctx["config"] = cfg
    ctx["home"] = str(ROOT)
    print(json.dumps(ctx, indent=2, ensure_ascii=False))


def validate(content: dict) -> list[str]:
    errors = [f"missing '{k}'" for k in ("date", "pages") if k not in content]
    for n, page in enumerate(content.get("pages", []), 1):
        cols = [page.get("left") or [], page.get("right") or []]
        cols += [col for row in page.get("rows") or [] for col in row.get("columns") or []]
        for b in (b for col in cols for b in col):
            if b.get("kind") not in BLOCK_KINDS:
                errors.append(f"page {n}: unknown block kind {b.get('kind')!r}")
    return errors


def cmd_build(args, cfg):
    content = json.loads(Path(args.content).read_text())
    if errors := validate(content):
        sys.exit("invalid content: " + "; ".join(errors))
    layout = args.layout or ("compact" if _mode(cfg) == "email" else "full")
    pdf = ROOT / "out" / f"{content['date']}.pdf"
    run = None if args.no_usage else usage.run_usage((cfg.get("cost") or {}).get("prices"))
    pages = render.to_pdf(content, cfg, pdf, layout, run)
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


def _mode(cfg) -> str:
    return (cfg.get("delivery") or {}).get("mode") or "auto"


def cmd_init(args, cfg):
    cfg_path = ROOT / "config.yaml"
    if cfg_path.exists():
        print(f"{cfg_path} already exists; edit it to change your paper")
    else:
        ROOT.mkdir(parents=True, exist_ok=True)
        shutil.copy(EXAMPLE_CONFIG, cfg_path)
        print(f"created {cfg_path}: write your wishes in it")
    printer = printers.find()
    print(f"printer: {printer or 'none found, editions will be saved as PDFs in ' + str(ROOT / 'out')}")


def cmd_home(args, cfg):
    print(ROOT)


def cmd_printers(args, cfg):
    preferred = ((cfg or {}).get("delivery") or {}).get("printer", "")
    print(json.dumps({"queues": printers.available(), "would_use": printers.find(preferred)}, indent=2))


def cmd_print(args, cfg):
    d = cfg.get("delivery") or {}
    printer = printers.find(d.get("printer", ""))
    if not printer:
        wanted = f"printer {d['printer']!r} is not available" if d.get("printer") else "no printer found"
        sys.exit(f"{wanted} (see `daily-brief printers`); PDF kept at {args.pdf}")
    cmd = ["lp", "-d", printer]
    if d.get("duplex", True):
        cmd += ["-o", "sides=two-sided-long-edge"]
    cmd += ["-o", "media=A4", "-t", "The Daily Brief", args.pdf]
    subprocess.run(cmd, check=True)
    print(f"sent {Path(args.pdf).name} to {printer}")


def cmd_deliver(args, cfg):
    """Deliver per config: auto prints if a printer is found and otherwise keeps
    the PDF, lp must print, email sends over SMTP, none keeps the PDF."""
    mode = _mode(cfg)
    if mode == "none":
        print(f"delivery off: PDF saved at {args.pdf}")
        return
    preferred = (cfg.get("delivery") or {}).get("printer", "")
    if mode == "auto" and not printers.find(preferred):
        missing = f"printer {preferred!r} is not available" if preferred else "no printer found"
        print(f"{missing}: PDF saved at {args.pdf}")
        return
    if mode == "lp":
        return cmd_print(args, cfg)
    pdf = Path(args.pdf)
    subject = f"{(cfg.get('paper') or {}).get('title', 'The Daily Brief')}, {pdf.stem}"
    print(deliver.send(pdf, cfg["delivery"]["email_to"], subject, dry_run=args.dry_run))


def main():
    p = argparse.ArgumentParser(prog="daily-brief")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="create the home folder and a config.yaml to edit")
    sub.add_parser("home", help="print the home folder's path")
    sub.add_parser("printers", help="list print queues and the one that would be used")
    sub.add_parser("context")
    b = sub.add_parser("build")
    b.add_argument("content")
    b.add_argument("--no-record", action="store_true", help="render only, don't update progress")
    b.add_argument("--no-usage", action="store_true", help="leave the run's model, tokens and cost out of the footer")
    b.add_argument("--layout", choices=list(render.LAYOUTS), help="default: compact for email delivery, else full")
    pr = sub.add_parser("print")
    pr.add_argument("pdf")
    dl = sub.add_parser("deliver", help="print, email or keep the PDF, per delivery.mode")
    dl.add_argument("pdf")
    dl.add_argument("--dry-run", action="store_true", help="build the email but don't send it")
    hn = sub.add_parser("hn", help="today's Hacker News front page as JSON")
    hn.add_argument("--top", type=int, default=30)
    sub.add_parser("weather", help="today's forecast for sources.weather as JSON")
    fd = sub.add_parser("feeds", help="recent posts from sources.feeds as JSON")
    fd.add_argument("--hours", type=int, default=48)
    args = p.parse_args()
    setup = {"init": cmd_init, "home": cmd_home, "printers": cmd_printers}
    if args.cmd in setup:  # these work before there is a config
        cfg_path = ROOT / "config.yaml"
        return setup[args.cmd](args, yaml.safe_load(cfg_path.read_text()) if cfg_path.exists() else None)
    cmds = {"context": cmd_context, "build": cmd_build, "print": cmd_print, "deliver": cmd_deliver, "hn": cmd_hn,
            "weather": cmd_weather, "feeds": cmd_feeds}
    cmds[args.cmd](args, load_config())
