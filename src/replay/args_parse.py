# -*- coding: utf-8 -*-
import argparse
import json


class ArgParse:
    @classmethod
    def load_args_config(cls, args=None):
        return ArgParse()._load_args_config(args)

    def _load_args_config(self, args=None):
        return vars(self._get_args(args))

    def _get_args(self, args):
        parser = argparse.ArgumentParser(
            description='python goreplay'
        )
        parser.add_argument(
            '-c', '--toml',
            action='store',
            dest='conf',
            required=True,
            metavar='/tmp/test.yaml',
            help='goreplay 配置文件路径 yaml语法'
        )

        # args - 要解析的字符串列表。 默认情况下None是从 sys.argv 获取。
        res = parser.parse_args(args)
        return res
