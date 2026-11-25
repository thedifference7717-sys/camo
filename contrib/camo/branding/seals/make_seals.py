# CAMO: draws the three Seal mascots (original art; blocky robots in ghillie suits). Run: python3 make_seals.py
# Writes seal-watch.svg, seal-code.svg, seal-scout.svg (website/assets/seals/). Same seeds -> same pictures.
import math, random
greens=['#3E5236','#4A5E3E','#56693F','#647A45','#728A4E','#5B5233','#6B6038','#3A4A30']
AMBER='#E0A63A'; AMBER_HI='#FFD27A'; MINT='#7FD3A0'; MINT_HI='#D8F5D0'
BODY={'watch':'#7C8B6A','code':'#6E8579','scout':'#857A5C'}
NAMES={'watch':'Seal Watch','code':'Seal Code','scout':'Seal Scout'}
ink='#1A2219'
def strands(P, box, inside, n, lmin=10, lmax=24, sway=0):
    st=[]
    for _ in range(n):
        x=random.uniform(box[0],box[2]); y=random.uniform(box[1],box[3])
        if not inside(x,y): continue
        L=random.uniform(lmin,lmax); a=math.radians(90+sway+random.uniform(-22,22)); b=random.uniform(-6,6)
        x2=x+L*math.cos(a); y2=y+L*math.sin(a)
        st.append((y,f'<path d="M{x:.1f} {y:.1f} Q{(x+x2)/2+b:.1f} {(y+y2)/2:.1f} {x2:.1f} {y2:.1f}" stroke="{random.choice(greens)}" stroke-width="{random.uniform(2.4,4.2):.1f}" stroke-linecap="round" fill="none"/>'))
    for _,s in sorted(st): P(s)
def limb(P, px, py, a1, a2, l1, l2, width, fill, joint, end):
    """Upper piece from (px,py) at angle a1 (0 = straight down, + swings left), lower piece bent a2 more at the
    elbow/knee, then `end` (hand or foot) at the tip. Ball joints at shoulder/hip and elbow/knee."""
    P(f'<g transform="rotate({a1} {px} {py})">')
    P(f'<rect x="{px-width/2}" y="{py}" width="{width}" height="{l1+6}" rx="{width*0.3:.0f}" fill="{fill}" stroke="{ink}" stroke-width="4"/>')
    P(f'<g transform="rotate({a2} {px} {py+l1})">')
    P(f'<rect x="{px-width/2+2}" y="{py+l1-4}" width="{width-4}" height="{l2+4}" rx="{width*0.3:.0f}" fill="{fill}" stroke="{ink}" stroke-width="4"/>')
    end(px, py+l1+l2)
    P('</g>')
    P(f'<circle cx="{px}" cy="{py+l1}" r="{width*0.42:.0f}" fill="{joint}" stroke="{ink}" stroke-width="4"/>')
    P('</g>')
    P(f'<circle cx="{px}" cy="{py}" r="{width*0.5:.0f}" fill="{joint}" stroke="{ink}" stroke-width="4"/>')

