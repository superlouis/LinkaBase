"""Small visual system. Button text is styled separately from document text."""
from pathlib import Path
import streamlit as st
from version import __version__
ICON=Path(__file__).parent/'assets'/'linkabase.png'
THEMES={
 'Midnight':dict(bg='#10141d',panel='#161c28',card='#1d2635',text='#edf3ff',muted='#adbed6',line='#334057',accent='#9bcaff',onaccent='#102b4b'),
 'Paper':dict(bg='#f5f7fc',panel='#edf1f8',card='#ffffff',text='#1d2c43',muted='#536580',line='#cbd5e3',accent='#245bd6',onaccent='#ffffff'),
 'Ocean':dict(bg='#0d202b',panel='#12303d',card='#193d4c',text='#e7f7fb',muted='#b0ced8',line='#376171',accent='#8be3d2',onaccent='#07352d')}
THEMES.update({
 'Forest':dict(bg='#10201b',panel='#172b23',card='#20392e',text='#effaf2',muted='#b4cdbb',line='#3c5947',accent='#a8dfaa',onaccent='#17381e'),
 'Plum':dict(bg='#201724',panel='#2b2031',card='#382a40',text='#fbf0ff',muted='#d3bbdc',line='#624c6d',accent='#e2b5fa',onaccent='#38134b'),
 'Sand':dict(bg='#faf7f0',panel='#f0eadd',card='#fffdf8',text='#393225',muted='#645840',line='#d6cbbb',accent='#795323',onaccent='#ffffff'),
 'Slate':dict(bg='#eff3f5',panel='#e2e9ed',card='#ffffff',text='#203443',muted='#506675',line='#bcccd5',accent='#245a78',onaccent='#ffffff'),
 'Rose':dict(bg='#fff6f7',panel='#f6e8ec',card='#ffffff',text='#462c36',muted='#7a5262',line='#dec1cc',accent='#9e365c',onaccent='#ffffff'),
})

# Sidebar surfaces are deliberately distinct from the reading canvas.
SIDEBARS={
 'Midnight':('#182b46','#122039','#304969'),
 'Paper':('#dde7f7','#e8eef9','#b8cae5'),
 'Ocean':('#064956','#103644','#39717b'),
 'Forest':('#234631','#193729','#4a7058'),
 'Plum':('#432b59','#33213f','#705382'),
 'Sand':('#e8dac0','#f0e5d1','#c9b38e'),
 'Slate':('#d3e2eb','#e1ebf1','#a9c1d0'),
 'Rose':('#edd3e0','#f3e0e9','#cfacc1'),
}

