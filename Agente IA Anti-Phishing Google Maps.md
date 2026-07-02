# **Especificaciones Técnicas y Arquitectura de un Sistema de Agentes de Inteligencia Artificial para la Mitigación de Phishing y Suplantación de Identidad Geográfica en la Red de Distribución de Yamaha Medellín**

La evolución de las tácticas de ciberdelincuencia ha encontrado un terreno fértil en las plataformas de servicios basados en la localización, específicamente en el ecosistema de Google Maps. En centros urbanos de alta densidad comercial y movilidad como Medellín, la suplantación de identidad de concesionarios de motocicletas no solo representa una infracción de propiedad intelectual, sino una amenaza directa a la seguridad financiera de los consumidores y a la integridad operativa de marcas líderes como Yamaha.1 El presente reporte técnico detalla las especificaciones para una solución agentificada de vigilancia continua, diseñada para identificar, validar y reportar de manera automatizada contenidos malintencionados, protegiendo así el ecosistema digital de Incolmotos Yamaha y su red de distribución autorizada en el Valle de Aburrá.

## **Análisis del Panorama de Amenazas en el Contexto de Medellín**

La ciudad de Medellín se caracteriza por una cultura de motociclismo profundamente arraigada, lo que convierte a marcas como Yamaha en objetivos primarios para redes de estafa sofisticadas. Se han identificado dos modalidades críticas de fraude que explotan las vulnerabilidades del contenido generado por el usuario en Google Maps. La primera modalidad implica la creación de puntos de interés ficticios en ubicaciones estratégicas, a menudo cerca de concesionarios reales en sectores como Guayabal, la Calle 33 o la Avenida San Juan.1 Estos sitios fraudulentos utilizan nombres que evocan autoridad, tales como "Yamaha Principal" o "Centro de Entregas Yamaha", y cargan fotografías legítimas de motocicletas y fachadas para engañar al usuario.5

La segunda modalidad, de carácter más técnico y sigiloso, consiste en la inyección de imágenes manipuladas mediante inteligencia artificial generativa dentro de los perfiles de negocios legítimos. Estas imágenes alteran digitalmente la fachada del establecimiento para mostrar números de contacto falsos, induciendo a los clientes a realizar transacciones de preventa o separar vehículos a través de canales no oficiales, generalmente solicitando transferencias a cuentas de personas naturales en plataformas como Nequi.5

| Atributo de la Amenaza | POI Ficticio (Clonación) | Manipulación de Fachada en Perfil Real |
| :---- | :---- | :---- |
| **Mecanismo** | Creación de un nuevo listado en Google Maps.1 | Carga de fotos en la sección de reseñas de un local existente.1 |
| **Objetivo** | Desviar el tráfico peatonal y digital a una ubicación falsa. | Engañar al usuario que consulta la ficha del negocio oficial. |
| **Herramienta de Engaño** | Nombres engañosos y fotos robadas de redes oficiales.2 | Fotos editadas con IA que cambian el teléfono en el letrero físico. |
| **Impacto Financiero** | Estafas masivas de preventas y "cuotas iniciales".5 | Pérdida de confianza en los canales de contacto oficiales. |
| **Dificultad de Detección** | Media (identificable mediante escaneo geofencing). | Muy Alta (requiere análisis forense de píxeles y OCR).8 |

## **Fundamentos del Ecosistema de Datos de Google Maps y Business Profile**

Para implementar una solución efectiva, es necesario navegar las capacidades técnicas de las interfaces de programación de aplicaciones de Google. La gestión de la presencia digital se divide entre la capacidad de administración de activos propios y el monitoreo del entorno competitivo y malicioso.

### **Google Business Profile API y la Gestión de Activos Propios**

La Business Profile API permite a las organizaciones gestionar sus ubicaciones verificadas a escala. Una característica fundamental para esta arquitectura es la suscripción a notificaciones push a través de Cloud Pub/Sub, lo que permite recibir alertas en tiempo real cuando un usuario carga una nueva foto o reseña en una ubicación administrada por la empresa.10 Este mecanismo elimina la necesidad de realizar peticiones constantes (polling) y permite una reacción inmediata ante la inyección de fotos manipuladas.

