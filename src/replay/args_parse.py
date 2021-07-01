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
            '-r1', '--rules-filter',
            action='store',
            type=json.loads,
            default={},
            dest='rules',
            help="""{"replace_dict":{"替换请求参数":""}, "delete_uri":["过滤url"],"ignore":["比较时忽略相关字段key"]}"""
        )
        parser.add_argument(
            '-r2', '--rules-compare',
            action='store',
            type=json.loads,
            default={},
            dest='rules',
            help="""暂无"""
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
        parser.add_argument(
            '-no-diff', '--no-diff',
            action='store_true',
            dest='no-diff',
            default=False,
            help='是否比较',
        )

        # args - 要解析的字符串列表。 默认情况下None是从 sys.argv 获取。
        res = parser.parse_args(args)
        return res
