"""모바일 친화적인 HTML ebook 뼈대 생성기.

사용 예:
    from html_shell import render_shell
    html = render_shell(
        title="성장하는 교사, 다섯 가지 질문",
        subtitle="AI·디지털 기반 수업 실천 가이드북",
        publisher="서울특별시교육청 · 2025",
        toc=[("preface","발간사"),("ch1","1장 · ...")],
        body_html="<section ...>...</section>",
    )

주요 특징
- Pretendard 웹폰트 CDN
- 반응형 (모바일 드로어 TOC, 1100px 이상 sticky 사이드 TOC)
- 다크모드 자동 대응
- 읽기 진행률 바
- 맨 위로 플로팅 버튼
- 글자 크기 A-/A+ 버튼 7단계 (localStorage 저장)
- `figure.book-fig` 카드 스타일
- 장별 accent 색상 6개(indigo/violet/rose/amber/emerald/teal)
"""

CSS = r"""
:root{
  --font:"Pretendard",-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;
  --bg:#fafaf9;--fg:#1a1a1a;--muted:#6b6b6b;--line:#e7e7e5;--card:#fff;--accent:#6366f1;--maxw:760px;
  --accent-indigo:#6366f1;--accent-violet:#8b5cf6;--accent-rose:#f43f5e;
  --accent-amber:#f59e0b;--accent-emerald:#10b981;--accent-teal:#14b8a6;
  --fs-scale:1;
}
@media(prefers-color-scheme:dark){
  :root{--bg:#0f1115;--fg:#e9eaec;--muted:#9aa0a6;--line:#262a31;--card:#151821;}
}
*{box-sizing:border-box}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--font);font-size:calc(17px * var(--fs-scale));line-height:1.8;font-weight:400;letter-spacing:-0.01em;word-break:keep-all;overflow-wrap:break-word}

/* progress bar */
#progress{position:fixed;top:0;left:0;height:3px;width:0;background:linear-gradient(90deg,var(--accent-teal),var(--accent-violet));z-index:200;transition:width .1s linear}

/* topbar */
.topbar{position:sticky;top:0;z-index:100;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:saturate(160%) blur(10px);-webkit-backdrop-filter:saturate(160%) blur(10px);border-bottom:1px solid var(--line)}
.topbar-inner{max-width:var(--maxw);margin:0 auto;display:flex;align-items:center;gap:12px;padding:12px 20px}
.topbar h1{font-size:15px;margin:0;font-weight:700;color:var(--fg);flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.menu-btn{appearance:none;border:1px solid var(--line);background:var(--card);color:var(--fg);padding:8px 12px;border-radius:10px;cursor:pointer;font-size:14px;font-family:inherit}
.menu-btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

/* font-size controls */
.fs-group{display:inline-flex;align-items:center;gap:0;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--card)}
.fs-btn{appearance:none;border:0;background:transparent;color:var(--fg);width:34px;height:34px;font-size:16px;font-weight:700;cursor:pointer;font-family:inherit;display:flex;align-items:center;justify-content:center}
.fs-btn:hover{background:var(--bg)}
.fs-btn:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.fs-btn+.fs-btn{border-left:1px solid var(--line)}
.fs-label{font-size:12px;color:var(--muted);padding:0 4px;min-width:34px;text-align:center;user-select:none}

/* main */
main{max-width:var(--maxw);margin:0 auto;padding:28px 20px 120px}
.book-title{text-align:center;padding:48px 0 28px;border-bottom:1px solid var(--line);margin-bottom:32px}
.book-title .eng{color:var(--muted);font-size:13px;letter-spacing:.12em;margin:0 0 14px}
.book-title h1{font-size:28px;font-weight:900;margin:0 0 8px;line-height:1.35}
.book-title p.sub{margin:0;color:var(--muted);font-size:15px}
.book-title p.publisher{margin:18px 0 0;font-size:13px;color:var(--muted)}

/* chapters */
.chapter{margin:48px 0;padding-top:24px;border-top:3px solid var(--accent)}
.chapter>h2{font-size:26px;font-weight:900;margin:4px 0 4px;color:var(--accent);letter-spacing:-.02em}
.chapter-intro{margin:10px 0 0;color:var(--muted);font-size:15px;line-height:1.75}
.chapter-body h3{font-size:21px;font-weight:800;margin:48px 0 12px;line-height:1.4;color:var(--fg);padding-top:8px}
.chapter-body h4{font-size:19px;font-weight:800;margin:36px 0 10px;line-height:1.4}
.chapter-body p{margin:14px 0}
.chapter-body ul,.chapter-body ol{padding-left:24px;margin:14px 0}
.chapter-body li{margin:6px 0}
.chapter-body blockquote{margin:20px 0;padding:14px 20px;border-left:4px solid var(--accent);background:var(--card);border-radius:4px;color:var(--muted)}

/* tables (cmp-table): 모바일에서 가로 스크롤로 안전 처리, 얇은 검정 테두리로 가독성 확보 */
table.cmp-table{width:100%;display:block;overflow-x:auto;-webkit-overflow-scrolling:touch;border-collapse:collapse;font-size:14px;line-height:1.6;margin:28px 0;background:var(--card);border:1px solid #1a1a1a;max-width:100%}
table.cmp-table caption{caption-side:top;text-align:left;margin:0 0 10px;font-size:14px;color:var(--muted);line-height:1.5;font-weight:400}
table.cmp-table caption strong{color:var(--fg);font-weight:700}
table.cmp-table thead{background:color-mix(in srgb,var(--accent) 10%,var(--card))}
table.cmp-table th,table.cmp-table td{padding:10px 12px;border:1px solid #1a1a1a;vertical-align:top;text-align:left;word-break:keep-all;overflow-wrap:break-word;min-width:84px}
table.cmp-table th{color:var(--fg);font-weight:700;font-size:13px;white-space:nowrap}
@media(max-width:640px){
  table.cmp-table{font-size:13px;line-height:1.55}
  table.cmp-table th,table.cmp-table td{padding:8px 10px;min-width:96px}
}
@media(prefers-color-scheme:dark){
  table.cmp-table{background:#1b1f27;border-color:#e9eaec}
  table.cmp-table th,table.cmp-table td{border-color:#e9eaec}
}

/* figures */
.chapter-figures{margin:36px 0 10px}
figure.book-fig{margin:28px 0;padding:18px;border-radius:14px;background:var(--card);border:1px solid var(--line);box-shadow:0 2px 12px rgba(0,0,0,.05)}
figure.book-fig a{display:block;line-height:0}
figure.book-fig img{display:block;width:100%;height:auto;border-radius:6px}
figure.book-fig figcaption{margin-top:12px;font-size:14px;color:var(--muted);line-height:1.6;text-align:center}
figure.book-fig figcaption strong{display:block;color:var(--fg);font-size:15px;margin-bottom:2px}
.fig-grid{display:grid;grid-template-columns:1fr;gap:0}
@media(min-width:900px){.fig-grid{grid-template-columns:1fr 1fr;gap:18px}.fig-grid figure.book-fig{margin:14px 0}}
@media(prefers-color-scheme:dark){figure.book-fig{background:#1b1f27;border-color:#2a2f3a}}

/* accent colors */
.accent-indigo{--accent:var(--accent-indigo)}
.accent-violet{--accent:var(--accent-violet)}
.accent-rose{--accent:var(--accent-rose)}
.accent-amber{--accent:var(--accent-amber)}
.accent-emerald{--accent:var(--accent-emerald)}
.accent-teal{--accent:var(--accent-teal)}

/* sidebar TOC (desktop) */
#sidebar-toc{display:none}
@media(min-width:1100px){
  main{margin-left:calc(50% - 620px);margin-right:auto}
  #sidebar-toc{display:block;position:fixed;top:80px;left:calc(50% - 600px + 780px);width:220px;max-height:calc(100vh - 100px);overflow-y:auto;padding:16px;border-left:1px solid var(--line);font-size:13px}
  #sidebar-toc h2{font-size:13px;margin:0 0 12px;color:var(--muted);letter-spacing:.08em}
  #sidebar-toc ul{list-style:none;padding:0;margin:0}
  #sidebar-toc li{margin:2px 0}
  #sidebar-toc a{display:block;padding:6px 8px;color:var(--fg);text-decoration:none;border-radius:6px;line-height:1.45}
  #sidebar-toc a:hover{background:var(--bg)}
  .menu-btn{display:none}
}

/* backtop */
#backtop{position:fixed;right:18px;bottom:22px;z-index:150;width:46px;height:46px;border-radius:50%;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.15);display:none;align-items:center;justify-content:center;font-size:20px}
#backtop.show{display:flex}
#backtop:hover{background:var(--accent);color:#fff;border-color:var(--accent)}

/* source bar (원문 링크/다운로드) */
.source-bar{max-width:var(--maxw);margin:18px auto 0;padding:14px 18px;background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:10px;font-size:14px;color:var(--muted);display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px}
.source-bar .label{font-weight:700;color:var(--fg)}
.source-bar a{color:var(--accent);text-decoration:none;font-weight:600;word-break:break-all}
.source-bar a:hover{text-decoration:underline}
.source-bar .dl-icon{display:inline-block;margin-right:4px}
@media(min-width:1100px){.source-bar{margin-left:calc(50% - 620px)}}

/* drawer TOC */
#toc-drawer{position:fixed;inset:0;z-index:300;background:rgba(0,0,0,.45);display:none}
#toc-drawer.open{display:block}
#toc-drawer .panel{position:absolute;top:0;right:0;width:82%;max-width:360px;height:100%;background:var(--card);box-shadow:-10px 0 30px rgba(0,0,0,.2);padding:24px 20px;overflow-y:auto}
#toc-drawer h2{font-size:15px;margin:6px 0 12px;color:var(--muted);letter-spacing:.08em}
#toc-drawer ul{list-style:none;padding:0;margin:0}
#toc-drawer li a{display:block;padding:12px 8px;color:var(--fg);text-decoration:none;font-size:15px;line-height:1.5;border-bottom:1px solid var(--line)}
#toc-close{position:absolute;top:12px;right:12px;border:0;background:transparent;font-size:28px;cursor:pointer;color:var(--fg)}
"""