### **Google Places API (New) y el Monitoreo Geoespacial**

Para la detección de sitios ficticios, la Places API (New) proporciona las herramientas necesarias para realizar búsquedas texturales y de proximidad. Mediante el uso de Nearby Search (New) y Text Search (New), el sistema puede identificar todos los negocios categorizados como "motorcycle\_dealer" o "motorcycle\_repair\_shop" en un radio determinado alrededor de las coordenadas de los concesionarios oficiales.12 Un componente crítico de la versión más reciente de esta API es el campo flagContentUri, el cual proporciona un enlace directo para que los usuarios (o agentes en este caso) puedan reportar contenido inapropiado o fraudulento directamente a los sistemas de moderación de Google.15

| Servicio API | Función Principal en la Solución | Tipo de Datos Retornados |
| :---- | :---- | :---- |
| **Business Profile API** | Monitoreo de activos propios (Yamaha Oficial). | Notificaciones de nuevas fotos y reseñas.10 |
| **Places API (New)** | Escaneo de POIs cercanos y obtención de URIs de reporte. | Detalles de lugar, fotos, reseñas y enlaces de denuncia.15 |
| **Cloud Vision API** | Extracción de texto en fachadas de locales sospechosos. | Texto detectado (OCR) y etiquetas de contenido.16 |
| **Vertex AI (Gemini)** | Análisis forense multimodal de imágenes manipuladas. | Clasificación de autenticidad y razonamiento explicativo.8 |

## **Arquitectura de la Solución Agentificada: El Sistema "Vigilante"**

La arquitectura propuesta se basa en un sistema de múltiples agentes especializados que operan de manera coordinada bajo un orquestador central. Este diseño permite separar las tareas de exploración, análisis y acción, garantizando la escalabilidad y la facilidad de mantenimiento.17

### **El Agente Explorador (Scout Agent)**

El Agente Explorador actúa como la primera línea de defensa. Su misión es la vigilancia constante del mapa de Medellín y el área metropolitana. Este agente realiza dos tipos de tareas:

1. **Vigilancia de Perfiles Propios**: Integrado con la Business Profile API, escucha las notificaciones de nuevos elementos multimedia. Ante cualquier carga de fotos por parte de "Local Guides" o usuarios anónimos en perfiles como "Mundo Yamaha Guayabal" o "Yamaha Motos Itagüí", el agente descarga el recurso y lo envía a la cola de análisis.4  
2. **Barrido Geoespacial Proactivo**: Ejecuta escaneos periódicos (cada 30 a 60 minutos) en zonas críticas. El barrido utiliza consultas como "Yamaha Medellín" o "Taller Yamaha" para identificar listados que no coincidan con la base de datos de concesionarios autorizados proporcionada por Incolmotos Yamaha.1

### **El Agente Forense de Visión (Forensic Vision Agent)**

Este agente es el núcleo inteligente de la solución. Recibe las imágenes capturadas por el Explorador y ejecuta una serie de validaciones multinivel para determinar la probabilidad de fraude.

#### **Reconocimiento Óptico de Caracteres (OCR) y Validación de Whitelist**

El agente utiliza modelos de visión computacional para extraer números telefónicos y URLs que aparecen físicamente en las fotos de las fachadas o en el texto de las reseñas. Estos datos se contrastan con una "Lista Blanca" dinámica que contiene la información de contacto oficial de la red Yamaha.3

![][image1]  
Donde ![][image2] es el texto extraído de la imagen y ![][image3] es el conjunto de números autorizados. Cualquier discrepancia genera una alerta de alta prioridad.16

#### **Análisis Forense de IA Generativa**

Para combatir las fotos creadas o editadas con IA, el agente emplea modelos de lenguaje de visión (VLM) como Gemini 1.5 Pro. Estos modelos analizan la coherencia semántica y física de la imagen, buscando artefactos comunes en la generación de texto digital sobre superficies reales, como inconsistencias en la iluminación, bordes dentados en las fuentes o sombras que no corresponden con la geometría de la fachada.8

