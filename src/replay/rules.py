# -*- coding: utf-8 -*-
from typing import Union
from jsoncomparison import Compare as JsonCompare, NO_DIFF


class FilterRules:
    """
    用于筛选过滤请求前收集的数据
    df中含有的key有：
        ['id1', 'timestamp', 'request_method', 'uri', 'get_params', 'post_data', 'headers', 'http_version']

    ！！！注意！！！
    ==============
    self._df 的操作只能在原始对象上进行删除或者修改，不能新建一个df对象给self._df
    例如： self._df = self._df.apply(func)
    ==============
    """

    def __init__(self, df):
        self._df = df

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
            self._df['get_params'] = self._df['get_params'].map(func)
            self._df['post_data'] = self._df['post_data'].map(func)
            # 取出请求header中的长度字段 会报错
            self._df['headers'] = self._df['headers'].map(func_header)

    def rule_delete_uri(self, args: list = None):
        if args is not None and isinstance(args, list):
            delete_indexs = self._df[self._df.apply(lambda x: True if x['uri'] in args else False, axis=1)].index
            self._df.drop(index=delete_indexs, inplace=True)

    def rule_filter_needed_uri(self, args: list = None):
        if args is not None and isinstance(args, list):
            delete_index = self._df[self._df.apply(lambda x: True if x['uri'] not in args else False, axis=1)].index
            self._df.drop(index=delete_index, inplace=True)

    def rule_filter_needed_params_or(self, args: list = None):
        """
        根据指定 get params中 的 key 过滤参数请求
        :param args:
        :return:
        """
        if args is not None and isinstance(args, list):
            def func(x):
                if any([True for i in args if i in x['get_params']]):
                    return False
                return True

            delete_index = self._df[self._df.apply(func, axis=1)].index
            self._df.drop(index=delete_index, inplace=True)


class CompareRules:
    is_pass = None

    def __init__(self, resp1: Union[dict, list, str], resp2: Union[dict, list, str]):
        self.resp1 = resp1
        self.resp2 = resp2

    def rule_json_compare(self, ignores: Union[list, dict] = None):
        """
        比较单个响应结果是否一致
        {"compare_all_equal":{"ignore":""}}
        @param resp1:
        @param resp2:
        @param ignores:
        @return:
        """
        _is_pass = JsonCompare(rules=ignores).check(self.resp1, self.resp2)

        self.is_pass = _is_pass == NO_DIFF
