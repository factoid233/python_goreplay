# -*- coding: utf-8 -*-
import pandas as pd
import logging
from src.replay.replay_post import ReplayPost
from src.replay.file_parse import FileParse
from src.replay.replay_prepare import ReplayPrepare
from src.replay.replay_run import ReplayRun

logger = logging.getLogger(__name__)


class ReplayOneHost:
    """
    请求前准备工作
    批量发送请求
    请求完后处理
    """
    def __init__(self, df:pd.DataFrame, gor_path: str, host: str, speed: float = 1, timeout: int = 5, rules=None, *args, **kwargs):
        if rules is None:
            rules = {}
        self.gor_path = gor_path
        self.host = host
        self.speed = speed
        self.timeout = timeout
        self.rules = rules
        self._df = df

        self.file_parse = None
        self.replay_prepare = None
        self.replay_run = None
        self.replay_post = None

    @property
    def df(self):
        return self._df

    def run(self):
        # 初始化
        # self.file_parse = FileParse(self.gor_path)
        # self._df = self.file_parse.parse_type1()
        self.replay_prepare = ReplayPrepare(self._df)
        self.replay_run = ReplayRun(self._df)
        self.replay_post = ReplayPost(self._df)

        # 执行流程
        self.replay_prepare.execute_rules(**self.rules)
        self.replay_prepare.process_timestamp(self.speed)
        self.replay_run.send_requests(host=self.host, timeout=self.timeout)
        self.replay_post.process_response()