| Técnica Forense | Descripción Técnica | Implementación en el Agente |
| :---- | :---- | :---- |
| **Análisis de Consistencia de Bordes** | Identificación de "aliasing" o bordes poco naturales en el texto editado. | Procesamiento de píxeles mediante VLM.8 |
| **Validación de Iluminación** | Verificación de que la luz sobre el número telefónico coincida con la luz ambiental de la foto. | Análisis de patrones geométricos de luz.20 |
| **Firma de Metadatos** | Revisión de campos EXIF o etiquetas de software de edición/IA (ej. DALL-E, Midjourney). | Extracción de metadatos de imagen.21 |
| **Snap-back de Difusión** | Evaluación de cómo se degrada la imagen bajo procesos de reconstrucción controlada. | Modelos de clasificación basados en regresión logística.22 |

### 

### **El Agente de Reporte y Mitigación (Reporter Agent)**

Una vez confirmada la sospecha de phishing, el Agente de Reporte ejecuta las acciones de mitigación necesarias. Su objetivo es neutralizar la amenaza antes de que cause daños económicos significativos.

1. **Activación de Notificaciones de Emergencia**: El sistema envía alertas inmediatas a través de canales de comunicación corporativa (ej. Slack, WhatsApp) detallando el tipo de amenaza, la ubicación y el material probatorio.17  
2. **Reporte Automatizado vía API**: Utiliza el enlace proporcionado por el campo flagContentUri de la Places API para iniciar el proceso de denuncia formal ante Google.15  
3. **Gestión de Quejas por Suplantación de Identidad**: Para casos de perfiles falsos recurrentes, el agente prepara automáticamente la documentación para el **Business Redressal Complaint Form**, incluyendo capturas de pantalla de Street View que demuestran la inexistencia del negocio en esa dirección física.24

## **Especificaciones de Implementación y Mejores Prácticas**

La implementación de este sistema debe adherirse estrictamente a las políticas de Google Maps Platform para evitar la suspensión de las credenciales de la API y garantizar la validez legal de los reportes.

### **Gestión de Identidad y Seguridad**

El acceso a las APIs debe realizarse mediante cuentas de servicio con permisos granulares. Se recomienda el uso de OAuth 2.0 para la autenticación de la Business Profile API, permitiendo que el agente actúe en representación de los administradores de los perfiles de Yamaha.10 Las claves de API deben estar restringidas por dirección IP o por identificadores de aplicación para prevenir su uso no autorizado.

### **Política de Almacenamiento y Privacidad**

De acuerdo con los términos de servicio de Google, no se permite el almacenamiento persistente de contenido de mapas por más de 30 días.29 El sistema debe implementar políticas de purga automática para las imágenes y reseñas analizadas que no hayan sido marcadas como evidencia de fraude. Además, se debe priorizar el procesamiento de datos públicos de negocios, evitando la recolección de información personal identificable (PII) de usuarios legítimos.30

### **Optimización de Costos y Recursos**

El monitoreo continuo puede generar costos significativos en Cloud. Para optimizar el presupuesto, el agente debe:

* Utilizar notificaciones push (Pub/Sub) en lugar de consultas frecuentes a la API para perfiles propios.10  
* Implementar una lógica de filtrado inicial (ej. detectar si una foto contiene texto antes de enviarla a un VLM costoso) utilizando modelos de OCR ligeros.32  
* Aprovechar el nivel gratuito mensual de la Vision API (primeras 1,000 unidades) para el análisis preliminar.32

| Componente | Producto Sugerido | Justificación Técnica |
| :---- | :---- | :---- |
| **Orquestador** | Vertex AI Agent Engine | Facilita el despliegue de agentes con memoria y herramientas.17 |
| **Modelos de IA** | Gemini 1.5 Flash / Pro | Capacidad multimodal para análisis de imágenes y razonamiento de fraude.8 |
| **Base de Datos** | Cloud Firestore | Almacenamiento de estado de corto plazo y listas blancas de teléfonos.33 |
| **Comunicación** | Cloud Pub/Sub | Gestión de eventos en tiempo real de Google Business Profile.10 |

