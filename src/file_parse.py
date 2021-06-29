# -*- coding: utf-8 -*-
import logging
import os.path
from urllib import parse
import pandas as pd
import re

logger = logging.getLogger(__name__)


class FileParse:
    """
    解析录制的流量的文件成Dataframe
    """
    br = "🐵🙈🙉\n"
    section_set_pass = {'\n', ''}
    all_type = {'1', '2', '3'}

    def __init__(self, path):
        self.path = path

    def parse_type1(self):
        """
        解析原始请求数据
        返回的 Dataframe中含有的字段有：
            ['id1', 'timestamp', 'request_method', 'uri', 'get_params', 'post_data', 'headers', 'http_version']
        :return:
        """
        df = self._parse_main(path=self.path, _type='1')
        if df.empty:
            raise RuntimeError(f'类型1 解析文件{self.path} 为空,退出程序')
        return df

    def parse_type2(self):
        """
        解析原始响应数据
        返回的 Dataframe中含有的字段有：
            ['id1', 'timestamp', 'request_method', 'uri', 'get_params', 'post_data', 'headers', 'http_version']
        :return:
        """
        df = self._parse_main(path=self.path, _type='2')
        df['host'] = 'server'
        df['remark'] = ''
        if df.empty:
            raise RuntimeError(f'类型2 解析文件{self.path} 为空,退出程序')
        return df

    def parse_type3(self):
        """
        解析回放响应数据
        返回的 Dataframe中含有的字段有：
            ['id1', 'timestamp', 'request_method', 'uri', 'get_params', 'post_data', 'headers', 'http_version']
        :return:
        """
        df = self._parse_main(path=self.path, _type='3')
        df['host'] = 'server'
        df['remark'] = ''
        if df.empty:
            raise RuntimeError(f'类型2 解析文件{self.path} 为空,退出程序')
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
            return self._proc_section2or3(section, '2')
        elif _type == '3':
            return self._proc_section2or3(section, '3')

    def _proc_section1(self, section):
        if section and section[0] == '1':
            post_data = id1 = timestamp = None
            section = section.strip(self.br)

            # 将post data 与 其他内容分割
            body: list = re.split('\r?\n\r?\n', section)
            if len(body) == 2:
                post_data = body[1]
                try:
                    post_data0 = parse.parse_qs(post_data, keep_blank_values=True)
                    post_data = {k: ",".join(v) for k, v in post_data0.items()}
                except ValueError:
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

    def _proc_section2or3(self, section, _type):
        if not isinstance(_type, str):
            raise TypeError("_type传参只能字符串")
        if _type not in ('2', '3'):
            raise ValueError("_type传参只能为{'2','3'}其中一个")
        if section and section[0] == _type:
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
        elif section and section[0] in self.all_type - {_type} or section in self.section_set_pass:
            return None
        else:
            logger.warning(f'goreplay 文件有误,type 2 读取错误，error detail:\n{section}')
            return None


if __name__ == '__main__':
    from src.util import get_root_path

    path = os.path.join(get_root_path(), 'src', 'example', 'test.gor')
    file_parse = FileParse(path)
    file_parse.parse_type1()
    file_parse.parse_type2()
    file_parse.parse_type3()
