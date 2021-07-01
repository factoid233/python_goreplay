# -*- coding: utf-8 -*-
import datetime
import json
import logging
import os

import numpy as np
import pandas as pd
from jsoncomparison import Compare as JsonCompare, NO_DIFF

from src.common import get_root_path

logger = logging.getLogger(__name__)


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


class Storage:
    def __init__(self, df):
        self.df: pd.DataFrame = df

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

    def _format_handler(self):
        key_show = ['uri', 'is_pass', 'request_method', 'host', 'get_params', 'post_data', 'http_code', 'response',
                    'response_compare_json', 'elapsed_time', 'remark', 'created_time']
        if self.df.empty:
            logger.info('无结果文件生成，无失败')
            exit(0)
        if 'is_pass' in self.df.keys():
            df: pd.DataFrame = self.df.loc[lambda x: x['is_pass'] == 'fail']
            df['response_compare_json'] = df['response'].map(self.generate_compare_json)
            df['response'] = df['response'].map(self.response_handle)

        else:
            df = self.df
            for v in ('response_compare_json', 'is_pass'):
                key_show.pop(key_show.index(v))
        # 选择部分字段存储
        df = df[key_show].copy()
        self.df = df.sort_values('uri')

    def store(self):
        self._format_handler()
        self._flush_to_csv()

    def _flush_to_csv(self):
        """
        写入到csv
        @return:
        """
        df = self.df
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