JS = r"""
(function(){
  var bar=document.getElementById('progress');
  var backtop=document.getElementById('backtop');
  function onScroll(){
    var h=document.documentElement.scrollHeight-window.innerHeight;
    var s=window.scrollY||window.pageYOffset;
    var p=h>0?(s/h)*100:0;
    bar.style.width=p+'%';
    if(s>400){backtop.classList.add('show');}else{backtop.classList.remove('show');}
  }
  window.addEventListener('scroll',onScroll,{passive:true});
  onScroll();
  var openBtn=document.getElementById('menu-btn');
  var drawer=document.getElementById('toc-drawer');
  var closeBtn=document.getElementById('toc-close');
  function open(){drawer.classList.add('open');}
  function close(){drawer.classList.remove('open');}
  if(openBtn)openBtn.addEventListener('click',open);
  if(closeBtn)closeBtn.addEventListener('click',close);
  drawer.addEventListener('click',function(e){if(e.target===drawer)close();});
  drawer.querySelectorAll('a').forEach(function(a){a.addEventListener('click',close);});
  backtop.addEventListener('click',function(){window.scrollTo({top:0,behavior:'smooth'});});

  var KEY='html_ebook_fs_scale';
  var STEPS=[0.85,0.92,1.0,1.08,1.17,1.27,1.38];
  var idx=2;
  try{
    var saved=parseFloat(localStorage.getItem(KEY));
    if(!isNaN(saved)){var best=2,diff=9;for(var i=0;i<STEPS.length;i++){var d=Math.abs(STEPS[i]-saved);if(d<diff){diff=d;best=i;}}idx=best;}
  }catch(e){}
  var fsLabel=document.getElementById('fs-label');
  function applyFs(){
    var s=STEPS[idx];
    document.documentElement.style.setProperty('--fs-scale',s);
    if(fsLabel)fsLabel.textContent=Math.round(s*100)+'%';
    try{localStorage.setItem(KEY,s);}catch(e){}
  }
  applyFs();
  var plus=document.getElementById('fs-plus'),minus=document.getElementById('fs-minus');
  if(plus)plus.addEventListener('click',function(){if(idx<STEPS.length-1){idx++;applyFs();}});
  if(minus)minus.addEventListener('click',function(){if(idx>0){idx--;applyFs();}});
})();
"""


