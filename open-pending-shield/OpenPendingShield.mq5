#property strict
#property version "1.00"
#property description "Original pending breakout EA. No expiry, licensing, network activation or account lock."
#include <Trade/Trade.mqh>

input bool EnableTrading=false;
input bool AllowNewEntries=true; // False retains management and cancels owned pending orders
input ulong Magic=2026102201;
input double Lots=0.01;
input bool EnableBuy=true;
input bool EnableSell=true;
input double EntryDistance=1.0;       // Symbol price units, not points or dollars of P/L
input double StopDistance=0.9;
input double TakeProfitDistance=1.1;
input bool UseATR=false;
input ENUM_TIMEFRAMES ATRTimeframe=PERIOD_M15;
input int ATRPeriod=14;
input double ATRMultiplier=1.5;
input double MaxEntryDistance=5.0;
input double MaxSpread=2.0;
input double MaxSpreadEntryRatio=0.25;
input double MaxCombinedRiskPercent=1.0; // Estimated SL loss across BOTH pending legs
input double DailyEquityLossPercent=5.0; // Account equity from first observation each broker day
input double TrailStart=0.6;
input double TrailDistance=0.5;
input double RepriceThreshold=0.2;
input int RepriceSeconds=5;
input int EntryCooldownSeconds=60;
input int PendingLifetimeSeconds=120;
input ulong SlippagePoints=20;
input bool ClearExecutionHalt=false; // Only after manually reconciling broker orders/history

CTrade trade;
int atr=INVALID_HANDLE;
datetime last_refresh=0, flat_since=0;
bool had_position=false, busy=false, halted=false;
string state="Starting", key, day_key;
string last_state="";
double day_equity=0;
int day_stamp=0;
int instance_lock=INVALID_HANDLE;
bool day_latched=false;

double TickSize(){return SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);}
double RoundUp(double p){return NormalizeDouble(MathCeil(p/TickSize()-1e-8)*TickSize(),_Digits);}
double RoundDown(double p){return NormalizeDouble(MathFloor(p/TickSize()+1e-8)*TickSize(),_Digits);}
bool OwnOrder(){return OrderGetString(ORDER_SYMBOL)==_Symbol && (ulong)OrderGetInteger(ORDER_MAGIC)==Magic;}
bool OwnPosition(){return PositionGetString(POSITION_SYMBOL)==_Symbol && (ulong)PositionGetInteger(POSITION_MAGIC)==Magic;}
int OwnPositions(){int n=0;for(int i=PositionsTotal()-1;i>=0;i--){if(PositionGetTicket(i)>0 && OwnPosition())n++;}return n;}
int OwnOrders(){int n=0;for(int i=OrdersTotal()-1;i>=0;i--){if(OrderGetTicket(i)>0 && OwnOrder())n++;}return n;}

