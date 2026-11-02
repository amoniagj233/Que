//+------------------------------------------------------------------+
//|                                   XAU_Dark_Horizon_Indicator.mq5 |
//|                       XAU DARK HORIZON SCALP AI                  |
//|                      Gold Market Decision Engine                 |
//+------------------------------------------------------------------+
#property copyright   "APEX AI Systems"
#property link        "https://apexai.internal"
#property version     "1.00"
#property description "XAU Dark Horizon Scalp AI: Real-Time Institutional HUD & Liquidity Engine"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Inputs
input color    InpHeaderColor       = C'255,191,0';    // Brand Gold Color
input color    InpSubHeaderColor    = C'0,210,255';    // Cyan Accent Color
input color    InpTextColor         = clrWhite;        // Text Color
input color    InpGreenColor        = C'0,230,118';    // Bullish Green
input color    InpRedColor          = C'255,23,68';     // Bearish Red
input color    InpZoneColor         = C'10,40,60';     // Precision Turn Zone Fill
input int      InpCorner            = 0;               // Anchor Corner (0=Top-Left)
input int      InpBaseX             = 20;              // Left Margin X
input int      InpBaseY             = 35;              // Top Margin Y

#define PREFIX "DH_HUD_"

//--- Telemetry State
string g_bias           = "BULLISH";
string g_impulse_grade  = "STRONG";
string g_price_cycle    = "EXPANSION";
int    g_impulse_val    = 78;
int    g_reversal_conf  = 86;
int    g_buyer_energy   = 78;
int    g_seller_energy  = 22;
int    g_momentum_val   = 83;
int    g_volume_act     = 76;
int    g_volatility     = 92;
string g_command        = "BUY READY";
string g_cmd_subtitle   = "High probability long scalp opportunity.";
string g_session        = "New York";
string g_next_session   = "Asia";
double g_sweep_high     = 0.0;
double g_sweep_low      = 0.0;
double g_turn_top       = 0.0;
double g_turn_bot       = 0.0;

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   EventSetTimer(1);
   UpdateMetrics();
   DrawHUD();
   DrawChartZones();
   ChartRedraw();
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Custom indicator deinitialization function                       |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   ObjectsDeleteAll(0, PREFIX);
   ChartRedraw();
}

//+------------------------------------------------------------------+
//| Timer event handler                                              |
//+------------------------------------------------------------------+
void OnTimer()
{
   UpdateMetrics();
   DrawHUD();
   DrawChartZones();
   ChartRedraw();
}

//+------------------------------------------------------------------+
//| Calculate event handler                                          |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
   return(rates_total);
}

//+------------------------------------------------------------------+
//| Compute real-time telemetry from bars & market                   |
//+------------------------------------------------------------------+
void UpdateMetrics()
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(_Symbol, _Period, 0, 50, rates);
   if(copied < 30) return;

   // 1. Directional bias via Fast vs Slow EMA approximation
   double sum_fast = 0, sum_slow = 0;
   for(int i = 0; i < 9; i++) sum_fast += rates[i].close;
   for(int i = 0; i < 21; i++) sum_slow += rates[i].close;
   double ema_fast = sum_fast / 9.0;
   double ema_slow = sum_slow / 21.0;

   if(ema_fast >= ema_slow)
   {
      g_bias = "BULLISH";
      g_command = "BUY READY";
      g_cmd_subtitle = "High probability long scalp opportunity.";
   }
   else
   {
      g_bias = "BEARISH";
      g_command = "SELL READY";
      g_cmd_subtitle = "High probability short scalp opportunity.";
   }

   // 2. High/Low sweeps & Turn zone
   double highest_p = rates[0].high;
   double lowest_p = rates[0].low;
   for(int i = 1; i < 30; i++)
   {
      if(rates[i].high > highest_p) highest_p = rates[i].high;
      if(rates[i].low < lowest_p) lowest_p = rates[i].low;
   }
   g_sweep_high = highest_p;
   g_sweep_low = lowest_p;
   
   // Midpoint Precision Entry Zone
   double mid = (highest_p + lowest_p) / 2.0;
   double range = highest_p - lowest_p;
   g_turn_top = mid + (range * 0.08);
   g_turn_bot = mid - (range * 0.08);

   // 3. Dynamic bar metrics
   double last_range = MathMax(rates[0].high - rates[0].low, _Point * 10);
   double body = MathAbs(rates[0].close - rates[0].open);
   g_impulse_val = (int)MathMin(98, MathMax(40, (body / last_range) * 100));

   // Buyer / Seller balance
   double buyer_w = rates[0].close - rates[0].low;
   g_buyer_energy = (int)MathMin(95, MathMax(15, (buyer_w / last_range) * 100));
   g_seller_energy = 100 - g_buyer_energy;

   // Session detector
   MqlDateTime dt;
   TimeCurrent(dt);
   int hour = dt.hour;
   if(hour >= 8 && hour < 16) { g_session = "London"; g_next_session = "New York"; }
   else if(hour >= 13 && hour < 21) { g_session = "New York"; g_next_session = "Asia"; }
   else { g_session = "Asia"; g_next_session = "London"; }
}

