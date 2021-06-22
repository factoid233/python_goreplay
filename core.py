# -*- coding: utf-8 -*-
import argparse
import datetime
import json
import logging.config
import os
import re
import sys
import urllib.parse
import uuid
from multiprocessing import Process, Manager
from typing import Tuple
from urllib import parse

import attr
import httpx
import numpy as np
import pandas as pd
import trio
from jsoncomparison import Compare as JsonCompare

from util.util import get_root_path, read_yaml, is_json_equal, java_token

log_config_path = os.path.join(get_root_path(), 'log_config.yaml')
logging.config.dictConfig(read_yaml(log_config_path))
logger = logging.getLogger(__name__)


class FileParse:
    """
    解析录制的流量的文件成Dataframe
    """
    br = "🐵🙈🙉\n"
    section_set_pass = {'\n', ''}

    def __init__(self, path):
        self.path = path

    def parse_type1(self):
        """
        解析原始请求数据
        :return:
        """
        df = self._parse_main(path=self.path, _type='1')
        if df.empty:
            logger.warning(f'解析文件{self.path} 为空,退出程序')
            exit(-1)
        return df

    def parse_type2(self):
        """
        解析原始响应数据
        :return:
        """
        df = self._parse_main(path=self.path, _type='2')
        df['host'] = 'server'
        df['remark'] = ''
        if df.empty:
            logger.warning(f'解析文件{self.path} 为空,退出程序')
            exit(-1)
        return df

    def _parse_main(self, path: str, _type: str) -> pd.DataFrame:
        """
        循环按行读取gor文件，支持超大文件读取
        格式化提取信息
        @param path:
        @return:
        """
        data = list()
        # 读取文件
        with open(path, 'r', encoding='utf-8', errors="ignore") as f:
            section = ""
            for line in f:
                section += line
                if line == self.br:
                    res = self._proc_section(section, _type)
                    if res is not None:
                        data.append(res)
                    # 重置section
                    section = ""
            res = self._proc_section(section, _type)
            if res is not None:
                data.append(res)
        # 将数据存储为dataframe格式 方便处理
        df = pd.DataFrame(data)
        return df

    def _proc_section(self, section, _type):
        if _type == '1':
            return self._proc_section1(section)
        elif _type == '2':
            return self._proc_section2(section)

    def _proc_section1(self, section):
        if section and section[0] == '1':
            post_data = id1 = timestamp = None
            section = section.strip(self.br)

            # 将post data 与 其他内容分割
            body: list = re.split('\r?\n\r?\n', section)
            if len(body) == 2:
                post_data = body[1]
                try:
                    post_data = json.loads(post_data)
                except json.JSONDecodeError:
                    return
            body1 = body[0]
            # 按行分割 第一行提取请求id 时间戳 时间戳精确度为纳秒
            body2: list = re.split('\r?\n', body1)
            line1: list = re.split(r'\s', body2[0])
            # 无请求id 直接跳过
            if not (len(line1) >= 3 and line1[0] == '1'):
                return
            _, id1, timestamp, *_ = line1

            # 第二行 提取提取请求方式、请求url、请求协议
            # 无第二行数据直接跳过
            if len(body2) < 2:
                return None
            line2: list = re.split(r'\s', body2[1])
            # 无请求方式和请求内容直接跳过
            if not (len(line2) == 3):
                return None
            request_method, url, http_version = line2
            # URL解析
            url_parse_result = parse.urlparse(url)
            uri = url_parse_result.path
            get_query = url_parse_result.query
            get_params = parse.parse_qsl(get_query)
            get_params = dict(get_params)

            # 剩余 headers 提取
            headers = dict()
            for item in body2[2:]:
                item2 = [item1.strip() for item1 in item.split(':')]
                if len(item2) == 2:
                    headers[item2[0]] = item2[1]
            res_dict = dict(id1=id1, timestamp=timestamp, request_method=request_method, uri=uri,
                            get_params=get_params, post_data=post_data, headers=headers, http_version=http_version)
            return res_dict
        elif section and section[0] in ('2', '3',) or section in self.section_set_pass:
            return None
        else:
            logger.warning(f'goreplay 文件有误,type 1读取错误,error detail:\n{section}')
            return None

    def _proc_section2(self, section):
        if section and section[0] == '2':
            response = id1 = timestamp = None
            section = section.strip(self.br)

            # 将响应结果 与 其他内容分割
            body: list = re.split('\r?\n\r?\n', section)
            if len(body) == 2:
                response: str = body[1]
                # 处理异常的response,意外多出两行
                if '\n' in response:
                    response_split = response.split('\n')
                    if len(response_split) > 2:
                        response = response.split('\n')[1]
            # body1 为除响应结果外的所有信息
            body1_text = body[0]
            # 按行分割 第一行提取请求id 时间戳 时间戳精确度为纳秒
            body1: list = re.split('\r?\n', body1_text)
            line1: list = re.split(r'\s', body1[0])
            # 无请求id 直接跳过
            if not len(line1) >= 3:
                return None
            _type, id1, timestamp, *_ = line1

            # 第二行 提取 请求协议 和响应code码
            # 无第二行直接跳过
            if len(body1) < 2:
                return None
            line2: list = re.split(r'\s', body1[1])
            # 无请求方式和请求内容直接跳过
            http_version, http_code, *_ = line2
            # response header解析
            response_headers = dict()
            for item in body1[2:]:
                item2 = [item1.strip() for item1 in re.split(r':\s', item)]
                if len(item2) == 2:
                    response_headers[item2[0]] = item2[1]
            res_dict = dict(id1=id1, timestamp=timestamp, http_code=http_code, response=response,
                            http_version=http_version, response_headers=response_headers)
            return res_dict
        elif section and section[0] in ('1', '3') or section in self.section_set_pass:
            return None
        else:
            logger.warning(f'goreplay 文件有误,type 2读取错误，error detail:\n{section}')
            return None


