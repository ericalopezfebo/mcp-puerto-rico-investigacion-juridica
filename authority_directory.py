"""Auxiliary jurisprudence directory for discovery-only context.

This module is intentionally NOT a source of legal authority.  It stores doctrinal
case seeds derived from the user's 2025 course indexes (Administrative,
Constitutional, Civil Procedure, Ethics, Evidence, Obligations & Contracts).

Rules:
* A directory hit may expand a query or help rank/discover candidates.
* A directory hit NEVER makes a proposition verified.
* Names/citations marked OCR must be checked against an official source.
* Search must continue through the local corpus and/or live primary sources.
"""
from __future__ import annotations

from dataclasses import dataclass

import server as jurisprudencia
import search_tuning


@dataclass(frozen=True)
class DirectoryAuthority:
    area: str
    case: str
    citation: str
    topics: tuple[str, ...]
    ocr_check: bool = False


AUTHORITIES: tuple[DirectoryAuthority, ...] = (
    # Derecho Administrativo
    DirectoryAuthority("derecho administrativo", "Agosto v. Fondo del Seguro del Estado", "132 DPR 866 (1993)", ("potestad reglamentaria", "ley habilitadora", "delegacion")),
    DirectoryAuthority("derecho administrativo", "Fuentes Bonilla v. ELA", "2018 TSPR 98", ("potestad reglamentaria", "jurisdiccion", "competencia")),
    DirectoryAuthority("derecho administrativo", "Centro Médico v. Departamento de Salud", "181 DPR 72 (2011)", ("reglamentacion", "ley habilitadora")),
    DirectoryAuthority("derecho administrativo", "Municipio de Aguada v. Junta de Calidad Ambiental", "2014 TSPR 7", ("debido proceso administrativo", "legitimacion", "revision judicial")),
    DirectoryAuthority("derecho administrativo", "Otero v. Toyota", "163 DPR 716 (2005)", ("adjudicacion administrativa", "determinaciones", "prueba")),
    DirectoryAuthority("derecho administrativo", "Acevedo v. Western Digital", "140 DPR 452 (1996)", ("cosa juzgada administrativa", "efecto preclusivo"), True),
    DirectoryAuthority("derecho administrativo", "Maldonado v. Junta de Planificación", "171 DPR 46 (2007)", ("jurisdiccion administrativa", "revision judicial")),
    DirectoryAuthority("derecho administrativo", "Buxó Santiago v. Oficina de Ética Gubernamental", "2024 TSPR 130", ("agotamiento de remedios", "jurisdiccion primaria", "justiciabilidad")),
    DirectoryAuthority("derecho administrativo", "Rivera v. Departamento de Servicios Sociales", "132 DPR 240 (1992)", ("agotamiento de remedios", "jurisdiccion primaria")),
    DirectoryAuthority("derecho administrativo", "Colón Rivera v. Departamento de Educación", "189 DPR 1033 (2013)", ("agotamiento de remedios", "jurisdiccion primaria")),
    DirectoryAuthority("derecho administrativo", "Beltrán Cintrón v. ELA", "2020 TSPR 26", ("jurisdiccion primaria", "jurisdiccion administrativa")),
    DirectoryAuthority("derecho administrativo", "Consejo de Titulares v. Gómez Estremera", "2012 TSPR 12", ("jurisdiccion primaria", "ley habilitadora"), True),
    DirectoryAuthority("derecho administrativo", "Security Services v. Autoridad de Energía Eléctrica", "2023 TSPR 149", ("subastas", "contratacion publica", "revision administrativa")),
    DirectoryAuthority("derecho administrativo", "Transporte Sonnell, LLC v. Junta de Subastas de la Autoridad de Carreteras", "2024 TSPR 82", ("subastas", "contratacion publica", "revision administrativa")),

    # Derecho Constitucional
    DirectoryAuthority("derecho constitucional", "Senado de Puerto Rico v. Tribunal Supremo de Puerto Rico", "2021 TSPR 141", ("separacion de poderes", "legitimacion", "sentencia declaratoria")),
    DirectoryAuthority("derecho constitucional", "Asociación de Empleados v. Crespo", "2012 TSPR 106", ("justiciabilidad", "academicidad", "madurez")),
    DirectoryAuthority("derecho constitucional", "Buxó Santiago v. Oficina de Ética Gubernamental", "2024 TSPR 130", ("justiciabilidad", "academicidad", "injunction")),
    DirectoryAuthority("derecho constitucional", "Bhatia v. Rosselló", "2017 TSPR 173", ("separacion de poderes", "mandamus", "justiciabilidad")),
    DirectoryAuthority("derecho constitucional", "Noriega v. Hernández Colón", "135 DPR 406 (1995)", ("separacion de poderes", "cuestion politica")),
    DirectoryAuthority("derecho constitucional", "Fundación Surfrider v. ARPE", "178 DPR 563 (2010)", ("legitimacion", "libertad de expresion")),
    DirectoryAuthority("derecho constitucional", "Rivera Schatz v. Pierluisi", "2019 TSPR 138", ("legitimacion", "injunction", "sentencia declaratoria")),
    DirectoryAuthority("derecho constitucional", "Alvarado Pacheco v. ELA", "188 DPR 598 (2013)", ("debido proceso", "libertad", "propiedad")),
    DirectoryAuthority("derecho constitucional", "Ramos v. Estado Libre Asociado", "2024 TSPR 58", ("igual proteccion", "escrutinio")),
    DirectoryAuthority("derecho constitucional", "Delucca Jiménez v. Colegio de Médicos Cirujanos", "2023 TSPR 119", ("igual proteccion", "escrutinio estricto"), True),
    DirectoryAuthority("derecho constitucional", "Municipio Autónomo de Peñuelas v. Ecosystems, Inc.", "2016 TSPR 247", ("preemption", "supremacia federal", "campo ocupado")),
    DirectoryAuthority("derecho constitucional", "Trinidad Hernández v. ELA", "188 DPR 828 (2013)", ("menoscabo obligaciones contractuales", "contratos", "constitucional")),

    # Procedimiento Civil
    DirectoryAuthority("procedimiento civil", "López García v. López García", "2018 TSPR 57", ("parte indispensable", "regla 16.1")),
    DirectoryAuthority("procedimiento civil", "Pérez Ríos v. Luma Energy, LLC", "2023 TSPR 136", ("parte indispensable", "regla 16.1")),
    DirectoryAuthority("procedimiento civil", "Freire Ruiz de Val v. Morales Román", "2024 TSPR 129", ("parte indispensable", "albacea", "testamento")),
    DirectoryAuthority("procedimiento civil", "Oriental Bank v. Pagán Acosta", "2024 TSPR 133", ("parte indispensable", "sustitucion de parte", "ejecucion hipotecaria")),
    DirectoryAuthority("procedimiento civil", "Ortiz Alvarado v. Great American Life Assurance Company of PR", "2011 TSPR 79", ("intervencion", "regla 21", "interes protegible")),
    DirectoryAuthority("procedimiento civil", "IG Builders Corp. v. 577 Headquarters Corp.", "2012 TSPR 66", ("intervencion", "regla 21", "propiedad embargada")),
    DirectoryAuthority("procedimiento civil", "Ramos Pérez v. Univisión Puerto Rico", "178 DPR 200 (2010)", ("sentencia sumaria", "regla 36")),
    DirectoryAuthority("procedimiento civil", "Consejo de Titulares v. Rocca Development Corp.", "2025 TSPR 6", ("sentencia sumaria", "hechos materiales")),
    DirectoryAuthority("procedimiento civil", "Fernández Martínez v. RAD-MAN San Juan, LLC", "2021 TSPR 149", ("sentencia sumaria", "oposicion", "prueba admisible")),
    DirectoryAuthority("procedimiento civil", "Meléndez González v. Cuebas, Inc.", "2015 TSPR 70", ("sentencia sumaria", "hechos incontrovertidos", "revision apelativa")),
    DirectoryAuthority("procedimiento civil", "Valencia v. García", "2012 TSPR 172", ("descubrimiento de prueba", "liberalidad")),
    DirectoryAuthority("procedimiento civil", "McNeil Healthcare, LLC v. Municipio de Las Piedras", "2021 TSPR 33", ("descubrimiento de prueba", "pertinencia")),
    DirectoryAuthority("procedimiento civil", "Alvear Maldonado v. Ernst & Young", "2014 TSPR 127", ("descubrimiento de prueba", "orden protectora", "privilegio")),
    DirectoryAuthority("procedimiento civil", "Szendrey v. Consejo de Titulares", "2011 TSPR 206", ("cosa juzgada", "identidad")),
    DirectoryAuthority("procedimiento civil", "Rodríguez Ocasio v. ACAA", "2017 TSPR 52", ("cosa juzgada", "impedimento colateral")),
    DirectoryAuthority("procedimiento civil", "Rivera Candela v. Universal Insurance Company", "2024 TSPR 99", ("alegaciones", "regla 6.1")),
    DirectoryAuthority("procedimiento civil", "Bernier González v. Rodríguez Becerra", "2018 TSPR 114", ("emplazamiento", "termino 120 dias")),
    DirectoryAuthority("procedimiento civil", "Sánchez Ruiz v. Higuera Pérez", "2020 TSPR 11", ("emplazamiento", "edictos", "diligencias")),
    DirectoryAuthority("procedimiento civil", "Rivera Schatz v. Pierluisi", "2019 TSPR 138", ("injunction", "sentencia declaratoria")),
    DirectoryAuthority("procedimiento civil", "Carrasquillo Román v. Departamento de Corrección", "2020 TSPR 70", ("mandamus", "deber ministerial")),

    # Evidencia
    DirectoryAuthority("evidencia", "Pueblo v. Rivera Cuevas", "181 DPR 699", ("reglas de evidencia", "aplicabilidad")),
    DirectoryAuthority("evidencia", "Acarón v. Departamento de Recursos Naturales", "2012 TSPR 134", ("evidencia en procedimientos administrativos", "flexibilidad")),
    DirectoryAuthority("evidencia", "Pueblo v. Nogales Molinelli", "2024 TSPR 139", ("determinaciones preliminares", "regla 109")),
    DirectoryAuthority("evidencia", "Pueblo v. Santos Santos", "2012 TSPR 95", ("confrontacion", "informe forense", "perito")),
    DirectoryAuthority("evidencia", "Pagán Cartagena v. First Hospital Panamericano", "2013 TSPR 102", ("privilegio abogado cliente", "comunicacion confidencial")),
    DirectoryAuthority("evidencia", "Blanco Matos v. Colón Mulero", "2018 TSPR 102", ("privilegio abogado cliente", "regla 109")),
    DirectoryAuthority("evidencia", "Pueblo v. De Jesús Mercado", "2013 TSPR 52", ("testimonio estereotipado", "credibilidad")),
    DirectoryAuthority("evidencia", "Rosado Reyes v. Global Healthcare Group, LLC", "2020 TSPR 136", ("autenticacion", "evidencia electronica")),
    DirectoryAuthority("evidencia", "Font de Bardon v. Mini-Warehouse Corp.", "179 DPR 322", ("peritos", "base de opinion")),

    # Ética Profesional
    DirectoryAuthority("etica profesional", "In re García Muñoz", "160 DPR 744", ("competencia", "educacion juridica continua")),
    DirectoryAuthority("etica profesional", "In re Custodio Valentín", "2012 TSPR 186", ("respeto", "agencias administrativas", "ordenes")),
    DirectoryAuthority("etica profesional", "In re Rivera Nazario", "2015 TSPR 109", ("etica ante agencias", "respeto", "diligencia")),
    DirectoryAuthority("etica profesional", "In re Nieves Nieves", "2011 TSPR 33", ("cumplimiento de ordenes", "diligencia")),
    DirectoryAuthority("etica profesional", "In re Feliciano Rodríguez", "2017 TSPR 109", ("deber de investigar", "imputaciones falsas", "canon 15")),
    DirectoryAuthority("etica profesional", "In re Sánchez Pérez", "2022 TSPR 98", ("competencia", "diligencia", "canon 18")),
    DirectoryAuthority("etica profesional", "In re Maldonado Torres", "2016 TSPR 229", ("informacion al cliente", "canon 19")),
    DirectoryAuthority("etica profesional", "In re Báez Genoval", "175 DPR 28", ("conflicto de intereses", "representacion simultanea")),
    DirectoryAuthority("etica profesional", "In re Aponte Duchesne", "2014 TSPR 85", ("conflicto potencial", "canon 21")),
    DirectoryAuthority("etica profesional", "In re Ramírez Salcedo", "2016 TSPR 174", ("honradez", "verdad", "canon 35")),
    DirectoryAuthority("etica profesional", "In re Huertas Soto", "2016 TSPR 81", ("canon 38", "conducta deshonrosa", "deber de denunciar")),

    # Obligaciones y Contratos: broad anchors; directory remains discovery-only.
    DirectoryAuthority("obligaciones y contratos", "Trinidad Hernández v. ELA", "188 DPR 828 (2013)", ("obligaciones contractuales", "menoscabo")),
    DirectoryAuthority("obligaciones y contratos", "Méndez v. Morales", "142 DPR 26", ("contrato", "honorarios", "forma escrita")),
    DirectoryAuthority("obligaciones y contratos", "López de Victoria v. Rodríguez", "113 DPR 265", ("contrato contingente", "honorarios")),
)


