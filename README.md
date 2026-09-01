<img width="800" height="200" alt="MCP-PR-Banner-Animated" src="https://github.com/user-attachments/assets/aeb3c16a-a191-4add-a50e-f429e6517bf2" />
# MCP Puerto Rico — Investigación Jurídica 🇵🇷

## Investigación jurídica verificable desde Claude, ChatGPT y otros clientes MCP

**MCP Puerto Rico — Investigación Jurídica** es una plataforma abierta de investigación jurídica de Puerto Rico. El objetivo es localizar y verificar **jurisprudencia, legislación, reglamentos, órdenes ejecutivas, decisiones administrativas y actualidad jurídica pública** sin convertir al modelo de lenguaje en fuente de autoridad.

> **Regla central: source-first / zero legal hallucination.** Si una autoridad, cita, nombre, número de caso, fecha, página o pasaje no puede verificarse en una fuente identificable, el MCP no debe inventarlo ni rellenarlo.

El repositorio y el paquete Python se llaman `mcp-puerto-rico-investigacion-juridica`. Los comandos históricos `mcp-puerto-rico-sentencias` se mantienen como aliases de compatibilidad para instalaciones existentes.

## Qué cubre

### Fuentes primarias oficiales

- **Tribunal Supremo de Puerto Rico** — opiniones, sentencias y resoluciones públicas.
- **Tribunal de Apelaciones** — determinaciones finales públicas disponibles desde enero de 2015, salvo casos confidenciales.
- **SUTRA / Oficina de Servicios Legislativos** — leyes, historial legislativo y relaciones explícitas de enmienda/derogación usadas para verificar vigencia legislativa.
- **Biblioteca Jurídica Virtual del Departamento de Estado** — leyes, resoluciones conjuntas, reglamentos, órdenes ejecutivas, decretos y proclamas disponibles públicamente.
- **Junta de Relaciones del Trabajo de Puerto Rico (JRT)** — decisiones y órdenes, órdenes administrativas y otros documentos públicos laborales; el MCP ya puede verificar por texto los PDFs gubernamentales descubiertos en esta colección.

### Fuentes secundarias públicas de descubrimiento

- **Microjuris Al Día** — búsqueda y contenido público para descubrir noticias, cambios y temas recientes.
- **LexJuris — menús públicos de jurisprudencia por año** — se usan únicamente como índice secundario de materia/resumen para priorizar candidatos en búsquedas globales de jurisprudencia.
- **CodeXPR** — puede utilizarse como índice secundario de descubrimiento cuando el contenido sea público, pero nunca como prueba final de vigencia.

**No se accede a productos premium, no se usan credenciales, no se evade ningún paywall y no se replica ninguna base de datos propietaria.** Una fuente secundaria nunca sustituye la sentencia, ley, reglamento u otra autoridad primaria correspondiente.

## Qué pretende replicar — y qué no

Este proyecto busca reproducir **funcionalidad de investigación** que normalmente ofrecen plataformas jurídicas comerciales: localizar fuentes, cruzar colecciones, encontrar autoridades relacionadas, extraer pasajes verificables y facilitar investigación temática.

No intenta copiar bases privadas, anotaciones editoriales, headnotes, clasificación propietaria ni contenido protegido de servicios de suscripción. Cuando el documento jurídico original está disponible públicamente, el MCP intenta trabajar directamente con ese original.

## Herramientas MCP

### Jurisprudencia del Tribunal Supremo — núcleo verificado

- `buscar_mejores_sentencias` — **herramienta preferida cuando el usuario pide “las mejores”, “más relevantes” o “Top N” decisiones.** Ejecuta un loop interno de descubrimiento → verificación oficial → reranking, sin recorrer años del más reciente al más antiguo y sin dar un bono automático por recencia.
- `investigar_argumento_juridico` — loop superior, limitado y auditable para una pregunta, proposición y hechos materiales. Ejecuta búsquedas complementarias, acumula autoridades oficiales, exige una pasada potencialmente adversa, comprueba estabilidad y termina por suficiencia o presupuesto. No declara automáticamente holding ni vigencia.
- `investigar_sentencias` — búsqueda documental por contenido de PDFs oficiales con rango de años explícito.
- `buscar_sentencias` — búsqueda temática por palabras/frases y año.
- `buscar_por_cita` — verificación exacta de una cita TSPR; no sustituye una cita inexistente por otra parecida.
- `leer_sentencia` — lee un documento público y extrae pasajes directamente de la fuente.

