//+------------------------------------------------------------------+
//|                                     CRT_Gold_Pro_Indicator.mq5   |
//|                    Candle Range Theory (CRT) Synchronized Live   |
//|               Visualizes Python Bot Strategy & MT5 Execution     |
//+------------------------------------------------------------------+
#property copyright   "APEX AI Systems"
#property link        "https://apexai.internal"
#property version     "1.00"
#property description "CRT Gold Pro: Synchronized M30 Range, M5 Sweep, M2 Engulfing & Live Trades"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//--- Input parameters
input string   InpSharedStateFile = "crt_gold_pro_state.json"; // Shared JSON File (FILE_COMMON)
input color    InpRangeHighColor  = clrYellow;                // CRT High Color
input color    InpRangeLowColor   = clrYellow;                // CRT Low Color
input color    InpMidpointColor   = clrWhite;                 // CRT Midpoint Color
input color    InpRangeFillColor  = C'20,30,45';              // CRT Box Shading Color
input color    InpBuyColor        = clrLimeGreen;             // Bullish Setup / Buy Color
input color    InpSellColor       = clrRed;                   // Bearish Setup / Sell Color
input int      InpCorner          = 0;                        // Dashboard Corner (0=Top-Left)
input int      InpXOffset         = 20;                       // Dashboard X Offset
input int      InpYOffset         = 40;                       // Dashboard Y Offset

//--- Constants
#define PREFIX "CRT_PRO_"

//--- State cache
string   g_bot_status     = "INITIALIZING";
string   g_state          = "WAITING_FOR_RANGE";
string   g_symbol         = "XAUUSD";
int      g_magic          = 9090;
double   g_crt_high       = 0.0;
double   g_crt_low        = 0.0;
double   g_crt_mid        = 0.0;
bool     g_range_active   = false;
datetime g_range_t1       = 0;
datetime g_range_t2       = 0;

bool     g_sweep_active   = false;
string   g_sweep_dir      = "";
double   g_sweep_price    = 0.0;

bool     g_signal_ready   = false;
string   g_sig_dir        = "";
double   g_sig_entry      = 0.0;
double   g_sig_sl         = 0.0;
double   g_sig_tp1        = 0.0;
double   g_sig_tp2        = 0.0;

bool     g_pos_active     = false;
long     g_pos_ticket     = 0;
string   g_pos_dir        = "";
double   g_pos_volume     = 0.0;
double   g_pos_entry      = 0.0;
double   g_pos_sl         = 0.0;
double   g_pos_tp2        = 0.0;
double   g_pos_pnl        = 0.0;
bool     g_tp1_reached    = false;

datetime g_last_sync_time = 0;
int      g_sync_countdown = 10;

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   EventSetTimer(1); // 1-second refresh timer for smooth live synchronization
   ReadSharedState();
   DrawDashboard();
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
//| Custom indicator iteration function                              |
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
//| Timer event function: Read Python State every second             |
//+------------------------------------------------------------------+
void OnTimer()
{
   ReadSharedState();
   UpdateChartVisuals();
   DrawDashboard();
   ChartRedraw();
}

//+------------------------------------------------------------------+
//| Simple JSON string value extractor                               |
//+------------------------------------------------------------------+
string ExtractJsonString(const string &json, const string key)
{
   string pattern = "\"" + key + "\":";
   int pos = StringFind(json, pattern);
   if(pos < 0) return "";
   pos += StringLen(pattern);
   while(pos < StringLen(json) && (StringGetCharacter(json, pos) == ' ' || StringGetCharacter(json, pos) == '\"')) pos++;
   int end = pos;
   while(end < StringLen(json) && StringGetCharacter(json, end) != '\"' && StringGetCharacter(json, end) != ',' && StringGetCharacter(json, end) != '}') end++;
   return StringSubstr(json, pos, end - pos);
}

double ExtractJsonNumber(const string &json, const string key)
{
   string val = ExtractJsonString(json, key);
   if(val == "") return 0.0;
   return StringToDouble(val);
}

