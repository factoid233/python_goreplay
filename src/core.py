# -*- coding: utf-8 -*-
from src.replay.args_parse import ArgParse
from src.replay.replay_run_types import ReplayRunTypeOne, ReplayRunTypeTwo,ReplayRunTypeNoCompare


def main():
    kwargs: dict = ArgParse.load_args_config()
    if 'no-diff' in kwargs:
        ins = ReplayRunTypeNoCompare()
    elif 'host2' in kwargs:
        ins = ReplayRunTypeTwo()
    elif 'host1' in kwargs:
        ins = ReplayRunTypeOne()
    else:
        raise RuntimeError
    ins.replay_main(**kwargs)
    return

if __name__ == '__main__':
    main()
