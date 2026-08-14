"""MCP server for verifiable Puerto Rico jurisprudence research.

Source-first: legal authorities, citations, names, dates, case numbers and
quotations are never invented. Search results are grounded in public sources;
quoted passages come only from text extracted from the source document.
"""
from __future__ import annotations

import asyncio
import io
import re
from dataclasses import dataclass, asdict
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from pypdf import PdfReader

mcp = FastMCP("puerto-rico-sentencias")

OFFICIAL_INDEX = "https://poderjudicial.pr/tribunal-supremo/decisiones-del-tribunal-supremo/"
LEXJURIS_SEARCH = "https://www.lexjuris.com/lexbusquedas.htm"
ALLOWED_HOSTS = {"poderjudicial.pr", "www.poderjudicial.pr", "dts.poderjudicial.pr", "lexjuris.com", "www.lexjuris.com"}
TIMEOUT = 12.0
MAX_RESULTS = 20
MAX_DOCUMENT_CHARS = 120_000
PDFS_PER_YEAR = 3
MAX_PDFS = 24

@dataclass
class Decision:
    title: str
    url: str
    source: str
    citation: str = ""
    case_number: str = ""
    date: str = ""
    judge: str = ""
    subject: str = ""
    snippet: str = ""
    page: int | None = None
    relevance_score: float = 0.0
    verified: bool = False
    verification_status: str = "unverified"

def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def normalize_text(text: str) -> str:
    text = (text or "").lower()
    for a, b in (("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ü","u")):
        text = text.replace(a, b)
    return clean(re.sub(r"[^a-z0-9ñ\s]", " ", text))

def normalize_citation(value: str) -> str:
    return clean(value).upper().replace("-", " ")

def extract_citation(text: str) -> str:
    m = re.search(r"\b((?:19|20)\d{2})\s*TSPR\s*(\d{1,4})\b", text or "", re.I)
    return clean(m.group(0)) if m else ""

def extract_case_number(text: str) -> str:
    for pat in (r"\b([A-Z]{1,5}-\d{2,5}-\d{1,6})\b", r"\b([A-Z]{1,5}\s+\d{2,5}-\d{1,6})\b"):
        m = re.search(pat, text or "", re.I)
        if m: return clean(m.group(1))
    return ""

def source_name(url: str) -> str:
    return "LexJuris" if "lexjuris.com" in url.lower() else "Poder Judicial de Puerto Rico"

def allowed_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme == "https" and p.hostname in ALLOWED_HOSTS
    except Exception:
        return False

async def fetch_response(client: httpx.AsyncClient, url: str) -> httpx.Response:
    if not allowed_url(url): raise ValueError("URL no permitida")
    r = await client.get(url)
    r.raise_for_status()
    return r

async def fetch_text(client: httpx.AsyncClient, url: str) -> str:
    return (await fetch_response(client, url)).text

def year_from_url(url: str) -> int | None:
    m = re.search(r"decisiones-del-tribunal-supremo-((?:19|20)\d{2})", url.lower())
    return int(m.group(1)) if m else None

def looks_like_year_page(url: str) -> bool:
    return bool(re.search(r"decisiones-del-tribunal-supremo-((?:19|20)\d{2})/?$", url.lower()))

def parse_index(html: str, base: str, year: int | None = None) -> list[Decision]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[Decision] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        text = clean(a.get_text(" ", strip=True)); href = urljoin(base, a["href"])
        hay = f"{text} {href}"; cit = extract_citation(hay); low = href.lower()
        if not (cit or low.split("?",1)[0].endswith(".pdf") or any(x in hay.upper() for x in ("SENTENCIA","OPINIÓN","OPINION","TSPR"))): continue
        cy = int(re.search(r"\d{4}", cit).group()) if cit else year_from_url(href)
        if year is not None and cy is not None and cy != year: continue
        if href in seen: continue
        seen.add(href)
        verified = bool(cit and href)
        out.append(Decision(text, href, source_name(href), cit, extract_case_number(hay), verified=verified,
                            verification_status="verified_source_identifier" if verified else "source_found_identifier_unconfirmed"))
    return out

def sample_evenly(items: list[Decision], n: int) -> list[Decision]:
    if len(items) <= n: return items
    idxs = sorted({round(i*(len(items)-1)/(n-1)) for i in range(n)}) if n > 1 else [0]
    return [items[i] for i in idxs]

