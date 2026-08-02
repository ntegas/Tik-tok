#!/usr/bin/env python
"""CLI для запуска пайплайна агентов.

Примеры:
    python scripts/run_pipeline.py research --platform youtube --niche "нейросети для новичков"
    python scripts/run_pipeline.py publish --platform telegram
    python scripts/run_pipeline.py analytics --platform telegram
    python scripts/run_pipeline.py queue --status approved
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import orchestrator
import storage


def main():
    parser = argparse.ArgumentParser(description="Управление пайплайном соцсеть-агентов")
    subparsers = parser.add_subparsers(dest="command", required=True)

    research = subparsers.add_parser("research", help="найти тренды и сгенерировать черновики")
    research.add_argument("--platform", required=True, choices=list(orchestrator.TREND_SOURCES))
    research.add_argument("--niche", required=True, help="ниша/тематика аккаунта")
    research.add_argument("--limit", type=int, default=10)

    publish = subparsers.add_parser("publish", help="опубликовать одобренные черновики")
    publish.add_argument("--platform", required=True, choices=list(orchestrator.PLATFORM_CLIENTS))

    analytics = subparsers.add_parser("analytics", help="сводка по опубликованным постам")
    analytics.add_argument("--platform", required=True, choices=list(orchestrator.PLATFORM_CLIENTS))

    queue = subparsers.add_parser("queue", help="показать очередь контента")
    queue.add_argument("--status")
    queue.add_argument("--platform")

    args = parser.parse_args()

    if args.command == "research":
        items = orchestrator.research_and_draft(args.platform, args.niche, args.limit)
        print(f"Создано черновиков: {len(items)}")
        print(json.dumps(items, ensure_ascii=False, indent=2))
    elif args.command == "publish":
        results = orchestrator.publish_approved(args.platform)
        print(f"Обработано: {len(results)}")
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif args.command == "analytics":
        summary = orchestrator.summarize_published(args.platform)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif args.command == "queue":
        items = storage.list_items(status=args.status, platform=args.platform)
        print(json.dumps(items, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
