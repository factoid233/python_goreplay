# -*- coding: utf-8 -*-
"""
主流程文件
"""
from multiprocessing import Manager, Process

import pandas as pd
from src.replay.file_parse import FileParse
from src.replay.replay_post import ReplayPost
from src.replay.replay_prepare import ReplayPrepare
from src.replay.replay_run import ReplayRun
from src.replay.replay_compare import ReplayCompare
from src.replay.store import Storage


class ReplayRunType:
    df = None
    res_host = dict(host1=None, host2=None)

    @staticmethod
    def check_df_is_empty(df: pd.DataFrame, err_msg: str):
        if df.empty:
            raise RuntimeError(err_msg)

    def replay_main(self, *args, **kwargs):
        pass


class ReplayRunTypeOne(ReplayRunType):
    """
    回放结果和录制的请求响应做比较
    """

    def replay_main(self, gor_path, host1: str, speed: float = 1, timeout=5, rules_filter=None,
                    rules_compare: dict = None, _slice=None, *args, **kwargs):
        if rules_filter is None:
            rules_filter = {}
        # 解析请求数据
        file_parse = FileParse(gor_path)
        df1 = file_parse.parse_type1()
        self.check_df_is_empty(df1, '解析请求数据 类型1 为空')
        self.res_host['host1'] = df1

        # 解析原始响应数据
        df2 = file_parse.parse_type2()
        self.check_df_is_empty(df2, '解析响应数据 类型2 为空')
        self.res_host['host2'] = df2

        # 回放请求前处理
        replay_prepare = ReplayPrepare(df1)
        replay_prepare.process_slice(_slice)
        replay_prepare.execute_rules(**rules_filter)
        replay_prepare.process_timestamp(speed)
        self.df = replay_prepare.df

        # 回放发送请求
        replay_run = ReplayRun(self.df)
        replay_run.send_requests(host=host1, timeout=timeout)
        self.df = replay_run.df

        # 回放后处理数据
        replay_post = ReplayPost(self.df)
        replay_post.process_response()
        self.df = replay_post.df

        # 比较数据
        res_compare = ReplayCompare(self.res_host)
        res_compare.compare_data(rules_compare)
        self.df = res_compare.df

        # 存储数据
        Storage(self.df).store()


class ReplayRunTypeTwo(ReplayRunType):

    def replay_one_host(self, gor_path, host1: str, speed: float = 1, timeout=5, rules_filter: dict = None,
                        _slice=None):
        df = None
        if rules_filter is None:
            rules_filter = {}
        # 解析请求数据
        file_parse = FileParse(gor_path)
        df1 = file_parse.parse_type1()
        self.check_df_is_empty(df1, '解析请求数据 类型1 为空')

        # 回放请求前处理
        replay_prepare = ReplayPrepare(df1)
        replay_prepare.process_slice(_slice)
        replay_prepare.execute_rules(**rules_filter)
        replay_prepare.process_timestamp(speed)
        df = replay_prepare.df

        # 回放发送请求
        replay_run = ReplayRun(df)
        replay_run.send_requests(host=host1, timeout=timeout)
        df = replay_run.df

        # 回放后处理数据
        replay_post = ReplayPost(df)
        replay_post.process_response()
        df = replay_post.df
        return df

    def one_process(self, gor_path, host: str, speed: float = 1, timeout=5, rules_filter=None, _slice=None, share=None,
                    share_name=None):
        df = self.replay_one_host(gor_path, host, speed, timeout, rules_filter, _slice)
        share[share_name] = df

    def replay_two_host_with_many_process(self, gor_path, host1: str, host2: str, speed: float = 1, timeout=5,
                                          rules_filter=None, _slice=None):
        # 回放请求
        with Manager() as manager:
            d = manager.dict()
            d['host1'] = None
            d['host2'] = None
            t1 = Process(target=self.one_process,
                         args=(gor_path, host1, speed, timeout, rules_filter, _slice, d, 'host1'))
            t2 = Process(target=self.one_process,
                         args=(gor_path, host2, speed, timeout, rules_filter, _slice, d, 'host2'))
            jobs = (t1, t2)
            for t in jobs:
                t.start()
            for t in jobs:
                t.join()
            for t in jobs:
                if t.exitcode != 0:
                    raise RuntimeError('多进程执行异常')
            # self.res_host = dict(map(lambda arg: (arg[0], pd.read_json(arg[1])), d.items()))
            self.res_host = dict(d.items())

    def replay_main(self, gor_path, host1: str, host2: str, speed: float = 1, timeout=5, rules_filter=None,
                    rules_compare: dict = None, _slice: str = None, *args, **kwargs):
        self.replay_two_host_with_many_process(gor_path, host1, host2, speed, timeout, rules_filter, _slice)
        # 比较结果
        res_compare = ReplayCompare(self.res_host)
        res_compare.compare_data(rules_compare)
        self.df = res_compare.df

        # 存储数据
        Storage(self.df).store()


class ReplayRunTypeNoCompare(ReplayRunType):
    def replay_main(self, gor_path, host1: str, speed: float = 1, timeout=5, rules_filter=None, *args, **kwargs):
        if rules_filter is None:
            rules_filter = {}
        # 解析请求数据
        file_parse = FileParse(gor_path)
        df1 = file_parse.parse_type1()
        self.check_df_is_empty(df1, '解析请求数据 类型1 为空')
        self.res_host['host1'] = df1

        # 回放请求前处理
        replay_prepare = ReplayPrepare(df1)
        replay_prepare.execute_rules(**rules_filter)
        replay_prepare.process_timestamp(speed)
        self.df = replay_prepare.df

        # 回放发送请求
        replay_run = ReplayRun(self.df)
        replay_run.send_requests(host=host1, timeout=timeout)
        self.df = replay_run.df

        # 回放后处理数据
        replay_post = ReplayPost(self.df)
        replay_post.process_response()
        self.df = replay_post.df

        # 存储数据
        Storage(self.df).store()


if __name__ == '__main__':
    from src.common.util import get_root_path
    import os

    # from src import logger_config
    # logger_config()
    # logging.basicConfig(level=logging.INFO)
    # path = os.path.join(get_root_path(), 'src', 'example', 'test.gor')
    path = 'E:\dingding\gor0902.log'
    ins = ReplayRunTypeOne()
    # ins.replay_main(path, '118.190.43.227:5014', speed=10)
    # ins2 = ReplayRunTypeTwo()
    ins.replay_main(path, host1='api.ceshi.che300.com', speed=4, rules_filter={
        "filter_needed_uri": ["/service/getUsedCarPrice"],"replace_dict":{"token":"123"}}, timeout=30, _slice='100')
    # ins3 = ReplayRunTypeNoCompare()
    # ins3.replay_main(path, host1='118.190.43.227:5014', speed=10)
