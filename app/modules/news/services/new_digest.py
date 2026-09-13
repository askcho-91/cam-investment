"""
AI-powered news summarization layer.

Sits on top of get_global_news / get_ngn_news (or any similarly-shaped
list[dict] of news items) and produces a compact, structured digest:
an overall summary + a short list of "highlights" worth a user's attention,
each with a one-line reason it matters and a sentiment tag.

Design notes:
- The LLM is used ONLY for narration/prioritization, never for numbers.
  We pass it the already-fetched headlines/summaries; we don't ask it to
  invent facts, prices, or dates.
- Results are cached in Redis, same pattern as the news fetchers, so you
  aren't re-summarizing on every request.
- Structured output (forced JSON) so the response is directly usable by
  the frontend without further parsing/regex.
"""

import json
import enum
from os import getenv
from logging import getLogger
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel, Field, ValidationError
from google import genai

from app.core.dependencies import redis_dependency

logger = getLogger(__name__)


GEMINI_API_KEY = getenv("GEMINI_API_KEY", "")

genai_client = genai.Client(api_key=getenv("GEMINI_API_KEY", ""))


SUMMARY_CACHE_TTL_SECONDS = 60 * 30  # 30 min, mirrors finnhub cache window


class SentimentEnum(str, enum.Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"


class NewsHighlight(BaseModel):
    headline: str
    why_it_matters: str
    sentiment: SentimentEnum
    url: str | None = None
    published_at: str | None = None


class NewsDigest(BaseModel):
    overview: str = Field(..., description="2-3 sentence high level summary")
    highlights: list[NewsHighlight]
    generated_at: str
    source_count: int


class NewsSummarizationError(Exception):
    pass


def _build_prompt(news_items: list[dict], max_items: int = 25) -> str:
    """
    Trim and format news items into a compact prompt payload.
    We cap the number of items sent to control token cost / latency,
    prioritizing the most recent ones (callers should pass items already
    sorted, but we defensively sort here too).
    """
    items = sorted(
        news_items,
        key=lambda x: x.get("published_at") or "",
        reverse=True,
    )[:max_items]

    lines = []
    for i, item in enumerate(items):
        lines.append(
            f"{i + 1}. HEADLINE: {item.get('headline')}\n"
            f"   SUMMARY: {item.get('summary') or 'N/A'}\n"
            f"   PUBLISHED_AT: {item.get('published_at')}\n"
            f"   URL: {item.get('url')}\n"
            f"   CATEGORIES: {item.get('categories')}"
        )
    return "\n".join(lines)


SYSTEM_PROMPT = """You are a financial news triage assistant for a market \
observation app. You will be given a numbered list of recent news items \
(headline, summary, publish date, url, categories).

Your job:
1. Pick only the items that are genuinely significant for someone tracking \
the market (mergers, regulatory action, major earnings surprises, central \
bank/policy moves, big price-moving events). Skip filler, duplicates, and \
minor items.
2. For each picked item, write ONE short sentence explaining why it matters \
to a market watcher (not a restatement of the headline).
3. Tag each with a sentiment: positive, negative, or neutral, based on \
market impact, not general tone.
4. Write a 2-3 sentence overview of the batch as a whole.

Rules:
- Never invent facts, numbers, or events not present in the input.
- Never fabricate a URL or published_at — copy them exactly from the \
matching input item.
- If nothing in the batch is significant, return an empty highlights list \
and say so plainly in the overview.
- Return ONLY valid JSON, no markdown fences, no preamble, matching this \
shape exactly:

{
  "overview": "string",
  "highlights": [
    {
      "headline": "string",
      "why_it_matters": "string",
      "sentiment": "positive|negative|neutral",
      "url": "string or null",
      "published_at": "string or null"
    }
  ]
}
"""


async def _call_llm(news_block: str) -> str:
    if not GEMINI_API_KEY:
        raise NewsSummarizationError("GEMINI_API_KEY is not configured")

    prompt = f"{SYSTEM_PROMPT}\n\n{news_block}"

    response = genai_client.interactions.create(
        model="gemini-3.5-flash-lite",
        input=prompt,
        generation_config={"thinking_level": "low"},
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": NewsDigest.model_json_schema(),
        },
    )
    return response.output_text


async def get_news_digest(
    redis: redis_dependency,
    news_items: list[dict],
    cache_key: str,
    force_refresh: bool = False,
) -> NewsDigest:
    """
    Produce (or fetch cached) AI digest for a given set of news items.

    cache_key should encode whatever makes this batch unique, e.g.
    f"news_digest:{category.value}" or f"news_digest:ngn:{category.value}".
    Callers are responsible for fetching the underlying news items first
    (via get_global_news / get_ngn_news) and passing them in here, so this
    layer stays source-agnostic.
    """
    redis_key = f"ai_news_digest:{cache_key}"

    if not force_refresh:
        cached = await redis.get(redis_key)
        if cached:
            try:
                return NewsDigest(**json.loads(cached))
            except ValidationError:
                logger.warning(
                    "Cached digest for %s failed validation, refreshing", redis_key
                )

    if not news_items:
        digest = NewsDigest(
            overview="No recent news available for this category.",
            highlights=[],
            generated_at=datetime.now(timezone.utc).isoformat(),
            source_count=0,
        )
        await redis.setex(
            redis_key, SUMMARY_CACHE_TTL_SECONDS, digest.model_dump_json()
        )
        return digest

    news_block = _build_prompt(news_items)
    llm_result = await _call_llm(news_block)
    digest = NewsDigest.model_validate_json(llm_result)

    await redis.setex(redis_key, SUMMARY_CACHE_TTL_SECONDS, digest.model_dump_json())
    return digest