bool ExtractJsonBool(const string &json, const string key)
{
   string val = ExtractJsonString(json, key);
   return (val == "true" || val == "True" || val == "1");
}

//+------------------------------------------------------------------+
//| Read Shared State from MT5 Common Files                          |
//+------------------------------------------------------------------+
void ReadSharedState()
{
   int handle = FileOpen(InpSharedStateFile, FILE_READ | FILE_TXT | FILE_COMMON);
   if(handle == INVALID_HANDLE)
   {
      g_sync_countdown--;
      if(g_sync_countdown <= 0)
         g_bot_status = "FILE_WAITING";
      return;
   }

   string content = "";
   while(!FileIsEnding(handle))
   {
      content += FileReadString(handle);
   }
   FileClose(handle);

   if(content == "") return;

   g_last_sync_time = TimeCurrent();
   g_bot_status     = ExtractJsonString(content, "bot_status");
   g_state          = ExtractJsonString(content, "state");
   g_symbol         = ExtractJsonString(content, "symbol");
   g_magic          = (int)ExtractJsonNumber(content, "magic");

   // Parse Range
   g_range_active   = ExtractJsonBool(content, "active");
   g_crt_high       = ExtractJsonNumber(content, "high");
   g_crt_low        = ExtractJsonNumber(content, "low");
   g_crt_mid        = ExtractJsonNumber(content, "midpoint");

   // Parse Sweep
   g_sweep_active   = ExtractJsonBool(content, "confirmed");
   g_sweep_dir      = ExtractJsonString(content, "direction");
   g_sweep_price    = ExtractJsonNumber(content, "sweep_price");

   // Parse Signal
   g_signal_ready   = ExtractJsonBool(content, "ready");
   g_sig_dir        = ExtractJsonString(content, "direction");
   g_sig_entry      = ExtractJsonNumber(content, "planned_entry");
   g_sig_tp1        = ExtractJsonNumber(content, "planned_tp1");
   g_sig_tp2        = ExtractJsonNumber(content, "planned_tp2");

   // Parse Position
   g_pos_active     = ExtractJsonBool(content, "active");
   g_pos_ticket     = (long)ExtractJsonNumber(content, "ticket");
   g_pos_dir        = ExtractJsonString(content, "direction");
   g_pos_volume     = ExtractJsonNumber(content, "volume");
   g_pos_entry      = ExtractJsonNumber(content, "entry_price");
   g_pos_sl         = ExtractJsonNumber(content, "sl");
   g_pos_tp2        = ExtractJsonNumber(content, "tp2");
   g_pos_pnl        = ExtractJsonNumber(content, "floating_pnl");
   g_tp1_reached    = ExtractJsonBool(content, "tp1_reached");
}

