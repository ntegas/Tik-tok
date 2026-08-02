# Tik-tok — агенты для ведения соцсетей

Набор LLM-агентов (на Claude) для полуавтоматического ведения TikTok, Instagram,
YouTube Shorts и Telegram: поиск трендов → генерация черновика поста →
модерация → публикация → аналитика.

## Агенты

| Агент | Файл | Что делает |
|---|---|---|
| Trend Researcher | `agents/trend_researcher.py` | Из сырого списка трендов отбирает релевантные под нишу аккаунта и объясняет, как адаптировать |
| Content Creator | `agents/content_creator.py` | Пишет подпись, хэштеги, хук и покадровый сценарий (режиссура) |
| Moderator | `agents/moderator.py` | Проверяет черновики перед публикацией и разбирает входящие комментарии (отвечать/скрыть/игнорировать) |
| Analytics | `agents/analytics.py` | Превращает сырые метрики постов в выводы и рекомендации |

Плюс `platforms/*` — клиенты конкретных соцсетей и источники трендов, и
`orchestrator.py`, который связывает агентов в единый пайплайн.

## Статус по платформам

| Платформа | Тренды | Публикация | Комментарии | Аналитика |
|---|---|---|---|---|
| YouTube | ✅ через YouTube Data API (только API key) | ⛔ нужен OAuth-клиент | ⛔ | ⛔ |
| Telegram | — (нет понятия трендов) | ✅ через Bot API | ⛔ (нужна discussion-группа) | ⛔ |
| TikTok | ⚠️ вручную в `data/manual_trends.json` | ⛔ нужен approved Content Posting API | ⛔ | ⛔ |
| Instagram | ⚠️ вручную в `data/manual_trends.json` | ⛔ нужен Business-аккаунт + App Review | ⛔ | ⛔ |

TikTok и Instagram не выдают публикацию/тренды без прохождения официального
review их API — это ограничение платформ, не кода. Как только появятся токены
(`.env`), заглушки (`NotImplementedError`) заменяются на рабочие вызовы.

## Быстрый старт

```bash
pip install -r requirements.txt
cp .env.example .env   # заполнить ANTHROPIC_API_KEY и нужные платформенные ключи
```

```bash
# 1. Найти тренды на YouTube под нишу и сгенерировать черновики
python scripts/run_pipeline.py research --platform youtube --niche "нейросети для новичков"

# 2. Посмотреть очередь (кто approved/rejected модератором)
python scripts/run_pipeline.py queue --status approved

# 3. Опубликовать одобренное (реально работает для telegram)
python scripts/run_pipeline.py publish --platform telegram

# 4. Сводка по опубликованным постам
python scripts/run_pipeline.py analytics --platform telegram
```

Для TikTok/Instagram: заполни `data/manual_trends.json` актуальными трендами
вручную (пока нет доступа к их API трендов), дальше пайплайн работает так же.

## Рендер видео (MoneyPrinterTurbo)

Вместо своего монтажного движка используем готовый open-source сервис
[MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) (MIT) —
он умеет сценарий → голос (TTS) → футаж → субтитры (Whisper/Edge) → сборка
видео. Подключён как git submodule в `external/MoneyPrinterTurbo`, мы его
не форкаем и не копируем код — вызываем как отдельный сервис по HTTP.

```bash
git submodule update --init --recursive
cd external/MoneyPrinterTurbo
docker compose up -d   # поднимет API на :8080 и веб-интерфейс на :8501
```

Клиент к нему — `platforms/moneyprinter.py` (`MoneyPrinterClient`): создать
задачу рендера, дождаться готовности, скачать файл. Пока не подключён к
`orchestrator.py` — это следующий шаг, отдельно от текущего.

## Роадмап

- **Фаза 1 (сейчас)**: искать тренды и предлагать похожий/такой же контент —
  текстовые черновики (подпись, хэштеги, сценарий).
- **Фаза 2**: связать `orchestrator.py` с `MoneyPrinterClient`, чтобы черновик
  автоматически превращался в готовый видеофайл.
- **Фаза 3**: получить official API-доступ к TikTok Content Posting API и
  Instagram Graph API, включить реальную публикацию и обработку комментариев.
