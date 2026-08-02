"""Клиент к MoneyPrinterTurbo (external/MoneyPrinterTurbo) — отдельному сервису,
который рендерит видео: сценарий -> голос -> футаж -> субтитры -> сборка.

Сервис поднимается отдельно (см. external/MoneyPrinterTurbo/docker-compose.yml)
и слушает MONEYPRINTER_BASE_URL. Мы вызываем его REST API, не встраиваем его код.
"""
import time

import requests

from config import MONEYPRINTER_API_KEY, MONEYPRINTER_BASE_URL

TASK_STATE_FAILED = -1
TASK_STATE_COMPLETE = 1
TASK_STATE_PROCESSING = 4


class MoneyPrinterClient:
    def __init__(self, base_url: str = MONEYPRINTER_BASE_URL, api_key: str = MONEYPRINTER_API_KEY):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self):
        return {"x-api-key": self.api_key} if self.api_key else {}

    def create_video(
        self,
        subject: str,
        script: str = "",
        language: str = "ru",
        aspect: str = "9:16",
        voice_name: str = "",
        subtitle_enabled: bool = True,
    ) -> str:
        """Запускает рендер видео, возвращает task_id."""
        payload = {
            "video_subject": subject,
            "video_script": script,
            "video_language": language,
            "video_aspect": aspect,
            "voice_name": voice_name,
            "subtitle_enabled": subtitle_enabled,
        }
        resp = requests.post(
            f"{self.base_url}/api/v1/videos", json=payload, headers=self._headers(), timeout=30
        )
        resp.raise_for_status()
        return resp.json()["data"]["task_id"]

    def get_task(self, task_id: str) -> dict:
        resp = requests.get(
            f"{self.base_url}/api/v1/tasks/{task_id}", headers=self._headers(), timeout=15
        )
        resp.raise_for_status()
        return resp.json()["data"]

    def wait_for_completion(self, task_id: str, poll_interval: float = 5.0, timeout: float = 1800.0) -> dict:
        """Опрашивает статус до готовности видео или ошибки. Возвращает финальный task-статус."""
        started = time.monotonic()
        while True:
            task = self.get_task(task_id)
            if task["state"] == TASK_STATE_COMPLETE:
                return task
            if task["state"] == TASK_STATE_FAILED:
                raise RuntimeError(f"MoneyPrinterTurbo task failed: {task.get('error')}")
            if time.monotonic() - started > timeout:
                raise TimeoutError(f"MoneyPrinterTurbo task {task_id} did not finish in {timeout}s")
            time.sleep(poll_interval)

    def download(self, file_uri: str, dest_path: str) -> str:
        """file_uri — один из путей в task['videos'], уже абсолютный URL или относительный API-путь."""
        url = file_uri if file_uri.startswith("http") else f"{self.base_url}{file_uri}"
        resp = requests.get(url, headers=self._headers(), stream=True, timeout=60)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return dest_path
