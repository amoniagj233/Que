//+------------------------------------------------------------------+
//|                                     StructureGrid_HH_LL_EA.mq5   |
//|                                  Copyright 2026, Institutional   |
//|                        Market Structure (HH/LL) + Smart Grid EA  |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Institutional"
#property link      "https://headway.trade"
#property version   "1.00"
#property description "StructureGrid Pro: Market Structure (HH/LL) + Smart Adaptive DCA Scalper for XAUUSD"

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//--- Inputs
input group "=== Risk & Basket Settings ===";
input double   InpBaseLot              = 0.01;      // Base Lot Size (Layer 1)
input int      InpMaxLayers            = 3;         // Max Averaging Layers (Capped at 3)
input double   InpTargetProfitUSD      = 3.50;      // Target Basket Profit ($)
input double   InpMaxBasketLossUSD     = 25.00;     // Emergency Max Basket Loss ($)
input ulong    InpMagicNumber          = 778899;    // Magic Number

input group "=== Market Structure Settings ===";
input ENUM_TIMEFRAMES InpStructureTF   = PERIOD_M15;// Market Structure Timeframe (HH/LL)
input int      InpFractalBars          = 5;         // Fractal Pivot Lookback Bars
input double   InpAtrMultiplier        = 1.2;       // Minimum Spacing (x ATR)
input int      InpAtrPeriod            = 14;        // ATR Indicator Period

//--- Global Variables
CTrade         trade;
CPositionInfo  posInfo;
CSymbolInfo    symInfo;
int            hAtr;
datetime       lastBarTimeM15;
double         g_invalidationLevel = 0.0;
string         g_currentRegime = "NONE";

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   if(!symInfo.Name(_Symbol)) return(INIT_FAILED);
   symInfo.Refresh();
   
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetMarginMode();
   trade.SetTypeFillingBySymbol(_Symbol);
   
   hAtr = iATR(_Symbol, InpStructureTF, InpAtrPeriod);
   if(hAtr == INVALID_HANDLE)
   {
      Print("[!] Error creating ATR indicator handle");
      return(INIT_FAILED);
   }
   
   lastBarTimeM15 = 0;
   Print("[+] StructureGrid HH/LL EA initialized successfully on ", _Symbol);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(hAtr != INVALID_HANDLE) IndicatorRelease(hAtr);
}

//+------------------------------------------------------------------+
//| Evaluate M15 Market Structure (HH / HL vs LL / LH)               |
//+------------------------------------------------------------------+
void EvaluateMarketStructure(string &regime, double &invLevel, double &atrVal)
{
   regime = "CHOP";
   invLevel = 0.0;
   atrVal = 3.50;
   
   double atrBuf[];
   ArraySetAsSeries(atrBuf, true);
   if(CopyBuffer(hAtr, 0, 0, 3, atrBuf) > 0) atrVal = atrBuf[0];
   
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(_Symbol, InpStructureTF, 0, 60, rates);
   if(copied < 30) return;
   
   // Fractal swing pivot detection
   double sh_prices[];
   double sl_prices[];
   ArrayResize(sh_prices, 0);
   ArrayResize(sl_prices, 0);
   
   int half = InpFractalBars / 2;
   for(int i = half; i < copied - half; i++)
   {
      double currH = rates[i].high;
      double currL = rates[i].low;
      bool isSH = true;
      bool isSL = true;
      
      for(int j = 1; j <= half; j++)
      {
         if(rates[i-j].high >= currH || rates[i+j].high >= currH) isSH = false;
         if(rates[i-j].low <= currL || rates[i+j].low <= currL) isSL = false;
      }
      
      if(isSH)
      {
         int sz = ArraySize(sh_prices);
         ArrayResize(sh_prices, sz + 1);
         sh_prices[sz] = currH;
      }
      if(isSL)
      {
         int sz = ArraySize(sl_prices);
         ArrayResize(sl_prices, sz + 1);
         sl_prices[sz] = currL;
      }
   }
   
   int totalSH = ArraySize(sh_prices);
   int totalSL = ArraySize(sl_prices);
   if(totalSH < 2 || totalSL < 2) return;
   
   // In array series or chronological? In our loop i goes 2 to N, so last added is oldest. Let's inspect first two (most recent)
   double sh1 = sh_prices[0]; // Most recent
   double sh2 = sh_prices[1]; // Previous
   double sl1 = sl_prices[0]; // Most recent
   double sl2 = sl_prices[1]; // Previous
   
   bool isHH = sh1 > sh2;
   bool isHL = sl1 > sl2;
   bool isLL = sl1 < sl2;
   bool isLH = sh1 < sh2;
   
   if(isHH && isHL)
   {
      regime = "BULLISH";
      invLevel = sl1 - 0.50; // Below recent Higher Low
   }
   else if(isLL && isLH)
   {
      regime = "BEARISH";
      invLevel = sh1 + 0.50; // Above recent Lower High
   }
}