//+------------------------------------------------------------------+
//| Draw or Update M30 Range, Sweep, Signals & Live Position Lines   |
//+------------------------------------------------------------------+
void UpdateChartVisuals()
{
   datetime t_now = TimeCurrent();
   datetime t_start = t_now - 14400; // 4 hours back for horizontal bounds

   // 1. Draw Reference Range
   if(g_crt_high > 0 && g_crt_low > 0)
   {
      // High Line
      CreateHLine(PREFIX + "CRT_HIGH", g_crt_high, InpRangeHighColor, STYLE_SOLID, 2);
      CreateText(PREFIX + "CRT_HIGH_LBL", t_now, g_crt_high, " CRT HIGH — " + DoubleToString(g_crt_high, 2), InpRangeHighColor);

      // Low Line
      CreateHLine(PREFIX + "CRT_LOW", g_crt_low, InpRangeLowColor, STYLE_SOLID, 2);
      CreateText(PREFIX + "CRT_LOW_LBL", t_now, g_crt_low, " CRT LOW — " + DoubleToString(g_crt_low, 2), InpRangeLowColor);

      // Midpoint Line
      CreateHLine(PREFIX + "CRT_MID", g_crt_mid, InpMidpointColor, STYLE_DASH, 1);
      CreateText(PREFIX + "CRT_MID_LBL", t_now, g_crt_mid, " CRT MIDPOINT — " + DoubleToString(g_crt_mid, 2), InpMidpointColor);
   }

   // 2. Draw Sweep Marker
   if(g_sweep_active && g_sweep_price > 0)
   {
      color sw_col = (g_sweep_dir == "BULLISH") ? InpBuyColor : InpSellColor;
      string sw_lbl = (g_sweep_dir == "BULLISH") ? "BULLISH CRT SWEEP (" + DoubleToString(g_sweep_price, 2) + ")" : "BEARISH CRT SWEEP (" + DoubleToString(g_sweep_price, 2) + ")";
      CreateText(PREFIX + "SWEEP_TAG", t_now - 300, g_sweep_price, sw_lbl, sw_col, 10);
   }

   // 3. Draw Live Real-Position Lines (Verified MT5 Execution)
   if(g_pos_active && g_pos_entry > 0)
   {
      color pos_col = (g_pos_dir == "BUY") ? clrDeepSkyBlue : clrOrangeRed;
      CreateHLine(PREFIX + "LIVE_ENTRY", g_pos_entry, pos_col, STYLE_SOLID, 2);
      
      string pnl_str = (g_pos_pnl >= 0 ? "+$" : "-$") + DoubleToString(MathAbs(g_pos_pnl), 2);
      CreateText(PREFIX + "LIVE_ENTRY_LBL", t_now, g_pos_entry, " LIVE " + g_pos_dir + " #" + IntegerToString(g_pos_ticket) + " (" + pnl_str + ")", pos_col, 9);

      if(g_pos_sl > 0)
      {
         CreateHLine(PREFIX + "LIVE_SL", g_pos_sl, clrCrimson, STYLE_DOT, 2);
         CreateText(PREFIX + "LIVE_SL_LBL", t_now, g_pos_sl, " LIVE SL: " + DoubleToString(g_pos_sl, 2), clrCrimson, 8);
      }

      if(g_pos_tp2 > 0)
      {
         CreateHLine(PREFIX + "LIVE_TP2", g_pos_tp2, clrLimeGreen, STYLE_DOT, 2);
         CreateText(PREFIX + "LIVE_TP2_LBL", t_now, g_pos_tp2, " LIVE TP2: " + DoubleToString(g_pos_tp2, 2), clrLimeGreen, 8);
      }
   }
   else
   {
      ObjectDelete(0, PREFIX + "LIVE_ENTRY");
      ObjectDelete(0, PREFIX + "LIVE_ENTRY_LBL");
      ObjectDelete(0, PREFIX + "LIVE_SL");
      ObjectDelete(0, PREFIX + "LIVE_SL_LBL");
      ObjectDelete(0, PREFIX + "LIVE_TP2");
      ObjectDelete(0, PREFIX + "LIVE_TP2_LBL");
   }
}