def styling(theme='Midnight'):
 c=THEMES.get(theme,THEMES['Midnight'])
 sidebar,sidebar_end,sidebar_line=SIDEBARS.get(theme,SIDEBARS['Midnight'])
 primary='button[kind^="primary"], [data-testid^="stBaseButton-primary"], [data-testid^="stBaseLinkButton-primary"], a[kind^="primary"]'
 secondary='button[kind^="secondary"], [data-testid^="stBaseButton-secondary"], [data-testid^="stBaseLinkButton-secondary"], a[kind^="secondary"]'
 def descendants(selectors):return ','.join(x.strip()+' *' for x in selectors.split(','))
 st.markdown(f'''<style>
 :root{{--lb-text:{c['text']};--lb-muted:{c['muted']};--lb-line:{c['line']}}}
 .stApp,[data-testid="stHeader"]{{background:{c['bg']};color:{c['text']}}}
 [data-testid="stSidebar"]{{background:{c['panel']};border-right:1px solid {c['line']}}}
 [data-testid="stAppDeployButton"],[data-testid="stDeployButton"],.stDeployButton,.stAppDeployButton{{display:none!important}}
 .block-container{{padding-top:3.8rem!important;padding-bottom:3rem;max-width:1400px}}
 h1{{font-size:1.85rem!important;line-height:1.4!important;padding:.4rem 0 .6rem!important;letter-spacing:-.8px;overflow:visible!important}}
 h2{{font-size:1.35rem!important;letter-spacing:-.3px}}h3{{font-size:1.1rem!important}}
 h1,h2,h3,p,label,[data-testid="stMarkdownContainer"]{{color:{c['text']}}}
 [data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{{color:{c['muted']}!important;opacity:1!important}}
 [data-testid="stMetric"]{{background:{c['card']};border:1px solid {c['line']};border-radius:12px;padding:18px}}
 [data-testid="stMetricValue"]{{color:{c['text']}}}
 [data-testid="stVerticalBlockBorderWrapper"]{{border-radius:14px;border-color:{c['line']}!important}}
 [data-baseweb="input"],[data-baseweb="input"]>div,[data-baseweb="base-input"],[data-baseweb="textarea"],textarea,input{{background:{c['card']}!important;color:{c['text']}!important}}
 input,textarea{{-webkit-text-fill-color:{c['text']}!important}}
 input::placeholder,textarea::placeholder{{-webkit-text-fill-color:{c['muted']}!important;color:{c['muted']}!important;opacity:1}}
 [data-baseweb="select"] div,[data-baseweb="select"] span,[data-baseweb="select"] [role="combobox"]{{background:{c['card']}!important;color:{c['text']}!important}}
 [data-baseweb="select"] svg,[data-baseweb="input"] svg{{color:{c['text']}!important;fill:currentColor!important}}
 [data-baseweb="popover"]>div,[data-baseweb="menu"],[role="listbox"],[role="option"]{{background:{c['card']}!important;color:{c['text']}!important}}
 [role="option"] *,[data-baseweb="menu"] *{{color:{c['text']}!important}}
 [role="option"][aria-selected="true"]{{outline:1px solid {c['accent']}}}
 [data-testid="stFileUploaderDropzone"],[data-testid="stForm"]{{background:{c['panel']};border-color:{c['line']}!important}}
 [data-testid="stFileUploaderDropzone"] *{{color:{c['text']}}}
 [data-testid="stExpander"] details,[data-testid="stExpander"] summary{{background:{c['panel']}!important;color:{c['text']}!important;border-color:{c['line']}!important}}
 [data-testid="stExpander"] summary *{{color:{c['text']}!important;-webkit-text-fill-color:{c['text']}!important}}
 [data-testid="stDialog"] [role="dialog"]{{background:{c['panel']};color:{c['text']}}}
 [data-baseweb="tab"] *,[data-baseweb="radio"] *,[data-baseweb="checkbox"] *{{color:{c['text']}!important}}
 a{{color:{c['accent']}}}
 {secondary}{{background:{c['card']}!important;color:{c['text']}!important;border:1px solid {c['line']}!important;border-radius:9px!important}}
 {descendants(secondary)}{{color:{c['text']}!important;-webkit-text-fill-color:{c['text']}!important}}
 {primary}{{background:{c['accent']}!important;color:{c['onaccent']}!important;border:1px solid {c['accent']}!important;border-radius:9px!important}}
 {descendants(primary)}{{color:{c['onaccent']}!important;-webkit-text-fill-color:{c['onaccent']}!important}}
 button:disabled,button:disabled *{{color:{c['muted']}!important;-webkit-text-fill-color:{c['muted']}!important;background:{c['panel']}!important;opacity:.85!important}}
 button:focus-visible,a:focus-visible{{outline:3px solid {c['accent']}!important;outline-offset:3px}}
 button{{transition:background .15s ease,box-shadow .15s ease}}
 [data-testid="stSidebar"] button{{text-align:left;justify-content:flex-start}}
 [data-testid="stSidebar"] [data-testid="stExpander"] details{{border:0!important}}
 [data-testid="stDialog"] [role="dialog"]{{width:min(1040px,94vw);max-width:1040px;border-radius:16px}}
 div[class*="st-key-libraryrow_"]{{padding:8px 10px;border-bottom:1px solid {c['line']};border-radius:8px}}
 div[class*="st-key-libraryrow_"]:hover{{background:{c['panel']}}}
 div[class*="st-key-libraryrow_"] button{{background:transparent!important;border:0!important;text-align:left;justify-content:flex-start;padding-left:0!important}}
 .lb-eyebrow{{font:600 10px monospace;letter-spacing:1.8px;color:{c['muted']};text-transform:uppercase;margin:8px 0}}
 .lb-version{{position:fixed;bottom:12px;left:22px;z-index:30;padding:6px 10px;background:{c['panel']};color:{c['muted']};font:11px monospace;border:1px solid {c['line']};border-radius:8px}}
 [data-testid="stSidebarUserContent"]{{padding-top:2rem!important;padding-bottom:4rem!important}}
 [data-testid="stSidebar"] [data-testid="stVerticalBlock"]{{gap:.6rem}}
 [data-testid="stSidebar"] button{{min-height:36px!important}}
 [data-testid="stSidebar"] hr{{margin:.65rem 0}}
 [data-testid="stSidebar"] [data-testid="stCaptionContainer"]{{opacity:1!important}}
 .lb-brand{{font-size:23px;font-weight:750;letter-spacing:-.8px;line-height:1.2;color:{c['text']}}}

 [data-testid="stSidebar"] div[class*="st-key-nav_"] button>div{{width:100%;justify-content:flex-start!important}}
 /* Visual refresh: navigation has its own surface; content stays calm. */
 [data-testid="stSidebar"]{{background:linear-gradient(160deg,{sidebar} 0%,{sidebar_end} 100%)!important;border-right:1px solid {sidebar_line};box-shadow:8px 0 32px #0000000d}}
 [data-testid="stSidebar"] [data-testid="stExpander"] details,[data-testid="stSidebar"] [data-testid="stExpander"] summary{{background:transparent!important;border:0!important}}
 [data-testid="stSidebar"] hr{{border-color:{sidebar_line};opacity:.8}}
 [data-testid="stSidebar"] div[class*="st-key-nav_"] button{{min-height:42px!important;border:1px solid transparent!important;border-radius:10px!important;padding:9px 12px!important;justify-content:flex-start!important;box-shadow:none!important}}
 [data-testid="stSidebar"] div[class*="st-key-nav_"] button[kind="secondary"]{{background:transparent!important}}
 [data-testid="stSidebar"] div[class*="st-key-nav_"] button[kind="secondary"]:hover{{background:{c['card']}!important;border-color:{sidebar_line}!important}}
 [data-testid="stSidebar"] div[class*="st-key-nav_"] button[kind="primary"]{{background:{c['card']}!important;border-color:{sidebar_line}!important;box-shadow:inset 3px 0 0 {c['accent']}!important}}
 [data-testid="stSidebar"] div[class*="st-key-nav_"] button[kind="primary"],[data-testid="stSidebar"] div[class*="st-key-nav_"] button[kind="primary"] *{{color:{c['text']}!important;-webkit-text-fill-color:{c['text']}!important}}
 [data-testid="stSidebar"] [data-testid="stExpander"] summary{{font-size:.83rem;font-weight:650}}
 [data-testid="stSidebarUserContent"]{{padding-left:1.25rem!important;padding-right:1.25rem!important}}
 [data-testid="stSidebar"] [data-testid="stVerticalBlock"]{{gap:.6rem}}
 .lb-brand{{font-size:25px;letter-spacing:-1px}}
 .lb-version{{background:{sidebar_end};border-color:{sidebar_line};border-radius:20px;font:11px system-ui;padding:5px 11px}}
 .lb-eyebrow{{font:650 10px/1.6 system-ui;letter-spacing:2px;margin:0;padding:6px 0;min-height:28px}}
 [data-testid="stMetric"]{{background:linear-gradient(145deg,{c['card']},{c['panel']});box-shadow:0 6px 20px #0000000a;border-radius:16px!important;border-top:2px solid {c['accent']}}}
 [data-testid="stMetricLabel"]{{font-size:.8rem!important}}
 [data-testid="stMetricValue"]{{font-weight:650;letter-spacing:-1px}}
 [data-testid="stDialog"] [role="dialog"]{{box-shadow:0 30px 100px #00000055;border:1px solid {c['line']};border-radius:20px}}
 button{{transition:background .16s ease,border-color .16s ease,box-shadow .16s ease}}
 button[kind="primary"]:hover{{box-shadow:0 4px 16px #00000020;filter:brightness(1.04)}}
 div[class*="st-key-libraryrow_"]{{padding:12px 14px;transition:background .16s ease}}
 @media(prefers-reduced-motion:reduce){{*,*::before,*::after{{transition:none!important;scroll-behavior:auto!important}}}}
 </style>''',unsafe_allow_html=True)
def footer():
 st.sidebar.markdown(f'<div class="lb-version">Linkabase · v{__version__}</div>',unsafe_allow_html=True)
def brand():
 a,b=st.columns([1,4],vertical_alignment='center')
 a.image(str(ICON),width=36);b.markdown('<div class="lb-brand">Linkabase</div>',unsafe_allow_html=True)
 st.caption('Work and knowledge, connected.')
def eyebrow(text):
 import html
 st.markdown('<div class="lb-eyebrow">'+html.escape(text)+'</div>',unsafe_allow_html=True)
