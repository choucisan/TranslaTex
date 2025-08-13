import time
import threading
from openai import OpenAI
from .config import config

lang_map = {
    "zh": "简体中文",
    "zh-TW": "繁體中文",
    "en": "英文",
    "fr": "法文",
    "de": "德文",
    "ja": "日文",
    "ko": "韩文",
    "ru": "俄文",
    "es": "西班牙文",
    "it": "意大利文"
}

class DeepSeekTranslator:
    def __init__(self):
        self.client = OpenAI(api_key=config.deepseek_key_default,
                             base_url="https://api.deepseek.com")
        self.lock = threading.Lock()
        self.last_request_time = 0
        self.min_interval = 0.5  # 防止触发QPS限制

    def wait_for_rate_limit(self):
        """限制请求速率，避免触发API限流"""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self.last_request_time = time.time()

    def translate(self, text, language_to, language_from, max_retries=3):
        """同步调用 DeepSeek API 翻译"""
        language = lang_map.get(language_to, language_to)

        prompt = (
            f"请将以下内容翻译为{language}，使用正式且学术的表达方式。"
            f"仅返回翻译后的文本，不要包含解释或其他信息：\n\n{text}"
        )

        for attempt in range(max_retries):
            try:
                self.wait_for_rate_limit()

                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant"},
                        {"role": "user", "content": prompt},
                    ]
                )
                return response.choices[0].message.content.strip()

            except Exception as e:
                print(f"[Retry {attempt+1}] Exception occurred during translation: {e}")
                time.sleep(1)

        return "[Translation failed]"