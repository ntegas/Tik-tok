# Как получить реальное видео (вне этой песочницы)

Эта облачная сессия работает через прокси, который **не поддерживает
WebSocket** и явно блокирует `speech.platform.bing.com` (Edge TTS). Поэтому
рендер видео здесь принципиально невозможен, независимо от ключей и
конфигурации — это ограничение сети песочницы, не баг проекта.

Пайплайн и код проверены и рабочие (см. коммит с фиксом aspect-ratio) — на
машине с обычным интернетом всё заработает сразу. Шаги:

```bash
git clone --recurse-submodules <URL твоего репозитория ntegas/Tik-tok>
cd Tik-tok/external/MoneyPrinterTurbo
cp config.example.toml config.toml
# впиши в config.toml (или .env) минимум один LLM-ключ (для генерации
# поисковых терминов футажа) и, если нужен не-local источник видео,
# pexels_api_keys / pixabay_api_keys
docker compose up -d      # api :8080, webui :8501
```

Затем из корня основного репозитория:

```bash
pip install -r requirements.txt
python3 -c "
from platforms.moneyprinter import MoneyPrinterClient
c = MoneyPrinterClient(base_url='http://localhost:8080', api_key='')
task_id = c.create_video(subject='...', script='...', language='ru')
result = c.wait_for_completion(task_id)
print(result['videos'])   # пути к готовым файлам
"
```

Либо через веб-интерфейс MoneyPrinterTurbo на `http://localhost:8501` —
руками, без нашего клиента.
