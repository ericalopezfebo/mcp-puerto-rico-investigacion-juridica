# Taxonomía de autoridades jurídicas

El proyecto ya no se limita a sentencias. La capa de investigación jurídica organiza resultados por **tipo de autoridad, materia, tema específico, fuente, jerarquía y estado de verificación**.

## Taxonomía inicial

La taxonomía se inspira en el inventario de autoridades preparado para el proyecto `legal-agents`. Ese inventario contiene aproximadamente 450 filas y cubre, entre otras, estas clases:

- Decisiones del Tribunal Supremo de Puerto Rico (TSPR / DPR)
- Decisiones federales
- Leyes especiales
- Códigos
- Estatutos constitucionales
- Reglamentos

Las materias representadas inicialmente incluyen principalmente:

- Derecho administrativo
- Derecho constitucional
- Derecho penal
- Cruces Administrativo–Constitucional
- Cruces Penal–Constitucional
- Cruces Administrativo–Penal

## El inventario es un *seed*, no una fuente primaria

El inventario sirve para:

1. descubrir autoridades que vale la pena verificar;
2. sembrar términos doctrinales y sinónimos de búsqueda;
3. construir relaciones entre materias y tipos de autoridad;
4. priorizar verificaciones futuras;
5. detectar huecos de cobertura.

**No debe utilizarse por sí solo como prueba de que una autoridad existe, está vigente o sostiene una proposición.** Algunas filas del inventario están expresamente marcadas como “Pendiente de verificar” o contienen notas de posible error de cita. Esa cautela se conserva en este proyecto.

## Regla de promoción de una autoridad

Una entrada pasa de `seed/no_verificada` a `verificada` solo cuando el MCP puede enlazarla con una fuente identificable y comprobar al menos su identificador. Para citas textuales, holdings, fechas, nombres de caso o páginas, la comprobación debe provenir del documento fuente correspondiente.

Estados recomendados:

- `seed_no_verificada`
- `fuente_encontrada_identificador_no_confirmado`
- `identificador_verificado`
- `texto_fuente_verificado`
- `vigencia_no_determinada`
- `vigencia_verificada`

## Jerarquía de fuentes

1. Constitución / legislación / reglamentación oficial
2. Tribunal Supremo de Puerto Rico
3. Tribunal de Apelaciones de Puerto Rico
4. Decisiones administrativas oficiales
5. Autoridad federal aplicable
6. Fuentes secundarias públicas para descubrimiento y contexto

Una noticia, resumen o comentario doctrinal puede ayudar a localizar un desarrollo, pero no sustituye la autoridad primaria para una proposición jurídica cuando la fuente primaria está disponible.

## Próximas expansiones

- Índice verificable de leyes y resoluciones conjuntas
- Reglamentos de agencias y su historial
- Órdenes ejecutivas
- Decisiones administrativas laborales
- Tribunal de Apelaciones con lectura de documento
- Autoridad federal pertinente a Puerto Rico
- Grafo de citas entre sentencias, leyes y reglamentos
- Vigencia / enmiendas / tratamiento posterior cuando pueda verificarse de forma fiable