//+------------------------------------------------------------------+
//| Draw On-Chart HUD Information Dashboard                          |
//+------------------------------------------------------------------+
void DrawDashboard()
{
   int x = InpXOffset;
   int y = InpYOffset;
   int rowH = 16;
   int w = 270;
   int totalRows = 13;

   // Background Box
   string bgName = PREFIX + "HUD_BG";
   if(ObjectFind(0, bgName) < 0)
   {
      ObjectCreate(0, bgName, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, bgName, OBJPROP_CORNER, InpCorner);
      ObjectSetInteger(0, bgName, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, bgName, OBJPROP_YDISTANCE, y);
      ObjectSetInteger(0, bgName, OBJPROP_XSIZE, w);
      ObjectSetInteger(0, bgName, OBJPROP_YSIZE, totalRows * rowH + 20);
      ObjectSetInteger(0, bgName, OBJPROP_BGCOLOR, C'12,18,28');
      ObjectSetInteger(0, bgName, OBJPROP_BORDER_TYPE, BORDER_FLAT);
      ObjectSetInteger(0, bgName, OBJPROP_COLOR, C'40,60,85');
      ObjectSetInteger(0, bgName, OBJPROP_WIDTH, 1);
      ObjectSetInteger(0, bgName, OBJPROP_BACK, false);
      ObjectSetInteger(0, bgName, OBJPROP_SELECTABLE, false);
   }

   // Title
   DrawLabel(PREFIX + "HUD_TITLE", x + 10, y + 8, "CRT GOLD PRO — LIVE STATUS", clrGold, 10, true);

   // Status rows
   int r = 1;
   DrawHUDRow(r++, "Symbol / Timeframe:", _Symbol + " (" + EnumToString(_Period) + ")", clrWhite);
   
   color st_col = (g_state == "POSITION_ACTIVE") ? clrLimeGreen : ((g_state == "SWEEP_CONFIRMED") ? clrYellow : clrDeepSkyBlue);
   DrawHUDRow(r++, "Bot Status / State:", g_bot_status + " | " + g_state, st_col);
   DrawHUDRow(r++, "Reference High (M30):", DoubleToString(g_crt_high, 2), InpRangeHighColor);
   DrawHUDRow(r++, "Reference Low (M30):", DoubleToString(g_crt_low, 2), InpRangeLowColor);
   DrawHUDRow(r++, "Range Midpoint (TP1):", DoubleToString(g_crt_mid, 2), InpMidpointColor);
   
   string sw_stat = g_sweep_active ? ("CONFIRMED (" + g_sweep_dir + ")") : "WAITING";
   DrawHUDRow(r++, "M5 Liquidity Sweep:", sw_stat, g_sweep_active ? clrLimeGreen : clrLightGray);

   string conf_stat = g_signal_ready ? ("READY (" + g_sig_dir + ")") : "SCANNING";
   DrawHUDRow(r++, "M2 Engulfing Confirm:", conf_stat, g_signal_ready ? clrLimeGreen : clrLightGray);

   string pos_stat = g_pos_active ? (g_pos_dir + " #" + IntegerToString(g_pos_ticket) + " (" + DoubleToString(g_pos_pnl, 2) + " USD)") : "NONE";
   DrawHUDRow(r++, "Active Trade Position:", pos_stat, g_pos_active ? (g_pos_pnl >= 0 ? clrLimeGreen : clrRed) : clrLightGray);

   DrawHUDRow(r++, "Magic Number:", IntegerToString(g_magic), clrCyan);
   DrawHUDRow(r++, "Risk Gate / Per Trade:", "0.25% Equity", clrWhite);
   
   bool is_synced = (TimeCurrent() - g_last_sync_time < 5);
   DrawHUDRow(r++, "Indicator Synchronization:", is_synced ? "LIVE (FILE_COMMON)" : "DATA_STALE", is_synced ? clrLimeGreen : clrRed);
}

void DrawHUDRow(int rowIdx, string label, string value, color valColor)
{
   int x = InpXOffset + 10;
   int y = InpYOffset + 12 + rowIdx * 16;
   DrawLabel(PREFIX + "LBL_" + IntegerToString(rowIdx), x, y, label, C'160,175,195', 8, false);
   DrawLabel(PREFIX + "VAL_" + IntegerToString(rowIdx), x + 135, y, value, valColor, 8, true);
}

void DrawLabel(string name, int x, int y, string text, color clr, int fontSize, bool isBold)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, InpCorner);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   }
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetString(0, name, OBJPROP_FONT, isBold ? "Segoe UI Bold" : "Segoe UI");
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fontSize);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
}

void CreateHLine(string name, double price, color clr, ENUM_LINE_STYLE style, int width)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   }
   ObjectSetDouble(0, name, OBJPROP_PRICE, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, style);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, width);
}

void CreateText(string name, datetime time, double price, string text, color clr, int fontSize=8)
{
   if(ObjectFind(0, name) < 0)
   {
      ObjectCreate(0, name, OBJ_TEXT, 0, time, price);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   }
   ObjectSetDouble(0, name, OBJPROP_PRICE, price);
   ObjectSetInteger(0, name, OBJPROP_TIME, time);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetString(0, name, OBJPROP_FONT, "Segoe UI Bold");
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, fontSize);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
}
//+------------------------------------------------------------------+
