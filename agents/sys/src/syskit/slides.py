"""A slide deck as one web page, for a large screen.

    deck = Deck("Title")
    deck.title_slide("Title", "Subtitle", "Footer line")
    deck.slide("Heading", '<img src="figs/diagram.svg" alt="">', note="One line under it.")
    deck.write(folder / "index.html")

Every slide is drawn on a 1600 by 900 stage that is scaled to the window.
Keys: right arrow, space or page down for the next slide; left arrow or page
up for the previous; Home and End; F for full screen. A click on the right or
left half of the screen does the same. ``#7`` in the address opens slide 7.
Printing gives one slide per page.
"""

from __future__ import annotations

import html
from pathlib import Path

CSS = """
:root { --ink:#0f172a; --muted:#475569; --line:#e2e8f0; --blue:#1d4ed8; --orange:#c2410c; }
* { box-sizing:border-box; }
html, body { margin:0; height:100%; background:#0b1120; overflow:hidden;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
#stage { position:absolute; left:50%; top:50%; width:1600px; height:900px;
  transform-origin:center center; background:#ffffff; overflow:hidden; }
.slide { position:absolute; inset:0; display:none; padding:54px 70px 60px; color:var(--ink); }
.slide.on { display:flex; flex-direction:column; }
.slide h2 { margin:0 0 6px; font-size:50px; font-weight:700; letter-spacing:-0.5px; }
.slide p.lead { margin:0 0 14px; font-size:27px; color:var(--muted); }
.slide .body { flex:1; min-height:0; display:flex; align-items:center; justify-content:center; }
.slide .body > img, .slide .body > svg { max-width:100%; max-height:100%; }
.slide p.note { margin:10px 0 0; font-size:24px; color:var(--muted); text-align:center; }
.slide.title { background:#0f172a; color:#f8fafc; justify-content:center; padding:0 110px; }
.slide.title h1 { margin:0 0 18px; font-size:92px; letter-spacing:-2px; }
.slide.title p { margin:0; font-size:38px; color:#cbd5e1; max-width:1200px; line-height:1.3; }
.slide.title p.foot { position:absolute; left:110px; bottom:70px; font-size:25px; color:#94a3b8; }
.pair { display:grid; grid-template-columns:1fr 1fr; gap:36px; width:100%; height:100%; }
.pair figure { margin:0; display:flex; flex-direction:column; min-height:0; }
.pair figure img { flex:1; min-height:0; width:100%; object-fit:contain; }
.pair figcaption { font-size:27px; line-height:1.3; text-align:center; padding-top:8px; }
.pair figcaption b { color:var(--orange); font-weight:700; }
table.big { border-collapse:collapse; width:100%; font-size:28px; }
table.big th, table.big td { text-align:left; padding:17px 22px; vertical-align:top;
  border-bottom:2px solid var(--line); }
table.big th { font-size:24px; color:var(--muted); font-weight:600; }
table.big td:first-child { font-weight:650; white-space:nowrap; }
table.big td.new { color:var(--orange); }
.cols { display:grid; grid-template-columns:repeat(3, 1fr); gap:34px; width:100%; align-self:start;
  margin-top:26px; }
.cols div { border-top:8px solid var(--blue); padding-top:16px; }
.cols div.started { border-color:var(--orange); } .cols div.next { border-color:#94a3b8; }
.cols h3 { margin:0 0 14px; font-size:40px; }
.cols ul { margin:0; padding-left:28px; font-size:30px; line-height:1.45; color:var(--muted); }
#bar { position:absolute; left:0; bottom:0; height:6px; background:var(--blue); width:0;
  transition:width .2s; }
#count { position:absolute; right:26px; bottom:16px; font-size:20px; color:#94a3b8; }
@media print {
  @page { size:1600px 900px; margin:0; }
  html, body { height:auto; overflow:visible; background:#fff; }
  #stage { position:static; transform:none !important; height:auto; }
  .slide { display:flex !important; flex-direction:column; position:relative; height:900px;
    page-break-after:always; }
  #bar, #count { display:none; }
}
"""

SCRIPT = """
const slides = [...document.querySelectorAll('.slide')];
const stage = document.getElementById('stage');
let at = 0;
function fit() {
  const k = Math.min(innerWidth / 1600, innerHeight / 900);
  stage.style.transform = `translate(-50%, -50%) scale(${k})`;
}
function show(n) {
  at = Math.max(0, Math.min(slides.length - 1, n));
  slides.forEach((s, i) => s.classList.toggle('on', i === at));
  document.getElementById('bar').style.width = (100 * (at + 1) / slides.length) + '%';
  document.getElementById('count').textContent = (at + 1) + ' / ' + slides.length;
  history.replaceState(null, '', '#' + (at + 1));
}
addEventListener('resize', fit);
addEventListener('keydown', e => {
  const next = ['ArrowRight', 'PageDown', ' ', 'Enter'];
  const back = ['ArrowLeft', 'PageUp', 'Backspace'];
  if (next.includes(e.key)) { show(at + 1); e.preventDefault(); }
  else if (back.includes(e.key)) { show(at - 1); e.preventDefault(); }
  else if (e.key === 'Home') show(0);
  else if (e.key === 'End') show(slides.length - 1);
  else if (e.key === 'f' || e.key === 'F') {
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen();
  }
});
addEventListener('click', e => {
  if (!e.target.closest('a')) show(at + (e.clientX > innerWidth / 2 ? 1 : -1));
});
addEventListener('hashchange', () => show((parseInt(location.hash.slice(1)) || 1) - 1));
fit(); show((parseInt(location.hash.slice(1)) || 1) - 1);
"""


class Deck:
    def __init__(self, title: str) -> None:
        self.title = title
        self.slides: list[str] = []

    def title_slide(self, title: str, subtitle: str, foot: str = "") -> None:
        foot_html = f'<p class="foot">{html.escape(foot)}</p>' if foot else ""
        self.slides.append(
            f'<section class="slide title"><h1>{html.escape(title)}</h1>'
            f"<p>{html.escape(subtitle)}</p>{foot_html}</section>"
        )

    def slide(self, heading: str, body: str, *, lead: str = "", note: str = "") -> None:
        """A slide with a heading and a body of HTML (an image, a diagram, a table)."""
        lead_html = f'<p class="lead">{html.escape(lead)}</p>' if lead else ""
        note_html = f'<p class="note">{html.escape(note)}</p>' if note else ""
        self.slides.append(
            f'<section class="slide"><h2>{html.escape(heading)}</h2>{lead_html}'
            f'<div class="body">{body}</div>{note_html}</section>'
        )

    def figure_slide(self, heading: str, image: str, *, lead: str = "", note: str = "") -> None:
        self.slide(heading, f'<img src="{html.escape(image)}" alt="">', lead=lead, note=note)

    def pair_slide(
        self, heading: str, figures: list[tuple[str, str]], *, lead: str = "", note: str = ""
    ) -> None:
        """Two pictures side by side; each is (image path, caption as HTML)."""
        cells = "".join(
            f'<figure><img src="{html.escape(image)}" alt=""><figcaption>{caption}</figcaption>'
            "</figure>"
            for image, caption in figures
        )
        self.slide(heading, f'<div class="pair">{cells}</div>', lead=lead, note=note)

    def render(self) -> str:
        return (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{html.escape(self.title)}</title><style>{CSS}</style></head><body>"
            f'<div id="stage">{"".join(self.slides)}<div id="bar"></div>'
            f'<div id="count"></div></div><script>{SCRIPT}</script></body></html>'
        )

    def write(self, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.render(), encoding="utf-8")
        return target
