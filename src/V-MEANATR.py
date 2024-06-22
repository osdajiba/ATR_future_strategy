from atrader import *
from src import func_lib 

def compute_TR_List(data,context):
    high = data['high'].values  # 最高价
    low = data['low'].values  # 最低价
    close = data['close'].values  # 收盘价
    value1 = high[-1 - context.N:-1] - low[-1 - context.N:-1]  # 最高价-最低价
    value2 = abs(high[-1 - context.N:-1] - close[-2 - context.N:-2])  # 涨幅
    value3 = abs(low[-1 - context.N:-1] - close[-2 - context.N:-2])  # 跌幅
    v23 = np.array([value2, value3])  # 涨跌幅
    TR0 = np.array([value1, v23.max(axis=0)])  # 合并涨跌幅和（最高价-最低价）
    TRlist = TR0.max(axis=0)  # 真实波幅
    return TRlist


def signal_func(context: Context):  # 利用行情数据构建外部函数返回的结果
    value = np.ones(context.TLen) * np.inf  # 长度等于标的个数的向量，用于记录交易信号
    k_data = get_reg_kdata(reg_idx=context.reg_kdata[1], length=30, df=True)  # 获取分钟数据，长度为30
    for i in range(context.TLen):
        data = k_data.loc[i * 30:i * 30 + 29]  # 获取标的数据
        open1 = data['open'].values  # 开盘价
        close = data['close'].values  # 收盘价

        TRlist = compute_TR_List(data, context)
        
        ATR = np.mean(TRlist[TRlist > 0]) if sum(TRlist[TRlist > 0] != 0) != 0 else 0
        upper = open1[-1] + context.M * ATR if ATR != 0 else open1[0]
        lower = open1[-1] - context.M * ATR if ATR != 0 else open1[0]

        if close[-1] > upper:
            value[i] = 1    # 大于upper时开多
        elif close[-1] < lower:
            value[i] = -1   # 小于lower时开空
        elif close[-1] < open1[-1]:
            value[i] = -2   # 小于open时平多
        elif close[-1] > open1[-1]:
            value[i] = 2    # 大于open时平空
            
    return value

def init(context: Context):
    """
    回测参数初始化
    """
    context.TLen = len(context.target_list)  # 标的个数
    context.N = 10  # 计算ATR的数据长度
    context.M = 0.5  # ATR权重
    context.stoploss = 0.08  # 止损
    context.stopprofit = 0.12  # 止盈
    context.trailinggap = 0.002  # 跟踪止损
    context.openprice = np.zeros(context.TLen)  # 记录入场价
    context.histextre = np.zeros(context.TLen)  # 记录最高价
    context.tradetime = []  # 空列表
    context.daynum = 0  # 初始化交易日
    reg_kdata(frequency='min', fre_num=120)  # 注册分钟数据
    reg_kdata(frequency='day', fre_num=1)  # 注册日线数据
    reg_userindi(indi_func=signal_func)  # 注册外部函数
    context.futureinfom = get_future_info(context.target_list)  # 获取标的信息