## 

## **Protocolo Forense para la Identificación de Manipulación de Fachadas**

La detección de números telefónicos falsos en fotos de fachadas requiere un enfoque técnico riguroso. El agente forense debe estar programado para identificar anomalías en tres dimensiones: tipografía, geometría y contexto digital.

### **Análisis de Tipografía y Fuente**

En las imágenes generadas por IA o editadas toscamente, el texto suele presentar una resolución diferente a la del resto de la imagen. El agente debe buscar inconsistencias en el "kerning" (espaciado entre letras) y en el estilo de la fuente. Los letreros físicos de Yamaha Medellín siguen manuales de identidad corporativa estrictos; cualquier desviación en la familia tipográfica es un indicador de fraude.8

### **Coherencia Geométrica y de Perspectiva**

Los modelos de edición digital a menudo fallan al alinear el texto con la perspectiva de la pared o el aviso físico. El agente de visión debe proyectar líneas de fuga sobre la superficie detectada. Si el ángulo del número telefónico no coincide con los puntos de fuga de la estructura arquitectónica, se clasifica como una alteración digital.20

### **Detección de Phishing mediante Contexto de Usuario**

El sistema no solo analiza la foto, sino el comportamiento del usuario que la subió. El agente debe evaluar:

* **Antigüedad de la cuenta**: Cuentas creadas recientemente con pocas contribuciones.27  
* **Patrones de carga**: Subida de la misma foto en múltiples ubicaciones geográficamente distantes.1  
* **Contenido de la reseña**: Uso de lenguaje de urgencia o promesas de "entrega inmediata" vinculadas al número telefónico falso.5

## **Estrategia de Mitigación y Reporte ante Google**

La efectividad de la solución depende de que los reportes sean aceptados y procesados rápidamente por Google. Existen dos caminos principales para la acción correctiva.

### **Reporte de Contenido Individual (Agente de Acción Rápida)**

Para fotos y reseñas individuales, el agente debe invocar el URI de reporte. Este proceso es vital porque vincula la denuncia a un objeto de contenido específico identificado por Google.15 La automatización de este paso reduce el tiempo de exposición de los clientes a la estafa de horas a minutos.

### **Denuncia por Suplantación de Marca (Agente de Redressal)**

Cuando se identifica una red de múltiples sitios falsos, el reporte individual es insuficiente. El agente debe compilar un caso de "Redressal" masivo. Este proceso es revisado por personal humano en Google y tiene una alta tasa de éxito si se presenta con evidencia contundente.25

**Estructura del Informe de Evidencia Generado por el Agente:**

* **Encabezado**: Identificación de la marca suplantada (Incolmotos Yamaha S.A.).36  
* **Listado de URLs**: Enlaces de Google Maps a todos los perfiles fraudulentos detectados.  
* **Prueba de Inexistencia**: Comparativa entre la ubicación del pin en el mapa y las imágenes de Street View que muestran un uso de suelo diferente (ej. un parque o una casa residencial).25  
* **Análisis Forense**: Adjuntar los resultados del VLM que demuestran la manipulación de las fotos utilizadas para dar credibilidad al perfil falso.8

| Campo del Formulario Redressal | Requisito del Agente | Ejemplo de Valor |
| :---- | :---- | :---- |
| **Nombre del Infractor** | Extraer de la ficha de Google Maps. | "Yamaha Motos San Juan \- Principal".5 |
| **Motivo del Reporte** | Seleccionar categoría de fraude. | "Misleading business info / Fraudulent activity".24 |
| **URL del Perfil** | Capturar mediante Places API. | https://www.google.com/maps/place/....37 |
| **Explicación del Impacto** | Narrativa generada por el LLM. | "El perfil suplanta a Yamaha para pedir depósitos por Nequi".5 |

## **Consideraciones Legales y de Cumplimiento**

La operación de un agente de monitoreo debe estar enmarcada en el cumplimiento de las normativas de protección de datos en Colombia (Ley 1581 de 2012\) y las políticas globales de Google.

