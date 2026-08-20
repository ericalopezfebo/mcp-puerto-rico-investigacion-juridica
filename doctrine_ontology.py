"""Controlled Puerto Rico legal-doctrine vocabulary for discovery and disambiguation.

This is an original search ontology: it stores names of doctrines, aliases, related
concepts, source-area hints, and common false senses. It does not reproduce treatise
or study-guide text and is not itself legal authority. Final MCP answers must still be
verified against primary sources.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LegalConcept:
    area: str
    aliases: tuple[str, ...]
    related: tuple[str, ...]
    verification_queries: tuple[str, ...] = ()
    false_senses: tuple[str, ...] = ()


LEGAL_CONCEPTS: dict[str, LegalConcept] = {
    # DERECHO ADMINISTRATIVO
    "agotamiento_remedios_administrativos": LegalConcept(
        area="derecho administrativo",
        aliases=("agotamiento de remedios", "agotamiento de remedios administrativos", "agotar remedios"),
        related=("revision judicial", "resolucion final", "finalidad", "jurisdiccion administrativa", "ultra vires", "futilidad", "pericia administrativa", "violacion sustancial de derechos constitucionales"),
        verification_queries=(
            "agotamiento remedios administrativos requisito revision judicial excepciones falta jurisdiccion",
            "agotamiento remedios futilidad ultra vires asunto estrictamente de derecho pericia administrativa",
        ),
    ),
    "jurisdiccion_primaria": LegalConcept(
        area="derecho administrativo",
        aliases=("jurisdiccion primaria", "jurisdiccion primaria exclusiva", "jurisdiccion concurrente", "jurisdiccion primaria concurrente"),
        related=("foro administrativo", "foro judicial", "pericia administrativa", "jurisdiccion exclusiva", "ley organica", "agotamiento de remedios"),
        verification_queries=(
            "jurisdiccion primaria exclusiva concurrente agencia tribunal pericia administrativa",
            "jurisdiccion primaria foro administrativo foro judicial ley confiere jurisdiccion exclusiva",
        ),
    ),
    "revision_judicial_administrativa": LegalConcept(
        area="derecho administrativo",
        aliases=("revision judicial", "recurso de revision judicial", "revision administrativa"),
        related=("orden final", "resolucion final", "orden interlocutoria", "determinaciones de hecho", "conclusiones de derecho", "deferencia judicial", "evidencia sustancial", "agotamiento de remedios"),
        verification_queries=(
            "revision judicial orden resolucion final agencia agotamiento remedios",
            "revision judicial determinaciones de hecho evidencia sustancial conclusiones de derecho deferencia",
        ),
    ),
    "reconsideracion_administrativa": LegalConcept(
        area="derecho administrativo",
        aliases=("mocion de reconsideracion administrativa", "reconsideracion ante agencia", "reconsideracion administrativa"),
        related=("revision judicial", "termino para revision", "denegatoria de plano", "resolucion final", "notificacion"),
        verification_queries=(
            "mocion reconsideracion agencia termino revision judicial denegatoria de plano",
            "reconsideracion administrativa notificacion interrupcion termino revision",
        ),
    ),
    "reglamentacion_agencias": LegalConcept(
        area="derecho administrativo",
        aliases=("facultad de reglamentacion", "reglamentacion de agencias", "poder de reglamentacion", "reglamento administrativo"),
        related=("ley habilitadora", "delegacion", "regla legislativa", "regla no legislativa", "participacion ciudadana", "expediente de reglamentacion", "ultra vires", "reglamento de emergencia", "impugnacion de reglamento"),
        verification_queries=(
            "facultad reglamentacion agencia ley habilitadora delegacion ultra vires",
            "regla legislativa regla no legislativa procedimiento reglamentacion participacion ciudadana",
            "agencia obligada a cumplir reglamento discrecion limitada derechos establecidos reglamento",
        ),
    ),
    "impugnacion_reglamento": LegalConcept(
        area="derecho administrativo",
        aliases=("impugnacion de reglamento", "impugnar reglamento", "nulidad de reglamento"),
        related=("reglamentacion", "vigencia", "procedimiento de reglamentacion", "tribunal de apelaciones", "ultra vires", "legitimacion"),
        verification_queries=(
            "impugnacion de su faz reglamento procedimiento reglamentacion nulidad",
            "reglamento nulo incumplimiento procedimiento ley procedimiento administrativo uniforme",
        ),
    ),
    "intervencion_administrativa": LegalConcept(
        area="derecho administrativo",
        aliases=("interventor administrativo", "intervencion administrativa", "solicitud de intervencion ante agencia"),
        related=("procedimiento adjudicativo", "interes legitimo", "parte", "solicitud escrita", "interes adversamente afectado", "representacion adecuada", "expediente completo", "pericia especializada"),
        verification_queries=(
            "intervencion administrativa interventor procedimiento adjudicativo interes legitimo solicitud escrita",
            "agencia solicitud intervencion interes afectado representacion adecuada expediente completo pericia",
        ),
        false_senses=("intervencion policial", "intervencion quirurgica", "intervencion apelativa", "regla 21 procedimiento civil"),
    ),
    "partes_proceso_administrativo": LegalConcept(
        area="derecho administrativo",
        aliases=("parte en procedimiento administrativo", "partes proceso adjudicativo", "parte administrativa"),
        related=("promovente", "promovido", "interventor", "notificacion", "revision judicial", "procedimiento adjudicativo"),
        verification_queries=("parte procedimiento administrativo promovente promovido interventor participacion no convierte en parte",),
    ),
    "empleado_carrera": LegalConcept(
        area="derecho administrativo constitucional",
        aliases=("empleado de carrera", "servicio de carrera", "puesto de carrera"),
        related=("interes propietario", "expectativa de continuidad", "debido proceso de ley", "vista informal", "notificacion de cargos", "principio de merito", "reinstalacion"),
        verification_queries=(
            "empleado de carrera interes propietario expectativa continuidad debido proceso vista informal",
            "servicio de carrera principio de merito reinstalacion empleado publico",
        ),
    ),
    "empleado_confianza": LegalConcept(
        area="derecho administrativo constitucional",
        aliases=("empleado de confianza", "puesto de confianza", "servicio de confianza"),
        related=("expectativa de continuidad", "libertad de asociacion", "ideas politicas", "formulacion de politica publica", "informacion confidencial", "empleado de carrera"),
        verification_queries=(
            "empleado de confianza expectativa continuidad libertad asociacion despido ideas politicas",
            "puesto confianza formulacion politica publica informacion confidencial afinidad politica",
        ),
    ),
    "error_administrativo": LegalConcept(
        area="derecho administrativo",
        aliases=("error administrativo", "error de agencia"),
        related=("actos propios", "ultra vires", "acto nulo", "derechos adquiridos", "reglamento", "buena fe"),
        verification_queries=(
            "error administrativo no crea derechos acto nulo ultra vires",
            "agencia error administrativo reglamento derechos reconocidos acto original ilegal ultra vires",
        ),
    ),
    "totalidad_record": LegalConcept(
        area="derecho administrativo",
        aliases=("totalidad del record", "decision basada en el expediente", "record administrativo", "expediente administrativo"),
        related=("debido proceso", "determinaciones de hecho", "revision judicial", "prueba ex parte", "informe escrito", "evidencia sustancial"),
        verification_queries=("decision administrativa basada exclusivamente expediente record prueba ex parte revision judicial",),
    ),

    # PROCEDIMIENTO CIVIL
    "intervencion_civil": LegalConcept(
        area="procedimiento civil",
        aliases=("interventor", "intervencion", "intervencion de terceros", "parte interventora", "regla 21"),
        related=("intervencion como cuestion de derecho", "intervencion permisible", "interes que amerite proteccion", "interes afectado", "representacion adecuada", "economia procesal", "dilacion", "perjuicio a partes originales"),
        verification_queries=(
            "regla 21 intervencion de terceros interventor definicion proposito economia procesal",
            "intervencion como cuestion de derecho interes amerite proteccion interes afectado representacion adecuada",
            "intervencion permisible dilacion perjuicio partes originales",
        ),
        false_senses=("intervencion policial", "intervencion administrativa", "intervencion apelativa", "intervencion gubernamental"),
    ),
    "parte_indispensable": LegalConcept(
        area="procedimiento civil",
        aliases=("parte indispensable", "acumulacion parte indispensable"),
        related=("interes real e inmediato", "remedio completo", "persona ausente", "multiplicidad de pleitos", "desestimacion"),
        verification_queries=("parte indispensable interes real inmediato remedio sin presencia persona ausente",),
    ),
    "sentencia_sumaria": LegalConcept(
        area="procedimiento civil",
        aliases=("sentencia sumaria", "mocion de sentencia sumaria", "regla 36"),
        related=("hecho material", "controversia genuina", "declaracion jurada", "evidencia admisible", "hechos incontrovertidos"),
        verification_queries=(
            "sentencia sumaria controversia genuina hecho material procede como cuestion de derecho",
            "regla 36 hechos materiales declaraciones juradas evidencia admisible",
        ),
    ),
    "desestimacion_10_2": LegalConcept(
        area="procedimiento civil",
        aliases=("regla 10.2", "mocion de desestimacion", "dejar de exponer reclamacion que justifique remedio"),
        related=("alegaciones", "hechos bien alegados", "jurisdiccion", "emplazamiento", "parte indispensable", "defensa afirmativa"),
        verification_queries=("regla 10.2 desestimacion hechos bien alegados reclamacion remedio",),
    ),
    "descubrimiento_prueba_civil": LegalConcept(
        area="procedimiento civil",
        aliases=("descubrimiento de prueba", "discovery", "reglas 23 a 34"),
        related=("pertinencia", "privilegio", "interrogatorio", "deposicion", "requerimiento de admisiones", "orden protectora", "deber de actualizar"),
        verification_queries=(
            "descubrimiento prueba liberal amplio pertinente no privilegiada",
            "interrogatorio deposicion requerimiento admisiones orden protectora descubrimiento",
        ),
    ),
    "cosa_juzgada": LegalConcept(
        area="procedimiento civil y administrativo",
        aliases=("cosa juzgada", "res judicata"),
        related=("identidad de cosas", "identidad de causas", "identidad de personas", "calidad litigantes", "defensa afirmativa", "finalidad"),
        verification_queries=("cosa juzgada identidad cosas causas personas calidad litigantes defensa afirmativa",),
    ),

    # EVIDENCIA
    "prueba_referencia": LegalConcept(
        area="evidencia",
        aliases=("prueba de referencia", "hearsay", "regla 801", "reglas 801 a 809"),
        related=("declaracion fuera del tribunal", "verdad de lo aseverado", "excepcion", "admision de parte", "declarante no disponible", "declaracion anterior", "record de negocio"),
        verification_queries=(
            "prueba referencia declaracion fuera juicio verdad aseverado regla general inadmisible excepcion",
            "admision de parte declarante no disponible excepciones prueba referencia",
        ),
    ),
    "autenticacion_evidencia": LegalConcept(
        area="evidencia",
        aliases=("autenticacion", "identificacion de evidencia", "regla 901", "reglas 901 a 903"),
        related=("cadena de custodia", "conocimiento personal", "documento publico", "pagina web", "caracteristicas distintivas", "estipulacion"),
        verification_queries=("autenticacion evidencia suficiente materia es lo que proponente sostiene cadena custodia",),
    ),
    "mejor_evidencia": LegalConcept(
        area="evidencia",
        aliases=("regla de la mejor evidencia", "best evidence", "reglas 1001 a 1008"),
        related=("original", "duplicado", "evidencia secundaria", "documento publico", "original extraviado", "resumen voluminoso"),
        verification_queries=("regla mejor evidencia contenido escrito original duplicado evidencia secundaria",),
    ),
    "testimonio_pericial": LegalConcept(
        area="evidencia",
        aliases=("testimonio pericial", "perito", "regla 702", "persona perita"),
        related=("conocimiento cientifico", "conocimiento tecnico", "conocimiento especializado", "cualificaciones", "confiabilidad", "base de opinion", "valor probatorio"),
        verification_queries=("testimonio pericial conocimiento cientifico tecnico especializado cualificaciones confiabilidad opinion",),
    ),
    "privilegio_abogado_cliente": LegalConcept(
        area="evidencia",
        aliases=("privilegio abogado cliente", "attorney client privilege", "regla 503"),
        related=("comunicacion confidencial", "servicios legales", "consejo legal", "cliente", "abogado"),
        verification_queries=("privilegio abogado cliente comunicacion confidencial servicios legales consejo profesional",),
    ),
    "pertinencia_evidencia": LegalConcept(
        area="evidencia",
        aliases=("pertinencia", "evidencia pertinente", "regla 401"),
        related=("hecho de consecuencia", "valor probatorio", "perjuicio", "confusion", "perdida de tiempo"),
        verification_queries=("evidencia pertinente hace mas o menos probable hecho consecuencias adjudicacion perjuicio confusion",),
    ),

    # CONSTITUCIONAL
    "debido_proceso": LegalConcept(
        area="derecho constitucional",
        aliases=("debido proceso de ley", "due process", "debido proceso sustantivo", "debido proceso procesal"),
        related=("libertad", "propiedad", "interes propietario", "notificacion", "oportunidad de ser oido", "juzgador imparcial", "decision basada en record"),
        verification_queries=(
            "debido proceso interes libertad propiedad procedimiento justo notificacion oportunidad ser oido",
            "debido proceso sustantivo privacion arbitraria libertad propiedad nexo racional",
        ),
    ),
    "igual_proteccion": LegalConcept(
        area="derecho constitucional",
        aliases=("igual proteccion de las leyes", "equal protection"),
        related=("clasificacion sospechosa", "escrutinio estricto", "nexo racional", "derecho fundamental", "discrimen", "condicion social", "ideas politicas"),
        verification_queries=(
            "igual proteccion clasificacion sospechosa escrutinio estricto interes apremiante",
            "igual proteccion clasificacion socioeconomica nexo racional interes legitimo",
        ),
    ),
    "derecho_intimidad": LegalConcept(
        area="derecho constitucional",
        aliases=("derecho a la intimidad", "intimidad", "privacy"),
        related=("dignidad", "vida privada", "expectativa razonable de intimidad", "autodeterminacion", "registro", "allanamiento", "injunction"),
        verification_queries=("derecho intimidad expectativa real razonable dignidad vida privada interes apremiante",),
    ),
    "accion_estado": LegalConcept(
        area="derecho constitucional",
        aliases=("accion de estado", "state action", "actor del estado"),
        related=("funcionario gubernamental", "asistencia estatal", "conducta atribuible al estado", "persona privada", "autoridad de derecho"),
        verification_queries=("accion de estado conducta atribuible estado funcionario asistencia estatal persona privada",),
    ),
    "justiciabilidad": LegalConcept(
        area="derecho constitucional",
        aliases=("justiciabilidad", "doctrinas de autolimitacion judicial"),
        related=("cuestion politica", "madurez", "academicidad", "legitimacion activa", "controversia real"),
        verification_queries=("justiciabilidad cuestion politica madurez academicidad legitimacion activa controversia real",),
    ),
    "academicidad": LegalConcept(
        area="derecho constitucional",
        aliases=("academicidad", "mootness", "caso academico"),
        related=("efecto practico", "controversia existente", "cambio factico", "conducta voluntariamente cesada", "consecuencias colaterales", "recurrente evade revision"),
        verification_queries=("academicidad remedio efecto practico controversia excepciones recurrente consecuencias colaterales",),
    ),
    "legitimacion_activa": LegalConcept(
        area="derecho constitucional",
        aliases=("legitimacion activa", "standing", "accion legitimada"),
        related=("dano claro palpable", "dano real inmediato", "relacion causal", "causa de accion", "asociacion", "tercero", "contribuyente"),
        verification_queries=("legitimacion activa dano claro palpable real inmediato relacion causal causa accion",),
    ),
    "separacion_poderes": LegalConcept(
        area="derecho constitucional",
        aliases=("separacion de poderes", "separation of powers"),
        related=("poder ejecutivo", "poder legislativo", "poder judicial", "funcion constitucional", "nombramiento", "destitucion", "litigios pendientes"),
        verification_queries=("separacion poderes funcion expresamente asignada independencia ramas gobierno",),
    ),
}


def matching_concepts(normalized_query: str) -> list[tuple[str, LegalConcept]]:
    """Return concepts whose alias appears in an already-normalized query."""
    matches: list[tuple[str, LegalConcept]] = []
    for name, concept in LEGAL_CONCEPTS.items():
        if any(alias in normalized_query for alias in concept.aliases):
            matches.append((name, concept))
    return matches