//+------------------------------------------------------------------+
//| Get Active Basket Telemetry                                      |
//+------------------------------------------------------------------+
int GetBasketInfo(int &totalOrders, double &totalVol, double &totalProfit, double &weightedPrice, ENUM_POSITION_TYPE &basketSide, double &lastOrderPrice)
{
   totalOrders = 0;
   totalVol = 0.0;
   totalProfit = 0.0;
   weightedPrice = 0.0;
   lastOrderPrice = 0.0;
   double volSumPrice = 0.0;
   
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(posInfo.SelectByIndex(i))
      {
         if(posInfo.Symbol() == _Symbol && posInfo.Magic() == InpMagicNumber)
         {
            totalOrders++;
            double vol = posInfo.Volume();
            double pnl = posInfo.Profit() + posInfo.Swap();
            double op = posInfo.PriceOpen();
            
            totalVol += vol;
            totalProfit += pnl;
            volSumPrice += op * vol;
            lastOrderPrice = op;
            basketSide = posInfo.PositionType();
         }
      }
   }
   
   if(totalVol > 0) weightedPrice = volSumPrice / totalVol;
   return totalOrders;
}

//+------------------------------------------------------------------+
//| Close Entire Basket                                              |
//+------------------------------------------------------------------+
void CloseEntireBasket(string reason)
{
   Print("[*] Closing Entire Basket: ", reason);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(posInfo.SelectByIndex(i))
      {
         if(posInfo.Symbol() == _Symbol && posInfo.Magic() == InpMagicNumber)
         {
            trade.PositionClose(posInfo.Ticket());
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   symInfo.RefreshRates();
   double bid = symInfo.Bid();
   double ask = symInfo.Ask();
   
   // 1. Evaluate Structure on M15
   double atrVal = 3.50;
   EvaluateMarketStructure(g_currentRegime, g_invalidationLevel, atrVal);
   
   // 2. Telemetry of current basket
   int totalOrders = 0;
   double totalVol = 0.0, totalProfit = 0.0, weightedPrice = 0.0, lastOrderPrice = 0.0;
   ENUM_POSITION_TYPE basketSide = POSITION_TYPE_BUY;
   GetBasketInfo(totalOrders, totalVol, totalProfit, weightedPrice, basketSide, lastOrderPrice);
   
   // 3. Basket Management & Exit Rules
   if(totalOrders > 0)
   {
      // A. Target Profit
      if(totalProfit >= InpTargetProfitUSD)
      {
         CloseEntireBasket(StringFormat("TARGET_PROFIT (+%.2f USD)", totalProfit));
         return;
      }
      
      // B. Max Loss Floor
      if(totalProfit <= -MathAbs(InpMaxBasketLossUSD))
      {
         CloseEntireBasket(StringFormat("MAX_LOSS_STOP (-%.2f USD)", MathAbs(totalProfit)));
         return;
      }
      
      // C. Structural Invalidation
      if(basketSide == POSITION_TYPE_BUY && g_invalidationLevel > 0.0 && bid <= g_invalidationLevel)
      {
         CloseEntireBasket(StringFormat("BULLISH_INVALIDATION_CUT (Bid <= %.2f)", g_invalidationLevel));
         return;
      }
      if(basketSide == POSITION_TYPE_SELL && g_invalidationLevel > 0.0 && ask >= g_invalidationLevel)
      {
         CloseEntireBasket(StringFormat("BEARISH_INVALIDATION_CUT (Ask >= %.2f)", g_invalidationLevel));
         return;
      }
      
      // D. Smart Averaging Layer Placement
      if(totalOrders < InpMaxLayers)
      {
         double dist = MathAbs((basketSide == POSITION_TYPE_BUY ? ask : bid) - lastOrderPrice);
         double minRequiredDist = atrVal * InpAtrMultiplier;
         
         bool isPullback = false;
         if(basketSide == POSITION_TYPE_BUY && ask <= (lastOrderPrice - minRequiredDist)) isPullback = true;
         if(basketSide == POSITION_TYPE_SELL && bid >= (lastOrderPrice + minRequiredDist)) isPullback = true;
         
         if(isPullback)
         {
            // Check M1 candle bounce
            MqlRates m1Rates[];
            ArraySetAsSeries(m1Rates, true);
            if(CopyRates(_Symbol, PERIOD_M1, 0, 2, m1Rates) >= 2)
            {
               bool isBounce = (basketSide == POSITION_TYPE_BUY && m1Rates[1].close > m1Rates[1].open) ||
                               (basketSide == POSITION_TYPE_SELL && m1Rates[1].close < m1Rates[1].open);
               if(isBounce)
               {
                  double lot = (totalOrders == 1) ? InpBaseLot : (InpBaseLot * 2.0);
                  double sl = (g_invalidationLevel > 0.0) ? g_invalidationLevel : 0.0;
                  
                  if(basketSide == POSITION_TYPE_BUY)
                     trade.Buy(lot, _Symbol, ask, sl, 0, StringFormat("SG-L%d-BUY", totalOrders+1));
                  else
                     trade.Sell(lot, _Symbol, bid, sl, 0, StringFormat("SG-L%d-SELL", totalOrders+1));
               }
            }
         }
      }
   }
   // 4. Initial Entry (Basket Empty)
   else
   {
      if(g_currentRegime == "BULLISH" || g_currentRegime == "BEARISH")
      {
         // M1 trigger confirmation
         MqlRates m1Rates[];
         ArraySetAsSeries(m1Rates, true);
         if(CopyRates(_Symbol, PERIOD_M1, 0, 2, m1Rates) >= 2)
         {
            bool m1Aligned = (g_currentRegime == "BULLISH" && m1Rates[0].close >= m1Rates[0].open) ||
                             (g_currentRegime == "BEARISH" && m1Rates[0].close <= m1Rates[0].open);
            if(m1Aligned && g_invalidationLevel > 0.0)
            {
               if(g_currentRegime == "BULLISH")
                  trade.Buy(InpBaseLot, _Symbol, ask, g_invalidationLevel, 0, "SG-L1-BUY");
               else
                  trade.Sell(InpBaseLot, _Symbol, bid, g_invalidationLevel, 0, "SG-L1-SELL");
            }
         }
      }
   }
   
   // Comment on chart
   string comment = StringFormat("StructureGrid Pro (HH/LL) | Regime: %s\nOrders: %d/%d | Total P/L: $%.2f | Target: +$%.2f | Inval: %.2f",
                                 g_currentRegime, totalOrders, InpMaxLayers, totalProfit, InpTargetProfitUSD, g_invalidationLevel);
   Comment(comment);
}
//+------------------------------------------------------------------+
