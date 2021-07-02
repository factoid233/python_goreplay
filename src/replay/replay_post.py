# -*- coding: utf-8 -*-
import logging
import urllib.parse

import httpx
import pandas as pd

logger = logging.getLogger(__name__)


class ReplayPost:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def process_response(self):
        """
        后处理一些reponse信息
        @return:
        """
        self.df['http_code'] = self.df['response_obj'].map(
            lambda x: x.status_code if isinstance(x, httpx.Response) and x else "null")
        self.df['elapsed_time'] = self.df['response_obj'].map(
            lambda x: x.elapsed.total_seconds() if isinstance(x, httpx.Response) and x else 0)
        self.df['response'] = self.df['response_obj'].map(
            lambda x: x.text if isinstance(x, httpx.Response) and x else x)

        self.df['get_params'] = self.df['get_params'].map(urllib.parse.urlencode)
        self.df.drop(columns=['response_obj'], inplace=True)
        logger.info(f'共发送请求 {self.df.shape[0]} 个')
