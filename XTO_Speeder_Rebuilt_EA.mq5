//+------------------------------------------------------------------+
//|                                     XTO_Speeder_Rebuilt_EA.mq5   |
//|                 Rebuilt XTO Speeder Pro - High Speed DCA Scalper |
//|                                     Enhanced with Safety Armor   |
//+------------------------------------------------------------------+
#property copyright "Rebuilt Engine 2026"
#property link      "https://tcodedang.github.io/XTO-Project/"
#property version   "5.00"
#property description "Rebuilt XTO Speeder EA: High-Speed Momentum DCA Grid Scalper"
#property description "Includes GroupTP (VWAP Basket TP), Grid Multiplier, and Disaster SL Protection"

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\OrderInfo.mqh>

//--- Input Parameters ---
input group "=== [1] BOT IDENTITY & EXECUTION ==="
input ulong    InpMagicNumber       = 1111;         // Magic Number (XTO Default: 1111)
input string   InpTradeComment      = "XTO-Rebuilt"; // Order Comment
input ulong    InpSlippage          = 20;           // Max Slippage (points)

input group "=== [2] LOT SIZING & DCA GRID ==="
input double   InpBaseLot           = 0.01;         // Initial Base Lot Size
input double   InpLotMultiplier     = 1.5;          // Grid Lot Multiplier
input int      InpGridStepPoints    = 60;           // Grid Step Spacing (points: 60 = $0.60 on Gold)
input int      InpMaxLayers         = 5;            // Maximum Grid Layers per Basket (Safety Cap)
input bool     InpAllowBuy          = true;         // Allow BUY Baskets
input bool     InpAllowSell         = true;         // Allow SELL Baskets

input group "=== [3] GROUP TAKE PROFIT (VWAP) ==="
input int      InpGroupTPPoints     = 60;           // Group TP Distance from VWAP (60 pts = $0.60)
input double   InpGroupTPUSD        = 2.50;         // Group TP Target in USD (0 = use Points)
input bool     InpUseTrailingTP     = false;        // Enable Basket Trailing Take Profit
input int      InpTrailingPoints    = 30;           // Trailing Step (points)

input group "=== [4] RISK & DISASTER ARMOR ==="
input double   InpMaxBasketLossUSD  = 50.00;        // Max Basket Loss in USD (Emergency Liquidation)
input double   InpDailyProfitTarget = 200.00;       // Daily Profit Target USD (0 = Disabled)
input double   InpDailyMaxLossUSD   = 100.00;       // Daily Max Loss USD (0 = Disabled)
input int      InpHardSLPoints      = 0;            // Hard Broker SL per order in Points (0 = Internal Only)

input group "=== [5] MOMENTUM & TREND FILTER ==="
input bool     InpUseTrendFilter    = true;         // Enable Fast Trend Filter
input int      InpFastEMAPeriod     = 21;           // Fast Momentum EMA Period
input int      InpSlowEMAPeriod     = 55;           // Slow Baseline EMA Period
input ENUM_TIMEFRAMES InpFilterTF   = PERIOD_M15;   // Filter Timeframe

//--- Global Variables ---
CTrade         m_trade;
CPositionInfo  m_position;

