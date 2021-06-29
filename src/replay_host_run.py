# -*- coding: utf-8 -*-
import pandas as pd

from src.replay_post import ReplayPost
from src.file_parse import FileParse
from src.replay_prepare import ReplayPrepare
from src.replay_run import ReplayRun


class ReplayOneHost:
    def __init__(self, gor_path: str, host: str, speed: float = 1, timeout: int = 5, rules=None, *args, **kwargs):
        if rules is None:
            rules = {}
        self.gor_path = gor_path
        self.host = host
        self.speed = speed
        self.timeout = timeout
        self.rules = rules
        self._df = pd.DataFrame()

        self.file_parse = None
        self.replay_prepare = None
        self.replay_run = None
        self.replay_post = None

    @property
    def df(self):
        return self._df

    def _run(self):
        # 初始化
        self.file_parse = FileParse(self.gor_path)
        self._df = self.file_parse.parse_type1()
        self.replay_prepare = ReplayPrepare(self._df)
        self.replay_run = ReplayRun(self._df)
        self.replay_post = ReplayPost(self._df)

        # 执行流程
        self.replay_prepare.execute_rules(**self.rules)
        self.replay_prepare.process_timestamp(self.speed)
        self.replay_run.send_requests(host=self.host, timeout=self.timeout)
        self.replay_post.process_response()

    @classmethod
    def run(cls, **kwargs):
        instance = cls(**kwargs)
        instance._run()
        return instance


if __name__ == '__main__':
    path = r'e:/temp/test7.gor'
    ins = ReplayOneHost(path, 'api2.che300.com', 0.5, )
    ins._run()