### Cómo funciona `buscar_mejores_sentencias`

```text
ARGUMENTO / PREGUNTA
        ↓
CANDIDATOS GLOBALES (1997 → presente)
  índice secundario público: materia/resumen
        ↓
RANKING TEMÁTICO INICIAL
        ↓
VERIFICACIÓN DE LOS MEJORES CANDIDATOS
  cita exacta + PDF oficial Poder Judicial
        ↓
RERANKING POR TEXTO REAL
        ↓
CITATION CHAINING DE TSPR EN PASAJES RELEVANTES
        ↓
NUEVA RONDA
        ↓
TOP-K ESTABLE O PRESUPUESTO AGOTADO
```

La fecha **no suma puntos por sí sola**. Una decisión de 2001 puede quedar por encima de una de 2026 si el texto verificado es más pertinente al argumento. El loop vive en Python dentro del MCP; no depende de que Claude decida repetir prompts o búsquedas año por año.

La capa pública de descubrimiento actualmente cubre 1997 en adelante. La herramienta no afirma cobertura exhaustiva de jurisprudencia anterior a 1997. Autoridades más antiguas pueden aparecer si se descubren a través de referencias verificables, pero ampliar esa cobertura histórica sigue pendiente.

### Vigencia e historial legislativo

- `construir_historial_legislativo` — recibe una ley como `Ley 80-1976` y busca automáticamente en el portal público de SUTRA leyes posteriores que la enmienden, deroguen, sustituyan o reenumeren. Cada relación candidata debe confirmarse en la página oficial de detalle de SUTRA antes de entrar al grafo.
- `verificar_vigencia_ley` — ejecuta el historial automático y devuelve un estado conservador. Detecta derogaciones o enmiendas explícitas; **no convierte la ausencia de resultados en una afirmación de vigencia**.
- `verificar_vigencia_legislativa` — inspecciona una URL oficial concreta de SUTRA/OSL o Departamento de Estado y extrae señales explícitas sin adivinar.
- `politica_vigencia_fuentes` — expone la jerarquía de fuentes y la regla de no usar CodeXPR/LexJuris/Microjuris como prueba final de vigencia.

```text
LEY / ARTÍCULO
     ↓
NORMALIZAR IDENTIFICADOR (ej. Ley 55-2020)
     ↓
BÚSQUEDA PÚBLICA EN SUTRA
     ↓
CANDIDATOS DE LEYES POSTERIORES
     ↓
ABRIR DETALLE OFICIAL DE CADA CANDIDATO
     ↓
EXTRAER RELACIONES EXPLÍCITAS
  ├─ enmienda
  ├─ deroga
  ├─ sustituye
  └─ reenumera
     ↓
GRAFO DE AFECTACIONES
     ↓
ESTADO CONSERVADOR DE VIGENCIA
```

La ausencia de una derogación en el grafo **no equivale a `vigente`**. Para una afirmación positiva de texto vigente todavía debe confirmarse el texto oficial aplicable/consolidado cuando exista.

### Investigación jurídica ampliada

- `buscar_mejores_autoridades` — **punto de entrada preferido para una pregunta que pueda requerir varias clases de autoridad.** Coordina el Top-K TSPR verificado con legislación/reglamentos, decisiones administrativas y otras colecciones públicas, manteniendo separados los resultados que todavía solo fueron descubiertos en un índice oficial.
- `leer_autoridad_publica` — recupera y lee un documento de una **fuente primaria pública autorizada** y devuelve pasajes exactos/página cuando están disponibles. No acepta Microjuris como autoridad primaria y no determina automáticamente vigencia, enmiendas o tratamiento posterior.
- `buscar_decisiones_laborales_verificables` — explora el índice público de la JRT, prioriza candidatos y lee un lote limitado de PDFs gubernamentales en `docs.pr.gov`; solo devuelve resultados cuya relevancia temática aparece en el texto fuente.
- `investigar_derecho_pr` — punto de entrada multi-fuente histórico. Coordina candidatos del Tribunal Supremo y Tribunal de Apelaciones y orienta hacia fuentes oficiales adicionales.
- `buscar_decisiones_apelaciones` — busca determinaciones finales públicas del Tribunal de Apelaciones por año y texto visible en el índice oficial.
- `buscar_biblioteca_juridica` — busca enlaces visibles en la Biblioteca Jurídica Virtual del Departamento de Estado.
- `buscar_decisiones_laborales` — herramienta histórica de descubrimiento superficial de la JRT; para investigación sustantiva se prefiere `buscar_decisiones_laborales_verificables`.
- `buscar_actualidad_juridica` — busca noticias/análisis públicos de Microjuris Al Día y los marca expresamente como **fuente secundaria**.
- `catalogo_fuentes_juridicas` — muestra las colecciones integradas y su jerarquía.
- `estado_investigacion_juridica` — diagnóstico de la capa ampliada.

