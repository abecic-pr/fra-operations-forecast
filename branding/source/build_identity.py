"""Build the approved vector identity and editable design mockups. Python stdlib only."""
from pathlib import Path
import html
import re

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
MOCKUPS = ROOT / 'mockups'
INK, BLUE, MUTED = '#17191D', '#0066CC', '#656B75'
CANVAS, LINE, GREEN = '#F5F5F7', '#DDE1E7', '#167247'
MARK = 'M48 212V84C48 48 72 28 108 28H224L188 64H112C94 64 84 72 84 90V108H196L160 144H84V212Q84 216 80 216H52Q48 216 48 212Z'
REVERSE = 'M49 212V84C49 49 72 29 108 29H222L188 63H112C93 63 83 72 83 90V109H194L160 143H83V212Q83 215 80 215H52Q49 215 49 212Z'
SMALL = 'M48 216V84C48 48 72 28 108 28H224L188 64H112C94 64 84 72 84 90V108H196L160 144H84V216Z'

def svg(w, h, body, title):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title, quote=True)}"><title>{html.escape(title)}</title>{body}</svg>'

def mark(x, y, size, color=INK, reverse=False):
    return f'<path transform="translate({x} {y}) scale({size/256})" fill="{color}" d="{REVERSE if reverse else MARK}"/>'

def rect(x,y,w,h,fill='white',r=0,stroke=None):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"'+(f' stroke="{stroke}"' if stroke else '')+'/>'

def text(x,y,t,size=14,fill=INK,weight=400,anchor='start'):
    return f'<text x="{x}" y="{y}" font-family="Helvetica Neue, Arial, sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">{html.escape(t)}</text>'

def line(x1,y1,x2,y2,color=LINE,width=1,dash=None):
    return f'<path d="M{x1} {y1}L{x2} {y2}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>'

def circle(x,y,r,fill):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>'

def pill(x,y,w,label,bg='#EEF0F3',fg=MUTED):
    return rect(x,y,w,28,bg,14)+text(x+w/2,y+19,label,12,fg,500,'middle')

def arrow(x,y,size=18,color=BLUE,west=False):
    return f'<g transform="translate({x} {y}) scale({size/24})'+(' rotate(180 12 12)' if west else '')+f'" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12H21M14 5L21 12L14 19"/></g>'

def check(x,y):
    return circle(x,y,8,GREEN)+f'<path d="M{x-3.5} {y}l2.4 2.5 4.8-5" fill="none" stroke="white" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'

def wind_path(x, y, width, height):
    values=[12,10,14,18,19,16,14,16,20,18,15,16,13,11,13,15,14]
    points=[(x+i*width/(len(values)-1),y+(24-value)*height/24) for i,value in enumerate(values)]
    return 'M'+'L'.join(f'{px:.2f} {py:.2f}' for px,py in points)

def icon(x,y,kind,color=MUTED):
    paths = {
        'overview':'M3 3H9V9H3ZM15 3H21V9H15ZM3 15H9V21H3ZM15 15H21V21H15Z',
        'forecast':'M3 18L8 11L13 14L21 5M3 22H22',
        'runways':'M6 3L18 21M3 7L15 25M19 3V14',
        'sources':'M4 5H20V20H4ZM8 9H16M8 13H16M8 17H13',
    }
    return f'<path transform="translate({x} {y}) scale(.75)" d="{paths[kind]}" fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'