def render_toc_items(toc):
    return "\n".join(f'<li><a href="#{id}">{label}</a></li>' for id, label in toc)


def render_shell(
    title: str,
    subtitle: str,
    publisher: str,
    toc: list,
    body_html: str,
    eng_title: str = "",
    description: str = "",
    source_url: str = "",
    source_file: str = "",
    source_label: str = "원문",
) -> str:
    """toc: [(section_id, label), ...]  /  body_html: 모든 <section>의 HTML

    source_url: 원문 웹페이지 URL (있으면 링크로 노출)
    source_file: 다운로드 가능한 로컬 원문 파일 경로 (URL이 없을 때 사용,
                 출력 폴더에 복사된 후 상대 경로로 링크됨)
    source_label: 원문 종류 라벨 (기본 "원문", 예: "원본 PDF", "원문 기사")
    """
    toc_items = render_toc_items(toc)
    desc = description or f"{title} 모바일 웹 버전"
    source_html = ""
    if source_url:
        source_html = (
            f'<div class="source-bar"><span class="label">{source_label}</span>'
            f'<a href="{source_url}" target="_blank" rel="noopener">{source_url}</a></div>'
        )
    elif source_file:
        import os
        fname = os.path.basename(source_file)
        source_html = (
            f'<div class="source-bar"><span class="label">{source_label}</span>'
            f'<a href="{fname}" download><span class="dl-icon">↓</span>{fname} 다운로드</a></div>'
        )
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@latest/dist/web/static/pretendard.min.css">
<style>{CSS}</style>
</head>
<body>
<div id="progress"></div>
<div class="topbar">
  <div class="topbar-inner">
    <h1>{title}</h1>
    <div class="fs-group" role="group" aria-label="글자 크기 조절">
      <button class="fs-btn" id="fs-minus" aria-label="글자 작게" title="글자 작게">A−</button>
      <span class="fs-label" id="fs-label" aria-live="polite">100%</span>
      <button class="fs-btn" id="fs-plus" aria-label="글자 크게" title="글자 크게">A+</button>
    </div>
    <button class="menu-btn" id="menu-btn" aria-label="목차 열기">목차</button>
  </div>
