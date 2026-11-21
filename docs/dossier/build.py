import asyncio, os, re, sys
from playwright.async_api import async_playwright
from pypdf import PdfReader
FOOT = '<div style="font-size:7.5pt;color:#6b7380;width:100%;padding:0 15mm;display:flex;justify-content:space-between;font-family:Helvetica"><span>ENSO Explorer — Dossier de conception — Katia Sakri</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'
async def render(html_path, out):
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome")
        pg = await b.new_page()
        await pg.goto("file://" + html_path); await pg.wait_for_timeout(500)
        await pg.pdf(path=out, format="A4", print_background=True, display_header_footer=True,
                     header_template="<span></span>", footer_template=FOOT,
                     margin={"top":"14mm","bottom":"16mm","left":"15mm","right":"15mm"})
        await b.close()
src = open("dossier.html").read()
titles = ["1. Besoin et contexte","2. Fonctionnel et UX","3. UML et modélisation","4. Architecture technique","5. Organisation du projet","6. Qualité et sécurité","7. Déploiement proposé","8. Bilan et sources"]
tmp = src
for i in range(1,9): tmp = tmp.replace("{{p%d}}"%i, "00")
open("_tmp.html","w").write(tmp)
asyncio.run(render(os.path.abspath("_tmp.html"),"_tmp.pdf"))
r = PdfReader("_tmp.pdf"); pages={}
for n,pgx in enumerate(r.pages,1):
    t = pgx.extract_text()
    for i,ti in enumerate(titles,1):
        if i not in pages and n>1 and re.search(r'^\s*'+re.escape(ti), t, re.M): pages[i]=n
print("pages totales:", len(r.pages), pages)
final = src
for i in range(1,9): final = final.replace("{{p%d}}"%i, str(pages.get(i,"?")))
open("_final.html","w").write(final)
asyncio.run(render(os.path.abspath("_final.html"),"Dossier_conception_ENSO_Explorer_Katia_Sakri.pdf"))
print("final:", len(PdfReader("Dossier_conception_ENSO_Explorer_Katia_Sakri.pdf").pages))