`buscar_mejores_autoridades` aplica **niveles de verificación**. Una autoridad cuyo texto primario fue leído y verificado puede entrar al ranking principal. Un resultado localizado únicamente en un índice o portal oficial se devuelve como `candidato_primario_por_verificar` y **no** se presenta como holding, texto estatutario vigente o regla de derecho confirmada. Una noticia pública se mantiene en un tercer nivel secundario de descubrimiento/contexto.

Para consultas de relaciones laborales/colectivas, el orquestador puede activar automáticamente la búsqueda verificada de la JRT. Para una consulta no laboral —por ejemplo, pensión alimenticia— no abre esa colección costosa innecesariamente.

Las herramientas existentes `opciones_busqueda` y `estado` continúan disponibles por compatibilidad con la etapa original del proyecto.

## Ejemplos

> “Tengo un argumento sobre pensión alimenticia. Busca las mejores 5 decisiones del Tribunal Supremo de Puerto Rico que puedan apoyarlo. No favorezcas casos recientes por ser recientes. Para cada resultado dame cita, caso, número, fecha, página, URL oficial y pasaje exacto.”

> “Verifica si la Ley 80-1976 y el artículo que quiero citar siguen sin una derogación o enmienda posterior relevante. Construye primero el historial legislativo en SUTRA y no presumas vigencia si la fuente oficial no lo demuestra.”

> “Investiga la obligación alimentaria de los padres en Puerto Rico. Dame las mejores autoridades primarias verificables: ley, reglamento aplicable si existe y jurisprudencia. Para cada caso cita la página y el pasaje exacto.”

> “Busca decisiones y órdenes verificables de la Junta de Relaciones del Trabajo sobre negociación colectiva y deber de justa representación. Dame el PDF oficial y los pasajes exactos.”

> “¿Qué cambió con la doctrina Chevron? Busca primero actualidad jurídica pública para detectar el desarrollo y después identifica la autoridad primaria que realmente cambió la doctrina. No uses el artículo como sustituto de la sentencia.”

> “Si solo encuentras tres autoridades verificables, devuelve tres. No completes la lista con casos marginales ni inventados.”

## Arquitectura de confianza

```text
PREGUNTA JURÍDICA
        ↓
DETECCIÓN DE MATERIA / TIPO DE AUTORIDAD
        ↓
FUENTES PRIMARIAS OFICIALES
  ├─ Constitución / leyes / SUTRA
  ├─ Reglamentos
  ├─ Tribunal Supremo
  ├─ Tribunal de Apelaciones
  └─ Decisiones administrativas
        ↓
DESCUBRIMIENTO / PRIORIZACIÓN
        ↓
LECTURA DEL DOCUMENTO FUENTE
        ↓
VERIFICACIÓN + VIGENCIA CUANDO APLICA
        ↓
PASAJES + PÁGINA + URL + METADATOS
        ↓
CLAUDE / CHATGPT / OTRO CLIENTE MCP
```

Las fuentes secundarias públicas se usan como **descubrimiento/contexto**, no como sustituto de la autoridad primaria.

## Taxonomía y datos semilla

El proyecto utiliza una taxonomía de `tipo de autoridad → materia → tema específico → fuente → estado de verificación`. Un inventario desarrollado para el proyecto `legal-agents` contiene alrededor de 450 autoridades de derecho administrativo, constitucional y penal, incluyendo TSPR/DPR, decisiones federales, leyes especiales, códigos y reglamentos.

Ese inventario se trata como **seed de investigación**, no como fuente de verdad. Algunas entradas están expresamente marcadas “Pendiente de verificar” o contienen notas de posible error. Ninguna entrada debe convertirse en autoridad confirmada hasta localizarse en una fuente verificable.

Ver [`docs/taxonomia-autoridades.md`](docs/taxonomia-autoridades.md).

## Instalación local

Requiere Python 3.10+ y Git.