</div>
<nav id="sidebar-toc" aria-label="사이드 목차">
  <h2>목차</h2>
  <ul>{toc_items}</ul>
</nav>
{source_html}
<main>
  <header class="book-title">
    {f'<p class="eng">{eng_title}</p>' if eng_title else ''}
    <h1>{title}</h1>
    <p class="sub">{subtitle}</p>
    <p class="publisher">{publisher}</p>
  </header>
{body_html}
</main>
<button id="backtop" aria-label="맨 위로">↑</button>
<div id="toc-drawer" role="dialog" aria-modal="true" aria-label="목차">
  <div class="panel">
    <button id="toc-close" aria-label="닫기">×</button>
    <h2>목차</h2>
    <ul>{toc_items}</ul>
  </div>
</div>
<script>{JS}</script>
</body>
</html>
"""


def render_figure(src: str, title: str, caption: str = "", page: int | None = None) -> str:
    cap = f"<strong>{title}</strong>"
    if caption:
        cap += caption
    if page:
        cap += f'<br><span style="font-size:12px;opacity:.7">원문 {page}쪽</span>'
    return (
        f'<figure class="book-fig">'
        f'<a href="figs/{src}" target="_blank" rel="noopener">'
        f'<img loading="lazy" src="figs/{src}" alt="{title}"></a>'
        f"<figcaption>{cap}</figcaption></figure>"
    )
