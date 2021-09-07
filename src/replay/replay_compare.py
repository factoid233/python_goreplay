# -*- coding: utf-8 -*-
import json
import logging
import pandas as pd
from src.replay.rules import CompareRules

logger = logging.getLogger(__name__)


class ReplayCompare:
    df = None

    def __init__(self, res_host: dict):
        self.res_host = res_host

    @staticmethod
    def str_to_json(_str):
        if isinstance(_str, (list, dict)):
            return _str
        try:
            _obj = json.loads(_str)
        except json.JSONDecodeError:
            _obj = _str
        return _obj

    def _is_pass(self, resp1, resp2, rules_kwargs: dict = None):
        """
        比较单个响应结果是否一致
        @param resp1:
        @param resp2:
        @param rules_kwargs:
        @return:
        """
        resp1 = self.str_to_json(resp1)
        resp2 = self.str_to_json(resp2)
        ins = CompareRules(resp1, resp2)
        if rules_kwargs is None:
            ins.rule_json_compare(ignores=None)

        elif isinstance(rules_kwargs, dict):
            prefix = 'rule_'
            rule_methods = list(filter(lambda x: prefix in x, ins.__dir__()))
            method, value = rules_kwargs.popitem()
            if method in rule_methods:
                ins = getattr(ins, method)(value)
            else:
                logger.warning(f"{method}方法未定义，将传入值用于默认的比较规则")
                ins.rule_json_compare(value)

        else:
            raise TypeError('compare_rule 只能为dict或者None')
        return ins.is_pass

    def compare_data(self, compare_rules=None):
        """
        比较两台服务器的响应结果
        @return:
        """
        df1: pd.DataFrame = self.res_host['host1']
        df2: pd.DataFrame = self.res_host['host2']
        # 取两个request_id的并集
        df1.set_index('id1', inplace=True)
        df2.set_index('id1', inplace=True)
        id1s = set(df1.index) | set(df2.index)
        df = pd.DataFrame(columns=df1.columns)
        df['is_pass'] = None
        for id1 in id1s:
            if id1 in df1.index and id1 in df2.index:
                need_keys = ['request_method', 'uri', 'get_params', 'post_data', 'headers', 'created_time', 'remark',
                             ]
                if 'replace_key' in df.keys():
                    need_keys.append('replace_key')
                df.at[id1, need_keys] = df1.loc[id1, need_keys]
                # 合并两个相同的字段为一个
                for item in ('host', 'http_code', 'response', 'elapsed_time', 'remark'):
                    if item == "response":
                        # 将response合并成二元列表
                        df.at[id1, item] = [self.str_to_json(df1.loc[id1, item]), self.str_to_json(df2.loc[id1, item])]
                    else:
                        _map_list = [i for i in (df1.loc[id1, item], df2.loc[id1, item]) if i]
                        df.at[id1, item] = "|".join(map(str, _map_list))

                is_pass = self._is_pass(df1.loc[id1, 'response'], df2.loc[id1, 'response'], rules_kwargs=compare_rules)
                df.loc[id1, 'is_pass'] = "pass" if is_pass else "fail"
        logger.info('比较 done. ')
        self.df = df
