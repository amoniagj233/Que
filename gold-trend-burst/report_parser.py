from html.parser import HTMLParser
import re
class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=[]; self.cell=None
    def handle_starttag(self, tag, attrs):
        if tag=='tr': self.row=[]
        if tag=='td': self.cell=[]
    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)
    def handle_endtag(self, tag):
        if tag=='td' and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split())); self.cell=None
        if tag=='tr' and self.row: self.rows.append(self.row)

def read_report(path):
    b=path.read_bytes()
    s=b.decode('utf-16' if b.startswith(b'\xff\xfe') else 'utf-8',errors='replace')
    parser=TableParser();parser.feed(s)
    metrics={}
    for row in parser.rows:
        for i,cell in enumerate(row[:-1]):
            if cell.endswith(':'): metrics[cell[:-1]]=row[i+1]
    def number(key):
        value=metrics.get(key,'0').replace(' ','').replace(',','')
        m=re.match(r'[-+]?\d+(?:\.\d+)?',value)
        return float(m[0]) if m else 0.0
    wins=re.search(r'([\d ]+)\s*\(([\d.]+)%\)',metrics.get('Profit Trades (% of total)',''))
    dd=re.search(r'([\d.]+)%',metrics.get('Equity Drawdown Maximal',''))
    deals=[row for row in parser.rows if len(row)==13 and re.match(r'^\d{4}\.\d{2}\.\d{2}',row[0]) and row[4] in ('in','out','out by','in/out')]
    return dict(net=number('Total Net Profit'),profit_factor=number('Profit Factor'),trades=int(number('Total Trades')),
                wins=int(wins[1].replace(' ','')) if wins else 0,win_rate=float(wins[2]) if wins else 0,
                dd_amount=number('Equity Drawdown Maximal'),dd_percent=float(dd[1]) if dd else None,
                history_quality=metrics.get('History Quality','unknown'),ticks=int(number('Ticks')),
                gross_profit=number('Gross Profit'),gross_loss=number('Gross Loss'),
                commission=sum(float(r[8].replace(' ','')) for r in deals),
                swap=sum(float(r[9].replace(' ','')) for r in deals),metrics=metrics,deals=deals)