def _norm(text: str) -> str:
    return jurisprudencia.normalize_text(text or "")


def directory_matches(query: str, maximo: int = 24) -> list[DirectoryAuthority]:
    """Find directory entries relevant to a query. Discovery only."""
    q = _norm(query)
    qtokens = {t for t in q.split() if len(t) >= 4}
    scored: list[tuple[float, DirectoryAuthority]] = []
    for item in AUTHORITIES:
        fields = [_norm(item.case), _norm(item.citation), _norm(item.area), *(_norm(t) for t in item.topics)]
        blob = " ".join(fields)
        score = 0.0
        if q and q in blob:
            score += 12.0
        for topic in item.topics:
            nt = _norm(topic)
            if nt and (nt in q or q in nt):
                score += 8.0
        overlap = sum(1 for token in qtokens if token in blob)
        score += min(8.0, overlap * 1.5)
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: (-x[0], x[1].case))
    return [item for _score, item in scored[: max(1, int(maximo))]]


_ORIGINAL_EXPANDED_QUERY_TERMS = search_tuning.expanded_query_terms


def expanded_query_terms_with_directory(query: str) -> list[tuple[str, float]]:
    """Blend directory seeds into discovery terms without treating them as proof."""
    weighted = dict(_ORIGINAL_EXPANDED_QUERY_TERMS(query))
    for item in directory_matches(query, maximo=18):
        case = _norm(item.case)
        citation = _norm(item.citation)
        if case:
            weighted[case] = max(weighted.get(case, 0.0), 0.78 if not item.ocr_check else 0.58)
        if citation:
            weighted[citation] = max(weighted.get(citation, 0.0), 0.70 if not item.ocr_check else 0.50)
        for topic in item.topics:
            nt = _norm(topic)
            if nt:
                weighted[nt] = max(weighted.get(nt, 0.0), 0.72)
    return sorted(weighted.items(), key=lambda pair: (-pair[1], pair[0]))


# search_tuning.improved_discovery_score resolves this global at call time, so
# existing registered MCP search tools automatically gain the directory context.
search_tuning.expanded_query_terms = expanded_query_terms_with_directory

DIRECTORY_METADATA = {
    "role": "discovery_context_only",
    "never_authority_by_itself": True,
    "must_continue_search": True,
    "must_verify_primary_source": True,
    "areas": (
        "derecho administrativo",
        "derecho constitucional",
        "procedimiento civil",
        "etica profesional",
        "evidencia",
        "obligaciones y contratos",
    ),
    "loaded_seed_count": len(AUTHORITIES),
}
