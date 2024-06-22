#!/usr/bin/env python
# -*- coding: utf-8 -*-
from atrader import *
import os
from src import func_lib


def run():
    # 加载策略配置
    config = func_lib.load_config()
    strategy_name = config['strategy_name']
    strategy_conf = config['config']
    target_list = strategy_conf['target_list']
    begin_date = strategy_conf['begin_date']
    end_date = strategy_conf['end_date']
    frequency = strategy_conf['frequency']

    # 查找策略地址
    current_path = os.path.realpath(__file__)
    strategy_path = os.path.normpath(os.path.join(current_path, f'../../src/{strategy_name}.py'))

    run_backtest(strategy_name=strategy_name, file_path=strategy_path, target_list=target_list,
                 frequency=frequency, fre_num=120, begin_date=begin_date, end_date=end_date)


if __name__ == '__main__':
    run()