def build_assets():
    ASSETS.mkdir(exist_ok=True)
    for name,color,shape in [('graphite',INK,MARK),('blue',BLUE,MARK),('black','#000000',MARK),('white','#FFFFFF',REVERSE)]:
        (ASSETS/f'fra-symbol-{name}.svg').write_text(svg(256,256,f'<path fill="{color}" d="{shape}"/>','FRA Operations Forecast — Flightpath'))
    (ASSETS/'fra-symbol-small.svg').write_text(svg(256,256,f'<path fill="{INK}" d="{SMALL}"/>','FRA Operations Forecast — small symbol'))
    fra=(ROOT/'source/fra-type-paths.txt').read_text()
    desc=(ROOT/'source/descriptor-type-paths.txt').read_text()
    for name,color in [('graphite',INK),('white','#FFFFFF')]:
        body=mark(0,0,200,color,reverse=name=='white')+f'<g fill="{color}">{fra}{desc}</g>'
        (ASSETS/f'fra-logo-horizontal-{name}.svg').write_text(svg(510,200,body,'FRA Operations Forecast'))
        body=mark(0,0,200,color,reverse=name=='white')+f'<g fill="{color}" transform="translate(0 28)">{fra}</g>'
        (ASSETS/f'fra-logo-compact-{name}.svg').write_text(svg(400,200,body,'FRA'))
        body=f'<g fill="{color}" transform="translate(-218 -26)">{fra}{desc}</g>'
        (ASSETS/f'fra-wordmark-{name}.svg').write_text(svg(292,142,body,'FRA Operations Forecast'))
        body=mark(128,0,256,color,reverse=name=='white')+f'<g fill="{color}" transform="translate(-48 210)">{fra}</g><g fill="{color}" transform="translate(-98 208)">{desc}</g>'
        (ASSETS/f'fra-logo-stacked-{name}.svg').write_text(svg(520,400,body,'FRA Operations Forecast'))
    (ASSETS/'fra-app-icon.svg').write_text(svg(256,256,rect(0,0,256,256,BLUE,56)+mark(31,31,194,'#FFFFFF',True),'FRA Operations Forecast app icon'))

