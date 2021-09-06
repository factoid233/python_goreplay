# -*- coding: utf-8 -*-
from src.replay.args_parse import ArgParse
from src.common.util import read_yaml
from src.replay.replay_run_types import ReplayRunTypeOne, ReplayRunTypeTwo, ReplayRunTypeNoCompare


def main():
    out_args: dict = ArgParse.load_args_config()
    kwargs = read_yaml(out_args.get('conf'))
    if 'no-diff' in kwargs and kwargs.get('no-diff') is True:
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
