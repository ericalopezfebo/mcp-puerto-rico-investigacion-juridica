# VELUM — MCP local para documentos legales 🇵🇷

**VELUM** es un servidor MCP **local-first** para abogados y profesionales que necesitan preparar documentos jurídicos sensibles antes de utilizar una IA.

## La idea central

```text
Documento legal original
        │
        ▼
   VELUM en tu equipo
        │
        ├── extracción local
        ├── redacción determinística
        ├── reglas personalizadas
        └── copia sanitizada local
                │
                ▼
       revisión humana
                │
                ▼
       IA externa, si el usuario decide compartir
```

### Qué significa "local"

Las funciones de privacidad de VELUM procesan el archivo **en la computadora donde se ejecuta el MCP**. No necesitan una cuenta de VELUM, una base de datos remota ni un servidor VELUM para anonimizar el documento.

- El archivo original se lee desde `VELUM_DOCUMENT_ROOT`.
- Las herramientas de privacidad no hacen llamadas HTTP para procesar documentos.
- VELUM usa MCP **stdio**; no abre un puerto HTTP para el servidor local.
- El original no se modifica.
- La copia anonimizada se crea dentro del directorio local permitido.
- La huella SHA-256 se calcula localmente sin devolver el contenido.
- La ruta de un documento se valida para impedir acceso fuera del directorio autorizado.

### Límite importante de privacidad

VELUM protege el **documento original durante el procesamiento local**. No puede controlar lo que un usuario posteriormente envíe a un proveedor de IA.

Si una herramienta devuelve texto a ChatGPT, Claude u otra IA, **ese texto sale del equipo y llega al proveedor de IA**. Por eso el flujo recomendado para material confidencial es:

1. Mantener el original dentro de `VELUM_DOCUMENT_ROOT`.
2. Procesarlo con VELUM localmente.
3. Generar texto o una copia sanitizada.
4. Revisar manualmente la sanitización.
5. Compartir únicamente el contenido que el abogado autorice.

**VELUM no garantiza que toda información personal, confidencial o privilegiada sea detectada automáticamente. La revisión humana sigue siendo necesaria.**

## No usamos un LLM para anonimizar

La anonimización básica es **determinística**, mediante reglas locales. Actualmente contempla, entre otros:

- correo electrónico;
- teléfonos con formato estadounidense/PR;
- SSN;
- números de tarjeta;
- fechas identificadas explícitamente como fecha de nacimiento;
- redacciones personalizadas definidas por el usuario.

Ejemplo:

```json
{
  "Jane Doe": "[CLIENTE]",
  "Acme Holdings LLC": "[EMPRESA]",
  "787-555-9876": "[TELEFONO_CLIENTE]"
}
```

Esto **no es una garantía de anonimización completa**. Nombres, direcciones, hechos, relaciones familiares, números de caso y combinaciones de hechos pueden requerir reglas adicionales y revisión profesional.

## Instalación

Requiere Python 3.10+.

```bash
git clone https://github.com/ericalopezfebo/mcp-puerto-rico-sentencias.git
cd mcp-puerto-rico-sentencias

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"

mkdir -p ~/Documents/VELUM
export VELUM_DOCUMENT_ROOT="$HOME/Documents/VELUM"
```

## Ejecutar VELUM

El servidor local se inicia con:

```bash
velum
```

También funciona:

```bash
python3 velum.py
```

Un servidor MCP por `stdio` normalmente **no muestra un menú ni abre una ventana**: queda esperando mensajes del cliente MCP. Esto es comportamiento esperado.

Para detenerlo manualmente:

```text
Ctrl+C
```

## Herramientas de privacidad

### `listar_documentos_locales`

Lista nombres y metadatos de archivos permitidos sin devolver su contenido.

### `huella_documento_local`

Calcula SHA-256 localmente.

### `preparar_documento_para_ia`

Lee el documento local, extrae su texto y aplica las redacciones determinísticas. Devuelve **solo el texto sanitizado**; el original no se devuelve como resultado de la herramienta.

### `crear_copia_anonimizada`

Crea una copia `.anonimizado.txt` dentro del directorio local permitido. El archivo original no se modifica.

### `estado_privacidad`

Expone el límite técnico de privacidad y deja claro qué ocurre si el resultado se entrega a una IA externa.

## Formatos locales

- PDF
- DOCX
- TXT
- Markdown
- HTML

Límite predeterminado: **25 MB por archivo**.

## Seguridad del sistema de archivos

Por defecto VELUM permite documentos solamente dentro de:

```text
~/Documents/VELUM
```

Puedes cambiarlo con:

```bash
export VELUM_DOCUMENT_ROOT="$HOME/Documents/VELUM"
```

Una herramienta no puede utilizar una ruta fuera de ese directorio. Esto reduce el riesgo de que una llamada MCP intente acceder a archivos como claves SSH, credenciales u otros archivos personales.

## Jurisprudencia de Puerto Rico

VELUM también incluye herramientas para investigación de jurisprudencia pública:

- `buscar_sentencias`
- `buscar_por_cita`
- `leer_sentencia`
- `opciones_busqueda`
- `estado`

Estas funciones son diferentes de las funciones de privacidad: **sí necesitan Internet para consultar las fuentes públicas configuradas**. La privacidad local de documentos no depende de esas consultas.

La regla de investigación es **source-first / zero citation hallucination**: el servidor no debe inventar casos, citas, nombres, fechas, holdings ni citas textuales.

## Clientes de IA

### Clientes que admiten MCP local por stdio

Un cliente compatible puede iniciar `velum` como proceso local. `examples/` contiene una configuración de referencia para clientes que aceptan el formato de configuración indicado.

### ChatGPT

La disponibilidad y el mecanismo de conexión de MCP dependen del producto de ChatGPT y de su configuración. Un MCP que solo corre por `stdio` en la computadora del usuario no debe describirse como "conectado directamente a ChatGPT" sin una capa de conexión compatible.

**La arquitectura de privacidad de VELUM no depende de un servidor VELUM remoto.** Si se utiliza un mecanismo externo para conectar el MCP con una IA, el usuario debe revisar qué datos devuelve cada herramienta y qué recibe el proveedor de IA.

## Qué NO hace VELUM

- No sube el documento original a un servidor VELUM.
- No guarda expedientes en una base de datos remota.
- No utiliza OpenAI, Anthropic u otro LLM para decidir qué texto ocultar.
- No modifica el archivo original.
- No promete detectar todos los datos personales o confidenciales.
- No convierte por sí solo un documento en "privilegiado" ni determina obligaciones éticas.

## Para uso jurídico

VELUM es una herramienta técnica de privacidad y preparación documental. **No sustituye el juicio profesional del abogado.** Antes de compartir material de un cliente con una IA, el abogado debe evaluar las obligaciones aplicables de confidencialidad, competencia, supervisión, seguridad de la información, consentimiento cuando corresponda y las reglas profesionales de su jurisdicción y organización.

Para jurisprudencia, verifica siempre la fuente primaria y la vigencia/aplicabilidad de la autoridad antes de utilizarla en un escrito.

## Pruebas

```bash
pytest -q
```

Las pruebas cubren, entre otras cosas:

- redacción de identificadores comunes;
- redacciones personalizadas;
- ausencia del original en el resultado sanitizado;
- rechazo de rutas fuera de `VELUM_DOCUMENT_ROOT`.

## Licencia

El código original está disponible bajo **MIT License**. La licencia del software no concede derechos sobre sentencias, sitios web, marcas, bases de datos u otros contenidos de terceros.
