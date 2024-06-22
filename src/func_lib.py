#!/usr/bin/env python
# -*- coding: utf-8 -*-

from atrader import *
import json
import sys
import os

sys.path.insert(0, '../')


def load_config():
    current_path = os.path.realpath(__file__)
    config_path = os.path.normpath(os.path.join(current_path, '../../conf/config.json'))
    print(config_path)
    
    with open(config_path, 'r') as file:
        config = json.load(file)
    return config

def reset_trade_count(context, bartime):
    """
    重置每日交易次数，如果当前时间为11:15或交易次数未初始化，则重置交易次数为零列表
    """
    nowtime = bartime[0].hour * 100 + bartime[0].minute  # 将时间转换为小时和分钟组合的整数格式
    if nowtime == 1115 or not context.tradetime:
        context.tradetime = list(np.zeros(context.TLen))  # 初始化交易次数列表
    return nowtime


def flatten_positions(context, long_positions, short_positions, nowtime):
    """
    平仓操作，在每日14:50至15:30之间完全平仓
    """
    if (np.sum(long_positions.values) + np.sum(short_positions.values)) != 0 and 1450 <= nowtime <= 1530:
        for i in range(context.TLen):
            if long_positions[i] != 0:
                order_target_volume(0, i, 0, 1, 2)  # 平多仓
            elif short_positions[i] != 0:
                order_target_volume(0, i, 0, 2, 2)  # 平空仓


def update_extreme(context, i, high, low):
    """
    更新历史最高或最低价格
    """
    if context.account().positions['volume_long'][i] > 0:
        context.histextre[i] = max(context.histextre[i], high[-1])  # 更新多仓的最高价
    elif context.account().positions['volume_short'][i] > 0:
        context.histextre[i] = min(context.histextre[i], low[-1])  # 更新空仓的最低价


def close_position(position, dsignal0, dsignal1, price, openprice, stoploss, stopprofit, histextre, trailinggap):
    """
    判断是否需要平仓
    """
    close_conditions = [
        position > 0 and not np.isinf(dsignal0) and not np.isinf(dsignal1) and dsignal1 <= 0,  # 反转平仓
        position > 0 and price < (openprice * (1 - stoploss)),  # 止损平仓
        position > 0 and histextre > (openprice * (1 + stopprofit)) and price < (histextre * (1 - trailinggap))
        # 跟踪止损平仓
    ]
    return any(close_conditions)  # 返回是否满足任一平仓条件


def get_float(account_series, idx):
    """
    输入字典，将其中第一个元素转化为浮点数
    """
    try:
        total_float = float(account_series.iloc[idx])  # 尝试将 Series 中的第二个元素转换为浮点数
    except (ValueError, TypeError, IndexError):
        total_float = 10000000.00 # 如果转换失败，则将 total_float 设为 0.0
    return total_float




