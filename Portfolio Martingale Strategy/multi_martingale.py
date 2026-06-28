"""
多资产简易马丁策略 - 只做多，赚钱就平仓（多级止盈版）

每个标的独立运行完整的马丁策略逻辑：
1. 无持仓时：开仓100股
2. 有持仓时：价格每下跌add_pct%，就加仓（倍数multiplier递增）
3. 赚钱时：多级止盈，分批平仓让利润奔跑
"""

from datetime import date
from typing import List, Tuple, Dict

from vnpy.trader.constant import Direction
from vnpy.trader.object import BarData
from vnpy_portfoliostrategy import StrategyTemplate, StrategyEngine


class MultiAssetMartingaleStrategy(StrategyTemplate):
    """多资产简易马丁策略 - 只做多，多级止盈版"""

    author = "MultiAssetMartingale"

    # ========== 基础参数 ==========
    initial_volume = 100        # 初始开仓手数（100股）
    multiplier = 2              # 加仓倍数
    add_pct = 0.03              # 加仓间距（价格每下跌3%加仓）
    max_add_count = 10          # 最大加仓次数
    cooldown_days = 1           # 平仓后冷却天数

    # ========== 多级止盈参数 ==========
    use_multi_target = True         # 启用多级止盈
    target1_pct = 0.02              # 第一目标盈利2%
    target1_ratio = 0.3             # 平仓30%
    target2_pct = 0.05              # 第二目标盈利5%
    target2_ratio = 0.3             # 再平仓30%
    target3_pct = 0.10              # 第三目标盈利10%
    target3_ratio = 0.4             # 全部平仓

    parameters = [
        "initial_volume", "multiplier", "add_pct", 
        "max_add_count", "cooldown_days",
        "use_multi_target", "target1_pct", "target1_ratio",
        "target2_pct", "target2_ratio", "target3_pct", "target3_ratio"
    ]
    variables = ["per_asset_capital"]

    def __init__(
        self,
        strategy_engine: StrategyEngine,
        strategy_name: str,
        vt_symbols: list[str],
        setting: dict
    ) -> None:
        """构造函数"""
        super().__init__(strategy_engine, strategy_name, vt_symbols, setting)

        self.asset_count = len(vt_symbols)
        
        # 每个标的的独立状态
        self.entry_records: Dict[str, List[Tuple[float, int]]] = {}
        self.avg_price: Dict[str, float] = {}
        self.next_add_price: Dict[str, float] = {}
        self.close_date: Dict[str, date] = {}
        self.pending_close: Dict[str, bool] = {}
        self.last_bar_date: Dict[str, date] = {}
        
        # 多级止盈记录
        self.target_reached: Dict[str, int] = {}  # 已触发的止盈级别
        
        # 初始化每个标的的状态
        for vt_symbol in vt_symbols:
            self.entry_records[vt_symbol] = []
            self.avg_price[vt_symbol] = 0.0
            self.next_add_price[vt_symbol] = 0.0
            self.close_date[vt_symbol] = None
            self.pending_close[vt_symbol] = False
            self.last_bar_date[vt_symbol] = None
            self.target_reached[vt_symbol] = 0
        
        # 调试计数器
        self._bar_count = 0
        self._trade_count = 0

    def on_init(self) -> None:
        """策略初始化"""
        self.write_log("=" * 60)
        self.write_log("多资产马丁策略初始化开始（多级止盈版）")
        self.write_log(f"资产数量: {self.asset_count}")
        self.write_log(f"资产列表: {self.vt_symbols}")
        self.write_log(f"初始开仓手数: {self.initial_volume}")
        self.write_log(f"加仓倍数: {self.multiplier}")
        self.write_log(f"加仓间距: {self.add_pct * 100}%")
        self.write_log(f"最大加仓次数: {self.max_add_count}")
        self.write_log(f"冷却天数: {self.cooldown_days}")
        
        if self.use_multi_target:
            self.write_log(f"多级止盈: 已启用")
            self.write_log(f"  目标1: {self.target1_pct*100}% 平仓{self.target1_ratio*100}%")
            self.write_log(f"  目标2: {self.target2_pct*100}% 平仓{self.target2_ratio*100}%")
            self.write_log(f"  目标3: {self.target3_pct*100}% 全部平仓")
        else:
            self.write_log(f"多级止盈: 未启用（盈利即平仓）")
        
        # 加载历史数据
        self.load_bars(10)
        self.write_log("策略初始化完成")
        self.write_log("=" * 60)

    def on_start(self) -> None:
        """策略启动回调"""
        self.write_log("策略启动")

    def on_stop(self) -> None:
        """策略停止回调"""
        self.write_log("策略停止")

    def on_bars(self, bars: Dict[str, BarData]) -> None:
        """K线切片回调 - bars是字典，key为vt_symbol，value为BarData"""
        
        self._bar_count += 1
        
        if not bars:
            return
        
        # 获取当前日期
        first_symbol = list(bars.keys())[0]
        current_date = bars[first_symbol].datetime.date()
        
        # 减少日志频率
        log_this_bar = (self._bar_count % 30 == 1)
        
        if log_this_bar:
            self.write_log(f"\n{'='*60}")
            self.write_log(f"on_bars第{self._bar_count}次调用 - 日期:{current_date}")
            self.write_log(f"收到{len(bars)}个标的")
            self.write_log(f"{'='*60}")
        
        for vt_symbol, bar in bars.items():
            current_price = bar.close_price
            
            # 跳过当天已处理的标的
            if self.last_bar_date.get(vt_symbol) == current_date:
                continue
            self.last_bar_date[vt_symbol] = current_date
            
            current_pos = self.get_pos(vt_symbol)
            avg = self.avg_price.get(vt_symbol, 0)
            records = self.entry_records.get(vt_symbol, [])
            
            if log_this_bar:
                self.write_log(f"\n--- {vt_symbol} ---")
                self.write_log(f"价格: {current_price:.4f}, 持仓: {current_pos}股, 均价: {avg:.4f}")
                self.write_log(f"已触达目标: {self.target_reached.get(vt_symbol, 0)}")
            
            # ========== 强制平空头 ==========
            if current_pos < 0:
                self.write_log(f"  [警告] 空头持仓{current_pos}股，强制平仓")
                self.set_target(vt_symbol, 0)
                self.entry_records[vt_symbol] = []
                self.avg_price[vt_symbol] = 0.0
                self.next_add_price[vt_symbol] = 0.0
                self.target_reached[vt_symbol] = 0
                continue
            
            # ========== 多级止盈平仓逻辑 ==========
            if current_pos > 0 and avg > 0:
                profit_pct = (current_price - avg) / avg
                target_reached = self.target_reached.get(vt_symbol, 0)
                
                if self.use_multi_target:
                    # 第三目标：盈利10%，全部平仓
                    if target_reached < 3 and profit_pct >= self.target3_pct:
                        profit_amount = current_pos * (current_price - avg)
                        self.write_log(f"  [全部止盈] 盈利{profit_pct:.2%}，平仓{current_pos}股")
                        
                        self.set_target(vt_symbol, 0)
                        self.entry_records[vt_symbol] = []
                        self.avg_price[vt_symbol] = 0.0
                        self.next_add_price[vt_symbol] = 0.0
                        self.pending_close[vt_symbol] = True
                        self.close_date[vt_symbol] = current_date
                        self.target_reached[vt_symbol] = 0
                        self._trade_count += 1
                        continue
                    
                    # 第二目标：盈利5%，再平仓30%
                    elif target_reached < 2 and profit_pct >= self.target2_pct:
                        close_volume = int(current_pos * self.target2_ratio)
                        if close_volume > 0:
                            new_pos = current_pos - close_volume
                            self.write_log(f"  [部分止盈2] 盈利{profit_pct:.2%}，平仓{close_volume}股，剩余{new_pos}股")
                            
                            self.set_target(vt_symbol, new_pos)
                            self.target_reached[vt_symbol] = 2
                            self._trade_count += 1
                            continue
                    
                    # 第一目标：盈利2%，平仓30%
                    elif target_reached < 1 and profit_pct >= self.target1_pct:
                        close_volume = int(current_pos * self.target1_ratio)
                        if close_volume > 0:
                            new_pos = current_pos - close_volume
                            self.write_log(f"  [部分止盈1] 盈利{profit_pct:.2%}，平仓{close_volume}股，剩余{new_pos}股")
                            
                            self.set_target(vt_symbol, new_pos)
                            self.target_reached[vt_symbol] = 1
                            self._trade_count += 1
                            continue
                else:
                    # 原版逻辑：盈利大于0就平仓
                    if profit_pct > 0:
                        profit_amount = current_pos * (current_price - avg)
                        self.write_log(f"  [平仓] 盈利{profit_pct:.2%}，平仓{current_pos}股")
                        
                        self.set_target(vt_symbol, 0)
                        self.entry_records[vt_symbol] = []
                        self.avg_price[vt_symbol] = 0.0
                        self.next_add_price[vt_symbol] = 0.0
                        self.pending_close[vt_symbol] = True
                        self.close_date[vt_symbol] = current_date
                        self.target_reached[vt_symbol] = 0
                        self._trade_count += 1
                        continue
            
            # ========== 冷却检查 ==========
            if self.pending_close.get(vt_symbol, False):
                close_dt = self.close_date.get(vt_symbol)
                if close_dt:
                    days_passed = (current_date - close_dt).days
                    if days_passed < self.cooldown_days:
                        continue
                    else:
                        self.pending_close[vt_symbol] = False
                        self.close_date[vt_symbol] = None
                        self.entry_records[vt_symbol] = []
                        self.avg_price[vt_symbol] = 0.0
                        self.next_add_price[vt_symbol] = 0.0
                        self.target_reached[vt_symbol] = 0
                        self.last_bar_date[vt_symbol] = None
            
            # ========== 开仓逻辑 ==========
            if current_pos == 0 and len(records) == 0:
                self.write_log(f"  [开仓] {self.initial_volume}股 @ {current_price:.4f}")
                
                self.set_target(vt_symbol, self.initial_volume)
                records.append((current_price, self.initial_volume))
                self.entry_records[vt_symbol] = records
                self._recalc_avg_price(vt_symbol)
                self.next_add_price[vt_symbol] = current_price * (1 - self.add_pct)
                self.target_reached[vt_symbol] = 0
                self._trade_count += 1
                continue
            
            # ========== 加仓逻辑 ==========
            if current_pos > 0 and len(records) < self.max_add_count:
                next_price = self.next_add_price.get(vt_symbol, 0)
                
                if current_price <= next_price:
                    add_count = len(records)
                    add_volume = int(self.initial_volume * (self.multiplier ** add_count))
                    new_total = current_pos + add_volume
                    
                    self.write_log(f"  [加仓] +{add_volume}股 @ {current_price:.4f}")
                    
                    records.append((current_price, add_volume))
                    self.entry_records[vt_symbol] = records
                    self._recalc_avg_price(vt_symbol)
                    self.next_add_price[vt_symbol] = current_price * (1 - self.add_pct)
                    self.set_target(vt_symbol, new_total)
                    self._trade_count += 1
        
        # 执行调仓
        self.rebalance_portfolio(bars)
        self.put_event()

    def _recalc_avg_price(self, vt_symbol: str) -> None:
        """重新计算持仓均价"""
        records = self.entry_records.get(vt_symbol, [])
        if not records:
            self.avg_price[vt_symbol] = 0.0
            return
        
        total_cost = 0.0
        total_vol = 0
        for price, vol in records:
            total_cost += price * vol
            total_vol += vol
        
        self.avg_price[vt_symbol] = total_cost / total_vol

    def calculate_price(
        self,
        vt_symbol: str,
        direction: Direction,
        reference: float
    ) -> float:
        """计算调仓委托价格"""
        if direction == Direction.LONG:
            return reference * 1.001
        else:
            return reference * 0.999