class ReplayPrepare:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.process_other()
        logger.info(f'共收集请求 {self.df.shape[0]} 个')

    def execute_rules(self, **kwargs):
        rule_keys = ('replace_dict', 'delete_uri', 'filter_needed_uri')
        for key, value in kwargs.items():
            if key in rule_keys:
                getattr(self, f'rule_{key}')(value)

    def rule_replace_dict(self, args: dict = None):
        """
        根据请求参数中key,替换key对应的value值
        get参数和post参数均替换
        :return:
        """
        if args is not None and isinstance(args, dict):

            def func(line):
                for key, value in args.items():
                    if isinstance(line, dict) and key in line:
                        line[key] = value
                return line

            def func_header(line: dict):
                if isinstance(line, dict):
                    for key, value in line.copy().items():
                        if key in ('content-length', 'Content-Length'):
                            line.pop(key)
                return line

            # 根据所给参数 替换get 或者post请求中的 key value
            self.df['get_params'] = self.df['get_params'].map(func)
            self.df['post_data'] = self.df['post_data'].map(func)
            # 取出请求header中的长度字段 会报错
            self.df['headers'] = self.df['headers'].map(func_header)

    def rule_delete_uri(self, args: list = None):
        if args is not None and isinstance(args, list):
            delete_indexs = self.df[self.df.apply(lambda x: True if x['uri'] in args else False, axis=1)].index
            self.df.drop(index=delete_indexs, inplace=True)

    def rule_filter_needed_uri(self, args: list = None):
        if args is not None and isinstance(args, list):
            delete_index = self.df[self.df.apply(lambda x: True if x['uri'] not in args else False, axis=1)].index
            self.df.drop(index=delete_index, inplace=True)

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