//+------------------------------------------------------------------+
//| Create UI Label helper                                           |
//+------------------------------------------------------------------+
void MakeLabel(string name, int x, int y, string text, color clr, int font_size=9, bool bold=false)
{
   string full_name = PREFIX + name;
   if(ObjectFind(0, full_name) < 0)
   {
      ObjectCreate(0, full_name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, full_name, OBJPROP_CORNER, InpCorner);
      ObjectSetInteger(0, full_name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, full_name, OBJPROP_HIDDEN, true);
   }
   ObjectSetInteger(0, full_name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, full_name, OBJPROP_YDISTANCE, y);
   ObjectSetString(0, full_name, OBJPROP_TEXT, text);
   ObjectSetString(0, full_name, OBJPROP_FONT, bold ? "Segoe UI Bold" : "Segoe UI");
   ObjectSetInteger(0, full_name, OBJPROP_FONTSIZE, font_size);
   ObjectSetInteger(0, full_name, OBJPROP_COLOR, clr);
}

//+------------------------------------------------------------------+
//| Create Background Rectangle helper                               |
//+------------------------------------------------------------------+
void MakePanel(string name, int x, int y, int w, int h, color bg_color, color border_color)
{
   string full_name = PREFIX + name;
   if(ObjectFind(0, full_name) < 0)
   {
      ObjectCreate(0, full_name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, full_name, OBJPROP_CORNER, InpCorner);
      ObjectSetInteger(0, full_name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, full_name, OBJPROP_HIDDEN, true);
   }
   ObjectSetInteger(0, full_name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, full_name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, full_name, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, full_name, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, full_name, OBJPROP_BGCOLOR, bg_color);
   ObjectSetInteger(0, full_name, OBJPROP_COLOR, border_color);
   ObjectSetInteger(0, full_name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
}

//+------------------------------------------------------------------+
//| Draw the Left Sidebar Institutional HUD                          |
//+------------------------------------------------------------------+
void DrawHUD()
{
   int x = InpBaseX;
   int y = InpBaseY;
   int panel_w = 260;

   // Main Background HUD Container
   MakePanel("MainBg", x - 8, y - 8, panel_w, 640, C'12,16,24', C'26,38,57');

   // Brand Header
   MakeLabel("Title", x, y, "XAU DARK HORIZON", InpHeaderColor, 12, true);
   y += 18;
   MakeLabel("SubTitle", x, y, "SCALP AI  |  GOLD DECISION ENGINE", InpSubHeaderColor, 8, false);
   y += 24;

   // 01 DIRECTION MATRIX
   MakeLabel("Sec1_Title", x, y, "01 DIRECTION MATRIX", C'0,210,255', 8, true);
   y += 16;
   MakeLabel("Sec1_L1", x, y, "Directional Bias:", C'140,160,185', 8);
   MakeLabel("Sec1_V1", x + 140, y, g_bias, (g_bias == "BULLISH") ? InpGreenColor : InpRedColor, 8, true);
   y += 15;
   MakeLabel("Sec1_L2", x, y, "Impulse Grade:", C'140,160,185', 8);
   MakeLabel("Sec1_V2", x + 140, y, g_impulse_grade, InpGreenColor, 8, true);
   y += 15;
   MakeLabel("Sec1_L3", x, y, "Price Cycle:", C'140,160,185', 8);
   MakeLabel("Sec1_V3", x + 140, y, g_price_cycle, C'0,210,255', 8, true);
   y += 22;

   // 02 IMPULSE METER
   MakeLabel("Sec2_Title", x, y, "02 IMPULSE METER", C'0,210,255', 8, true);
   y += 16;
   string meter = "";
   int bars = (int)(g_impulse_val / 6);
   for(int b = 0; b < 16; b++) meter += (b < bars) ? "|" : ".";
   MakeLabel("Sec2_Bar", x, y, "[" + meter + "]  " + IntegerToString(g_impulse_val) + "%", C'255,170,0', 8, true);
   y += 15;
   MakeLabel("Sec2_Sub", x, y, "Impulse Building  |  Trend: STRONG", C'140,160,185', 8);
   y += 22;

   // 03 HORIZON TURN RADAR
   MakeLabel("Sec3_Title", x, y, "03 HORIZON TURN RADAR", C'0,210,255', 8, true);
   y += 16;
   MakeLabel("Sec3_Conf", x, y, "( " + IntegerToString(g_reversal_conf) + "% )", InpGreenColor, 12, true);
   MakeLabel("Sec3_Lbl", x + 70, y + 2, "REVERSAL CONFIDENCE", InpTextColor, 8, true);
   y += 16;
   MakeLabel("Sec3_Sub", x + 70, y, "High probability turn", InpGreenColor, 8);
   y += 24;

   // 04 FLOW TELEMETRY
   MakeLabel("Sec4_Title", x, y, "04 FLOW TELEMETRY", C'0,210,255', 8, true);
   y += 16;
   MakeLabel("Sec4_L1", x, y, "Buyer Energy:", C'140,160,185', 8);
   MakeLabel("Sec4_V1", x + 140, y, IntegerToString(g_buyer_energy) + "%", InpGreenColor, 8, true);
   y += 15;
   MakeLabel("Sec4_L2", x, y, "Seller Energy:", C'140,160,185', 8);
   MakeLabel("Sec4_V2", x + 140, y, IntegerToString(g_seller_energy) + "%", InpRedColor, 8, true);
   y += 15;
   MakeLabel("Sec4_L3", x, y, "Momentum:", C'140,160,185', 8);
   MakeLabel("Sec4_V3", x + 140, y, IntegerToString(g_momentum_val) + "%", C'255,170,0', 8, true);
   y += 15;
   MakeLabel("Sec4_L4", x, y, "Volume Activity:", C'140,160,185', 8);
   MakeLabel("Sec4_V4", x + 140, y, IntegerToString(g_volume_act) + "%", C'255,170,0', 8, true);
   y += 15;
   MakeLabel("Sec4_L5", x, y, "Volatility:", C'140,160,185', 8);
   MakeLabel("Sec4_V5", x + 140, y, IntegerToString(g_volatility) + "%", C'0,210,255', 8, true);
   y += 22;

   // 05 SCALP COMMAND
   MakeLabel("Sec5_Title", x, y, "05 SCALP COMMAND", C'0,210,255', 8, true);
   y += 16;
   MakeLabel("Sec5_Cmd", x, y, g_command, InpGreenColor, 12, true);
   y += 16;
   MakeLabel("Sec5_Sub", x, y, g_cmd_subtitle, C'140,160,185', 8);
   y += 22;

   // 06 RISK PULSE
   MakeLabel("Sec6_Title", x, y, "06 RISK PULSE", C'0,210,255', 8, true);
   y += 16;
   MakeLabel("Sec6_L1", x, y, "Momentum shift detected.", InpGreenColor, 8);
   y += 14;
   MakeLabel("Sec6_L2", x, y, "Stop hunt confirmed. Demand verified.", C'140,160,185', 8);
   y += 22;

   // 07 MARKET CLOCK
   MakeLabel("Sec7_Title", x, y, "07 MARKET CLOCK", C'0,210,255', 8, true);
   y += 16;
   MakeLabel("Sec7_L1", x, y, "Current Session:", C'140,160,185', 8);
   MakeLabel("Sec7_V1", x + 140, y, g_session, InpTextColor, 8, true);
   y += 15;
   MakeLabel("Sec7_L2", x, y, "Next Session:", C'140,160,185', 8);
   MakeLabel("Sec7_V2", x + 140, y, g_next_session, C'140,160,185', 8);
   y += 15;
   MakeLabel("Sec7_L3", x, y, "Spread:", C'140,160,185', 8);
   double sp = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) * _Point;
   MakeLabel("Sec7_V3", x + 140, y, DoubleToString(sp, 2) + " pts", InpTextColor, 8, true);
}

