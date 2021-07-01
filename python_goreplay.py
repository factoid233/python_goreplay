# -*- coding: utf-8 -*-
from src.core import main

if __name__ == '__main__':
    main()

"""
python3 python_goreplay.py -h1 172.16.2.22:8088 -h2 172.16.2.211:8182 -v 1 -p goreplay/test.gor -r '{"replace_dict":{"user":"test","client_user":"test","client_channel":"test"},"delete_uri":["/actuator/prometheus"]}' 
"""
