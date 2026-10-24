#property strict
#property version "1.00"
#property description "M5 trend, M1 trigger, three protected market entries and short holding times."
#include <Trade/Trade.mqh>
input bool EnableTrading=true;
input bool AllowNewEntries=true;
input ulong Magic=2026102303;
input double BasketRiskPercent=0.75;
input double DailyLossPercent=3.0;
input double ExposureStepUnits=1.0; // One Gold unit = 0.01 lot on a 100-unit standard contract
input double StopATR=1.0;
input double Target1ATR=0.5;
input double Target2ATR=0.75;
input double Target3ATR=1.0;
input double TrailATR=0.35;
input double BreakBufferATR=0.05;
input double MinBodyATR=0.25;
input double MaxExtensionATR=2.0;
input double MinADX=0.0;
input double MaxSpreadTargetRatio=0.25;
input double MaxSpreadPrice=1.0;
input int CooldownSeconds=10;
input int MaxHoldingSeconds=180;
input ulong SlippagePoints=20;
input bool ClearExecutionHalt=false;

CTrade trade;
int emaFast,emaSlow,emaEntry,atrHandle,adxHandle,lockHandle=INVALID_HANDLE;
bool busy=false,halted=false,protect=false,wasOpen=false;
datetime lastSignal=0,lastFlat=0,basketStart=0,nextEntryAttempt=0,lastManage=0;
string key,state="Starting",lastState="";
int dayStamp=0;
double dayEquity=0;
bool dayStopped=false;
long basketCount=0,entryCount=0,tpCount=0,timeoutCount=0;

