# Agente de CV — Wazy

Es un agente conversacional que conoce y representa la trayectoria profesional de Jesus Huazano, las interacciones con la API son compatibles con la especificacion [Open Responses](https://www.openresponses.org/). Reclutadores o público en general puedn preguntar acerca de experiencia, habilidades, investigacion o cualquier detalle que prefieran conocer, el agente responderá basado en la informacion plasmada en el CV, NUNCA inventará informacióm.

## Estructura

```
/
├── app/
│   ├── main.py                 # FastAPI app con endpoint para "health check" disponible para entornos productivos
│   ├── config.py                # Configuracion base del entorno (variables de entorno)
│   ├── auth.py                  # Verificacion  autenticacion
│   ├── schemas.py                # Modelos Pydantic para la cumplir con Open Responses
│   ├── routers/
│   │   └── responses.py          # POST /v1/responses — ciclo del agente para responder, además maneja el uso de herramients y auditoria 
│   ├── contexts/
│   │   ├── cv_agent.py            # Descripcion del agente y su comportamiento. Podrian agregarse mas agentes.
│   │   ├── tools.py               # Definicion de herramientas disponibles para el agente, se pueden agregar más
│   │   └── sources/
│   │       └── CV-Huazano-FULL-EN_V1.md   # CV actual
│   ├── memory/
│   │   └── database.py            # Manejo de SQLite para la auditoria y trazabilidad de las conversaciones
│   └── storage/
│       └── memory.db              # DB SQLite, esta se crea al momento de  trabajar con el agente, por ende no existe en el repositorio
├── chat-ui.py                    # Interfaz web local usando Gradio chat para un prototipado rapido
├── requirements.txt
└── example.env                   # Ejemp,o de .env con la plantilla de variables pero sin datos reales
```

## Arquitectura

```
Cliente - GUI del chat
        │  POST /v1/responses  (Authorization: Bearer <token>)
        ▼
FastAPI ─ auth.verify_token ─ routers/responses.py
        │
        ├─ Primero llama a Responses donde se controla la personalidad del agente, y desglosa las instrucciones entre las herramientas disponibles para su labor (instrucciones = trato basado en la personalidad del agente, tools = [read_cv, fetch_link])
        │
        ├─ si el usuario pide información de algun otro tema, el agente redirige la conversación hacia el contenido del CV, para evitar un uso indebido del agente y del modelo — guardrail.
        │
        ├─ si el modelo pide usar una herramienta:
        │     read_cv()      → lee el archivo del CV desde disco
        │     fetch_link(url) → llamada a la API de GitHub, o intento de lectura de tags públicos de LinkedIn. En ambos casos se ejecuta si existe el enlace en el CV y si la plataforma de destino lo permite. Cualquier otro dominio se rechaza ANTES de hacer cualquier llamada de red — guardrail.
        │
        ├─ el resultado de la tool se envía de vuelta vía previous_response_id → segunda llamada → se repite hasta que no pida más tools
        │
        ├─ se guarda un registro en SQLite (conversation_turns) patra llevar auditoría de lo conversado auditoría, nunca se le devuelve al modelo
        │
        ▼
Se retorna la respuesta en formato Open Responses
```

## Decisiones Técnicas Clave

### ¿Porqué FastAPI?
FastAPI es un framework reconocido que facilita la creación de API Restful de manera rápida y eficiente. Al aplicar el spec de Open Responses, permite integrar directamente con el SDK de OpenAI donde `client.responses.create()` tiene el mismo formato que pide el spec. Sin esto, haía falta una capa de traducción con cualquier otro proveedor, aquí es donde el modelo async de FastAPI encaja bien con el ciclo de llamadas a las tools (esperar a OpenAI, esperar las llamadas HTTP salientes a GitHub/LinkedIn), y su integración con Pydantic valida los requests contra el esquema JSON del spec.

### ¿Porqué no usar Langchain y RAG?
Este agente por diseño es "chico" basado su funcionamiento en un solo archivo de información: el CV de una persona. Entonces implementar un pipeline completo de RAG sería util en el caso donde el knowledge-base fuese mucho más grande(con diversos archivos y sources), problema que acá no existe. El manejo de un ciclo de llamadas a herramientas cubre la obtención de información y consulta del SDK de OpenAI. Para este caso en particular, esta estructura permite observar el mecanismo de forma explicita en lugar de tener una caja negra (el executor de Langchain) que solo dá un resultado al final.

### ¿Cuando puede aplicarse Langchain?
Si el proyecto crece a tener multiples CVs/sources (en el orden de los cientos o miles), además las herramientas y/o número de agentes incrementa, entonces lo ideal es usar Langchain para abstraerlos comportamientos y orquestar el proceso completo. Además, el almacenamiento de la información cobraría mayor relevancia haciendo uso de vectores y memoria más rápida  para optimizar el desempeño general del agente.

### Por qué tools en vez de meter todo en el "Agent prompt"
Al separar en herramientas y "personalidad" del agente, hacemos una distinción entre "¿Que puedo hacer?" y "¿Como debo comportarme?". Adicional, esta separación evita que el modelo intente hacer acciones no autorizadas o que intente comportarse de manera  indebida en haras de resolver  las preguntas del cliente. 

El agente Wazy tiene  las siguientes herramientas para trabajar:
- `read_cv` el system prompt le indica al modelo que siempre llame a esta herramienta antes de responder preguntas de trayectoria, previniendo incrustar el CV completo en cada request o inventar "historias".
- `fetch_link` le permite al agente responder con datos "online" en vez de información estática, mientras que una white-list estricta de dominios (`github.com`, `linkedin.com` únicamente) evita que la herramienta se use para consultar URLs ajenas, implementando implicitamente un Guardrail.

Como extra a las herramientas, el agente tiene un guardrail más, que indica que no debe responder preguntas que no estén relacionadas con el CV o con la trayectoria profesional de la persona, redirigiendo en todo momento el foco de la conversación hacia el CV/experiencia profesional.

#### ¿Porqué el agente maneja el consultar LinkedIn como una limitación?
LinkedIn bloquea el scraping sin autenticación, por ello en vez de fingir que esto no es una limitación, la rama de LinkedIn en `fetch_link` detecta los modos de falla específicos (error de red, redirección a authwall, ausencia de tags públicos Open Graph) y devuelve un mensaje claro y honesto para que el agente recurra a lo que ya sabe por el CV — en vez de romperse, quedarse "pensando" o inventar un resumen de perfil.

### En este caso ¿Porqué la memoria de la conversación depende del propio estado de OpenAI?
El backend es stateless respecto a la continuidad del modelo. En cada request se pasa el `previous_response_id` esto le permite a OpenAI reconstruir todo el contexto anterior del lado del servidor.

#### Ventaja para este caso del agente
- No necesitamos mantener un historial local de la conversación.
- El modelo tiene una visión más completa del contexto.
- Reducción de complejidad en el backend.

#### Desventajas para este caso del agente
- No podemos manejar el historial de la conversación para futuras sesiones.
- El modelo tiene que manejar la continuidad del contexto por sí solo durante la sesión actual.
- No podemos agregar información adicional al contexto que no esté en la conversación.

#### Casos donde conviene implementar memoria en el agente
- Cuando la información que maneja el agente es sensible y no debiera permanecer en proveedores externos
- Cuando se necesita mantener un historial de la conversación para futuras sesiones.
- Cuando la información historica deba influir en decisiones o procesos futuros
- Cuando la cantidad de sources es muy grande y se necesita optimizar el contexto
- Cuando se tienen diversos clientes y cada uno necesita un historial separado

### En este caso,¿Porqué SQLite es usado como deposito de auditoría?
La tabla `conversation_turns` existe para la observabilidad propia, es decir saber "qué se preguntó", "qué tool corrió" y "qué se respondió". Con ello Responde verificamos que el agente se comporta de forma coherente a lo que establecimos. Además se uso SQLite por practicidad para este proyecto, en su momento podria usarrse otra base de datos así como bases de datos vectoriales si el sistema se complejisa.

### ¿Porqué se incluye unlogging estructurado (módulo `logging` de Python)?
Con ello obtenemos salidas con niveles de prioridad, timestamps, y filtrable vía `LOG_LEVEL`, adicionalmente esta es una práctica estándar para trazar un servicio corriendo, sirviendo como base necesaria para algun debug o revisión rapido.

#### ¿Esto sustituye las herramientas de monitoreo y/o observabilidad?
De ningun modo las sustituye, pero es una ayuda para ciertos casos y entornos como lo siguiente:
- Debug rápido de algun problema
- Debug en entornos locales y de staging para rastrear el flujo paso a paso
- Facilidad de lectura para desarrolladores JR o nuevos en el equipo.

Siempre se debe priorizar el uso de herramientas de monitoreo y/o observabilidad (sentry, datadog, glitchtip, etc.) para un mejor tracking y análisis

### ¿Porqué la configuración vive en `pydantic-settings` + `.env`?
Los "secrets keys" y algunos otros valores de entorno nunca deben vivir en el código por razones básicas de seguridad y prácticas de desarrollo. El archivo `example.env` funge como una plantilla del archivo `.env` real, así cualquiera que clone el proyecto sabe exactamente qué configurar sin ver nunca un valor real.

Por el lado de `pydantic`, su estructura estricta garantiza que los valores necesarios para la configuración existan, sean validados y tipados en tiempo de ejecución, evitando así errores de configuración que en muchos casos pueden pasar desapercibidos, en sistemas grandes principalmente.

### ¿Porqué la GUI está en Gradio y no en un frontend propio?
Gradio da un cliente de chat funcional desde el mismo Python, sin configuración de CORS, sin pipeline de build/deploy separado, y sin exponer la API key del lado del cliente. Por lo acotado del caso es una solución ideal.

#### ¿Podría implementarse un front más elaborado?
Sí, por ejemplo podriamos montar algo nuevo con React o Vue, pero habria que tener otras consideraciones como:
- Configuración de CORS
- Pipeline de build/deploy separado
- Exposición de la API key del lado del cliente o bien un manejo de permisos más complejo para autenticar al usuario y validar su acceso (via JWT por ejemplo).
- Manejo y creación de múltiples componentes visuales, así como sus estados.

### ¿Por qué el system prompt tiene una instrucción explícita anti-alucinación?
Para este caso en particular, el agente representa la trayectoria profesional real de una persona ante reclutadores reales, la precisión es un requisito obligatorio.  Por tal razon al modelo se le indica expresamente que diga cuando algo "no lo sabe" debido a que no está en el CV, en vez de inferirlo o inventarlo.

#### ¿Existen casos donde esta regla no aplica?
Este "guardrail" es fundamental en la mayoria de agentes que manejan información sensible o conlleve decisiones criticas para él u otros procesos. Podrá darse un caso donde un agente  ayude a una persona a desarrollar arte, en tal caso esta regla  limitaria el desempeño de ese agente.

### ¿Porqué un harness de evaluación ad-hoc?
Los cambios en el prompt del agente o en las herramientas pueden romper silenciosamente el funcionamiento de lo que antes funcionaba,la forma de notarlo en una etapa inicial es probando a mano y confirmando todos los casos. En este proyecto `eval/cases.py` codifica un conjunto fijo de pares pregunta/comportamiento esperado basado en el CV real (cumpliendo guardrails y evitando alucinaciones ante información faltante). Por supárte `eval/run_eval.py` los corre contra el endpoint real `/v1/responses` probando el "happy-path" completo (auth, el loop de tool calling, los guardrails), no una función aislada.

La evaluación usa comparación simple de palabras clave (`must_include` / `must_not_include`) en vez de una segunda llamada al modelo como juez: esto mantiene las pruebas  determinísticas y baratas. Normalmente la misma entrada siempre produce el mismo veredicto, sin costo extra de API e indeterminismo agregado propio tipo de sistema evaluado. Los casos de prueba también funcionan como documentación  de qué significa una "respuesta correcta" para este agente.

#### ¿Existen frameworks/librerías/alternativas mas robustas?
Sí, existen herramientas como `mlflow`, `DeepEval`, `pytest`, entre otras que pueden ser usados para evaluar agentes. Sin embargo, para este caso en particular, la simplicidad y determinismo del harness ad-hoc puede ser suficiente.s

## Cómo Correr el agente

```bash
python3 -m venv environment
source environment/bin/activate
pip install -r requirements.txt

cp example.env .env   # completar con valores reales: OPENAI_API_KEY, API_KEY, DEFAULT_OPENAI_MODEL, API_URL, LOG_LEVEL

uvicorn app.main:app --reload
```

## Limitaciones Conocidas
- Los datos de LinkedIn se limitan a lo que exponga públicamente la plataforma, obtener el perfil completo requeriere autenticación, algo que este proyecto puede hacer.
- El agente está acotado a un solo CV; una versión multi-candidato necesitaría una capa de retrieval, que quedó fuera de alcance a propósito.