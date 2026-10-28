"""Telegram -> Groq -> GitHub blog publisher."""
import asyncio
import datetime as dt
import logging
import os
import re

import frontmatter
from github import Github, GithubException
from groq import Groq
from telegram import Update
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("blogbot")

# ---------- Config (environment variables) ----------
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_CHAT_ID = 9161348784  # Seedha aapki ID yahan rakh di hai
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")  # e.g. https://myblog.vercel.app
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "change-me-secret")  # letters/digits/_/-
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")  # set automatically on Render
PORT = int(os.environ.get("PORT", "10000"))

SYSTEM_PROMPT = """You are a senior SaaS analyst writing for an SEO-focused software review blog.

OUTPUT FORMAT (STRICT):
- Output ONLY a Markdown document. No preamble, no closing remarks, no code fences around the document.
- The very first line MUST be `---`. Begin with YAML frontmatter containing EXACTLY these keys:
  title: "<SEO title, 50-60 chars, wrapped in double quotes, includes the software name and 'Review'>"
  description: "<meta description, 140-160 chars, in double quotes>"
  date: "YYYY-MM-DD"
  tags: ["tag1", "tag2", "tag3", "tag4"]
- Close the frontmatter with a line containing only `---`.
- Never use double quotes inside frontmatter values; use apostrophes instead.
- Do NOT put an H1 (`# `) in the body; the title is rendered from frontmatter.

BODY STRUCTURE (use `##` and `###` headings only, in this order):
## Overview  (what it is, who it is for; 2 short paragraphs)
## Key Features  (5-7 bullet points, each starting with a bold feature name)
## Pricing  (plans in general terms; tell readers to verify current prices on the official site)
## Pros and Cons  (### Pros and ### Cons, 4-5 bullets each)
## Best Alternatives  (4-5 alternatives, each as ### <Name> with a 2-3 sentence comparison)
## Comparison Table  (a Markdown table: Tool | Best for | Free plan? | Standout feature)
## Final Verdict  (a clear 1-paragraph recommendation)
## FAQ  (3 questions as ### headings with short answers)

RULES:
- 1,200-1,600 words, clear and practical, neutral and honest tone.
- Use only facts you are confident about. If unsure about a price, version number or statistic, stay general. Never invent numbers, quotes, awards or user counts.
- Naturally use the target keyword (software name + 'review', 'alternatives') without keyword stuffing.
- Valid GitHub-flavored Markdown only. No HTML."""


# ---------- Helpers ----------
def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80] or "post"


def clean_output(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"^```(?:markdown|md)?\s*\n", "", text)
    text = re.sub(r"\n```\s*$", "", text)
    idx = text.find("---")
    return text[idx:] if idx > 0 else text


def generate_article(software: str) -> str:
    client = Groq(api_key=GROQ_API_KEY)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0.5,
        max_tokens=4000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Write the review-and-alternatives article for: {software}"},
        ],
    )
    return clean_output(resp.choices[0].message.content)


def validate_and_finalize(markdown: str):

    post = frontmatter.loads(markdown)
    for key in ("title", "description", "tags"):
        if not post.metadata.get(key):
            raise ValueError(f"Missing frontmatter key: {key}")
    if not isinstance(post.metadata["tags"], list):
        raise ValueError("tags must be a list")
    if len(post.content.split()) < 400:
        raise ValueError("Article too short")
    post.metadata["date"] = dt.date.today().isoformat()  # never trust LLM for the date
    return post


def push_to_github(slug: str, content: str, title: str) -> str:
    repo = Github(GITHUB_TOKEN).get_repo(GITHUB_REPO)
    path = f"posts/{slug}.md"
    try:
        existing = repo.get_contents(path, ref=GITHUB_BRANCH)
        repo.update_file(path, f"Update post: {title}", content, existing.sha, branch=GITHUB_BRANCH)
    except GithubException as e:
        if e.status != 404:
            raise
        repo.create_file(path, f"Add post: {title}", content, branch=GITHUB_BRANCH)
    return path


def publish(software: str) -> tuple[str, str]:
    post = validate_and_finalize(generate_article(software))
    slug = slugify(software) + "-review"
    push_to_github(slug, frontmatter.dumps(post), post.metadata["title"])
    return post.metadata["title"], slug


# ---------- Telegram handlers ----------
def is_admin(update: Update) -> bool:
    return bool(update.effective_user) and update.effective_user.id == ADMIN_CHAT_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await update.message.reply_text("Send me a software name (e.g. Notion) and I'll publish a review.")


async def handle_software(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        log.warning("Blocked non-admin user %s", update.effective_user.id if update.effective_user else None)
        return
    software = update.message.text.strip()[:80]
    await update.message.reply_text(f"Generating review for {software}...")
    try:
        title, slug = await asyncio.to_thread(publish, software)
    except Exception as e:
        log.exception("Publish failed")
        await update.message.reply_text(f"Failed: {e}")
        return
    url = f"{SITE_URL}/posts/{slug}/" if SITE_URL else f"(slug: {slug})"
    await update.message.reply_text(f"Published: {title}\nLive in ~1-2 min after Vercel builds:\n{url}")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_software))

    if RENDER_URL:  # production: webhook (lets Render's free tier sleep and wake on messages)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=WEBHOOK_SECRET,
            webhook_url=f"{RENDER_URL}/{WEBHOOK_SECRET}",
            secret_token=WEBHOOK_SECRET,
            drop_pending_updates=False,
        )
    else:  # local testing
        app.run_polling()


if __name__ == "__main__":
    main()
