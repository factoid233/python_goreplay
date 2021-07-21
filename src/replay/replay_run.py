# -*- coding: utf-8 -*-
import datetime
import json
import logging
import sys

import httpx
import pandas as pd
import trio

logger = logging.getLogger(__name__)


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
                content_type = line['headers'].get('Content-Type') or line['headers'].get('Content-type')
                if content_type is not None:
                    if 'form' in content_type:
                        response = await client.post(url=url, params=line['get_params'], data=line['post_data'],
                                                     headers=line['headers'])
                    elif 'json' in content_type:
                        response = await client.post(url=url, params=line['get_params'], json=line['post_data'],
                                                     headers=line['headers'])
                    else:
                        response = await client.post(url=url, params=line['get_params'],
                                                     content=json.dumps(line['post_data'], ensure_ascii=False),
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
