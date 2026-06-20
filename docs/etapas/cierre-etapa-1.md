# Cierre Etapa 1 — Vertex Insights

Documento de cierre de la **Etapa 1** (Setup del proyecto e identidad del equipo). Primera etapa del Sprint 1, dedicada a la creación y configuración del repositorio, la implementación del tablero de trabajo y la documentación de las convenciones operativas del equipo.

---

## 1. Información general

| Atributo | Valor |
|---|---|
| Etapa | 1 — Setup del proyecto e identidad del equipo |
| Sprint asociado | Sprint 1 |
| Fase CRISP-DM | Business Understanding (cierre) |
| Líder de etapa | Scrum Master |
| Fecha de cierre | 17 de junio de 2026 |
| Duración real | 1 día calendario |
| Estado al cierre | Completada |
| Tags de versión | V1.0.0, V1.0.1 |

---

## 2. Objetivo de la etapa

Materializar la infraestructura técnica del proyecto: crear el repositorio, definir su estructura, configurar el tablero ágil, documentar las convenciones operativas del equipo y dejar todo listo para que el desarrollo técnico arranque en la Etapa 2.

La Etapa 1 es bloqueante para todas las posteriores. Su ejecución estuvo concentrada en el Scrum Master.

---

## 3. Entregables producidos

### 3.1. Repositorio operativo

| Atributo | Valor |
|---|---|
| URL | https://github.com/cfgarciac/vertex-insights-olist-recommender |
| Visibilidad | Público |
| Licencia | MIT |
| Cuenta propietaria | cfgarciac (cuenta personal del Scrum Master) |

### 3.2. Estructura del repositorio

Estructura estándar para proyectos de Machine Learning, materializada en el primer commit:

```
vertex-insights-olist-recommender/
├── .github/
│   ├── ISSUE_TEMPLATE/         Plantilla estructurada para historias
│   └── workflows/              Espacio para CI futuro
├── artifacts/                  Modelos serializados
├── data/
│   ├── raw/                    Datos originales (no versionados)
│   └── processed/              Datos transformados (no versionados)
├── docs/                       Documentación del proyecto
├── notebooks/                  Notebooks exploratorios y de modelado
├── reports/                    Informes y dashboards
├── scripts/                    Scripts operativos del repositorio
├── src/                        Código fuente
├── tests/                      Pruebas unitarias
├── .gitignore
├── Dockerfile                  Placeholder (se completa en Etapa 7)
├── LICENSE
├── README.md
├── requirements.txt            Dependencias de producción
└── requirements-dev.txt        Dependencias de desarrollo
```

### 3.3. Modelo de ramas

Siete ramas largas, creadas a partir del primer commit de `master`:

| Rama | Propósito |
|---|---|
| `master` | Rama principal; recibe merges desde `developer` al cierre de cada etapa con tag de versión |
| `developer` | Rama de integración; recibe Pull Requests desde las ramas personales |
| `Cristian` | Rama personal de García Cadena, Cristian Fernando (Scrum Master) |
| `Harrison` | Rama personal de Tutalcha Pame, Harrison Alberto (Product Owner) |
| `Juan` | Rama personal de López Solórzano, Juan Carlos (Data Analyst) |
| `Amaury` | Rama personal de Aguilar Lomas, Oscar Amaury (Data Scientist) |
| `Nassim` | Rama personal de Wessin, Nassim (Machine Learning Engineer) |

### 3.4. Tablero de trabajo (GitHub Projects)

| Atributo | Valor |
|---|---|
| Nombre del Project | Vertex Insights — Sprint 1 |
| Plantilla base | Board enriquecida de GitHub |
| Estados del flujo | Backlog, Ready, In progress, In review, Done |
| Campos personalizados | Status, Estimación (S/M/L) |
| Workflows activos | Auto-add to project |

### 3.5. Sistema de etiquetas (labels)

Dieciocho etiquetas creadas en el repositorio, organizadas en tres categorías:

| Categoría | Etiquetas |
|---|---|
| Etapa asociada | `etapa-1`, `etapa-2`, `etapa-3`, `etapa-4`, `etapa-5`, `etapa-6`, `etapa-7`, `etapa-8`, `etapa-9` |
| Rol responsable primario | `po`, `sm`, `da`, `ds`, `mle` |
| Tipo de tarjeta | `story`, `task`, `bug`, `docs` |

### 3.6. Plantilla de issue (Issue Form)

Plantilla estructurada en formato YAML para la creación de nuevas historias de usuario, ubicada en `.github/ISSUE_TEMPLATE/historia_usuario.yml`. Garantiza consistencia de información en todos los issues abiertos por el equipo.

### 3.7. Documento de convenciones del equipo

Archivo `docs/convenciones.md`. Establece como fuente única de verdad las convenciones de commits (Conventional Commits), la política de Pull Requests, la sincronización diaria con `developer`, la propiedad por subcarpetas, la Definition of Done global, las convenciones de nomenclatura y el esquema de versionado.

### 3.8. Backlog del Sprint 1 cargado como issues

Las diez historias del Sprint 1 (HU-02 a HU-11) quedan cargadas como issues del repositorio, vinculadas al Project, etiquetadas con su etapa, rol y tipo.

---

## 4. Estado del repositorio al cierre

### 4.1. Tags de versión publicados

| Tag | Descripción |
|---|---|
| `V1.0.0` | Estructura técnica inicial: estructura de carpetas, archivos base, siete ramas creadas |
| `V1.0.1` | Cierre completo de Etapa 1: plantilla de issue, convenciones del equipo, tablero configurado |

### 4.2. Estado del backlog del Sprint 1

| Historia | Estado al cierre de Etapa 1 |
|---|---|
| HU-02 — Configurar el repositorio y la infraestructura | Done |
| HU-03 — Configurar el tablero de trabajo en GitHub Projects | In progress |
| HU-04 a HU-11 | Backlog |

---

## 5. Decisiones tomadas durante la ejecución

Tres decisiones nuevas se documentan en la Bitácora del proyecto al cierre de esta etapa:

| ID | Título | Resumen |
|---|---|---|
| D-13 | Configuración del tablero GitHub Projects | Adopción de la plantilla enriquecida (cinco estados de Status), reparto pragmático entre campos del Project (Status, Estimación) y labels del repositorio (etapa, rol, tipo) |
| D-14 | Visibilidad pública del repositorio y licencia MIT | Repositorio público con licencia MIT explícita, para habilitar uso como pieza de portafolio del equipo |
| D-15 | Plantilla de issue como Issue Form estructurada | Uso del formato YAML (Issue Forms) en lugar de Markdown clásico, para garantizar formularios validados al crear nuevas historias |

---

## 6. Hitos cumplidos

- Repositorio creado, configurado y publicado.
- Estructura estándar de carpetas y archivos base implementada.
- Modelo de siete ramas largas establecido.
- Tablero ágil configurado en GitHub Projects.
- Dieciocho etiquetas implementadas en el repositorio.
- Plantilla estructurada de issue (Issue Form) creada.
- Documento de convenciones del equipo redactado y mergeado.
- Diez historias del Sprint 1 cargadas como issues con su metadata completa.
- Tags V1.0.0 y V1.0.1 publicados en `master`.

---

## 7. Conexión con la Etapa 2

La Etapa 1 deja la infraestructura técnica completa. La Etapa 2 (Entendimiento del negocio y análisis exploratorio) toma como insumos:

- El repositorio operativo, con ramas personales listas para que cada integrante trabaje.
- El backlog priorizado con las historias HU-04, HU-05 y HU-06 como alcance de la etapa.
- Las convenciones documentadas, que rigen los Pull Requests y los commits desde la primera línea de código.
- El dataset Olist, cuya exploración inicial constituye el foco principal de la etapa.

**Foco de la Etapa 2:**

- HU-04: Entender el problema y los datos disponibles (Data Scientist).
- HU-05: Análisis exploratorio profundo de las nueve tablas de Olist (Data Analyst).
- HU-06: Informe exploratorio en Power BI (Data Analyst).

---

*Documento de cierre de la Etapa 1 del Proyecto Final. Vertex Insights — Carrera Data Science de Henry.*