LEGAL_SYNONYMS = {
    "pension alimenticia": ["pension alimenticia","pensión alimenticia","alimentos","obligacion alimentaria","obligación alimentaria","alimentante","alimentista","manutencion","manutención","cuota alimentaria","sustento"],
    "alimentos": ["alimentos","pension alimenticia","pensión alimenticia","obligacion alimentaria","obligación alimentaria","alimentante","alimentista","manutencion","manutención"],
    "custodia": ["custodia","guarda","patria potestad","relaciones paterno filiales"],
    "divorcio": ["divorcio","divorciado","disolucion matrimonial","disolución matrimonial"],
    "menor": ["menor","menores","niño","niña","hijo","hija"],
}

def query_terms(query: str) -> list[str]:
    raw = [x for x in re.findall(r"[\wÀ-ÿ]+", query.lower()) if len(x) > 2]
    norm = normalize_text(query); out = list(raw)
    for key, vals in LEGAL_SYNONYMS.items():
        if normalize_text(key) in norm or any(normalize_text(v) in norm for v in vals): out += vals
    seen: set[str] = set(); result=[]
    for x in out:
        nx=normalize_text(x)
        if nx and nx not in seen: seen.add(nx); result.append(x)
    return result

def extract_html_document(html: str) -> tuple[str,list[str]]:
    soup=BeautifulSoup(html,"html.parser")
    for tag in soup(["script","style","noscript","nav","footer"]): tag.decompose()
    blocks=[clean(t.get_text(" ",strip=True)) for t in soup.find_all(["p","blockquote","li"])]
    blocks=[b for b in blocks if len(b)>=20]
    text="\n\n".join(blocks) if blocks else clean(soup.get_text(" ",strip=True))
    return text, (blocks or ([text] if text else []))

def extract_pdf_document(content: bytes) -> tuple[str,list[str]]:
    reader=PdfReader(io.BytesIO(content)); pages=[]; paragraphs=[]
    for pn,page in enumerate(reader.pages,1):
        raw=(page.extract_text() or "").replace("\r","\n")
        blocks=[clean(x) for x in re.split(r"\n\s*\n+",raw) if clean(x)]
        for b in blocks: paragraphs.append(f"[página {pn}] {b}")
        if blocks: pages.append("\n\n".join(blocks))
    return "\n\n".join(pages), paragraphs

def find_relevant_paragraphs(paragraphs: list[str], terms: str|list[str], limit: int=8) -> list[dict[str,Any]]:
    vals=terms if isinstance(terms,list) else query_terms(terms)
    nts=[normalize_text(x) for x in vals if normalize_text(x)]
    scored=[]
    for i,p in enumerate(paragraphs):
        low=normalize_text(p); hits=sum(1 for t in nts if t in low)
        if hits: scored.append((hits+(2 if hits>=2 else 0),i,p))
    scored.sort(key=lambda x:(-x[0],x[1]))
    return [{"numero":i+1,"texto":p,"coincidencias":s} for s,i,p in scored[:limit]]

def score_document(decision: Decision, text: str, paragraphs: list[str], query: str) -> tuple[float,dict[str,Any]|None]:
    terms=query_terms(query); low=normalize_text(text[:MAX_DOCUMENT_CHARS]); score=2.0 if decision.citation else 0.0
    for t in terms:
        nt=normalize_text(t); c=min(low.count(nt),5) if nt else 0
        if c: score += 1.0 + min(c,4)*0.7
    rel=find_relevant_paragraphs(paragraphs,terms,6)
    if rel: score += min(10.0,sum(x["coincidencias"] for x in rel)/2)
    return score, rel[0] if rel else None

async def get_year_links(client: httpx.AsyncClient, main_html: str, year: int) -> list[Decision]:
    links=parse_index(main_html,OFFICIAL_INDEX)
    year_links=[x for x in links if year_from_url(x.url)==year]
    direct=[x for x in year_links if x.url.lower().split("?",1)[0].endswith(".pdf")]
    pages=[x for x in year_links if looks_like_year_page(x.url)]
    if not pages: return direct
    try:
        nested=parse_index(await fetch_text(client,pages[0].url),pages[0].url,year)
        return dedupe(direct+nested)
    except Exception:
        return direct

def dedupe(items: list[Decision]) -> list[Decision]:
    seen=set(); out=[]
    for x in items:
        if x.url not in seen: seen.add(x.url); out.append(x)
    return out

