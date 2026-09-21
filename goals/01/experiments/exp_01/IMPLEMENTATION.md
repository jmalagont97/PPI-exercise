# Implementation Plan: exp_01 — Generación del Ground Truth Maestro
**Experiment**: experiments/exp_01/ · **Project**: PPI-exercise (goal 01) · **Date**: 2026-09-21
**Basado en**: `DESIGN.md` (aceptado por el PI)

---

## 1. Objetivo

Implementar el generador determinista de `ground_truth.tsv`: parsing MITAB del archivo maestro IntAct, extracción de positivos MI:0407 (self-incluidas), muestreo de negativos Pool A balanceado (seed 42), verificación estricta de colisiones y registro de versión.

## 2. Artefactos a Crear

```
goals/01/experiments/exp_01/
├── scripts/
│   └── build_ground_truth.py    ← único script (stdlib de Python, sin dependencias externas)
└── results/
    ├── ground_truth.tsv         ← generado por el script
    └── version.txt              ← generado por el script
```

## 3. Especificación del Script `scripts/build_ground_truth.py`

- **Lenguaje/deps**: Python 3, solo stdlib (`csv`, `random`, `hashlib`, `subprocess`, `datetime`). Ejecutable con el env `bioDL` (aunque no requiere paquetes de ese env — stdlib puro garantiza reproducibilidad).
- **Rutas**: RELATIVAS a la raíz del repo, ancladas desde la ubicación del script (`<script_dir>/../../../..` → raíz). Prohibidas las absolutas (regla del sistema de investigación).
  - Entrada: `data/A.thaliana_interactome.txt`
  - Salidas: `goals/01/experiments/exp_01/results/ground_truth.tsv` y `version.txt`
- **Constantes**: `SEED = 42`, `TAXID = "3702"`, `DIRECT = "MI:0407"`.

### Flujo (4 pasos, código lean sin try/except defensivos):

1. **Parsing**: leer MITAB (TSV, `csv.DictReader`); filtrar filas con taxid 3702 en A y B; extraer primer accession `uniprotkb:` de las columnas 1–2 (colapsando `|`); construir:
   - `all_pairs`: set de pares ordenados `(min, max)` con CUALQUIER evidencia MI (universo de exclusión de negativos).
   - `direct_pairs`: subconjunto con al menos una evidencia MI:0407.
   - `pair_meta`: por par directo → max(miscore), n_evidencias, lista de métodos únicos (nombres legibles PSI-MI, sin prefijos).
   - `locus`: uniprot → AGI, desde alias `(locus name)` de cualquier fila donde aparezca la proteína.
2. **Muestreo de negativos**: `random.seed(42)`; loop `random.sample(sorted(proteinas), 2)` → par ordenado; rechazar si está en `all_pairs`; hasta completar `len(direct_pairs)` negativos. Los self-pairs no pueden aparecer (sample sin reemplazo de 2 elementos distintos); los positivos self-loop (A,A) se conservan intactos en positivos.
3. **Verificación post-muestreo (hard assertions)**: `assert` de (a) `len(positivos) == 1424`, (b) `len(negativos) == 1424`, (c) `negativos ∩ all_pairs == ∅`, (d) `negativos ∩ direct_pairs == ∅`, (e) sin duplicados en la unión. Si un assert falla → el script aborta con mensaje claro (falla explícita, no silenciada).
4. **Escritura**:
   - `ground_truth.tsv` (columnas): `uniprot_A, uniprot_B, locus_A, locus_B, label, interaction_type, miscore_max, n_evidences, methods`
     - positivos: `label=positive`, `interaction_type=MI:0407`, meta de evidencias; negativos: `label=negative`, `interaction_type=none`, `miscore_max=NA`, `n_evidences=0`, `methods=NA`. Locus faltante → campo vacío.
     - Orden de filas: positivos primero (orden lexicográfico del par), negativos después (orden de muestreo reproducible → orden lexicográfico también, para estabilidad).
   - `version.txt`: fecha UTC, seed, sha256 de `data/A.thaliana_interactome.txt`, hash corto de Git (`git rev-parse --short HEAD`, desde la raíz).
   - **Telemetría de una línea por hito** (stdout, `python -u`): `[parse] 59337 filas 3702/3702 | 41474 pares evidencia | 1424 directos`, `[sample] 1424 negativos, colisiones=0`, `[write] ground_truth.tsv 2848 filas`.

## 4. Ejecución

Cómputo local < 60 s → **primer plano** (sin tmux, regla 2.C del sistema):

```bash
conda activate bioDL && python -u goals/01/experiments/exp_01/scripts/build_ground_truth.py
```

Previo: commit de `scripts/` + `DESIGN.md` + `IMPLEMENTATION.md` (checklist de reproducibilidad exige Git limpio).

## 5. Criterios de Aceptación (verificación post-corrida)

1. `ground_truth.tsv` existe con **2,848 filas de datos** + header.
2. 1,424 `positive` / 1,424 `negative` (verificable con `cut -f5 | sort | uniq -c`).
3. Ningún par negativo aparece en el archivo maestro (verificación independiente con un one-liner de auditoría, no solo el assert interno).
4. `version.txt` contiene seed 42 + sha256 válido + hash de commit.
5. Los 78 self-loops directos (A,A) presentes y etiquetados como positivos.

## 6. Fuera de Alcance

- Recuperación de secuencias (UniProt REST) → experimento posterior.
- Split train/test (group split por proteína) → fase de modelado.
- Promoción a `data/` compartido vía `-link-data` → decisión del PI tras aceptar resultados.

## 7. Pasos Siguientes (tras aprobación de este plan)

1. Aprobación explícita del PI (Gatekeeping) → escribir `scripts/build_ground_truth.py`.
2. Commit de scripts → ejecutar en primer plano → verificar criterios de la Sección 5.
3. Marcar `exp_01` como `running` en `experiments/index.md` al lanzar; al ver resultados → `completed` + consolidación con `experiment-reporter` (`reports/summary.md`) + entrada en `.logbook.md`.