void Halt(string reason)
{
   halted=true; state=reason;
   if(!MQLInfoInteger(MQL_TESTER))GlobalVariableSet(key+".halt",1);
   Print("EXECUTION HALTED: ",reason,". Reconcile broker history before ClearExecutionHalt.");
}
bool ResultOK(bool sent,string operation)
{
   uint r=trade.ResultRetcode();
   if(sent && (r==TRADE_RETCODE_DONE || r==TRADE_RETCODE_PLACED || r==TRADE_RETCODE_NO_CHANGES))return true;
   if(r==TRADE_RETCODE_MARKET_CLOSED || r==TRADE_RETCODE_PRICE_OFF)
   {
      // Explicit rejection, no order accepted: wait before checking the session again.
      flat_since=TimeCurrent();state="Waiting for broker session/quotes";return false;
   }
   if(r==TRADE_RETCODE_FROZEN || (operation=="Trail position" && r==TRADE_RETCODE_INVALID_STOPS))
   {
      // Explicit no-change rejection. Retain existing protection; reconcile on next quote.
      state="Broker freeze/stop distance: existing protection retained";return false;
   }
   Halt(operation+": "+IntegerToString((int)r)+" "+trade.ResultRetcodeDescription());
   return false; // Never retry a potentially accepted order blindly
}
bool CancelPending()
{
   bool ok=true;
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=OrderGetTicket(i);
      if(ticket>0 && OwnOrder())
         if(!ResultOK(trade.OrderDelete(ticket),"Delete pending"))ok=false;
   }
   return ok && OwnOrders()==0;
}
void UpdateDay()
{
   MqlDateTime dt; TimeToStruct(TimeCurrent(),dt);
   int stamp=dt.year*10000+dt.mon*100+dt.day;
   if(stamp==day_stamp)return;
   day_stamp=stamp;
   day_latched=false;
   day_key=key+".day."+IntegerToString(stamp);
   if(!MQLInfoInteger(MQL_TESTER) && GlobalVariableCheck(day_key))day_equity=GlobalVariableGet(day_key);
   else
   {
      day_equity=AccountInfoDouble(ACCOUNT_EQUITY);
      if(!MQLInfoInteger(MQL_TESTER))GlobalVariableSet(day_key,day_equity);
   }
   if(!MQLInfoInteger(MQL_TESTER))day_latched=GlobalVariableCheck(day_key+".stop");
}
bool DailyBlocked()
{
   UpdateDay();
   if(day_equity<=0 || AccountInfoDouble(ACCOUNT_EQUITY)<=day_equity*(1-DailyEquityLossPercent/100.0))
   {
      day_latched=true;
      if(!MQLInfoInteger(MQL_TESTER))GlobalVariableSet(day_key+".stop",1);
   }
   return day_latched;
}
double BrokerGap()
{
   return (MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                   SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))+2)*_Point+TickSize();
}
bool SessionOpen()
{
   MqlDateTime now;TimeToStruct(TimeCurrent(),now);
   int sec=now.hour*3600+now.min*60+now.sec;
   datetime from,to;
   for(uint i=0;SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)now.day_of_week,i,from,to);i++)
   {
      int a=(int)from%86400,b=(int)to%86400;
      if(a==b || (a<b && sec>=a && sec<b) || (a>b && (sec>=a || sec<b)))return true;
   }
   return false;
}
void TrailPositions()
{
   MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
   double gap=MathMax(TrailDistance,BrokerGap());
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);if(ticket==0 || !OwnPosition())continue;
      bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
      double open=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
      if(sl<=0){Halt("Owned position has no stop loss");continue;}
      double freeze=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL)*_Point+TickSize();
      double mark=buy?q.bid:q.ask;
      if(MathAbs(mark-sl)<=freeze || (tp>0 && MathAbs(tp-mark)<=freeze))continue;
      double movement=buy ? q.bid-open : open-q.ask;
      if(movement<TrailStart)continue;
      double next=buy ? RoundDown(q.bid-gap) : RoundUp(q.ask+gap);
      if((buy && next>sl+TickSize()) || (!buy && next<sl-TickSize()))
         ResultOK(trade.PositionModify(ticket,next,tp),"Trail position");
   }
}
bool ForeignSymbolExposure()
{
   // Especially necessary on netting accounts: foreign trades would merge ownership.
   for(int i=PositionsTotal()-1;i>=0;i--)
      if(PositionGetTicket(i)>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && !OwnPosition())return true;
   for(int i=OrdersTotal()-1;i>=0;i--)
      if(OrderGetTicket(i)>0 && OrderGetString(ORDER_SYMBOL)==_Symbol && !OwnOrder())return true;
   return false;
}
bool VolumeValid()
{
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   return step>0 && Lots>=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)-1e-9 &&
          Lots<=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX)+1e-9 && MathAbs(Lots/step-MathRound(Lots/step))<1e-7;
}
bool RiskAllowed(double buy,double buy_sl,double sell,double sell_sl)
{
   double loss=0,p=0,margin=0,m=0;
   if(EnableBuy)
   {
      if(!OrderCalcProfit(ORDER_TYPE_BUY,_Symbol,Lots,buy,buy_sl,p) || p>=0)return false;
      loss-=p;
      if(!OrderCalcMargin(ORDER_TYPE_BUY,_Symbol,Lots,buy,m))return false;
      margin+=m;
   }
   if(EnableSell)
   {
      if(!OrderCalcProfit(ORDER_TYPE_SELL,_Symbol,Lots,sell,sell_sl,p) || p>=0)return false;
      loss-=p;
      if(!OrderCalcMargin(ORDER_TYPE_SELL,_Symbol,Lots,sell,m))return false;
      margin+=m;
   }
   return loss<=AccountInfoDouble(ACCOUNT_EQUITY)*MaxCombinedRiskPercent/100.0 && margin<AccountInfoDouble(ACCOUNT_MARGIN_FREE)*0.9;
}
void Cycle()
{
   if(!EnableTrading){state="Disabled: EnableTrading=false";return;}
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED) ||
      !AccountInfoInteger(ACCOUNT_TRADE_ALLOWED) || !AccountInfoInteger(ACCOUNT_TRADE_EXPERT))
      {state="Trading permission unavailable";return;}
   int positions=OwnPositions();
   if(positions>0)
   {
      DailyBlocked(); // Latch breach even if equity later recovers before the position closes.
      had_position=true;CancelPending();TrailPositions();
      if(!halted)state="Managing position; opposite pending cancelled";
      return;
   }
   if(had_position){had_position=false;flat_since=TimeCurrent();}
   if(halted){CancelPending();state="Execution halted: reconcile and restart with ClearExecutionHalt";return;}
   if(!AllowNewEntries){CancelPending();state="Entries paused; position management enabled";return;}
   if(DailyBlocked()){CancelPending();state="Daily equity loss guard: entries stopped";return;}
   if(ForeignSymbolExposure()){CancelPending();state="Other strategy/manual exposure on this symbol";return;}
   if(TimeCurrent()-flat_since<EntryCooldownSeconds){state="Entry cooldown";return;}
   if(TimeCurrent()-last_refresh<RepriceSeconds)return;
   last_refresh=TimeCurrent();
   if(!SessionOpen()){state="Outside broker trading session";return;}
   MqlTick q;
   if(!SymbolInfoTick(_Symbol,q) || q.ask<=0 || q.bid<=0 || q.ask<q.bid || TimeCurrent()-q.time>10)
      {CancelPending();state="Invalid or stale quote";return;}
   double distance=EntryDistance;
   if(UseATR)
   {
      double b[1];
      if(CopyBuffer(atr,0,1,1,b)!=1 || !MathIsValidNumber(b[0]) || b[0]<=0)
         {CancelPending();state="Waiting for closed-bar ATR";return;}
      distance=MathMax(EntryDistance,b[0]*ATRMultiplier);
   }
   if(distance>MaxEntryDistance){CancelPending();state="ATR distance exceeds maximum";return;}
   if(q.ask-q.bid>MaxSpread || q.ask-q.bid>distance*MaxSpreadEntryRatio)
      {CancelPending();state="Spread guard";return;}
   long mode=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_MODE);
   if(mode!=SYMBOL_TRADE_MODE_FULL){CancelPending();state="Symbol must allow both directions";return;}
   double gap=BrokerGap();
   distance=MathMax(distance,gap);
   if(distance>MaxEntryDistance){CancelPending();state="Broker entry distance exceeds maximum";return;}
   double buy=RoundUp(q.ask+distance),sell=RoundDown(q.bid-distance);
   double sl_gap=MathMax(StopDistance,gap),tp_gap=MathMax(TakeProfitDistance,gap);
   double bsl=RoundDown(buy-sl_gap),ssl=RoundUp(sell+sl_gap);
   double btp=RoundUp(buy+tp_gap),stp=RoundDown(sell-tp_gap);
   if(bsl<=0 || stp<=0 || !VolumeValid() || !RiskAllowed(buy,bsl,sell,ssl))
      {CancelPending();state="Volume, combined SL risk, margin or price guard";return;}
   bool found_buy=false,found_sell=false;
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=OrderGetTicket(i);if(ticket==0 || !OwnOrder())continue;
      long type=OrderGetInteger(ORDER_TYPE);
      bool is_buy=type==ORDER_TYPE_BUY_STOP;
      if((type!=ORDER_TYPE_BUY_STOP && type!=ORDER_TYPE_SELL_STOP) ||
         (is_buy && (!EnableBuy || found_buy)) || (!is_buy && (!EnableSell || found_sell)))
         {Halt("Unexpected/duplicate owned pending order");CancelPending();return;}
      if(is_buy)found_buy=true;else found_sell=true;
      if(MathAbs(OrderGetDouble(ORDER_VOLUME_CURRENT)-Lots)>1e-8)
         {Halt("Owned order volume differs from configured lot");CancelPending();return;}
      double price=is_buy?buy:sell;
      if(MathAbs(OrderGetDouble(ORDER_PRICE_OPEN)-price)>=RepriceThreshold)
      {
         if(!ResultOK(trade.OrderModify(ticket,price,is_buy?bsl:ssl,is_buy?btp:stp,
                     ORDER_TIME_SPECIFIED,TimeCurrent()+PendingLifetimeSeconds,0),"Reprice pending"))
            {CancelPending();return;}
      }
   }
   // A position may have filled while broker operations above were in flight.
   if(OwnPositions()>0){CancelPending();return;}
   if(EnableBuy && !found_buy)
   {
      if(!ResultOK(trade.BuyStop(Lots,buy,_Symbol,bsl,btp,ORDER_TIME_SPECIFIED,
                  TimeCurrent()+PendingLifetimeSeconds,"OpenPendingShield"),"Place buy stop"))
         {CancelPending();return;}
   }
   if(OwnPositions()>0){CancelPending();return;}
   if(EnableSell && !found_sell)
   {
      if(!ResultOK(trade.SellStop(Lots,sell,_Symbol,ssl,stp,ORDER_TIME_SPECIFIED,
                  TimeCurrent()+PendingLifetimeSeconds,"OpenPendingShield"),"Place sell stop"))
         {CancelPending();return;}
   }
   state="Pending breakout orders protected by SL/TP";
}
int OnInit()
{
   if(Magic==0 || !MathIsValidNumber(Lots) || Lots<=0 || EntryDistance<=0 || StopDistance<=0 || TakeProfitDistance<=0 ||
      MaxEntryDistance<EntryDistance || MaxSpread<=0 || MaxSpreadEntryRatio<=0 || MaxCombinedRiskPercent<=0 ||
      MaxCombinedRiskPercent>100 || DailyEquityLossPercent<=0 || DailyEquityLossPercent>100 || TrailStart<0 ||
      TrailDistance<=0 || RepriceThreshold<=0 || RepriceSeconds<1 || EntryCooldownSeconds<0 ||
      PendingLifetimeSeconds<30 || ATRPeriod<2 || ATRMultiplier<=0 || (!EnableBuy && !EnableSell) || TickSize()<=0)
      return INIT_PARAMETERS_INCORRECT;
   key="OPS."+IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))+"."+IntegerToString((long)Magic);
   // Exclusive common-file handle prevents a second terminal/chart using this identity.
   if(EnableTrading)
   {
      instance_lock=FileOpen(key+".lock",FILE_READ|FILE_WRITE|FILE_BIN|FILE_COMMON);
      if(instance_lock==INVALID_HANDLE){Print("Another instance owns this account/magic identity.");return INIT_FAILED;}
   }
   if(!MQLInfoInteger(MQL_TESTER))
   {
      if(ClearExecutionHalt)GlobalVariableDel(key+".halt");
      halted=GlobalVariableCheck(key+".halt");
   }
   long expiry=SymbolInfoInteger(_Symbol,SYMBOL_EXPIRATION_MODE);
   if(EnableTrading && (expiry & SYMBOL_EXPIRATION_SPECIFIED)==0)
      {Print("Broker must support specified pending expiration (safety timeout).");return INIT_FAILED;}
   trade.SetExpertMagicNumber(Magic);trade.SetDeviationInPoints(SlippagePoints);
   trade.SetTypeFillingBySymbol(_Symbol);trade.SetAsyncMode(false);
   if(UseATR){atr=iATR(_Symbol,ATRTimeframe,ATRPeriod);if(atr==INVALID_HANDLE)return INIT_FAILED;}
   UpdateDay();EventSetTimer(1);
   Print("OpenPendingShield 1.00: original EA; trading=",EnableTrading,". No licensing or activation checks.");
   return INIT_SUCCEEDED;
}
void Run()
{
   if(busy)return;busy=true;Cycle();
   if(state!=last_state){Print("Status: ",state);last_state=state;}
   Comment("OpenPendingShield 1.00\n",state,"\nOwn positions: ",OwnPositions()," | pending: ",OwnOrders(),
           "\nRisk budget: ",DoubleToString(MaxCombinedRiskPercent,2),"% | day baseline: ",DoubleToString(day_equity,2));
   busy=false;
}
void OnTick(){Run();}
void OnTimer(){Run();}
void OnTradeTransaction(const MqlTradeTransaction &tx,const MqlTradeRequest &request,const MqlTradeResult &result)
{
   if(EnableTrading && tx.type==TRADE_TRANSACTION_DEAL_ADD && tx.symbol==_Symbol && OwnPositions()>0)
   {had_position=true;CancelPending();}
}
void OnDeinit(const int reason)
{
   EventKillTimer();if(atr!=INVALID_HANDLE)IndicatorRelease(atr);Comment("");
   if(instance_lock!=INVALID_HANDLE)FileClose(instance_lock);
   // Do not transact during unload. Pending orders retain broker-side expiration and SL/TP.
}