```bash
git clone https://github.com/ericalopezfebo/mcp-puerto-rico-investigacion-juridica.git
cd mcp-puerto-rico-investigacion-juridica
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

Comando principal:

```bash
mcp-puerto-rico-investigacion-juridica
```

Los comandos históricos siguen funcionando:

```bash
mcp-puerto-rico-sentencias
```

### Claude Desktop / Cowork

Ejemplo de configuración local:

```json
{
  "mcpServers": {
    "puerto-rico-investigacion-juridica": {
      "command": "/RUTA/AL/REPO/.venv/bin/python",
      "args": ["/RUTA/AL/REPO/bootstrap_server.py"]
    }
  }
}
```

En Windows usa `.venv\\Scripts\\python.exe`.

### Claude Code

```bash
claude mcp add puerto-rico-investigacion-juridica -- /RUTA/AL/REPO/.venv/bin/python /RUTA/AL/REPO/bootstrap_server.py
```

## ChatGPT / servidor remoto

El repositorio incluye `remote_server.py`, `Dockerfile` y `render.yaml`. El servidor remoto expone el mismo conjunto de herramientas — incluidas la búsqueda relevance-first, la orquestación multi-fuente y el historial legislativo automático — mediante Streamable HTTP en:

```text
https://TU-DOMINIO/mcp
```

El CI construye la imagen Docker además de ejecutar los tests/imports, para detectar módulos faltantes antes de publicar cambios. El endpoint de demostración no tiene SLA y un plan gratuito puede sufrir arranque en frío o timeouts.

## Integridad jurídica

El MCP debe observar estas reglas:

1. **No inventar autoridades.**
2. **No inventar citas, nombres, números de expediente, fechas, páginas o quotations.**
3. **Distinguir fuente primaria de secundaria.**
4. **Conservar URL y procedencia.**
5. **Una coincidencia temática no equivale a holding.**
6. **No presentar una noticia como derecho vigente.**
7. **No determinar vigencia de una ley/reglamento sin evidencia suficiente.**
8. **No interpretar ausencia de derogación detectada como prueba automática de vigencia.**
9. **Si la evidencia no alcanza, devolver menos resultados o `no_determinada`.**
10. **No acceder ni intentar eludir contenido de suscripción.**
11. **Preferir “no verificado” a una conclusión plausible pero no demostrada.**

## Estado de cobertura

| Colección | Estado |
|---|---|
| Tribunal Supremo | ✅ PDF oficial, cita/página/pasaje + loop relevance-first 1997→presente |
| Orquestación multi-fuente | ✅ Separa ranking verificado de candidatos oficiales pendientes de verificación de contenido |
| Lector genérico de autoridad primaria | ✅ HTML/PDF con pasajes verificables en hosts primarios autorizados |
| Historial legislativo SUTRA | ✅ Grafo automático de enmiendas/derogaciones explícitas con verificación de detalle oficial |
| Vigencia legislativa positiva | 🟡 Conservadora: detecta afectaciones; confirmar texto oficial consolidado sigue siendo requisito para afirmar vigencia positiva |
| Decisiones administrativas laborales (JRT) | ✅ Descubrimiento global acotado + verificación de texto en PDFs gubernamentales |
| Tribunal de Apelaciones | 🟡 Índice oficial y búsqueda inicial; profundización por materia/documento pendiente |
| Leyes / resoluciones conjuntas | 🟡 Portal oficial integrado + historial SUTRA; búsqueda estructurada/texto consolidado pendiente |
| Reglamentos | 🟡 Portal oficial integrado; texto/vigencia/historial pendiente |
| Órdenes ejecutivas | 🟡 Portal oficial integrado |
| Autoridad federal | ⏳ Próxima expansión |
| Actualidad jurídica pública | 🟡 Microjuris Al Día como fuente secundaria |
| Grafo de citas / tratamiento posterior | 🟡 Citation chaining TSPR inicial; tratamiento posterior completo pendiente |

## Licencia y contenido de terceros

El **código de este repositorio** se publica bajo licencia MIT. Eso no convierte en MIT los documentos, sitios o contenido de terceros a los que el MCP enlaza o consulta. Cada fuente mantiene sus propios términos, derechos y políticas.

Este proyecto no está afiliado ni respaldado por el Poder Judicial de Puerto Rico, la Oficina de Servicios Legislativos, el Departamento de Estado, la Junta de Relaciones del Trabajo, CodeXPR, LexJuris ni Microjuris.

## Aviso

Herramienta de investigación jurídica. No sustituye la revisión profesional de las autoridades, historial, vigencia, tratamiento posterior ni expediente oficial. Antes de presentar una autoridad en un escrito, verifica la fuente primaria y su estado actual.
