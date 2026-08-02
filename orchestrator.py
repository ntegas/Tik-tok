"""Пайплайн: тренды -> черновик поста -> модерация -> публикация -> аналитика.

Фаза 1 (сейчас): искать тренды и предлагать похожий/такой же контент.
Фаза 2 (позже): подключить video_editor для полноценного монтажа видео вместо
текстового shot_list, и реальные publish-клиенты TikTok/Instagram после
получения API-доступа.
"""
from agents.analytics import AnalyticsAgent
from agents.content_creator import ContentCreatorAgent
from agents.moderator import ModeratorAgent
from agents.trend_researcher import TrendResearcherAgent
from platforms.instagram import InstagramClient
from platforms.manual_trends import ManualTrendSource
from platforms.moneyprinter import MoneyPrinterClient
from platforms.telegram import TelegramClient
from platforms.tiktok import TikTokClient
from platforms.youtube import YouTubeClient, YouTubeTrendSource
import storage

TREND_SOURCES = {
    "youtube": YouTubeTrendSource(),
    "tiktok": ManualTrendSource("tiktok"),
    "instagram": ManualTrendSource("instagram"),
}

PLATFORM_CLIENTS = {
    "youtube": YouTubeClient(),
    "tiktok": TikTokClient(),
    "instagram": InstagramClient(),
    "telegram": TelegramClient(),
}


def research_and_draft(platform: str, niche: str, limit: int = 10) -> list:
    """Тянет тренды для платформы, отбирает релевантные, генерирует черновики,
    прогоняет через модератора и сохраняет в очередь. Возвращает созданные items."""
    trend_source = TREND_SOURCES[platform]
    raw_trends = trend_source.fetch_trends(limit=limit)

    researcher = TrendResearcherAgent()
    selected_trends = researcher.select_trends(niche, raw_trends)

    creator = ContentCreatorAgent()
    moderator = ModeratorAgent()

    created_items = []
    for trend in selected_trends:
        draft = creator.draft_post(niche, trend)
        review = moderator.review_post(draft)
        status = "approved" if review.get("approved") else "rejected"
        item = storage.add_item(
            platform=platform,
            trend=trend,
            status=status,
            draft=draft,
            review=review,
        )
        created_items.append(item)
    return created_items


def publish_approved(platform: str) -> list:
    """Публикует все approved-элементы очереди для платформы. Если клиент платформы
    ещё не подключён (NotImplementedError), помечает item как publish_failed с причиной."""
    client = PLATFORM_CLIENTS[platform]
    results = []
    for item in storage.list_items(status="approved", platform=platform):
        try:
            result = client.publish(item["draft"])
            updated = storage.update_item(
                item["id"], status="published", post_id=result["post_id"], post_url=result.get("url")
            )
        except NotImplementedError as exc:
            updated = storage.update_item(item["id"], status="publish_failed", failure_reason=str(exc))
        results.append(updated)
    return results


def render_and_deliver_to_telegram(subject: str, script: str, language: str = "ru", caption: str = "") -> dict:
    """Рендерит видео через MoneyPrinterTurbo и присылает готовый файл в Telegram."""
    mpt = MoneyPrinterClient()
    task_id = mpt.create_video(subject=subject, script=script, language=language)
    task = mpt.wait_for_completion(task_id)
    video_uri = task["videos"][0]

    local_path = f"/tmp/{task_id}.mp4"
    mpt.download(video_uri, local_path)

    telegram = TelegramClient()
    return telegram.send_video(local_path, caption=caption or subject)


def summarize_published(platform: str) -> dict:
    """Собирает аналитику по опубликованным постам. metrics должны быть уже
    записаны в item (через client.get_analytics, где он реализован)."""
    published = storage.list_items(status="published", platform=platform)
    metrics = [item.get("metrics") for item in published if item.get("metrics")]
    if not metrics:
        return {"summary": "Нет метрик для анализа — либо ещё нет публикаций, "
                            "либо get_analytics не реализован для этой платформы.",
                "what_worked": [], "what_to_try_next": []}
    return AnalyticsAgent().summarize(metrics)