async def read_decision(client: httpx.AsyncClient, decision: Decision, query: str) -> Decision:
    try:
        r=await fetch_response(client,decision.url); ct=r.headers.get("content-type","").lower()
        pdf="application/pdf" in ct or r.url.path.lower().endswith(".pdf") or decision.url.lower().split("?",1)[0].endswith(".pdf")
        text,paragraphs=extract_pdf_document(r.content) if pdf else extract_html_document(r.text)
        if not text: return decision
        score,best=score_document(decision,text,paragraphs,query); decision.relevance_score=round(score,2)
        if best:
            decision.snippet=best["texto"]; m=re.search(r"\[página (\d+)\]",best["texto"]); decision.page=int(m.group(1)) if m else None
        cit=extract_citation(text)
        if cit: decision.citation=cit; decision.verified=True; decision.verification_status="verified_source_identifier"
        if not decision.case_number: decision.case_number=extract_case_number(text)
        return decision
    except Exception:
        return decision

async def content_search(query: str, years: list[int], limit: int) -> list[Decision]:
    headers={"User-Agent":"mcp-puerto-rico-sentencias/1.0","Accept":"text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.5"}
    limits=httpx.Limits(max_connections=8,max_keepalive_connections=8)
    timeout=httpx.Timeout(TIMEOUT,connect=5.0)
    async with httpx.AsyncClient(timeout=timeout,follow_redirects=True,headers=headers,limits=limits) as client:
        try: main_html=await fetch_text(client,OFFICIAL_INDEX)
        except Exception: return []
        year_results=await asyncio.gather(*(get_year_links(client,main_html,y) for y in years),return_exceptions=True)
        candidates=[]
        for res in year_results:
            if isinstance(res,list): candidates += sample_evenly([x for x in res if x.url.lower().split("?",1)[0].endswith(".pdf")],PDFS_PER_YEAR)
        candidates=dedupe(candidates)[:MAX_PDFS]
        sem=asyncio.Semaphore(8)
        async def one(d):
            async with sem: return await read_decision(client,d,query)
        results=await asyncio.gather(*(one(d) for d in candidates))
    results=[r for r in results if r.verified and r.relevance_score>0]
    results.sort(key=lambda r:(-r.relevance_score,r.citation or r.title))
    return results[:limit]

async def official_search(query: str, year: int|None, limit: int) -> list[Decision]:
    headers={"User-Agent":"mcp-puerto-rico-sentencias/1.0"}; timeout=httpx.Timeout(TIMEOUT,connect=5.0)
    async with httpx.AsyncClient(timeout=timeout,follow_redirects=True,headers=headers) as client:
        html=await fetch_text(client,OFFICIAL_INDEX)
        candidates=parse_index(html,OFFICIAL_INDEX,year)
    terms=query_terms(query); scored=[]
    for x in candidates:
        blob=normalize_text(f"{x.title} {x.citation} {x.case_number} {x.subject}")
        s=sum(1 for t in terms if normalize_text(t) in blob)
        if s: scored.append((s,x))
    if scored: return [x for _,x in sorted(scored,key=lambda z:-z[0])[:limit]]
    years=[year] if year is not None else [2026,2025,2024,2023,2022,2021,2020,2019]
    return await content_search(query,years,limit)

async def citation_search(citation: str) -> list[Decision]:
    req=normalize_citation(citation)
    if not req: return []
    m=re.search(r"\b((?:19|20)\d{2})\b",req); year=int(m.group(1)) if m else None
    results=await official_search(citation,year,MAX_RESULTS)
    return [x for x in results if x.citation and normalize_citation(x.citation)==req and x.verified]

@mcp.tool()
async def buscar_sentencias(consulta: str, ano: int|None=None, maximo: int=10) -> dict[str,Any]:
    """Busca sentencias/opiniones públicas. No inventa autoridades."""
    try:
        maximo=max(1,min(int(maximo),MAX_RESULTS)); results=await official_search(consulta,ano,maximo)
        return {"consulta":consulta,"ano":ano,"resultados":[asdict(x) for x in results],"fuente":OFFICIAL_INDEX,
                "regla_integridad":"Solo se devuelven documentos encontrados en fuentes permitidas; los campos no disponibles quedan vacíos."}
    except Exception as e: return {"consulta":consulta,"ano":ano,"resultados":[],"error":"No fue posible consultar las fuentes públicas.","detalle_tecnico":str(e)}