def on_data(context: Context):
    """
    主函数，按天循环回测
    """
    context.daynum += 1  # 增加回测天数
    userindi0 = get_reg_userindi(reg_idx=context.reg_userindi[0], length=2)  # 获取用户信号数据
    if len(userindi0) < 2:
        return

    # 获取当前仓位和当前时刻数据
    long_positions = context.account().positions['volume_long']
    short_positions = context.account().positions['volume_short']
    bartime = get_current_bar(target_indices=[])['time_bar']

    # 每次开盘前重置交易次数并获取当前时间
    nowtime = func_lib.reset_trade_count(context, bartime)
    
    # 每天收盘前完全平仓
    func_lib.flatten_positions(context, long_positions, short_positions, nowtime)

    mdata = get_reg_kdata(reg_idx=context.reg_kdata[0], length=30, fill_up=False, df=True)  # 获取分钟线数据
    ddata = get_reg_kdata(reg_idx=context.reg_kdata[1], length=1, fill_up=False, df=True)  # 获取日线数据

    for i in range(context.TLen):
        # 数据处理
        mdatai = mdata.loc[i * 30: i * 30 + 29]  # 获取标的分钟数据

        dsignal0 = userindi0.value.values[0][i]  # 昨天信号
        dsignal1 = userindi0.value.values[1][i]  # 当天信号
        
        ddatai = ddata[ddata['target_idx'] == i]  # 取日线数据
        if len(ddatai)==0 or ddatai['volume'].values[-1] == 0 or (
                ddatai['high'].values[-1] - ddatai['low'].values[-1]) == 0:
            continue  # 跳过无效数据
        
        if ddatai['close'].isna().any():
            return   
        
        # 计算ATR指标
        high, low, close = mdatai['high'].values, mdatai['low'].values, mdatai['close'].values  # 获取高低收数据
        TRlist = compute_TR_List(mdatai, context)
        ATR = np.mean(TRlist[TRlist > 0]) if sum(TRlist[TRlist > 0]) != 0 else 0
 
        # 交易逻辑
        if long_positions[i] > 0 and short_positions[i] > 0:
            # 记录最高值或最低值
            func_lib.update_extreme(context, i, high, low)  # 更新历史最高最低价

            # 平多仓条件
            closeBuy1 = long_positions[i] > 0 and not np.isinf(dsignal0) and not np.isinf(dsignal1) and dsignal1 <= 0
            closeBuy2 = long_positions[i] > 0 and close[-1] < (context.openprice[i] * (1 - context.stoploss))
            closeBuy3 = long_positions[i] > 0 and context.histextre[i] > (context.openprice[i] * (1 + context.stopprofit)) \
                        and close[-1] < (context.histextre[i] * (1 - context.trailinggap))

            # 平空仓条件
            closeSell1 = short_positions[i] < 0 and not np.isinf(dsignal0) and not np.isinf(dsignal1) and dsignal1 >= 0
            closeSell2 = short_positions[i] < 0 and close[-1] > (context.openprice[i] * (1 + context.stoploss))
            closeSell3 = short_positions[i] < 0 and context.histextre[i] < (context.openprice[i] * (1 - context.stopprofit)) \
                        and close[-1] > (context.histextre[i] * (1 + context.trailinggap))

            # 满足条件时平仓，并记录交易次数
            if closeBuy1 or closeBuy2 or closeBuy3:
                order_target_volume(account_idx=0, target_idx=i, target_volume=0, side=1, order_type=2)
                context.tradetime[i] += 1
            elif closeSell1 or closeSell2 or closeSell3:
                order_target_volume(account_idx=0, target_idx=i, target_volume=0, side=2, order_type=2)
                context.tradetime[i] += 1

        execute_trades(context, i, dsignal0, dsignal1, close, ATR)  # 执行交易


def execute_trades(context, i, dsignal0, dsignal1, close, range2):
    """
    执行交易，根据信号开仓或平仓
    """
    long_positions = context.account().positions['volume_long']
    short_positions = context.account().positions['volume_short']
    multiplier = context.futureinfom['multiplier'].iloc[i]
    account_data = context.account()

    try:  # 检查成交量 amount 是否异常
        account_cash = account_data.cash['valid_cash'].values[0]  # 获取可用资金
        amount = int(account_cash / context.TLen / close[-1] / multiplier)  # 计算交易手数
        if np.isnan(amount):
            amount = 1
    except (KeyError, IndexError, ValueError) as e:
        print(f"Error calculating amount: {e}")
        amount = 0  # 或者其他合适的默认值

    # 判断是否开多单
    if short_positions[i] >= 0 and not np.isinf(dsignal0) and not np.isinf(
            dsignal1) and dsignal0 != 1 and dsignal1 == 1 and context.tradetime[i] < 2 and range2 > 0:
        order_volume(0, i, amount, 1, 1, 2)  # 开多单
        context.openprice[i] = close[-1]  # 记录开仓价
        context.histextre[i] = close[-1]  # 更新跟踪止损价
    # 判断是否开空单
    elif long_positions[i] >= 0 and not np.isinf(dsignal0) and not np.isinf(
            dsignal1) and dsignal0 != -1 and dsignal1 == -1 and context.tradetime[i] < 2 and range2 > 0:
        order_volume(0, i, amount, 2, 1, 2)  # 开空单
        context.openprice[i] = close[-1]  # 记录开仓价
        context.histextre[i] = close[-1]  # 更新跟踪止损价
