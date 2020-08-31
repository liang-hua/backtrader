import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.font_manager as fm
from datetime import datetime
import backtrader as bt
import tushare as ts
token = 'aab90c7d0642054c64c7d99e40542ee372e40ca864e247314f9bf9d3'
ts.set_token(token)
pro = ts.pro_api()
#正常显示画图时出现的中文和负号
from pylab import mpl
mpl.rcParams['font.sans-serif']=['SimHei']
mpl.rcParams['axes.unicode_minus']=False
class MyStrategy(bt.Strategy):
    '''
    #平滑异同移动平均线MACD
            DIF(蓝线): 计算12天平均和26天平均的差，公式：EMA(C,12)-EMA(c,26)
           Signal(DEM或DEA或MACD) (红线): 计算macd9天均值，公式：Signal(DEM或DEA或MACD)：EMA(MACD,9)
            Histogram (柱): 计算macd与signal的差值，公式：Histogram：MACD-Signal

            period_me1=12
            period_me2=26
            period_signal=9
            macd = ema(data, me1_period) - ema(data, me2_period)
            signal = ema(macd, signal_period)
            histo = macd - signal
    '''
    # 平滑异同移动平均线MACD
    # 买入与卖出算法：
    #   macd、signal、histo都大于0且未持仓，买入
    #   macd、signal、histo都小于等于0，卖出持仓股票
    params=(('printlog',False),)

    def __init__(self):
        macd = bt.ind.MACD()
        self.macd = macd.macd
        self.signal = macd.signal
        self.histo = bt.ind.MACDHisto()

    def next(self):
        if not self.position:  # 没有持仓
            # self.data.close是表示收盘价
            # 收盘价大于histo，买入
            if self.macd > 0 and self.signal > 0 and self.histo > 0:
                self.buy()
        else:
            # 收盘价小于等于histo，卖出
            if self.macd <= 0 and self.signal <= 0 and self.histo <= 0:
                self.sell()

    #交易记录日志（可省略，默认不输出结果）
    def log(self, txt, dt=None,doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()},{txt}')

    #记录交易执行情况（可省略，默认不输出结果）
    def notify_order(self, order):
        # 如果order为submitted/accepted,返回空
        if order.status in [order.Submitted, order.Accepted]:
            return
        # 如果order为buy/sell executed,报告价格结果
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入:\n价格:{order.executed.price},\
                成本:{order.executed.value},\
                手续费:{order.executed.comm}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(f'卖出:\n价格：{order.executed.price},\
                成本: {order.executed.value},\
                手续费{order.executed.comm}')
            self.bar_executed = len(self)

        # 如果指令取消/交易失败, 报告结果
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('交易失败')
        self.order = None

    #记录交易收益情况（可省略，默认不输出结果）
    def notify_trade(self,trade):
        if not trade.isclosed:
            return
        self.log(f'策略收益：\n毛收益 {trade.pnl:.2f}, 净收益 {trade.pnlcomm:.2f}')

    #回测结束后输出结果（可省略，默认输出结果）
    def stop(self):
        self.log('期末总资金 %.2f' %
                 (self.broker.getvalue()), doprint=True)



def plot_stock(code,title,start,end):
    #旧版tushare接口
   dd=ts.get_k_data(code,autype='qfq',start=start,end=end)
   dd.index=pd.to_datetime(dd.date)
   dd.close.plot(figsize=(14,6),color='r')
   plt.title(title+'价格走势\n'+start+':'+end,size=15)
   plt.annotate(f'期间累计涨幅:{(dd.close[-1]/dd.close[0]-1)*100:.2f}%', xy=(dd.index[-150],dd.close.mean()),
            xytext=(dd.index[-500],dd.close.min()), bbox = dict(boxstyle = 'round,pad=0.5',
           fc = 'yellow', alpha = 0.5),
            arrowprops=dict(facecolor='green', shrink=0.05),fontsize=12)
   plt.show()

#浦发银行股票
plot_stock('600000','浦发银行','2010-01-01','2020-08-30')
# 初始化cerebro回测系统设置
cerebro = bt.Cerebro()
#新版tushare接口获取数据
df = ts.pro_bar(ts_code='600000.SH', adj='qfq', start_date='20100101',end_date='20200830')
#df=ts.get_k_data('600000',autype='qfq',start='2010-01-01',end='2020-03-30')
df = df.sort_values(by="trade_date", axis=0, ascending=True)
df.index=pd.to_datetime(df.trade_date)
df=df[['open','high','low','close','vol']]
df.columns = ['open','high','low','close','volume']

data = bt.feeds.PandasData(dataname=df,
                            fromdate=datetime(2010, 1, 1),
                            todate=datetime(2020, 8, 30) )
# 加载数据
cerebro.adddata(data)
# 将交易策略加载到回测系统中
#设置printlog=True，表示打印交易日志log
cerebro.addstrategy(MyStrategy,printlog=True)
# 设置初始资本为10,000
cerebro.broker.setcash(10000.0)
# 设置交易手续费为 0.1%
cerebro.broker.setcommission(commission=0.001)
#设置买入设置，策略，数量
cerebro.addsizer(bt.sizers.FixedSize, stake=1000)
#回测结果
cerebro.run()
#获取最后总资金
portvalue = cerebro.broker.getvalue()
#Print out the final result
print(f'总资金: {portvalue:.2f}')