@mcp.tool()
async def investigar_sentencias(consulta: str, anos: str="2026,2025,2024,2023,2022,2021,2020,2019", maximo: int=5) -> dict[str,Any]:
    """Encuentra autoridades relevantes por texto y devuelve evidencia extraída del PDF oficial.

    Importante: la puntuación es textual; no significa que el caso sostenga el argumento.
    El modelo debe revisar el pasaje y la sentencia completa antes de afirmar un holding.
    """
    try:
        years=list(dict.fromkeys(int(x.strip()) for x in anos.split(",") if x.strip().isdigit()))[:8] or [2026,2025,2024,2023,2022,2021,2020,2019]
        maximo=max(1,min(int(maximo),10)); results=await content_search(consulta,years,maximo)
        return {"consulta":consulta,"anos_consultados":years,"resultados":[asdict(x) for x in results],"total":len(results),
                "verificacion":"Cada resultado fue leído desde un documento fuente permitido y conserva su URL. Los pasajes son texto extraído, no generados por el modelo.",
                "limitacion":"La relevancia es coincidencia textual/temática; no sustituye análisis jurídico del holding o vigencia del precedente."}
    except Exception as e: return {"consulta":consulta,"resultados":[],"total":0,"error":"No fue posible completar la investigación documental.","detalle_tecnico":str(e)}

@mcp.tool()
async def buscar_por_cita(cita: str) -> dict[str,Any]:
    """Verifica una cita TSPR exacta; no aproxima ni sustituye citas."""
    try:
        results=await citation_search(cita)
        return {"cita":cita,"encontrado":bool(results),"verificado":bool(results),"resultados":[asdict(x) for x in results],
                "mensaje":"La cita exacta no fue encontrada en la fuente oficial consultada." if not results else "Cita exacta encontrada en fuente permitida.","fuente":OFFICIAL_INDEX}
    except Exception as e: return {"cita":cita,"encontrado":False,"verificado":False,"resultados":[],"error":str(e)}

@mcp.tool()
async def leer_sentencia(url: str, terminos: str="", max_parrafos: int=8) -> dict[str,Any]:
    """Lee un PDF/HTML público y devuelve pasajes exactos extraídos de la fuente."""
    if not allowed_url(url): return {"url":url,"verificado":False,"error":"URL no permitida."}
    headers={"User-Agent":"mcp-puerto-rico-sentencias/1.0"}; timeout=httpx.Timeout(TIMEOUT,connect=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout,follow_redirects=True,headers=headers) as client:
            r=await fetch_response(client,url)
        ct=r.headers.get("content-type","").lower(); pdf="application/pdf" in ct or url.lower().split("?",1)[0].endswith(".pdf")
        text,paras=extract_pdf_document(r.content) if pdf else extract_html_document(r.text)
        if not text: return {"url":url,"verificado":False,"error":"La fuente no contiene texto extraíble."}
        rel=find_relevant_paragraphs(paras,terminos,max(1,min(int(max_parrafos),30)))
        return {"url":url,"fuente":source_name(url),"tipo_documento":"PDF" if pdf else "HTML","cita_tspr":extract_citation(text),"numero_caso":extract_case_number(text),
                "parrafos":rel,"total_parrafos_extraidos":len(paras),"procedencia":"Texto extraído directamente del documento fuente; no generado por el modelo.","verificado":True}
    except Exception as e: return {"url":url,"verificado":False,"error":"No fue posible leer o extraer el documento.","detalle_tecnico":str(e)}

@mcp.tool()
def opciones_busqueda(consulta: str="", campo: str="fuentes") -> dict[str,Any]:
    return {"consulta":consulta,"campo":campo,"fuentes":{"tribunal_supremo":OFFICIAL_INDEX,"lexjuris":LEXJURIS_SEARCH},
            "herramientas_recomendadas":{"investigar_sentencias":"Buscar autoridades por contenido","buscar_por_cita":"Verificar una cita TSPR exacta","leer_sentencia":"Extraer pasajes de una sentencia"},
            "regla_integridad":"Si una autoridad no se encuentra en una fuente permitida, se informa como no encontrada."}

@mcp.tool()
def estado() -> dict[str,Any]:
    return {"servidor":"puerto-rico-sentencias","version":"1.1.0","fuentes":[OFFICIAL_INDEX,LEXJURIS_SEARCH],
            "citation_integrity":{"no_casos_inventados":True,"no_citas_inventadas":True,"no_nombres_inventados":True,"no_fechas_o_ponentes_inferidos":True,"no_citas_aproximadas_en_buscar_por_cita":True,"no_citas_textuales_generadas":True,"source_required":True},
            "documentos":{"pdf":True,"html":True,"pasajes_con_procedencia":True,"pagina_pdf":True},"rendimiento":{"pdfs_por_busqueda":MAX_PDFS,"timeout_segundos":TIMEOUT},
            "privacidad":"No se almacenan consultas ni documentos por defecto.","anti_bot":"No se eluden CAPTCHA, autenticación ni controles de acceso."}

def main(): mcp.run()
if __name__=="__main__": main()
