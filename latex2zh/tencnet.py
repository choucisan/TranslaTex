from .tencentcloud.common import credential, exception
from .tencentcloud.tmt.v20180321 import tmt_client
from .config import config
import time
import threading

class TencentTranslator:
    def __init__(self):
        self.cred = credential.Credential(config.tencent_secret_id, config.tencent_secret_key)
        self.client = tmt_client.TmtClient(self.cred, 'ap-shanghai')
        self.lock = threading.Lock()
        self.last_request_time = 0
        self.min_interval = 0.25

    def is_error_request_frequency(self, e: exception.TencentCloudSDKException):
        code = e.get_code()
        return code == 'RequestLimitExceeded'

    def wait_for_rate_limit(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self.last_request_time = time.time()

    def translate(self, text, language_to, language_from, max_retries=3):
        for attempt in range(max_retries):
            try:
                self.wait_for_rate_limit()
                request = tmt_client.models.TextTranslateRequest()
                request.Source = language_from
                request.Target = language_to
                request.SourceText = text
                request.ProjectId = 0
                request.UntranslatedText = config.math_code
                result = self.client.TextTranslate(request)
                return result.TargetText
            except exception.TencentCloudSDKException as e:
                if self.is_error_request_frequency(e):

                    time.sleep(1)
                else:
                    raise e
        raise RuntimeError()