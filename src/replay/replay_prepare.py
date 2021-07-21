# -*- coding: utf-8 -*-
import logging
import re

import pandas as pd
from src.replay.rules import FilterRules

logger = logging.getLogger(__name__)


class ReplayPrepare:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.process_other()

    def execute_rules(self, **kwargs):
        filter_rules = FilterRules(self.df)
        prefix = 'rule_'
        rule_keys = list(map(lambda x: x.replace(prefix, ''), filter(lambda x: prefix in x, filter_rules.__dir__())))
        for key, value in kwargs.items():
            if key in rule_keys:
                getattr(filter_rules, f'{prefix}{key}')(value)

    def process_timestamp(self, speed):
        """
        处理时间戳，实现请求倍速
        @param speed:   2：2倍速回放    0.5：0.5倍速回放
        @return:
        """
        # 将时间戳转换为数字
        self.df['timestamp'] = pd.to_numeric(self.df['timestamp'])
        # 将时间戳转换为datetime 对象
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        # 时间戳从小到大排序
        self.df.sort_values(by=['timestamp'], inplace=True)
        # 计算 sleep的秒数
        self.df['sleep'] = (self.df['timestamp'] - self.df['timestamp'].min()).map(lambda x: x.total_seconds())
        # 实现倍速
        self.df['sleep'] = self.df['sleep'] / speed
        logger.info(f"共需运行{self.df['sleep'].max() / 60} 分钟")

    def process_slice(self, _slice):
        """对原始读取的df数据进行切片"""
        mather = re.match(r'^(?:(\d+),)?(\d+)$', _slice)
        if mather is not None:
            start = mather.group(1)
            start = int(start) if start is not None else None
            end = int(mather.group(2))
            need_index = self.df.loc[start:end, ].index
            drop_indexs = set(self.df.index) - set(need_index)
            self.df.drop(index=drop_indexs, inplace=True)
        logger.info(f'共收集请求 {self.df.shape[0]} 个')

    def process_other(self):
        """
        处理headers中的Content-Length长度问题
        :return:
        """

        def func_header(line: dict):
            if isinstance(line, dict):
                for key, value in line.copy().items():
                    if key in ('content-length', 'Content-Length'):
                        line.pop(key)
            return line

        self.df['headers'] = self.df['headers'].map(func_header)


if __name__ == '__main__':
    from src.common import get_root_path
    from src.replay.file_parse import FileParse
    import os

    path = os.path.join(get_root_path(), 'src', '../example', 'test.gor')
    file_parse = FileParse(path)
    df = file_parse.parse_type1()
    replay_before = FilterRules(df)