### **Uso Ético de la IA en la Vigilancia**

El agente debe actuar como una herramienta de protección de marca y no como un sistema de ataque hacia competidores legítimos. Es fundamental implementar umbrales de confianza elevados para evitar "falsos positivos". Se recomienda que cualquier reporte que afecte a un negocio con más de un año de antigüedad sea validado por un supervisor humano antes de ser enviado a Google.18

### **Colaboración con Autoridades**

Dado que estas estafas constituyen delitos penales en Colombia, el agente debe ser capaz de exportar logs de actividad y evidencias en formatos compatibles con los requerimientos de la Policía Nacional o la Fiscalía General de la Nación.7 Esto incluye preservar la cadena de custodia digital de las imágenes capturadas y los metadatos asociados a las cuentas sospechosas detectadas en Maps.

## **Conclusiones y Futuro del Sistema**

El despliegue de un sistema de agentes de IA para la vigilancia de Google Maps representa una solución avanzada y necesaria para la red de Yamaha en Medellín. Al automatizar la identificación de fotos manipuladas y perfiles ficticios, la marca no solo protege sus ingresos, sino que cumple con su responsabilidad social de prevenir estafas masivas contra ciudadanos incautos. La arquitectura agentificada aquí descrita es lo suficientemente flexible para evolucionar a medida que los estafadores adopten nuevas tecnologías, permitiendo la integración de modelos de detección de fraude más complejos sin necesidad de reescribir la infraestructura base.

La clave del éxito reside en la integración simbiótica entre la precisión del análisis forense visual y la velocidad de respuesta permitida por las APIs oficiales de Google. En el largo plazo, este sistema puede extenderse para monitorear otras plataformas como Facebook Marketplace o perfiles de Instagram, creando un escudo digital integral para la marca Yamaha en la región antioqueña.38

#### **Works cited**