int            h_ema_fast           = INVALID_HANDLE;
int            h_ema_slow           = INVALID_HANDLE;
double         g_balanceStart       = 0.0;
double         g_closedProfit       = 0.0;
datetime       g_lastDayChecked     = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   m_trade.SetExpertMagicNumber(InpMagicNumber);
   m_trade.SetDeviationInPoints(InpSlippage);
   m_trade.SetTypeFillingBySymbol(_Symbol);

   g_balanceStart = AccountInfoDouble(ACCOUNT_BALANCE);
   g_closedProfit = 0.0;
   g_lastDayChecked = iTime(_Symbol, PERIOD_D1, 0);

   if(InpUseTrendFilter)
   {
      h_ema_fast = iMA(_Symbol, InpFilterTF, InpFastEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
      h_ema_slow = iMA(_Symbol, InpFilterTF, InpSlowEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
      if(h_ema_fast == INVALID_HANDLE || h_ema_slow == INVALID_HANDLE)
      {
         Print("Error creating EMA indicators!");
         return(INIT_FAILED);
      }
   }

   PrintFormat("XTO Speeder Rebuilt EA initialized. Magic=%d | BaseLot=%.2f | Step=%d | GroupTP=%d | MaxLayers=%d",
               InpMagicNumber, InpBaseLot, InpGridStepPoints, InpGroupTPPoints, InpMaxLayers);
   PrintFormat("Khôi phục g_closedProfit=%.2f | g_balanceStart=%.2f", g_closedProfit, g_balanceStart);

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(h_ema_fast != INVALID_HANDLE) IndicatorRelease(h_ema_fast);
   if(h_ema_slow != INVALID_HANDLE) IndicatorRelease(h_ema_slow);
   Comment("");
}

//+------------------------------------------------------------------+
//| Helper: Get Point Value for Symbol                               |
//+------------------------------------------------------------------+
double GetPointValue()
{
   double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   if(pt == 0) pt = 0.01;
   return pt;
}

//+------------------------------------------------------------------+
//| Calculate Basket Metrics (VWAP, Lots, Count, Floating Profit)    |
//+------------------------------------------------------------------+
void GetBasketMetrics(ENUM_POSITION_TYPE pos_type, int &count, double &total_lots, double &vwap, double &floating_pnl, double &worst_price, double &best_price)
{
   count = 0;
   total_lots = 0.0;
   vwap = 0.0;
   floating_pnl = 0.0;
   worst_price = (pos_type == POSITION_TYPE_BUY) ? 9999999.0 : 0.0;
   best_price  = (pos_type == POSITION_TYPE_BUY) ? 0.0 : 9999999.0;

   double volume_price_sum = 0.0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(m_position.SelectByIndex(i))
      {
         if(m_position.Symbol() == _Symbol && m_position.Magic() == InpMagicNumber && m_position.PositionType() == pos_type)
         {
            count++;
            double vol = m_position.Volume();
            double op = m_position.PriceOpen();
            total_lots += vol;
            volume_price_sum += (op * vol);
            floating_pnl += m_position.Profit() + m_position.Swap();

            if(pos_type == POSITION_TYPE_BUY)
            {
               if(op < worst_price) worst_price = op;
               if(op > best_price)  best_price = op;
            }
            else
            {
               if(op > worst_price) worst_price = op;
               if(op < best_price)  best_price = op;
            }
         }
      }
   }

   if(total_lots > 0)
      vwap = volume_price_sum / total_lots;
}