def desktop():
    s=[rect(0,0,1600,1120,CANVAS),rect(0,0,224,1120,'#FBFBFD'),line(224,0,224,1120)]
    s += [rect(28,32,42,42,BLUE,11),mark(32,36,34,'white',True),text(82,50,'FRA',20,weight=600),text(82,69,'Operations Forecast',10,MUTED)]
    for i,(label,kind) in enumerate([('Overview','overview'),('Forecast','forecast'),('Runways','runways'),('Sources','sources')]):
        y=138+i*52
        if i==0:s.append(rect(16,y-4,192,42,'#E8EFF9',10))
        s += [icon(30,y+6,kind,BLUE if i==0 else MUTED),text(62,y+23,label,14,BLUE if i==0 else MUTED,500)]
    s += [line(24,993,200,993),text(28,1028,'Frankfurt Airport',13,weight=500),text(28,1051,'EDDF',12,MUTED),pill(27,1072,85,'Prototype')]
    s += [text(280,65,'Frankfurt outlook',34,weight=600),text(281,96,'Runway direction and weather suitability',16,MUTED),pill(1373,36,171,'Illustrative demo data'),text(1544,98,'30 Oct 2026  /  UTC',13,MUTED,anchor='end')]
    s += [rect(280,132,1264,324,'white',22),line(554,164,554,424),line(1148,164,1148,424)]
    s += [text(312,177,'Observed direction',15,MUTED),text(307,280,'25',104,weight=400),arrow(470,231,36,INK,True),text(313,317,'Westbound',23,weight=500),text(313,350,'Observed at 10:00 UTC',13,MUTED),pill(312,386,183,'Sample operation record')]
    s += [text(586,177,'Runway overview',15,MUTED)]
    # Simplified runway topology. The illustration is explicitly not navigational.
    s.append('<g transform="translate(627 235)">')
    for dy,left,right in [(0,'07L','25R'),(62,'07C','25C'),(94,'07R','25L')]:
        s += [line(38,dy+64,395,dy-66,'#E0E6EE',13),line(46,dy+61,387,dy-63,BLUE,7),line(51,dy+59,380,dy-61,'white',1.3,'8 9'),text(26,dy+68,left,10,MUTED,anchor='end'),text(406,dy-66,right,10,MUTED)]
    s += [line(-8,70,-8,138,'#BBC2CC',12),line(-8,74,-8,134,'white',1.2,'6 6'),text(-8,160,'18',10,MUTED,anchor='middle')]
    s.append('</g>')
    s += [text(586,432,'Simplified schematic',11,MUTED),circle(1029,428,3,BLUE),text(1038,432,'Direction 25',11,MUTED)]
    s += [text(1180,177,'Wind observation',15,MUTED),text(1177,238,'12',60,weight=400),text(1252,235,'kt',22,MUTED),text(1180,269,'250° WSW  ·  Gusts 18 kt',14,MUTED),line(1180,291,1512,291),text(1180,324,'Runway 18 weather',14,MUTED),check(1189,351),text(1207,360,'Suitable',25,weight=500),text(1180,394,'Official status: unknown',13,MUTED),text(1180,417,'Suitability from weather rules',12,MUTED)]
    s += [rect(280,480,1264,460,'white',22),text(312,524,'48-hour outlook',23,weight=500),text(313,550,'Weather-based baseline',13,MUTED)]
    s += [rect(1380,506,132,34,'#EFF0F3',8),text(1413,528,'24 h',12,MUTED,500,'middle'),rect(1446,509,63,28,'white',6),text(1477,528,'48 h',12,INK,500,'middle')]
    s += [rect(312,576,1200,62,'#F0F6FF',12),arrow(331,596,21),text(369,600,'Next potential change',12,MUTED),text(369,622,'25 → 07',17,INK,500),text(1319,613,'18:00–19:00 UTC',16,INK,500,'end'),pill(1385,593,105,'Forecast','#E0ECFC',BLUE)]
    s += [text(312,681,'Direction',13,MUTED),rect(460,659,174,32,'#E5EEF9',7),text(547,681,'25',14,BLUE,500,'middle'),rect(638,659,874,32,'#EDF0F4',7),text(1075,681,'07',14,INK,500,'middle')]
    s += [text(312,722,'RWY18 weather',13,MUTED),rect(460,705,1200-148,25,'#EAF5EE',6),text(985,723,'Suitable',12,GREEN,500,'middle')]
    s += [text(312,787,'Wind (kt)',13,MUTED)]
    for value,y in [(24,754),(12,802),(0,850)]:
        s += [line(460,y,1512,y,'#EDF0F4'),text(445,y+4,str(value),10,MUTED,anchor='end')]
    d=wind_path(460,754,1052,96)
    s += [f'<path d="{d}L1512 850H460Z" fill="#F2F7FE"/>',f'<path d="{d}" fill="none" stroke="{BLUE}" stroke-width="2.5" stroke-dasharray="6 5" stroke-linecap="round"/>',circle(460,802,4,INK)]
    for x,t in [(460,'30 Oct, 10:00'),(723,'22:00'),(986,'31 Oct, 10:00'),(1250,'22:00'),(1512,'1 Nov, 10:00')]:s.append(text(x,878,t,11,MUTED,anchor='start' if x==460 else 'end' if x==1512 else 'middle'))
    s += [circle(467,910,3,INK),text(480,914,'Observation',11,MUTED),line(589,910,611,910,BLUE,2,'5 4'),text(620,914,'Forecast',11,MUTED),text(1512,914,'Deterministic baseline · no probability estimate',11,MUTED,anchor='end')]
    s += [text(282,979,'Data provenance',15,INK,500)]
    for x,title,body in [(282,'Weather observation','Sample METAR · 10:00 UTC'),(612,'Forecast input','Synthetic forecast · issued 08:00 UTC'),(994,'Operating direction','Sample record · 10:00 UTC'),(1332,'Official runway status','Not connected')]:
        s += [text(x,1014,title,12,MUTED),text(x,1037,body,12,INK)]
    s += [line(280,1061,1544,1061),text(281,1090,'Design preview. All values are illustrative; no live sources are connected.',12,MUTED)]
    return svg(1600,1120,''.join(s),'FRA Operations Forecast desktop design — illustrative demo data')

