"""Shared visual system for the native Streamlit workspace."""
from html import escape
import base64
from pathlib import Path
import streamlit as st
from version import get_version
ICON=Path(__file__).parent/'assets'/'linkabase.svg'
THEMES={
 'Midnight':dict(bg='#10141d',panel='#161c28',card='#1d2635',text='#edf3ff',muted='#adbed6',line='#334057',accent='#9bcaff',onaccent='#102b4b'),
 'Paper':dict(bg='#f7f8fa',panel='#f0f2f5',card='#ffffff',text='#20252d',muted='#657184',line='#e0e5ed',accent='#4263eb',onaccent='#ffffff'),
 'Ocean':dict(bg='#0d202b',panel='#12303d',card='#193d4c',text='#e7f7fb',muted='#b0ced8',line='#376171',accent='#8be3d2',onaccent='#07352d')}
THEMES.update({
 'Forest':dict(bg='#10201b',panel='#172b23',card='#20392e',text='#effaf2',muted='#b4cdbb',line='#3c5947',accent='#a8dfaa',onaccent='#17381e'),
 'Plum':dict(bg='#201724',panel='#2b2031',card='#382a40',text='#fbf0ff',muted='#d3bbdc',line='#624c6d',accent='#e2b5fa',onaccent='#38134b'),
 'Sand':dict(bg='#faf7f0',panel='#f0eadd',card='#fffdf8',text='#393225',muted='#645840',line='#d6cbbb',accent='#795323',onaccent='#ffffff'),
 'Slate':dict(bg='#eff3f5',panel='#e2e9ed',card='#ffffff',text='#203443',muted='#506675',line='#bcccd5',accent='#245a78',onaccent='#ffffff'),
 'Rose':dict(bg='#fff6f7',panel='#f6e8ec',card='#ffffff',text='#462c36',muted='#7a5262',line='#dec1cc',accent='#9e365c',onaccent='#ffffff'),
})