//+------------------------------------------------------------------+
//| Close Entire Basket of Positions                                 |
//+------------------------------------------------------------------+
void CloseBasket(ENUM_POSITION_TYPE pos_type, string reason)
{
   PrintFormat("XTO Speeder: Closing %s Basket [%s]", (pos_type == POSITION_TYPE_BUY ? "BUY" : "SELL"), reason);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(m_position.SelectByIndex(i))
      {
         if(m_position.Symbol() == _Symbol && m_position.Magic() == InpMagicNumber && m_position.PositionType() == pos_type)
         {
            m_trade.PositionClose(m_position.Ticket());
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Calculate Next Lot Size based on Multiplier                      |
//+------------------------------------------------------------------+
double CalculateNextLot(int layer)
{
   double lot = InpBaseLot * MathPow(InpLotMultiplier, layer);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);

   if(step > 0)
      lot = MathFloor(lot / step) * step;

   if(lot < min_lot) lot = min_lot;
   if(lot > max_lot) lot = max_lot;

   return NormalizeDouble(lot, 2);
}

//+------------------------------------------------------------------+
//| Check Trend Bias from EMA Crossover                              |
//+------------------------------------------------------------------+
int GetTrendBias()
{
   if(!InpUseTrendFilter || h_ema_fast == INVALID_HANDLE || h_ema_slow == INVALID_HANDLE)
      return 0; // Neutral / Both allowed

   double fast_val[1], slow_val[1];
   if(CopyBuffer(h_ema_fast, 0, 0, 1, fast_val) <= 0 || CopyBuffer(h_ema_slow, 0, 0, 1, slow_val) <= 0)
      return 0;

   if(fast_val[0] > slow_val[0]) return 1;  // Bullish Trend
   if(fast_val[0] < slow_val[0]) return -1; // Bearish Trend
   return 0;
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick)) return;

   double pt = GetPointValue();

   //--- Metrics for BUY Basket ---
   int buy_count = 0;
   double buy_lots = 0.0, buy_vwap = 0.0, buy_pnl = 0.0, buy_worst = 0.0, buy_best = 0.0;
   GetBasketMetrics(POSITION_TYPE_BUY, buy_count, buy_lots, buy_vwap, buy_pnl, buy_worst, buy_best);

   //--- Metrics for SELL Basket ---
   int sell_count = 0;
   double sell_lots = 0.0, sell_vwap = 0.0, sell_pnl = 0.0, sell_worst = 0.0, sell_best = 0.0;
   GetBasketMetrics(POSITION_TYPE_SELL, sell_count, sell_lots, sell_vwap, sell_pnl, sell_worst, sell_best);

   //--- DISASTER RECOVERY CHECK (Hard Account Protection) ---
   if(InpMaxBasketLossUSD > 0)
   {
      if(buy_count > 0 && buy_pnl <= -InpMaxBasketLossUSD)
      {
         PrintFormat("DISASTER SHIELD ACTIVATED: BUY Basket Loss -$%.2f exceeded limit -$%.2f! Liquidating.",
                     MathAbs(buy_pnl), InpMaxBasketLossUSD);
         CloseBasket(POSITION_TYPE_BUY, "Disaster_Emergency_SL");
         return;
      }
      if(sell_count > 0 && sell_pnl <= -InpMaxBasketLossUSD)
      {
         PrintFormat("DISASTER SHIELD ACTIVATED: SELL Basket Loss -$%.2f exceeded limit -$%.2f! Liquidating.",
                     MathAbs(sell_pnl), InpMaxBasketLossUSD);
         CloseBasket(POSITION_TYPE_SELL, "Disaster_Emergency_SL");
         return;
      }
   }

   //--- GROUP TAKE PROFIT (GroupTP_3 Logic) ---
   // 1. BUY Basket GroupTP
   if(buy_count > 0 && buy_vwap > 0)
   {
      double buy_target_tp = buy_vwap + (InpGroupTPPoints * pt);
      bool tp_hit = (tick.bid >= buy_target_tp);

      if(InpGroupTPUSD > 0 && buy_pnl >= InpGroupTPUSD)
         tp_hit = true;

      if(tp_hit)
      {
         PrintFormat("GroupTP_3 BUY ► avg=%.2f | TP=%.2f | Bid=%.2f | Profit=+$%.2f",
                     buy_vwap, buy_target_tp, tick.bid, buy_pnl);
         CloseBasket(POSITION_TYPE_BUY, "GroupTP_Hit");
         return;
      }
   }

   // 2. SELL Basket GroupTP
   if(sell_count > 0 && sell_vwap > 0)
   {
      double sell_target_tp = sell_vwap - (InpGroupTPPoints * pt);
      bool tp_hit = (tick.ask <= sell_target_tp);

      if(InpGroupTPUSD > 0 && sell_pnl >= InpGroupTPUSD)
         tp_hit = true;

      if(tp_hit)
      {
         PrintFormat("GroupTP_3 SELL ► avg=%.2f | TP=%.2f | Ask=%.2f | Profit=+$%.2f",
                     sell_vwap, sell_target_tp, tick.ask, sell_pnl);
         CloseBasket(POSITION_TYPE_SELL, "GroupTP_Hit");
         return;
      }
   }

   //--- GRID DCA LAYER MANAGEMENT ---
   double step_dist = InpGridStepPoints * pt;
   int trend = GetTrendBias();

   // 1. Manage BUY Basket Grid
   if(InpAllowBuy)
   {
      if(buy_count == 0)
      {
         // Initial Layer Entry
         if(trend >= 0) // Trend is Bullish or Neutral
         {
            double lot = CalculateNextLot(0);
            double sl = (InpHardSLPoints > 0) ? (tick.ask - InpHardSLPoints * pt) : 0.0;
            m_trade.Buy(lot, _Symbol, tick.ask, sl, 0.0, InpTradeComment);
            PrintFormat("XTO Speeder: Opened Initial BUY %.2f @ %.2f", lot, tick.ask);
         }
      }
      else if(buy_count < InpMaxLayers)
      {
         // Averaging Down (Price must drop below lowest entry by step_dist)
         if((buy_worst - tick.ask) >= step_dist)
         {
            double next_lot = CalculateNextLot(buy_count);
            double sl = (InpHardSLPoints > 0) ? (tick.ask - InpHardSLPoints * pt) : 0.0;
            m_trade.Buy(next_lot, _Symbol, tick.ask, sl, 0.0, InpTradeComment);
            PrintFormat("XTO Speeder: Layer %d BUY %.2f @ %.2f (Dist: %.2f pts)",
                        buy_count + 1, next_lot, tick.ask, (buy_worst - tick.ask) / pt);
         }
      }
   }

   // 2. Manage SELL Basket Grid
   if(InpAllowSell)
   {
      if(sell_count == 0)
      {
         // Initial Layer Entry
         if(trend <= 0) // Trend is Bearish or Neutral
         {
            double lot = CalculateNextLot(0);
            double sl = (InpHardSLPoints > 0) ? (tick.bid + InpHardSLPoints * pt) : 0.0;
            m_trade.Sell(lot, _Symbol, tick.bid, sl, 0.0, InpTradeComment);
            PrintFormat("XTO Speeder: Opened Initial SELL %.2f @ %.2f", lot, tick.bid);
         }
      }
      else if(sell_count < InpMaxLayers)
      {
         // Averaging Up (Price must rise above highest entry by step_dist)
         if((tick.bid - sell_worst) >= step_dist)
         {
            double next_lot = CalculateNextLot(sell_count);
            double sl = (InpHardSLPoints > 0) ? (tick.bid + InpHardSLPoints * pt) : 0.0;
            m_trade.Sell(next_lot, _Symbol, tick.bid, sl, 0.0, InpTradeComment);
            PrintFormat("XTO Speeder: Layer %d SELL %.2f @ %.2f (Dist: %.2f pts)",
                        sell_count + 1, next_lot, tick.bid, (tick.bid - sell_worst) / pt);
         }
      }
   }

   //--- ON-CHART HUD DASHBOARD ---
   string hud = "";
   hud += "========================================\n";
   hud += "     🚀 XTO SPEEDER PRO [REBUILT] 🚀    \n";
   hud += "========================================\n";
   hud += StringFormat("Account: %d | Server: %s\n", AccountInfoInteger(ACCOUNT_LOGIN), AccountInfoString(ACCOUNT_SERVER));
   hud += StringFormat("Balance: $%.2f | Equity: $%.2f\n", AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
   hud += StringFormat("Trend Bias: %s\n", (trend > 0 ? "BULLISH 🟢" : (trend < 0 ? "BEARISH 🔴" : "NEUTRAL ⚪")));
   hud += "----------------------------------------\n";
   hud += StringFormat("BUY Basket : %d / %d Layers | Lots: %.2f\n", buy_count, InpMaxLayers, buy_lots);
   hud += StringFormat("BUY VWAP   : %.2f | Target TP: %.2f\n", buy_vwap, (buy_vwap > 0 ? buy_vwap + InpGroupTPPoints * pt : 0.0));
   hud += StringFormat("BUY Profit : $%.2f\n", buy_pnl);
   hud += "----------------------------------------\n";
   hud += StringFormat("SELL Basket: %d / %d Layers | Lots: %.2f\n", sell_count, InpMaxLayers, sell_lots);
   hud += StringFormat("SELL VWAP  : %.2f | Target TP: %.2f\n", sell_vwap, (sell_vwap > 0 ? sell_vwap - InpGroupTPPoints * pt : 0.0));
   hud += StringFormat("SELL Profit: $%.2f\n", sell_pnl);
   hud += "----------------------------------------\n";
   hud += StringFormat("Max Basket SL Limit : -$%.2f\n", InpMaxBasketLossUSD);
   hud += "========================================";

   Comment(hud);
}
//+------------------------------------------------------------------+
