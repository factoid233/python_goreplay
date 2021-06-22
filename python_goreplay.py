# -*- coding: utf-8 -*-
from core import ReplayMain

if __name__ == '__main__':
    ReplayMain.replay_main()

"""
python3 python_goreplay.py -h1 172.16.2.22:8088 -h2 172.16.2.211:8182 -v 1 -p goreplay/test.gor -r '{"replace_dict":{"user":"test","client_user":"test","client_channel":"test"},"delete_uri":["/actuator/prometheus"]}' 
"""