class ReplayRun:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    async def _send_request_one(self, client: httpx.AsyncClient, host, index, line: pd.Series, total: int):
        """
        协程发送单个请求
        @param client:
        @param host:
        @param index:
        @param line:
        @return:
        """
        # self.logger.debug(line['sleep'])
        # 阻塞相应的时间，使请求按照原始时间线发送请求
        await trio.sleep(line['sleep'])

        http_version = line['http_version'].split('/')[0].lower()
        url = http_version + '://' + host + line['uri']

        current = datetime.datetime.now().isoformat()
        response = "null"
        remark = ""
        try:
            if line['request_method'] == 'GET':
                response = await client.get(url=url, params=line['get_params'], headers=line['headers'])
            elif line['request_method'] == 'POST':
                response = await client.post(url=url, params=line['get_params'], json=line['post_data'],
                                             headers=line['headers'])
            response.raise_for_status()
            logger.debug(f"|-- {url}\n\t{response.text}")
        except httpx.TimeoutException as exc:
            remark = "{}".format(client.timeout)
        except httpx.HTTPStatusError as exc:
            response = exc.response
            remark = f"Error response {exc.response.status_code} while requesting {exc.request.url!r}."
        except httpx.HTTPError as exc:
            remark = sys.exc_info()[0].__doc__.strip()
        finally:
            if remark:
                logger.error(remark)

        # 添加请求信息
        self.df.loc[index, 'host'] = host
        self.df.loc[index, 'created_time'] = current
        self.df.loc[index, 'response_obj'] = response
        self.df.loc[index, 'remark'] = remark

    async def _send_requests(self, host: str, timeout: int):
        """
        协程并发发送请求
        @param host:
        @param timeout:
        @return:
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with trio.open_nursery() as nursery:
                for index, line in self.df.iterrows():
                    nursery.start_soon(self._send_request_one, client, host, index, line, self.df.shape[0])

    def send_requests(self, host: str, timeout: int):
        trio.run(self._send_requests, host, timeout)
        logger.info('replay_run success')


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
        # self.df['payload'] = self.df.apply(axis=1,
        #                                    func=lambda x: x['get_params'] if x['request_method'] == 'GET'
        #                                    else x['post_data'])
        logger.info(f'共发送请求 {self.df.shape[0]} 个')


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


class ReplayCompare:
    def __init__(self, res_host: list):
        self.res_host = res_host

    def str_to_json(self, _str):
        try:
            _obj = json.loads(_str)
        except Exception:
            _obj = _str
        return _obj

    def _is_pass(self, resp1, resp2, compare_rules: dict = None):
        """
        比较单个响应结果是否一致
        @param resp1:
        @param resp2:
        @param compare_rules:
        @return:
        """
        resp1 = self.str_to_json(resp1)
        resp2 = self.str_to_json(resp2)
        if 'compare_all_equal' in compare_rules.keys():
            is_pass = self._compare_all_equal(resp1, resp2, ignores=compare_rules.get('compare_all_equal'))
            return is_pass
        if 'compare_jsonpath' in compare_rules.keys():
            return
        else:
            is_pass = self._compare_all_equal(resp1, resp2, ignores=None)
            return is_pass

    def _compare_all_equal(self, resp1, resp2, ignores: list = None):
        """
        比较单个响应结果是否一致
        {"compare_all_equal":{"ignore":""}}
        @param resp1:
        @param resp2:
        @return:
        """
        if ignores is None:
            ignores = []
        is_pass = is_json_equal(resp1, resp2, ignores=ignores)

        if isinstance(resp1, str) or isinstance(resp2, str):
            is_pass = False
        elif not (resp1 and resp2):
            is_pass = False
        elif "null" in resp1 or "null" in resp2:
            is_pass = False
        return is_pass

    def _compare_jsonpath(self, resp1, resp2, args: dict):
        """

        :param resp1:
        :param resp2:
        :param args:{"/cs/vhis/accident/query":}
        :return:
        """

    def _compare_data(self, compare_rules=None) -> pd.DataFrame:
        """
        比较两台服务器的响应结果
        @return:
        """
        host1: Tuple[str, pd.DataFrame] = self.res_host[0]
        host2: Tuple[str, pd.DataFrame] = self.res_host[1]
        df1: pd.DataFrame = host1[1]
        df2: pd.DataFrame = host2[1]
        # 取两个request_id的并集
        df1.set_index('id1', inplace=True)
        df2.set_index('id1', inplace=True)
        id1s = set(df1.index) | set(df2.index)
        df = pd.DataFrame(columns=df1.columns)
        for id1 in id1s:
            if id1 in df1.index and id1 in df2.index:
                df.at[id1,
                      ['request_method', 'uri', 'get_params', 'post_data', 'headers', 'created_time', 'remark']] \
                    = df1.loc[id1,
                              ['request_method', 'uri', 'get_params', 'post_data', 'headers', 'created_time', 'remark']]
                # 合并两个相同的字段为一个
                for item in ('host', 'http_code', 'response', 'elapsed_time', 'remark'):
                    if item == "response":
                        # 将response合并成二元列表
                        df.at[id1, item] = [self.str_to_json(df1.loc[id1, item]), self.str_to_json(df2.loc[id1, item])]
                    else:
                        _map_list = [i for i in (df1.loc[id1, item], df2.loc[id1, item]) if i]
                        df.at[id1, item] = "|".join(map(str, _map_list))

                is_pass = self._is_pass(df1.loc[id1, 'response'], df2.loc[id1, 'response'], compare_rules=compare_rules)
                df.loc[id1, 'is_pass'] = "pass" if is_pass else "fail"
        logger.info('比较 done. ')
        return df

    @classmethod
    def compare_data(cls, res_host, compare_rules=None) -> pd.DataFrame:
        return cls(res_host)._compare_data(compare_rules)


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NpEncoder, self).default(obj)


@attr.s
class Storage:
    df = attr.ib(type=pd.DataFrame)

    def _generate_file_name(self):
        return datetime.datetime.now().strftime('Replay%Y%m%d%H%M%S')

    @classmethod
    def generate_compare_json(cls, x: list):
        """
        将两个对比json,合成一个美化输出
        {
        "project": {
            "version": {
                "_message": "Types not equal. Expected: <str>, received: <float>",
                "_expected": "str",
                "_received": "float"
            },
            "license": {
                "_message": "Values not equal. Expected: <MIT>, received: <Apache 2.0>",
                "_expected": "MIT",
                "_received": "Apache 2.0"
            },
            "language": {
                "versions": {
                    "_length": {
                        "_message": "Lengths not equal. Expected <2>, received: <1>",
                        "_expected": 2,
                        "_received": 1
                    },
                    "_content": {
                        "0": {
                            "_message": "Value not found. Expected <3.5>",
                            "_expected": 3.5,
                            "_received": null
                        }
                    }
                }
            }
        },
        "os": {
            "_message": "Key does not exists. Expected: <os>",
            "_expected": "os",
            "_received": null
        }
        }
        :param x:
        :return:
        """
        expected, actual = x
        diff = JsonCompare().check(expected, actual)
        return json.dumps(diff, ensure_ascii=False)

    @classmethod
    def response_handle(cls, x: list):
        """
        美化reponseexcel显示
        :param x:
        :return:
        """
        x1, x2 = x
        x1 = json.dumps(x1, ensure_ascii=False, cls=NpEncoder)
        x2 = json.dumps(x2, ensure_ascii=False, cls=NpEncoder)
        return f"{x1}\n\n{'=' * 50}\n\n{x2}"

    def _flush_to_csv(self):
        """
        写入到csv
        @return:
        """
        df: pd.DataFrame = self.df.loc[lambda x: x['is_pass'] == 'fail']
        df = df.sort_values('uri')

        df['response_compare_json'] = df['response'].map(self.generate_compare_json)
        df['response'] = df['response'].map(self.response_handle)
        # 选择部分字段存储
        df = df[
            ['uri', 'is_pass', 'request_method', 'host', 'get_params', 'post_data', 'http_code', 'response',
             'response_compare_json', 'elapsed_time', 'remark', 'created_time']].copy()
        # 重置索引
        df.reset_index(inplace=True)
        file_dir = os.path.join(get_root_path(), 'output')
        file_name = '{}.csv'.format(self._generate_file_name())
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        file_path = os.path.join(file_dir, file_name)
        if not df.empty:
            # 遇到乱码替换成 ？？
            logger.info('开始写入...')
            df.to_csv(file_path, index=True, encoding='gbk', errors='replace', mode='a',
                      chunksize=10000)
            logger.info(f'生成结果文件{file_path}')
        else:
            logger.info('无结果文件生成，无失败')

    @classmethod
    def flush_to_csv(cls, df):
        cls(df)._flush_to_csv()


class ReplayMain:
    res_host = []
    result_compare_df = None

    @classmethod
    def replay_main(cls):
        ins = cls()
        kwargs = ins._load_args_config(args=None)
        ins.replay_run(**kwargs)

    def replay_run(self, gor_path, host1: str, rules: dict, speed: float = 1, timeout=5, host2: str = None):
        """

        :param gor_path:
        :param host1:
        :param rules: {'replace_dict':'替换请求参数', 'delete_uri':'过滤url','ignore':'比较时忽略相关字段'}
        :param speed:
        :param timeout:
        :param host2:
        :return:
        """
        if host2 is None:
            self.replay_one_host(gor_path, host1, rules, speed, timeout)
        else:
            self.replay_two_host(gor_path, host1, host2, rules, speed, timeout)

    def replay_two_host(self, gor_path, host1: str, host2: str, rules: dict, speed: float = 1, timeout=5):
        self._run_replay(gor_path=gor_path, hosts=[host1, host2], rules=rules, speed=speed, timeout=timeout)
        self._replay_common(rules)

    def replay_one_host(self, gor_path, host1: str, rules: dict, speed: float = 1, timeout=5):
        self._run_replay(gor_path=gor_path, hosts=[host1], rules=rules, speed=speed, timeout=timeout)
        if len(self.res_host) == 0:
            exit(-1)
        self.res_host.append((self.generate_batch(), FileParse(gor_path).parse_type2()))
        self._replay_common(rules)

    def _replay_common(self, rules):
        self.result_compare_df = ReplayCompare.compare_data(self.res_host, compare_rules=rules)
        Storage.flush_to_csv(self.result_compare_df)

    def generate_batch(self):
        batch = uuid.uuid1().hex
        return batch

    def _load_args_config(self, args):
        return vars(self._get_args(args))

    def _get_args(self, args):
        parser = argparse.ArgumentParser(
            description='python goreplay'
        )
        parser.add_argument(
            '-p', '--path',
            action='store',
            dest='gor_path',
            required=True,
            metavar='/mnt/d/Projects/Python/api_test/src/cases/goreplay_replay/20201224.log',
            help='goreplay 流量回放的绝对路径'
        )
        parser.add_argument(
            '-h1', '--host1',
            action='store',
            dest='host1',
            required=True,
            metavar='127.0.0.1:8080',
            help='流量回放的ip地址带端口号'
        )
        parser.add_argument(
            '-h2', '--host2',
            action='store',
            dest='host2',
            default=None,
            metavar='127.0.0.1:8080',
            help='流量回放的ip地址带端口号'
        )
        parser.add_argument(
            '-r', '--rules',
            action='store',
            type=json.loads,
            default={},
            dest='rules',
            help="""{"replace_dict":{"替换请求参数":""}, "delete_uri":["过滤url"],"ignore":["比较时忽略相关字段key"]}"""
        )
        parser.add_argument(
            '-v', '--speed',
            action='store',
            type=float,
            dest='speed',
            default=1,
            metavar='2.5',
            help='回放倍速'
        )
        parser.add_argument(
            '-t', '--timeout',
            action='store',
            dest='timeout',
            default=5,
            help='超时时间 秒',
            metavar='5'
        )
        # args - 要解析的字符串列表。 默认情况下None是从 sys.argv 获取。
        res = parser.parse_args(args)
        return res

    def _run_replay_thread(self, **kwargs):
        """
        单个线程回放
        @param gor_file_path:
        @param host:
        @param replace_args:
        @param speed:
        @param timout:
        @return:
        """
        res = ReplayOneHost.run(**kwargs)
        kwargs['share'][self.generate_batch()] = res.df.to_json()

    def _run_replay(self, **kwargs):
        """
        回放多台服务器
        一台服务器一个进程
        """
        ts = []
        with Manager() as manager:
            d = manager.dict()
            for host in kwargs.pop('hosts'):
                kwargs1 = kwargs.copy()
                kwargs1['host'] = host
                kwargs1['share'] = d
                t = Process(target=self._run_replay_thread,
                            kwargs=kwargs1)
                t.start()
                ts.append(t)
            for t in ts:
                t.join()
            for key, value in d.items():
                self.res_host.append((key, pd.read_json(value)))


if __name__ == '__main__':
    # ReplayMain.replay_main()
    path = r'E:\dingding\pubtest_web.log'
    # path = r'/home/yxgao/Downloads/vin_request_20210428_small.log'
    rules1 = {"filter_needed_uri":
                  ["/cs/vhis/accident/query", "/cs/vhis/accident/analysis", "/cs/vhis/eval",
                   "/cs/vhis/analysis", "/cs/vhis/condition/query"]}
    rules2 = {'replace_dict': {"user": "test",
                               "channel": "test",
                               "client_user": "test",
                               "client_channel": "test",
                               "token": java_token()}}
    ReplayMain().replay_run(gor_path=path, host1='172.16.2.2:9455', rules={},
                            speed=3)
    # x1 = FileParse(path)
    # x1.parse_type1()
    # ReplayOneHost.run(gor_path=path,
    #                   host='118.190.235.150:5027',
    #                   compare_rules={
    #                       'replace_dict': {
    #                           "user": "test",
    #                           "channel": "test",
    #                           "client_user": "test",
    #                           "client_channel": "test",
    #                           "token": java_token()
    #                       },
    #                       'filter_needed_uri': ["/cs/vhis/accident/query", "/cs/vhis/accident/analysis",
    #                                             "/cs/vhis/eval", "/cs/vhis/analysis", "/cs/vhis/condition/query"]
    #                   },
    #                   )
    # x1 = ReplayMain()
    # x1.replay_one_host(gor_path=path,
    #                    host1='118.190.235.150:5024',
    #                    compare_rules={
    #                        'replace_dict': {
    #                            "user": "test",
    #                            "channel": "test",
    #                            "client_user": "test",
    #                            "client_channel": "test",
    #                            "token": java_token()
    #                        },
    #                        'delete_uri': ['/actuator/prometheus']
    #                    }, )
