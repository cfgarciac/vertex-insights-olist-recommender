# Convenciones del equipo Vertex Insights

Documento vivo. Establece las convenciones técnicas y operativas del equipo durante todo el Proyecto Final. Cualquier ajuste se acuerda en la Sprint Retrospective y se actualiza directamente en este archivo.

---

## 1. Convenciones de commits

El equipo usa **Conventional Commits**: cada commit empieza con un prefijo que indica el tipo de cambio. Esto hace que el historial sea legible automáticamente y permite generar changelogs.

### Formato

```
<tipo>(<scope-opcional>): <descripción>
```

### Tipos en uso

| Tipo | Cuándo se usa |
|---|---|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de un defecto |
| `docs` | Cambio solo en documentación |
| `style` | Formato de código (espacios, comas), sin cambios funcionales |
| `refactor` | Reorganización de código sin cambiar comportamiento |
| `test` | Agregar o modificar pruebas |
| `chore` | Tareas de mantenimiento, configuración, setup |

### Ejemplos válidos

- `feat: implementar baseline de popularidad por categoría`
- `fix: corregir manejo de nulos en pipeline de productos`
- `docs: agregar sección de instalación al README`
- `chore: V1.0.0 - estructura inicial del proyecto`

### Reglas adicionales

- Descripción en español, en presente, sin punto final.
- Máximo 72 caracteres en la primera línea.
- Si la historia asociada existe, referenciarla en el cuerpo del commit con `Refs: #N` (donde `N` es el número del issue).

---

## 2. Estructura de ramas

El proyecto opera con **siete ramas largas**:

| Rama | Propósito |
|---|---|
| `master` | Rama principal. Solo recibe merges desde `developer` al cierre de cada etapa, marcados con tag de versión. |
| `developer` | Rama de integración. Recibe PRs desde las ramas personales. Todo lo que se entrega para el sprint pasa por aquí. |
| `Cristian` | Rama personal de Cristian Fernando García Cadena (Scrum Master). |
| `Harrison` | Rama personal de Harrison Alberto Tutalcha Pame (Product Owner). |
| `Juan` | Rama personal de Juan Carlos López Solórzano (Data Analyst). |
| `Amaury` | Rama personal de Oscar Amaury Aguilar Lomas (Data Scientist). |
| `Nassim` | Rama personal de Nassim Wessin (Machine Learning Engineer). |

Cada integrante trabaja exclusivamente en su propia rama personal. Las ramas personales no se eliminan al mergear: viven todo el proyecto.

---

## 3. Política de Pull Requests

### Flujo estándar

1. Cada integrante trabaja en su rama personal.
2. Cuando una unidad de trabajo está lista, abre un **Pull Request** desde su rama hacia `developer`.
3. El PR debe ser revisado por **al menos un compañero distinto al autor** antes del merge.
4. Una vez aprobado, el autor mergea el PR.
5. La rama personal sigue viva. El autor sincroniza su rama personal con `developer` al día siguiente para mantenerse al día.

### Convención del título del PR

```
[HU-NN] Descripción corta del cambio
```

Donde `HU-NN` es el identificador de la historia asociada.

### Definition of Done de un PR

Antes de mergear, el PR debe cumplir:

- Título con `[HU-NN]` y descripción clara.
- Descripción del PR diligenciada (qué hace, por qué, cómo probarlo).
- Aprobación de al menos un revisor distinto al autor.
- Sin conflictos con `developer`.
- Issue asociado referenciado en la descripción del PR (`Closes #N` o `Refs #N`).

---

## 4. Sincronización diaria con developer

Para evitar drift entre ramas personales y `developer`, cada integrante debe:

- **Inicio del día:** hacer fetch de `developer` y mergear (o rebasear) sus cambios en la rama personal.
- **Fin del día:** si hay trabajo terminado, abrir o actualizar el PR correspondiente.

Comandos típicos:

```bash
git checkout developer
git pull origin developer
git checkout <rama_personal>
git merge developer
# Resolver conflictos si los hay
```

---

## 5. Propiedad suave por subcarpetas

Cada rol tiene responsabilidad primaria sobre ciertas subcarpetas del repositorio. **No** son zonas exclusivas (cualquier integrante puede tocar cualquier archivo si la historia lo amerita), pero la responsabilidad de mantenimiento y revisión recae en el rol primario.

| Subcarpeta | Rol responsable principal |
|---|---|
| `notebooks/` | Data Analyst y Data Scientist |
| `src/` | Machine Learning Engineer (despliegue), Data Scientist (modelado), Data Analyst (utilidades de datos) |
| `tests/` | Quien escribe el código asociado |
| `docs/` | Scrum Master y Product Owner |
| `reports/` | Data Analyst |
| `artifacts/` | Data Scientist y Machine Learning Engineer |
| `.github/` | Scrum Master |
| `scripts/` | Scrum Master (operaciones del repo) |

---

## 6. Definition of Done global

Una historia se considera **Done** cuando cumple TODOS los criterios siguientes:

- Todos los criterios de aceptación del issue marcados como cumplidos.
- Código mergeado a `developer` vía PR aprobado.
- Documentación asociada actualizada.
- Pruebas (cuando aplique) ejecutándose sin errores.
- El issue está cerrado en GitHub con referencia al PR que lo cierra (`Closes #N`).

---

## 7. Convenciones de nomenclatura

| Elemento | Convención | Ejemplo |
|---|---|---|
| Archivos Python | `snake_case.py` | `feature_engineering.py` |
| Funciones Python | `snake_case` | `def build_co_occurrence_matrix()` |
| Clases Python | `PascalCase` | `class RecommendationEngine` |
| Variables Python | `snake_case` | `customer_embeddings` |
| Constantes | `UPPER_SNAKE_CASE` | `MAX_RECOMMENDATIONS = 10` |
| Notebooks | `NN_descripcion_corta.ipynb` | `01_eda_inicial.ipynb` |
| Issues (título) | `[HU-NN] Descripción` | `[HU-05] Realizar el EDA sobre Olist` |
| Tags de versión | `V<sprint>.<etapa>.<patch>` | `V1.0.0`, `V1.4.0` |
| Ramas personales | Nombre propio capitalizado | `Cristian`, `Harrison` |

---

## 8. Convención de versiones (tags)

Cada cierre de etapa genera un tag en `master`. El esquema es:

```
V<sprint>.<etapa>.<patch>
```

Donde:
- `<sprint>` es el número del sprint (1 para Sprint 1, 2 para Sprint 2).
- `<etapa>` es el número de la etapa cerrada dentro del sprint.
- `<patch>` se incrementa para correcciones menores intermedias.

| Tag | Cierre de | Notas |
|---|---|---|
| V1.0.0 | Etapa 1 | Estructura inicial del repositorio |
| V1.1.0 | Etapa 2 | EDA completa |
| V1.2.0 | Etapa 3 | Feature engineering reproducible |
| V1.3.0 | Etapa 4 | Modelado P1: baseline + ≥2 clasificadores de entrega tardía |
| V1.4.0 | Etapa 5 | Cierre Sprint 1, Sprint Review |
| V1.5.0 | Etapa 6 | Evaluación y selección de modelo |
| V1.6.0 | Etapa 7 | API + Docker + Dashboard |
| V1.7.0 | Etapa 8 | Documentación técnica + monitoreo |
| V1.8.0 | Etapa 9 | Entrega final |

---

*Documento vivo. Última actualización: cierre de Etapa 1.*
