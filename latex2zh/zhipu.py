import time
import threading
from zhipuai import ZhipuAI
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


class ZhipuTranslator:
    def __init__(self):
        self.client = ZhipuAI(api_key=config.zhipu_key_default)
        self.lock = threading.Lock()
        self.last_request_time = 0
        self.min_interval = 0.01

    def wait_for_rate_limit(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self.last_request_time = time.time()

    def translate(self, text, language_to, language_from, max_retries=3):
        language = lang_map[language_to]

        prompt = (
            f"请将以下内容翻译为{language}，使用正式且学术的表达方式。仅返回翻译后的文本，不要包含解释或其他信息：\n\n{text}"
        )

        for attempt in range(max_retries):
            try:
                self.wait_for_rate_limit()

                response = self.client.chat.asyncCompletions.create(
                    model="glm-4-flash-250414",
                    messages=[{"role": "user", "content": prompt}],
                )

                task_id = response.id

                for _ in range(40):
                    result = self.client.chat.asyncCompletions.retrieve_completion_result(id=task_id)
                    if result.task_status == 'SUCCESS':
                        return result.choices[0].message.content.strip()
                    elif result.task_status == 'FAILED':
                        raise RuntimeError("ZhipuAI Translation task failed!")
                    time.sleep(2)

                raise TimeoutError("ZhipuAI Translation task timeout")

            except Exception as e:
                print(f"[Retry {attempt+1}] Exception: {e}")
                time.sleep(1)

        return "[Translation failed]"