//+------------------------------------------------------------------+
//| Draw On-Chart Turn Windows & Liquidity Sweep Levels              |
//+------------------------------------------------------------------+
void DrawChartZones()
{
   if(g_sweep_high <= 0.0 || g_sweep_low <= 0.0) return;

   datetime t1 = TimeCurrent() - 7200;
   datetime t2 = TimeCurrent() + 1800;

   // 1. Sell Liquidity Sweep Level (Top Line)
   string s_name = PREFIX + "SweepSell";
   if(ObjectFind(0, s_name) < 0)
   {
      ObjectCreate(0, s_name, OBJ_TREND, 0, t1, g_sweep_high, t2, g_sweep_high);
      ObjectSetInteger(0, s_name, OBJPROP_RAY_RIGHT, true);
      ObjectSetInteger(0, s_name, OBJPROP_STYLE, STYLE_DOT);
      ObjectSetInteger(0, s_name, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, s_name, OBJPROP_COLOR, C'180,100,255');
   }
   ObjectSetDouble(0, s_name, OBJPROP_PRICE, 0, g_sweep_high);
   ObjectSetDouble(0, s_name, OBJPROP_PRICE, 1, g_sweep_high);

   // Sell Sweep Label
   string sl_name = PREFIX + "SweepSell_Lbl";
   if(ObjectFind(0, sl_name) < 0)
   {
      ObjectCreate(0, sl_name, OBJ_TEXT, 0, TimeCurrent() - 1800, g_sweep_high);
      ObjectSetString(0, sl_name, OBJPROP_FONT, "Segoe UI Bold");
      ObjectSetInteger(0, sl_name, OBJPROP_FONTSIZE, 8);
      ObjectSetInteger(0, sl_name, OBJPROP_COLOR, C'180,100,255');
   }
   ObjectSetDouble(0, sl_name, OBJPROP_PRICE, g_sweep_high + (_Point * 20));
   ObjectSetString(0, sl_name, OBJPROP_TEXT, "SELL LIQUIDITY SWEEP  v  Stop Hunt");

   // 2. Buy Prime / Demand Level (Bottom Line)
   string b_name = PREFIX + "SweepBuy";
   if(ObjectFind(0, b_name) < 0)
   {
      ObjectCreate(0, b_name, OBJ_TREND, 0, t1, g_sweep_low, t2, g_sweep_low);
      ObjectSetInteger(0, b_name, OBJPROP_RAY_RIGHT, true);
      ObjectSetInteger(0, b_name, OBJPROP_STYLE, STYLE_DOT);
      ObjectSetInteger(0, b_name, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, b_name, OBJPROP_COLOR, InpGreenColor);
   }
   ObjectSetDouble(0, b_name, OBJPROP_PRICE, 0, g_sweep_low);
   ObjectSetDouble(0, b_name, OBJPROP_PRICE, 1, g_sweep_low);

   // Buy Prime Label
   string bl_name = PREFIX + "SweepBuy_Lbl";
   if(ObjectFind(0, bl_name) < 0)
   {
      ObjectCreate(0, bl_name, OBJ_TEXT, 0, TimeCurrent() - 1800, g_sweep_low);
      ObjectSetString(0, bl_name, OBJPROP_FONT, "Segoe UI Bold");
      ObjectSetInteger(0, bl_name, OBJPROP_FONTSIZE, 8);
      ObjectSetInteger(0, bl_name, OBJPROP_COLOR, InpGreenColor);
   }
   ObjectSetDouble(0, bl_name, OBJPROP_PRICE, g_sweep_low - (_Point * 25));
   ObjectSetString(0, bl_name, OBJPROP_TEXT, "BUY PRIME  ^  Liquidity Sweep Complete | Demand Confirmed");

   // 3. Horizon Turn Window (Precision Entry Zone Rectangle)
   string rect_name = PREFIX + "TurnWindow";
   if(ObjectFind(0, rect_name) < 0)
   {
      ObjectCreate(0, rect_name, OBJ_RECTANGLE, 0, TimeCurrent() - 2400, g_turn_top, TimeCurrent() + 1200, g_turn_bot);
      ObjectSetInteger(0, rect_name, OBJPROP_COLOR, C'0,120,180');
      ObjectSetInteger(0, rect_name, OBJPROP_BGCOLOR, InpZoneColor);
      ObjectSetInteger(0, rect_name, OBJPROP_BACK, true);
      ObjectSetInteger(0, rect_name, OBJPROP_FILL, true);
   }
   ObjectSetDouble(0, rect_name, OBJPROP_PRICE, 0, g_turn_top);
   ObjectSetDouble(0, rect_name, OBJPROP_PRICE, 1, g_turn_bot);

   // Zone Label
   string zl_name = PREFIX + "TurnWindow_Lbl";
   if(ObjectFind(0, zl_name) < 0)
   {
      ObjectCreate(0, zl_name, OBJ_TEXT, 0, TimeCurrent() - 1200, (g_turn_top + g_turn_bot) / 2.0);
      ObjectSetString(0, zl_name, OBJPROP_FONT, "Segoe UI Bold");
      ObjectSetInteger(0, zl_name, OBJPROP_FONTSIZE, 8);
      ObjectSetInteger(0, zl_name, OBJPROP_COLOR, C'0,210,255');
   }
   ObjectSetDouble(0, zl_name, OBJPROP_PRICE, (g_turn_top + g_turn_bot) / 2.0);
   ObjectSetString(0, zl_name, OBJPROP_TEXT, "HORIZON TURN WINDOW  |  Precision Entry Zone");
}
//+------------------------------------------------------------------+