def styling(theme='Paper'):
 c=THEMES.get(theme,THEMES['Paper'])
 sidebar=c['card'] if theme in ('Paper','Sand','Slate','Rose') else c['panel']
 st.html(f"""<style>
 :root{{--lb-text:{c['text']};--lb-muted:{c['muted']};--lb-line:{c['line']};--lb-card:{c['card']};--lb-accent:{c['accent']}}}
 .stApp,h1,h2,h3,p,button,input,textarea,label{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
 [data-testid="stHeader"]{{height:0!important;background:transparent!important}}
 .stApp,[data-testid="stHeader"]{{background:{c['bg']};color:{c['text']}}}
 [data-testid="stAppDeployButton"],[data-testid="stDeployButton"]{{display:none}}
 .block-container{{max-width:1510px;padding:1.25rem 2.25rem 2.5rem}}
 [data-testid="stMainBlockContainer"]>[data-testid="stVerticalBlock"]{{gap:.85rem}}
 h1{{font-size:1.8rem!important;font-weight:650!important;letter-spacing:-.7px;line-height:1.3!important;padding:.2rem 0 .5rem!important}}
 h2{{font-size:1.15rem!important;font-weight:600!important}}h3{{font-size:1rem!important;font-weight:600!important}}
 h1,h2,h3,p,label,[data-testid="stMarkdownContainer"]{{color:{c['text']}}}
 [data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{{color:{c['muted']}!important}}
 [data-testid="stMetric"]{{background:{c['card']};border:1px solid {c['line']};border-radius:8px;padding:17px 20px}}
 [data-testid="stMetricValue"]{{font-size:1.9rem;font-weight:550;letter-spacing:-1px;color:{c['text']}}}
 [data-testid="stMetricLabel"] p{{font-size:.8rem;color:{c['muted']}}}
 [data-testid="stVerticalBlockBorderWrapper"],[data-testid="stContainer"]{{border-color:{c['line']}!important;border-radius:8px}}
 [data-testid="stForm"]{{background:{c['card']};border-color:{c['line']};border-radius:8px}}
 [data-baseweb="input"],[data-baseweb="input"]>div,[data-baseweb="base-input"],[data-baseweb="textarea"],textarea,input{{background:{c['card']}!important;color:{c['text']}!important}}
 input,textarea{{-webkit-text-fill-color:{c['text']}!important}}
 input::placeholder,textarea::placeholder{{color:{c['muted']}!important;-webkit-text-fill-color:{c['muted']}!important}}
 [data-baseweb="select"] div,[data-baseweb="select"] span,[data-baseweb="select"] [role="combobox"], [data-baseweb="popover"]>div,[data-baseweb="menu"],[role="listbox"],[role="option"]{{background:{c['card']}!important;color:{c['text']}!important}}
 [role="option"] *,[data-baseweb="menu"] *{{color:{c['text']}!important}}
 [data-baseweb="select"] svg,[data-baseweb="input"] svg{{color:{c['muted']}!important;fill:currentColor!important}}
 [data-testid="stExpander"] details,[data-testid="stExpander"] summary{{background:{c['card']};border-color:{c['line']};color:{c['text']}}}
 [data-baseweb="tab"] *,[data-baseweb="radio"] *,[data-baseweb="checkbox"] *{{color:{c['text']}!important}}
 a{{color:{c['accent']}}}
 button[kind^="secondary"],a[kind^="secondary"]{{background:{c['card']}!important;color:{c['text']}!important;border:1px solid {c['line']}!important;border-radius:6px!important}}
 button[kind^="secondary"] *,a[kind^="secondary"] *{{color:{c['text']}!important;-webkit-text-fill-color:{c['text']}!important}}
 button[kind^="primary"],a[kind^="primary"]{{background:{c['accent']}!important;border:1px solid {c['accent']}!important;border-radius:6px!important;color:{c['onaccent']}!important}}
 button[kind^="primary"] *,a[kind^="primary"] *{{color:{c['onaccent']}!important;-webkit-text-fill-color:{c['onaccent']}!important}}
 .st-key-page-add-action{{max-width:150px;margin-left:auto}}
 button p{{font-size:.82rem!important}}button{{transition:border-color .15s,background .15s}}
 button:disabled{{opacity:.5!important}}button:focus-visible,a:focus-visible{{outline:2px solid {c['accent']}!important;outline-offset:3px}}
 [data-testid="stSidebar"]{{background:{sidebar};border-right:1px solid {c['line']};min-width:224px!important;max-width:224px!important;width:224px!important}}
 [data-testid="stSidebarContent"]{{padding:0 16px!important}}
 [data-testid="stSidebarHeader"]{{height:32px;min-height:32px}}
 [data-testid="stSidebarUserContent"]{{padding:0 0 1.5rem!important}}
 [data-testid="stSidebar"] [data-testid="stVerticalBlock"]{{gap:.35rem}}
 [data-testid="stSidebar"] hr{{margin:.7rem 0;border-color:{c['line']}}}
 [data-testid="stSidebar"] button{{justify-content:flex-start;text-align:left;min-height:36px}}
 [data-testid="stSidebar"] div[class*="st-key-nav_"] button{{background:transparent!important;border:1px solid transparent!important;padding:8px 11px!important;box-shadow:none!important}}
 [data-testid="stSidebar"] div[class*="st-key-nav_"] button>div{{width:100%;justify-content:flex-start}}
 [data-testid="stSidebar"] div[class*="st-key-nav_"] button:hover{{background:{c['panel']}!important}}
 [data-testid="stSidebar"] div[class*="st-key-nav_"] button[kind="primary"]{{background:{c['panel']}!important;border-color:{c['line']}!important}}
 [data-testid="stSidebar"] div[class*="st-key-nav_"] button[kind="primary"] *{{color:{c['accent']}!important;-webkit-text-fill-color:{c['accent']}!important}}
 .st-key-library_tree{{border-left:1px solid {c['line']};margin-left:8px;padding-left:8px}}
 .st-key-library_tree button{{min-height:34px!important}}
 .st-key-topic_content{{background:{c['card']};padding:14px!important;border-color:{c['line']}!important}}
 .st-key-content_toolbar{{border-bottom:1px solid {c['line']};padding-bottom:12px}}
 .st-key-diagram_canvas{{border:1px solid {c['line']};border-radius:8px;overflow:hidden}}
 .st-key-diagram_toolbar{{padding:3px 0}}
 .st-key-diagram_preview{{background:{c['card']};border:1px solid {c['line']};border-radius:8px;padding:14px}}
 .st-key-note-add{{max-width:150px;margin-left:auto}}
 .st-key-topic_actions{{margin-bottom:0}}
 .lb-brand-row{{display:flex;align-items:center;gap:10px;padding:3px 0}}.lb-brand-row img{{width:29px;height:29px;flex-shrink:0}}
 .lb-brand{{font-size:23px;font-weight:650;letter-spacing:-.9px;color:{c['text']}}}
 .lb-eyebrow{{font-size:10px;letter-spacing:1px;text-transform:uppercase;color:{c['muted']};padding:12px 0 4px}}
 .lb-breadcrumb{{font-size:12px;color:{c['muted']};border-bottom:1px solid {c['line']};background:{sidebar};padding:17px 36px;margin:-12px -36px 13px;min-height:54px}}
 .lb-breadcrumb span{{margin:0 10px;opacity:.5}}
 [data-testid="stSidebar"] div[class*="st-key-nav_"] button[kind="primary"]{{background:color-mix(in srgb,{c['accent']} 9%,{sidebar})!important;border-color:transparent!important}}
 .lb-version{{font-size:10px;color:{c['muted']};padding-top:12px}}
 .lb-row-title{{font-size:13px;font-weight:550;line-height:1.6;color:{c['text']}}}
 .lb-row-meta{{font-size:11px;color:{c['muted']};margin-top:4px;line-height:1.6}}
 .lb-badge{{display:inline-block;font-size:10px;border:1px solid {c['line']};padding:2px 7px;border-radius:4px;color:{c['muted']};margin-left:7px;white-space:nowrap}}
 .lb-summary{{padding:18px 21px;background:{c['card']};border:1px solid {c['line']};border-radius:8px}}
 .lb-summary strong{{font-size:14px;font-weight:600}}.lb-summary p{{font-size:12px;color:{c['muted']};margin:7px 0 0}}
 div[class*="st-key-focusrow_"],div[class*="st-key-libraryrow_"],div[class*="st-key-recentrow_"]{{border-bottom:1px solid {c['line']};padding:12px 2px}}
 div[class*="st-key-libraryrow_"]:hover{{background:{c['panel']}}}
 div[class*="st-key-libraryrow_"] button{{background:transparent!important;border:0!important;justify-content:flex-start;text-align:left;padding-left:0!important}}
 div[class*="st-key-overview_"]{{background:{c['card']}}}
 div[class*="st-key-wikireader_"]{{background:{c['card']};padding:22px 28px;border-radius:7px}}
 div[class*="st-key-wikireader_"] h1{{font-size:1.7rem!important}}div[class*="st-key-wikireader_"] h2{{font-size:1.25rem!important;margin-top:20px}}div[class*="st-key-wikireader_"] p{{line-height:1.8}}
 [data-testid="stDialog"] [role="dialog"]{{background:{c['bg']};color:{c['text']};width:min(1040px,94vw);max-width:1040px;border:1px solid {c['line']};border-radius:12px}}
 @media(max-width:768px){{[data-testid="stHeader"]{{height:2.5rem!important}}.lb-breadcrumb{{margin:0 0 12px;padding:10px 0;background:transparent}}.block-container{{padding:2.5rem 1rem 2rem}}h1{{font-size:1.55rem!important}}div[class*="st-key-wikireader_"]{{padding:16px}}}}
 @media(prefers-reduced-motion:reduce){{*,*::before,*::after{{transition:none!important;animation:none!important}}}}
 </style>""")

def footer():
 st.sidebar.markdown(f'<div class="lb-version">Linkabase · v{escape(get_version())} · Self-hosted</div>',unsafe_allow_html=True)

def logo_image():
 encoded=base64.b64encode(ICON.read_bytes()).decode()
 return '<img alt="Linkabase" src="data:image/svg+xml;base64,'+encoded+'" width="29" height="29">'

def brand():
 st.html('<div class="lb-brand-row">'+logo_image()+'<span class="lb-brand">Linkabase</span></div>')


def eyebrow(text):
 st.html('<div class="lb-eyebrow">'+escape(text)+'</div>')

def breadcrumb(*parts):
 st.html('<div class="lb-breadcrumb">'+'<span>/</span>'.join(escape(part) for part in parts)+'</div>')

def item_label(title,detail,badge=''):
 chip='<span class="lb-badge">'+escape(badge)+'</span>' if badge else ''
 st.html('<div class="lb-row-title">'+escape(title)+chip+'</div><div class="lb-row-meta">'+escape(detail)+'</div>')
