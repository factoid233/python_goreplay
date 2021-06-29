# -*- coding: utf-8 -*-
import json
import logging
from typing import Tuple, Union

import pandas as pd
from jsoncomparison import Compare as JsonCompare

logger = logging.getLogger(__name__)


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

    # todo
    def _compare_all_equal(self, resp1: Union[dict, list, str], resp2: Union[dict, list, str], ignores: list = None):
        """
        比较单个响应结果是否一致
        {"compare_all_equal":{"ignore":""}}
        @param resp1:
        @param resp2:
        @return:
        """
        if ignores is None:
            ignores = []
        is_pass = JsonCompare().check(resp1, resp2)

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