1. Incolmotos Yamaha alerta a clientes, grupos de interés y comunidad en general sobre prácticas irregulares., accessed March 17, 2026, [https://www.incolmotos-yamaha.com.co/incolmotos-yamaha-alerta-sobre-practicas-irregulares/](https://www.incolmotos-yamaha.com.co/incolmotos-yamaha-alerta-sobre-practicas-irregulares/)  
2. Estafadores que suplantan a Yamaha habrían “tumbado” a más de 500 clientes, accessed March 17, 2026, [https://www.elcolombiano.com/antioquia/estafa-suplantacion-marca-yamaha-colombia-clientes-afectados-MF27118217](https://www.elcolombiano.com/antioquia/estafa-suplantacion-marca-yamaha-colombia-clientes-afectados-MF27118217)  
3. Puntos de Atención \- Incolmotos Yamaha, accessed March 17, 2026, [https://www.incolmotos-yamaha.com.co/puntos-de-atencion/](https://www.incolmotos-yamaha.com.co/puntos-de-atencion/)  
4. Consigue la motocicleta de tus sueños, visitando uno de los concesionarios de Mundo Yamaha, accessed March 17, 2026, [https://yamaha-mundoyamaha.com/conoce-los-concesionarios-mundo-yamaha/](https://yamaha-mundoyamaha.com/conoce-los-concesionarios-mundo-yamaha/)  
5. ¡Cayó en la Trampa con su Moto Nueva\! UNA ESTAFA MILLONARIA \- Historia de Suscriptor \- YouTube, accessed March 17, 2026, [https://www.youtube.com/watch?v=JAcU7KMudxw](https://www.youtube.com/watch?v=JAcU7KMudxw)  
6. FRAUDES Y ESTAFAS \- Yamaha Joya Pabon SAS, accessed March 17, 2026, [https://yamahajoyapabon.com/fraudesyestafas/](https://yamahajoyapabon.com/fraudesyestafas/)  
7. Incolmotos Yamaha alerta a clientes, grupos de interés y comunidad en general sobre prácticas irregulares de suplantación digital, accessed March 17, 2026, [https://www.incolmotos-yamaha.com.co/suplantacion-digital/](https://www.incolmotos-yamaha.com.co/suplantacion-digital/)  
8. Detecting Text Manipulation in Images using Vision Language Models \- arXiv, accessed March 17, 2026, [https://arxiv.org/html/2509.10278v1](https://arxiv.org/html/2509.10278v1)  
9. Detecting Text Manipulation in Images using Vision Language Models \- BMVA Archive, accessed March 17, 2026, [https://bmva-archive.org.uk/bmvc/2025/assets/workshops/SRBS/Paper\_1/paper.pdf](https://bmva-archive.org.uk/bmvc/2025/assets/workshops/SRBS/Paper_1/paper.pdf)  
10. Manage real-time notifications | Google Business Profile APIs, accessed March 17, 2026, [https://developers.google.com/my-business/content/notification-setup](https://developers.google.com/my-business/content/notification-setup)  
11. Google My Business API, accessed March 17, 2026, [https://developers.google.com/my-business/reference/rest](https://developers.google.com/my-business/reference/rest)  
12. Overview | Places API \- Google for Developers, accessed March 17, 2026, [https://developers.google.com/maps/documentation/places/web-service/overview](https://developers.google.com/maps/documentation/places/web-service/overview)  
13. About the Places API (New) | Google for Developers, accessed March 17, 2026, [https://developers.google.com/maps/documentation/places/web-service/op-overview](https://developers.google.com/maps/documentation/places/web-service/op-overview)  
14. REST Resource: places | Places API \- Google for Developers, accessed March 17, 2026, [https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places)  
15. Report inappropriate content | Places API \- Google for Developers, accessed March 17, 2026, [https://developers.google.com/maps/documentation/places/web-service/content-reporting](https://developers.google.com/maps/documentation/places/web-service/content-reporting)  
16. OCR With Google AI, accessed March 17, 2026, [https://cloud.google.com/use-cases/ocr](https://cloud.google.com/use-cases/ocr)  
17. Building Scalable AI Agents: Design Patterns With Agent Engine On Google Cloud, accessed March 17, 2026, [https://cloud.google.com/blog/topics/partners/building-scalable-ai-agents-design-patterns-with-agent-engine-on-google-cloud](https://cloud.google.com/blog/topics/partners/building-scalable-ai-agents-design-patterns-with-agent-engine-on-google-cloud)  
18. Multi-agent AI system in Google Cloud | Cloud Architecture Center, accessed March 17, 2026, [https://docs.cloud.google.com/architecture/multiagent-ai-system](https://docs.cloud.google.com/architecture/multiagent-ai-system)  
19. OCR for Phone Numbers \- Automated Data Extraction API & SDK \- Klippa, accessed March 17, 2026, [https://www.klippa.com/en/ocr/data-fields/phone-numbers/](https://www.klippa.com/en/ocr/data-fields/phone-numbers/)  
20. Detect AI Images: Lighting, Text Artifacts, and Forensics \- AGIRI, accessed March 17, 2026, [https://agiri.org/detect-ai-images-lighting-text-artifacts-and-forensics](https://agiri.org/detect-ai-images-lighting-text-artifacts-and-forensics)  
21. Detecting AI-Generated Images: An Overview for Lawyers and Workplace Investigators, accessed March 17, 2026, [https://www.wagnerlegalpc.com/blog/detecting-ai-generated-images-an-overview-for-lawyers-and-workplace-investigators](https://www.wagnerlegalpc.com/blog/detecting-ai-generated-images-an-overview-for-lawyers-and-workplace-investigators)  
22. Detecting AI-Generated Images via Diffusion Snap-Back Reconstruction: A Forensic Approach \- arXiv.org, accessed March 17, 2026, [https://arxiv.org/html/2511.00352v2](https://arxiv.org/html/2511.00352v2)  
23. The 4-Layer Architecture of AI Systems | by Ben King | Google Cloud \- Community \- Medium, accessed March 17, 2026, [https://medium.com/google-cloud/the-4-layer-architecture-of-ai-systems-935d1ceaf657](https://medium.com/google-cloud/the-4-layer-architecture-of-ai-systems-935d1ceaf657)  
24. Report a business on Google Maps, accessed March 17, 2026, [https://support.google.com/maps/answer/16109801?hl=en](https://support.google.com/maps/answer/16109801?hl=en)  
25. How To Find and Report Spam/Fake Businesses on Google \- Professor M, accessed March 17, 2026, [https://professorm.org/google-my-business-training-free/how-to-find-and-report-spam-fake-businesses-on-google-guide/](https://professorm.org/google-my-business-training-free/how-to-find-and-report-spam-fake-businesses-on-google-guide/)  
26. How to Use Google's Spam Redressal Form to Level the Local Playing Field \- BrightLocal, accessed March 17, 2026, [https://www.brightlocal.com/blog/how-to-use-googles-spam-redressal-form-to-level-the-local-playing-field/](https://www.brightlocal.com/blog/how-to-use-googles-spam-redressal-form-to-level-the-local-playing-field/)  
27. Google business reviews API: Everything you need to know \- WiserReview, accessed March 17, 2026, [https://wiserreview.com/blog/google-business-reviews-api/](https://wiserreview.com/blog/google-business-reviews-api/)  
28. Google Reviews API: How to Access, Use, and Benefits \- Taggbox, accessed March 17, 2026, [https://taggbox.com/blog/google-reviews-api/](https://taggbox.com/blog/google-reviews-api/)  
29. Method: places.get | Places API | Google for Developers, accessed March 17, 2026, [https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places/get\#Review](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places/get#Review)  
30. Google Maps Scraping: Complete 2025 Guide to Extract Business Data & Generate Leads, accessed March 17, 2026, [https://scrap.io/google-maps-scraping-complete-guide-business-data-leads-2025](https://scrap.io/google-maps-scraping-complete-guide-business-data-leads-2025)  
31. Is It Legal to Scrape Google Maps? What You Should Know, accessed March 17, 2026, [https://igleads.io/resources/is-it-legal-to-scrape-google-maps/](https://igleads.io/resources/is-it-legal-to-scrape-google-maps/)  
32. Vision AI: Image and visual AI tools | Google Cloud, accessed March 17, 2026, [https://cloud.google.com/vision](https://cloud.google.com/vision)  
33. Choose your agentic AI architecture components \- Google Cloud Documentation, accessed March 17, 2026, [https://docs.cloud.google.com/architecture/choose-agentic-ai-architecture-components](https://docs.cloud.google.com/architecture/choose-agentic-ai-architecture-components)  
34. Detecting Text Manipulation in Images using Vision Language Models \- Semantic Scholar, accessed March 17, 2026, [https://www.semanticscholar.org/paper/Detecting-Text-Manipulation-in-Images-using-Vision-Vidit-Korshunov/3dad518c6969349e40fdc07fac596092ed47ac8e](https://www.semanticscholar.org/paper/Detecting-Text-Manipulation-in-Images-using-Vision-Vidit-Korshunov/3dad518c6969349e40fdc07fac596092ed47ac8e)  
35. Decoding Building Facades \- mediaTUM, accessed March 17, 2026, [https://mediatum.ub.tum.de/doc/1785050/m8w6dm8a4cf23ektyqnybcjfy.eg-ice2025\_full\_paper\_decoding\_building\_facades\_Noll\_Noichl\_final.pdf](https://mediatum.ub.tum.de/doc/1785050/m8w6dm8a4cf23ektyqnybcjfy.eg-ice2025_full_paper_decoding_building_facades_Noll_Noichl_final.pdf)  
36. Incolmotos Yamaha S A Nit 890 916, Girardota, Colombia \- Volza, accessed March 17, 2026, [https://www.volza.com/company-profile/incolmotos-yamaha-s-a-nit-890-916-224983/](https://www.volza.com/company-profile/incolmotos-yamaha-s-a-nit-890-916-224983/)  
37. How to Use Google's Redressal Form | Sixth City Marketing, accessed March 17, 2026, [https://www.sixthcitymarketing.com/2020/10/14/redressal-form/](https://www.sixthcitymarketing.com/2020/10/14/redressal-form/)  
38. Online Brand Protection Solutions \- Detect & Remove Digital Threats, accessed March 17, 2026, [https://www.brandshield.com/](https://www.brandshield.com/)  
39. Brand Protection | Doppel, accessed March 17, 2026, [https://www.doppel.com/product/brand-protection](https://www.doppel.com/product/brand-protection)

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAYCAYAAAACqyaBAAABq0lEQVR4Xu2VSygFYRTHj1cpzxSJkFgorxWylixYWFmwQClK2SDvhY3yiK3HQuyUrERRRLKh2KEoRUl2CDv+p3O6dzrENTOx4Fe/7tz/mbnfnPm++w3RP3+VcngQgvtwGxbLZf4wB49gNcyAqXADvsJamKx5o2a5cpl3IuEZTDL5DXwgqTu5hhEmc00lHDVZHkmH6yYPh4cm80QTzDFZG8ngPSaPgwMm850lksFLbeEnuIX35OPchko+SddrtuADvGY+pZ1k8G5b8Egh3LGhZZlk8BJb8Agv3mkbOgmDd/T1fBfAXjgBYzXjzz6SQYpgJ8nOmQ4n4QnJ7tii57+DVzd3vWkLDgbhgh43wGaSgUdgFJwneXqtcJGkoXj4CLP0nABp8AJeknT8rF7Bc5gdOFM6fiH5Ye5wCsZQcEtm9ii4TSdqVgZP9dg1XXCXZKCPVi7fyBNJp074RmdM9m0q4IrjewrJwuR8GNbAY63xFFbp8Sqsh5kku6cruFt+A3bAfjhEsuXWkcz1GNzSuvOvOq71WRjtyF3Bc2nfdvyoeXHxDdrHziTY4J9f4Q1s9E8mBxIrDwAAAABJRU5ErkJggg==>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADcAAAAYCAYAAABeIWWlAAACs0lEQVR4Xu2XWaiNURiGX/PspIgitikXJ1Ek08XhgpSSpBQSOZmHRGRKUiLDDSGZipILMhRCmUqJG1IyHhRSRImS8L5962ftz7+zHfvEr/3U0/nXt9Y+56x/rfWtbwNlypT5mwyh9+lz+jL8fEQf0Mf0Cp1MGycfyCKH6Vc6KIo1pXNDfEsUzxxarbe0ge8gT+hn2tl3ZIFOsNU56TtIffqefqG5/K5sMBE2ucW+gwyD9e138cywGzaBfi7ehV6nz2h715cZlC217VbSpXQFPQQ7g/tomx9Di+KfyazJebtJxwRH0ypYtvxdNtDTdFoUq6DTo3Yhih2Xo2fpNRf/iUmwya1x8drQg16mc+jwKD6A7ojahSh2nFhC9/qgZw9sclUuXhu0nbf5YB1xik7xQY+qkI+0ie9IoQVdRDchP/nobtxM78AqGk0yYRTdSDtEsXp0BGwLV4dY2rhmsOpoGe1P+4a4/t47/OLe7QVbtUu+IwVtmfOwz+juq6Fto34lkYewcq5RiHWEnb1ddGaIiYN0FuyMvYJVRX5cQ3qGjqTN6V3YdheaqIqOVPTL7tE3sFX7AEv34+JBDq2Ikk3CDTo2arein2BvO6EyxF/AzqPQVroanrWCAwuMm0EvhmfxlPYOz7qPdZxKwmDYS0hKM71xlWPdv48AhtLbUTtBmTeZjNBqaJt5/LhzdHV4ztHXsJchVElpu5YEvdmaqL2V7ozaYh494GLiCOxcLYCt6jHk/2OqgHTO0sYlO2U+PUEn0K6w+7cbXR76/xglEV3y62DfEHTuYnTZz3YxsZ2up+NDuw/sHtQElUCmFhinSSu2kK6Frfiq0HchPPcM7ZKgbOm/NSimTHsLVq6loTEx2l4qHjx+nBJTy/DsC4rWrl0nHIUVAMdd/L9AlYjq0Xa+o0yJ+Qa7wYA9X6tA5gAAAABJRU5ErkJggg==>