double Tick(){return SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);}
double Up(double v){return NormalizeDouble(MathCeil(v/Tick()-1e-8)*Tick(),_Digits);}
double Down(double v){return NormalizeDouble(MathFloor(v/Tick()+1e-8)*Tick(),_Digits);}
bool Own(){return PositionGetString(POSITION_SYMBOL)==_Symbol && (ulong)PositionGetInteger(POSITION_MAGIC)==Magic;}
int Count(){int n=0;for(int i=PositionsTotal()-1;i>=0;i--)if(PositionGetTicket(i)>0 && Own())n++;return n;}
void Save(string suffix,double v){if(!MQLInfoInteger(MQL_TESTER))GlobalVariableSet(key+suffix,v);}
double Read(string suffix){return (!MQLInfoInteger(MQL_TESTER) && GlobalVariableCheck(key+suffix))?GlobalVariableGet(key+suffix):0;}
void Halt(string why){halted=true;Save(".halt",1);state="HALTED: "+why;Print(state);}
double Gap(){return (MathMax(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))+3)*_Point+Tick();}
bool Buffer(int handle,int shift,double &value)
{
   double data[1];if(CopyBuffer(handle,0,shift,1,data)!=1 || !MathIsValidNumber(data[0]))return false;
   value=data[0];return true;
}
bool Indicators(double &vol,int &direction,double &entryEMA)
{
   double f1,f2,s1,a;
   if(!Buffer(atrHandle,1,vol) || vol<=0 || !Buffer(emaFast,1,f1) || !Buffer(emaFast,2,f2) ||
      !Buffer(emaSlow,1,s1) || !Buffer(emaEntry,1,entryEMA) || !Buffer(adxHandle,1,a))return false;
   MqlRates r[1];if(CopyRates(_Symbol,PERIOD_M5,1,1,r)!=1)return false;
   direction=0;
   if(a<MinADX)return true;
   if(r[0].close>f1 && f1>s1 && f1>f2)direction=1;
   if(r[0].close<f1 && f1<s1 && f1<f2)direction=-1;
   return true;
}
void Day()
{
   MqlDateTime d;TimeToStruct(TimeCurrent(),d);int stamp=d.year*10000+d.mon*100+d.day;
   if(stamp!=dayStamp)
   {
      dayStamp=stamp;string tag=".d"+IntegerToString(stamp);
      dayEquity=Read(tag);if(dayEquity<=0){dayEquity=AccountInfoDouble(ACCOUNT_EQUITY);Save(tag,dayEquity);}
      dayStopped=Read(tag+"s")>0;
   }
   if(dayEquity>0 && AccountInfoDouble(ACCOUNT_EQUITY)<=dayEquity*(1-DailyLossPercent/100))
   {dayStopped=true;Save(".d"+IntegerToString(stamp)+"s",1);}
}
bool Session()
{
   MqlDateTime t;TimeToStruct(TimeCurrent(),t);int sec=t.hour*3600+t.min*60+t.sec;
   datetime a,b;
   for(uint i=0;SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)t.day_of_week,i,a,b);i++)
   {int x=(int)a%86400,y=(int)b%86400;if(x==y || (x<y && sec>=x && sec<y) || (x>y && (sec>=x || sec<y)))return true;}
   return false;
}
bool Foreign()
{
   for(int i=PositionsTotal()-1;i>=0;i--)if(PositionGetTicket(i)>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && !Own())return true;
   for(int i=OrdersTotal()-1;i>=0;i--)if(OrderGetTicket(i)>0 && OrderGetString(ORDER_SYMBOL)==_Symbol)return true;
   return false;
}
bool Confirm(bool sent,string action,bool entry=false,ulong managedTicket=0)
{
   uint r=trade.ResultRetcode();
   if(sent && (r==TRADE_RETCODE_DONE || (!entry && (r==TRADE_RETCODE_DONE_PARTIAL || r==TRADE_RETCODE_NO_CHANGES))))return true;
   // A broker TP/SL can close this ticket during execution delay. Never retry another ticket.
   if(!entry && managedTicket>0 && !PositionSelectByTicket(managedTicket))return false;
   if(!entry && (r==TRADE_RETCODE_POSITION_CLOSED || r==TRADE_RETCODE_FROZEN || r==TRADE_RETCODE_INVALID_STOPS))return false;
   if(r==TRADE_RETCODE_REQUOTE || r==TRADE_RETCODE_PRICE_CHANGED || r==TRADE_RETCODE_PRICE_OFF ||
      r==TRADE_RETCODE_MARKET_CLOSED || r==TRADE_RETCODE_INVALID_STOPS || r==TRADE_RETCODE_NO_MONEY || r==TRADE_RETCODE_TOO_MANY_REQUESTS)
   {state="Broker rejected "+action+": "+trade.ResultRetcodeDescription();nextEntryAttempt=TimeCurrent()+30;Print(state);return false;}
   Halt(action+" uncertain/failed "+IntegerToString((int)r)+": "+trade.ResultRetcodeDescription());return false;
}
void Manage(double vol,int direction)
{
   if(TimeCurrent()==lastManage)return;lastManage=TimeCurrent();
   MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);if(ticket==0 || !Own())continue;
      datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
      if(basketStart==0 || opened<basketStart)basketStart=opened;
      bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
      double sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP),entry=PositionGetDouble(POSITION_PRICE_OPEN);
      if(sl<=0){Halt("Owned position has no SL");Confirm(trade.PositionClose(ticket),"unprotected close",false,ticket);continue;}
      bool timeout=TimeCurrent()-opened>=MaxHoldingSeconds;
      if(timeout || (direction!=0 && direction!=(buy?1:-1)))
      {if(Confirm(trade.PositionClose(ticket),"time/trend exit",false,ticket) && timeout)timeoutCount++;continue;}
      if(!protect || vol<=0)continue;
      double gap=Gap(),mark=buy?q.bid:q.ask;
      double freeze=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL)*_Point+Tick();
      if(MathAbs(mark-sl)<=freeze || (tp>0 && MathAbs(tp-mark)<=freeze))continue;
      double proposed=buy?Down(q.bid-MathMax(gap,TrailATR*vol)):Up(q.ask+MathMax(gap,TrailATR*vol));
      // Require at least entry plus one tick; never loosen existing protection.
      if((buy && proposed>=entry+Tick() && proposed>sl+Tick()) || (!buy && proposed<=entry-Tick() && proposed<sl-Tick()))
         Confirm(trade.PositionModify(ticket,proposed,tp),"protect winner",false,ticket);
   }
}
double LotFor(double entry,double stop,int side,double allocation)
{
   double p,step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);
   if(contract<=0 || step<=0)return 0;
   step=MathCeil(MathMax(step,ExposureStepUnits/contract)/step-1e-8)*step;
   if(step<=0 || !OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,1,entry,stop,p) || p>=0)return 0;
   double lots=MathFloor((allocation/(-p))/step+1e-8)*step;
   lots=MathMin(lots,MathFloor(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX)/step+1e-8)*step);
   if(lots<SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN)-1e-9)return 0;
   return NormalizeDouble(lots,8);
}
void Enter(int side,double vol,datetime signal)
{
   double budget=AccountInfoDouble(ACCOUNT_EQUITY)*BasketRiskPercent/100.0;
   double allocation=budget*0.9/3.0; // 10% reserve for fill drift; not a guarantee against gaps/fees.
   double targets[3];targets[0]=Target1ATR;targets[1]=Target2ATR;targets[2]=Target3ATR;
   MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
   double gap=Gap(),distance=MathMax(StopATR*vol,gap);
   double price=side>0?q.ask:q.bid;
   double stop=side>0?Down(price-distance):Up(price+distance);
   double lot=LotFor(price,stop,side,allocation),margin;
   if(lot<=0){state="Minimum broker lot exceeds basket risk budget";return;}
   if(!OrderCalcMargin(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,lot,price,margin) || margin*3>AccountInfoDouble(ACCOUNT_MARGIN_FREE)*0.9)
   {state="Insufficient margin for three trades";return;}
   double limit=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_LIMIT);
   if(limit>0 && lot*3>limit){state="Three trades exceed symbol volume limit";return;}
   lastSignal=signal;Save(".signal",(double)signal);protect=false;Save(".protect",0);basketStart=TimeCurrent();
   int completed=0;
   for(int leg=0;leg<3;leg++)
   {
      if(!SymbolInfoTick(_Symbol,q) || q.ask-q.bid>MaxSpreadPrice || q.ask-q.bid>Target1ATR*vol*MaxSpreadTargetRatio)break;
      price=side>0?q.ask:q.bid;
      stop=side>0?Down(price-distance):Up(price+distance);
      double tp=side>0?Up(price+MathMax(targets[leg]*vol,gap)):Down(price-MathMax(targets[leg]*vol,gap));
      double currentLot=LotFor(price,stop,side,allocation);
      if(currentLot<=0)break;
      currentLot=MathMin(lot,currentLot);
      string comment="GTB-"+IntegerToString((int)signal)+"-"+IntegerToString(leg+1);
      bool sent=side>0?trade.Buy(currentLot,_Symbol,0,stop,tp,comment):trade.Sell(currentLot,_Symbol,0,stop,tp,comment);
      if(!Confirm(sent,"entry leg "+IntegerToString(leg+1),true))break;
      completed++;entryCount++;
      // Validate actual fills; do not add more risk after a bad/unknown fill.
      double risk=0;
      for(int j=PositionsTotal()-1;j>=0;j--)
      {
         if(PositionGetTicket(j)==0 || !Own())continue;
         double loss;
         if(PositionGetDouble(POSITION_SL)<=0 || !OrderCalcProfit(side>0?ORDER_TYPE_BUY:ORDER_TYPE_SELL,_Symbol,
            PositionGetDouble(POSITION_VOLUME),PositionGetDouble(POSITION_PRICE_OPEN),PositionGetDouble(POSITION_SL),loss))
         {Halt("Cannot verify fill protection/risk");break;}
         risk+=MathMax(0,-loss);
      }
      if(halted || risk>budget){if(risk>budget)Halt("Fill risk exceeded basket budget");break;}
      if(Count()<completed)break; // A leg already exited: do not refill it into a new burst.
   }
   if(completed>0){basketCount++;wasOpen=true;Print("BURST signal=",signal," legs=",completed," risk_budget=",DoubleToString(budget,2));}
   if(!halted)state="Burst filled "+IntegerToString(completed)+"/3; protected by broker SL/TP";
}
void Cycle()
{
   if(!EnableTrading){state="Disabled: set EnableTrading=true";return;}
   if(!MQLInfoInteger(MQL_TESTER) && !TerminalInfoInteger(TERMINAL_CONNECTED)){state="MT5 disconnected";return;}
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)){state="Enable MT5 toolbar Algo Trading";return;}
   if(!MQLInfoInteger(MQL_TRADE_ALLOWED)){state="Enable Allow Algo Trading in EA properties";return;}
   if(!AccountInfoInteger(ACCOUNT_TRADE_ALLOWED) || !AccountInfoInteger(ACCOUNT_TRADE_EXPERT)){state="Account blocks EA trading";return;}
   Day();
   double vol=0,entryEMA=0;int direction=0;bool ready=Indicators(vol,direction,entryEMA);
   int n=Count();
   if(n>0){wasOpen=true;Manage(vol,direction);if(!halted)state="Managing "+IntegerToString(Count())+" burst trades";return;}
   if(wasOpen){wasOpen=false;lastFlat=TimeCurrent();Save(".flat",lastFlat);protect=false;Save(".protect",0);basketStart=0;}
   if(halted){state="Execution halted: reconcile broker history before clearing";return;}
   if(!AllowNewEntries){state="New baskets paused";return;}
   if(dayStopped){state="Daily loss stop latched until next broker day";return;}
   if(TimeCurrent()-lastFlat<CooldownSeconds || TimeCurrent()<nextEntryAttempt){state="Cooldown";return;}
   if(!ready){state="Waiting for closed M1/M5 indicator data";return;}
   if(direction==0){state="No aligned M5 trend";return;}
   if(Foreign()){state="Other exposure/orders on this symbol";return;}
   if(!Session()){state="Outside broker trading session";return;}
   if(SymbolInfoInteger(_Symbol,SYMBOL_TRADE_MODE)!=SYMBOL_TRADE_MODE_FULL){state="Symbol is not fully tradable";return;}
   MqlTick q;if(!SymbolInfoTick(_Symbol,q) || q.bid<=0 || q.ask<q.bid || TimeCurrent()-q.time>10){state="Waiting for valid fresh quote";return;}
   double spread=q.ask-q.bid;
   if(spread>MaxSpreadPrice || spread>Target1ATR*vol*MaxSpreadTargetRatio){state="Spread too large for quick profit target";return;}
   MqlRates bar[1];if(CopyRates(_Symbol,PERIOD_M1,1,1,bar)!=1)return;
   datetime signal=bar[0].time;
   if(signal<=lastSignal){state="Waiting for a fresh M1 signal";return;}
   double body=bar[0].close-bar[0].open;
   bool momentum=direction>0?body>=MinBodyATR*vol:-body>=MinBodyATR*vol;
   bool pullback=direction>0?(bar[0].low<=entryEMA && bar[0].close>entryEMA && body>0):
                              (bar[0].high>=entryEMA && bar[0].close<entryEMA && body<0);
   bool aligned=direction>0?bar[0].close>entryEMA:bar[0].close<entryEMA;
   double mark=q.bid; // MT5 OTC candles use bid prices for both signal directions.
   bool crossed=direction>0?mark>=bar[0].high+BreakBufferATR*vol:mark<=bar[0].low-BreakBufferATR*vol;
   if(!aligned || (!momentum && !pullback) || !crossed || MathAbs(mark-entryEMA)>MaxExtensionATR*vol)
   {state="M5 trend ready; waiting for fresh M1 break";return;}
   Enter(direction,vol,signal);
}
int OnInit()
{
   if(Magic==0 || BasketRiskPercent<=0 || BasketRiskPercent>3 || DailyLossPercent<=0 || DailyLossPercent>10 ||
      ExposureStepUnits<=0 || StopATR<=0 || Target1ATR<=0 || Target2ATR<Target1ATR || Target3ATR<Target2ATR || TrailATR<=0 ||
      BreakBufferATR<0 || MinBodyATR<0 || MaxExtensionATR<=0 || MinADX<0 || MaxSpreadTargetRatio<=0 ||
      MaxSpreadPrice<=0 || CooldownSeconds<0 || MaxHoldingSeconds<10 || Tick()<=0)return INIT_PARAMETERS_INCORRECT;
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
   {Print("Three separate positions require a hedging account.");return INIT_FAILED;}
   key="GTB."+IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))+"."+IntegerToString((long)Magic);
   if(EnableTrading){lockHandle=FileOpen(key+".lock",FILE_READ|FILE_WRITE|FILE_BIN|FILE_COMMON);if(lockHandle==INVALID_HANDLE){Print("Another GTB instance owns this account/magic");return INIT_FAILED;}}
   if(ClearExecutionHalt && !MQLInfoInteger(MQL_TESTER))GlobalVariableDel(key+".halt");
   halted=Read(".halt")>0;lastSignal=(datetime)Read(".signal");lastFlat=(datetime)Read(".flat");protect=Read(".protect")>0;
   emaFast=iMA(_Symbol,PERIOD_M5,20,0,MODE_EMA,PRICE_CLOSE);
   emaSlow=iMA(_Symbol,PERIOD_M5,50,0,MODE_EMA,PRICE_CLOSE);
   emaEntry=iMA(_Symbol,PERIOD_M1,9,0,MODE_EMA,PRICE_CLOSE);
   atrHandle=iATR(_Symbol,PERIOD_M1,14);adxHandle=iADX(_Symbol,PERIOD_M5,14);
   if(emaFast==INVALID_HANDLE || emaSlow==INVALID_HANDLE || emaEntry==INVALID_HANDLE || atrHandle==INVALID_HANDLE || adxHandle==INVALID_HANDLE)return INIT_FAILED;
   trade.SetExpertMagicNumber(Magic);trade.SetDeviationInPoints(SlippagePoints);trade.SetAsyncMode(false);trade.SetTypeFillingBySymbol(_Symbol);
   Day();EventSetTimer(1);
   Print("GTB START 1.00 trading=",EnableTrading," contract=",SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE));
   return INIT_SUCCEEDED;
}
void Run(){if(busy)return;busy=true;Cycle();if(state!=lastState){Print("GTB STATUS ",state);lastState=state;}Comment("Gold Trend Burst 1.00\n",state,"\nM5 trend / M1 entry | basket risk ",BasketRiskPercent,"% | max 3 trades");busy=false;}
void OnTick(){Run();}
void OnTimer(){Run();}
void OnTradeTransaction(const MqlTradeTransaction &tx,const MqlTradeRequest &req,const MqlTradeResult &res)
{
   if(tx.type!=TRADE_TRANSACTION_DEAL_ADD || tx.symbol!=_Symbol || !HistoryDealSelect(tx.deal))return;
   if((ulong)HistoryDealGetInteger(tx.deal,DEAL_MAGIC)!=Magic)return;
   if(HistoryDealGetInteger(tx.deal,DEAL_ENTRY)==DEAL_ENTRY_OUT && HistoryDealGetInteger(tx.deal,DEAL_REASON)==DEAL_REASON_TP)
   {protect=true;Save(".protect",1);tpCount++;}
}
double OnTester(){Print("GTB STATS baskets=",basketCount," entries=",entryCount," tp_exits=",tpCount," timeouts=",timeoutCount);return TesterStatistics(STAT_PROFIT);}
void OnDeinit(const int reason)
{
   EventKillTimer();IndicatorRelease(emaFast);IndicatorRelease(emaSlow);IndicatorRelease(emaEntry);IndicatorRelease(atrHandle);IndicatorRelease(adxHandle);
   if(lockHandle!=INVALID_HANDLE)FileClose(lockHandle);Comment("");
}