def seal(kind, seed):
    random.seed(seed); o=[]; P=o.append
    acc,hi=(MINT,MINT_HI) if kind=='code' else (AMBER,AMBER_HI)
    P('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 600" width="480" height="600">')
    P(f'<title>{NAMES[kind]}: a blocky CAMO watch-team robot in a ghillie suit, in action</title>')
    P(f'''<defs><radialGradient id="g-{kind}"><stop offset="0" stop-color="{hi}"/><stop offset="0.45" stop-color="{acc}"/><stop offset="1" stop-color="{acc}" stop-opacity="0"/></radialGradient>
<linearGradient id="m-{kind}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#C9D0BF"/><stop offset="1" stop-color="#5E6A5F"/></linearGradient>
<linearGradient id="b-{kind}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{BODY[kind]}"/><stop offset="1" stop-color="#3F4A3A"/></linearGradient></defs>''')
    G=f'url(#g-{kind})'; M=f'url(#m-{kind})'; B=f'url(#b-{kind})'
    hand=lambda x,y: P(f'<rect x="{x-21}" y="{y-6}" width="42" height="36" rx="12" fill="{M}" stroke="{ink}" stroke-width="4"/>')
    foot=lambda x,y: P(f'<rect x="{x-26}" y="{y-8}" width="52" height="24" rx="6" fill="#2A3326" stroke="{ink}" stroke-width="4"/>')
    # pose table: (body dx, dy, tilt), legs (L ang, R ang, length), arms (L ang, R ang)
    pose={'watch':(6,0,-6,(26,34,-34,28),(40,-55,-100,-12)),   # stride; right arm points ahead, left arm swings
          'code': (0,4,0,(12,-4,-12,4),(70,-100,-40,-62)),     # planted; left hand swipes, right hand on the screen
          'scout':(0,22,-8,(38,48,-64,80),(42,-62,-95,-70))}[kind] # crouch-run; right hand holds the spyglass
    dx,dy,tilt,(lL1,lL2,lR1,lR2),(aL1,aL2,aR1,aR2)=pose
    cx=240+dx
    # effects behind the figure
    if kind=='watch':
        for i,r in enumerate((60,92,124)):
            P(f'<path d="M{cx+52+r*0.25:.0f} {58-r*0.55:.0f} A{r} {r} 0 0 1 {cx+52+r*0.25:.0f} {58+r*0.55:.0f}" stroke="{acc}" stroke-width="{5-i}" fill="none" opacity="{0.9-0.25*i:.2f}" stroke-linecap="round"/>')
        for y in (300,330,360):
            P(f'<line x1="{cx-150}" y1="{y}" x2="{cx-104}" y2="{y}" stroke="#4A5E4E" stroke-width="5" stroke-linecap="round"/>')
    if kind=='code':
        for gx,gy,t,sz,rot in ((70,120,'{ }',30,-14),(400,110,'01',24,10),(420,250,'&lt;/&gt;',26,-8),(60,300,'#',30,12),(392,430,';',30,0)):
            P(f'<text x="{gx}" y="{gy}" font-family="monospace" font-weight="700" font-size="{sz}" fill="{acc}" opacity="0.75" transform="rotate({rot} {gx} {gy})">{t}</text>')
    if kind=='scout':
        for i in range(9):
            x=random.uniform(20,140); y=random.uniform(150,470); a=random.uniform(0,180)
            P(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="12" ry="5" transform="rotate({a:.0f} {x:.0f} {y:.0f})" fill="{random.choice(greens[2:5])}"/>')
            P(f'<line x1="{x+18:.0f}" y1="{y:.0f}" x2="{x+44:.0f}" y2="{y:.0f}" stroke="#4A5E4E" stroke-width="3" stroke-linecap="round" opacity="0.7"/>')
    P(f'<g transform="translate({dx} {dy}) rotate({tilt} 240 330)">')
    # legs from the hips
    J='#2A3326'
    limb(P,214,414,lL1,lL2,64,58,40,B,J,lambda x,y: foot(x,y))
    limb(P,266,414,lR1,lR2,64,58,40,B,J,lambda x,y: foot(x,y))
    P(f'<rect x="186" y="400" width="108" height="28" rx="8" fill="#2A3326" stroke="{ink}" stroke-width="4"/>')
    # back arm (left side of picture)
    def item_L(x,y):
        hand(x,y)
    limb(P,170,268,aL1,aL2,50,46,30,B,J,item_L)
    # torso + cape + badge
    P(f'<path d="M168 262 Q170 250 186 250 L294 250 Q310 250 312 262 L296 404 L184 404 Z" fill="{B}" stroke="{ink}" stroke-width="4" stroke-linejoin="round"/>')
    P(f'<path d="M206 330 L274 330" stroke="{ink}" stroke-width="3" opacity="0.35"/>')
    P('<path d="M148 248 Q240 214 332 248 L316 318 Q240 336 164 318 Z" fill="#2F3D2A"/>')
    sway=-14 if kind!='code' else 0   # cape blows back when moving
    strands(P,(140,226,340,330),lambda x,y: 232<y<330 and abs(x-240)<92-(y-232)*0.25,330,sway=sway)
    P('<g transform="translate(240 362)">')
    P(f'<path d="M0 -30 L26 -20 L23 10 Q18 28 0 37 Q-18 28 -23 10 L-26 -20 Z" fill="#121A15" stroke="{acc}" stroke-width="3.5"/>')
    if kind=='watch': P(f'<path d="M-16 3 L-7 3 L-3 -10 L3 15 L7 3 L16 3" stroke="{acc}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>')
    elif kind=='code': P(f'<path d="M-8 -9 L-15 3 L-8 15 M8 -9 L15 3 L8 15 M4 -12 L-4 18" stroke="{acc}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>')
    else: P(f'<circle cx="-3" cy="-1" r="10" fill="none" stroke="{acc}" stroke-width="3.5"/><line x1="4" y1="6" x2="13" y2="17" stroke="{acc}" stroke-width="4.5" stroke-linecap="round"/>')
    P('</g>')
    # neck + head
    P(f'<rect x="220" y="236" width="40" height="24" fill="#2A3326" stroke="{ink}" stroke-width="4"/>')
    P(f'<rect x="172" y="112" width="136" height="128" rx="22" fill="{M}" stroke="{ink}" stroke-width="4"/>')
    P(f'<rect x="188" y="150" width="104" height="66" rx="14" fill="#0B0F0C" stroke="{ink}" stroke-width="3"/>')
    if kind=='watch':
        P(f'<circle cx="244" cy="183" r="34" fill="{G}" opacity="0.8"/><circle cx="244" cy="183" r="21" fill="#0B0F0C" stroke="{acc}" stroke-width="4"/>')
        P(f'<circle cx="250" cy="183" r="9" fill="{hi}"/><circle cx="254" cy="178" r="3" fill="#fff" opacity="0.9"/>')
    elif kind=='code':
        for ex,d in ((218,1),(262,-1)):
            P(f'<circle cx="{ex}" cy="186" r="20" fill="{G}" opacity="0.7"/>')
            P(f'<path d="M{ex+6*d} 175 L{ex-6*d} 186 L{ex+6*d} 197" stroke="{hi}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>')
    else:
        P(f'<circle cx="218" cy="183" r="18" fill="{G}" opacity="0.8"/><rect x="208" y="180" width="22" height="8" rx="4" fill="{hi}"/>')  # squinting eye
    P(f'<rect x="226" y="224" width="28" height="6" rx="3" fill="{ink}"/>')
    # hood
    P('<path d="M156 140 Q154 76 240 72 Q326 76 324 140 L316 190 L306 138 Q240 124 174 138 L164 190 Z" fill="#2F3D2A"/>')
    strands(P,(148,70,332,190),lambda x,y: (((x-240)/90)**2+((y-118)/44)**2<1 and y<136) or (118<y<176 and (164<x<178 or 302<x<316)),620,lmin=9,lmax=22,sway=sway/2)
    # head gear
    if kind=='watch':
        P(f'<line x1="240" y1="84" x2="240" y2="50" stroke="#8E9888" stroke-width="7" stroke-linecap="round"/>')
        P(f'<path d="M204 56 Q236 14 280 42 Q246 64 204 56 Z" fill="{M}" stroke="{ink}" stroke-width="3"/>')  # dish turned to the right
        P(f'<circle cx="262" cy="34" r="12" fill="{G}"/><circle cx="262" cy="34" r="4.5" fill="{hi}"/>')
    elif kind=='code':
        for x2 in (190,290):
            P(f'<line x1="{240+(x2-240)*0.4:.0f}" y1="84" x2="{x2}" y2="40" stroke="#8E9888" stroke-width="5" stroke-linecap="round"/>')
            P(f'<circle cx="{x2}" cy="40" r="13" fill="{G}"/><circle cx="{x2}" cy="40" r="5" fill="{hi}"/>')
    else:
        for x,y,a,L in ((190,98,-130,44),(286,92,-70,50),(240,84,-100,38)):
            r=math.radians(a); x2=x+L*math.cos(r); y2=y+L*math.sin(r)
            P(f'<line x1="{x}" y1="{y}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="#6B5A3A" stroke-width="5" stroke-linecap="round"/>')
            P(f'<ellipse cx="{x2:.0f}" cy="{y2:.0f}" rx="11" ry="5" transform="rotate({a+90} {x2:.0f} {y2:.0f})" fill="#728A4E"/>')
    # front arm (right side of picture) with its item
    def item_R(x,y):
        hand(x,y)
    if kind=='scout':   # spyglass held to the right eye, pointing ahead
        P(f'<rect x="262" y="168" width="58" height="30" rx="6" fill="#2A3326" stroke="{ink}" stroke-width="4"/>')
        P(f'<rect x="316" y="164" width="96" height="38" rx="7" fill="{M}" stroke="{ink}" stroke-width="4"/>')
        P(f'<rect x="408" y="158" width="26" height="50" rx="7" fill="{M}" stroke="{ink}" stroke-width="4"/>')
        P(f'<ellipse cx="434" cy="183" rx="6" ry="20" fill="{hi}" stroke="{acc}" stroke-width="3"/>')
    limb(P,310,268,aR1,aR2,50,46,30,B,J,item_R)
    if kind=='code':   # holo screen in front of the hands
        P(f'<g transform="rotate(-6 390 300)"><rect x="330" y="236" width="128" height="92" rx="10" fill="#0B0F0C" fill-opacity="0.85" stroke="{acc}" stroke-width="4"/>')
        for i,w in enumerate((80,56,92,40,68)):
            P(f'<rect x="344" y="{252+i*14}" width="{w}" height="6" rx="3" fill="{acc}" opacity="{0.95-0.12*i:.2f}"/>')
        P('</g>')
    P('</g></svg>')
    return '\n'.join(o)
for k,sd in (('watch',7717),('code',1337),('scout',2026)):
    open(f'seal-{k}.svg','w').write(seal(k,sd))