def mobile():
    s=[rect(0,0,390,1010,CANVAS),rect(0,0,390,84,'#FBFBFD'),line(0,84,390,84),rect(24,25,34,34,BLUE,9),mark(26,27,30,'white',True),text(69,47,'FRA',18,weight=600),pill(213,29,153,'Illustrative demo data')]
    s += [text(24,131,'Frankfurt outlook',27,weight=600),text(25,158,'30 Oct 2026  /  UTC',13,MUTED),rect(20,183,350,267,'white',20)]
    s += [text(40,216,'Observed direction',13,MUTED),text(36,294,'25',78),text(42,324,'Westbound',17,weight=500),text(42,349,'10:00 UTC',11,MUTED),line(204,209,204,350),text(227,217,'Wind',13,MUTED),text(223,274,'12',48),text(279,272,'kt',19,MUTED),text(226,303,'250° WSW',12,MUTED),text(226,327,'Gusts 18 kt',12,MUTED)]
    s += [line(40,370,350,370),check(49,398),text(65,402,'RWY18 weather: suitable',13,INK,500),text(42,427,'Official status: unknown',12,MUTED)]
    s += [rect(20,470,350,330,'white',20),text(40,505,'48-hour outlook',20,weight=500),text(40,529,'Weather-based baseline',12,MUTED),rect(40,548,310,64,'#F0F6FF',10),text(56,571,'Next potential change',12,MUTED),text(56,594,'25 → 07',17,weight=500),text(334,592,'18:00–19:00 UTC',12,BLUE,500,'end')]
    s += [rect(40,631,53,26,'#E5EEF9',6),text(66,649,'25',12,BLUE,500,'middle'),rect(97,631,253,26,'#EDF0F4',6),text(225,649,'07',12,INK,500,'middle'),text(40,680,'Forecast wind (kt)',11,MUTED)]
    for value,y in [(24,695),(12,721),(0,747)]:s += [line(64,y,350,y,'#EDF0F4'),text(55,y+3,str(value),9,MUTED,anchor='end')]
    s += [f'<path d="{wind_path(64,695,286,52)}" fill="none" stroke="#0066CC" stroke-width="2" stroke-dasharray="5 4" stroke-linecap="round"/>',circle(64,721,3,INK),text(40,774,'30 Oct, 10:00',10,MUTED),text(350,774,'1 Nov, 10:00',10,MUTED,anchor='end')]
    s += [text(24,830,'Illustrative records',12,INK,500),text(24,853,'Observation 10:00 UTC · Forecast issued 08:00 UTC',10,MUTED),text(24,874,'No live sources connected. No probability estimate.',10,MUTED)]
    s += [rect(0,914,390,96,'#FBFBFD'),line(0,914,390,914)]
    for x,label,kind in [(47,'Overview','overview'),(146,'Forecast','forecast'),(245,'Runways','runways'),(344,'Sources','sources')]:
        s += [icon(x-9,933,kind,BLUE if label=='Overview' else MUTED),text(x,975,label,10,BLUE if label=='Overview' else MUTED,500,'middle')]
    s += [rect(139,995,112,4,INK,2)]
    return svg(390,1010,''.join(s),'FRA Operations Forecast mobile design — illustrative demo data')

def board():
    s=[rect(0,0,1600,1160,'#FAFAFC'),text(64,66,'FRA Operations Forecast',22,weight=500),text(1536,66,'Flightpath / Visual identity',14,MUTED,anchor='end'),line(64,92,1536,92)]
    s += [rect(64,124,976,480,'white',24),mark(120,187,300),text(484,324,'FRA',86,weight=500),text(489,379,'Operations Forecast',32),text(118,552,'A clear direction.',24,MUTED)]
    s += [rect(1064,124,472,480,INK,24),rect(1180,215,240,240,BLUE,53),mark(1209,244,182,'white',True),text(1300,550,'One idea. At every size.',16,'#C5CAD2',400,'middle')]
    s += [text(64,660,'Quiet by design.',36,weight=500),text(64,695,'Soft surfaces. Precise type. Space to see what matters.',18,MUTED)]
    for x,name,code in [(64,'Canvas',CANVAS),(364,'Surface','#FFFFFF'),(664,'Graphite',INK),(964,'Flight blue',BLUE),(1264,'Secondary',MUTED)]:
        s += [rect(x,735,272,125,code,16,LINE if code in [CANVAS,'#FFFFFF'] else None),text(x,892,name,16,weight=500),text(x,918,code,13,MUTED)]
    s += [line(64,956,1536,956),text(64,1011,'Aa',47,weight=500),text(161,994,'System sans-serif',18,weight=500),text(161,1022,'Native typography. Tabular figures. Clear hierarchy.',14,MUTED)]
    s += [text(978,994,'25   07   18',38,weight=400),text(978,1024,'Runway information takes the lead.',14,MUTED),text(64,1113,'FRA Operations Forecast / AI Week Frankfurt 2026',12,MUTED),text(1536,1113,'Approved direction A',12,MUTED,anchor='end')]
    return svg(1600,1160,''.join(s),'FRA Operations Forecast — Flightpath visual identity')

if __name__ == '__main__':
    build_assets()
    MOCKUPS.mkdir(exist_ok=True)
    (MOCKUPS/'app-desktop.svg').write_text(desktop())
    (MOCKUPS/'app-mobile.svg').write_text(mobile())
    (ROOT/'identity-board.svg').write_text(board())
    print('Built logo assets, desktop and mobile design mockups, and identity board.')
