# Experiment Report: Ground Truth Maestro — Pares Directos (MI:0407) vs. Negativos Pool A
**Experiment**: goals/01/experiments/exp_01/
**Project**: PPI-exercise (goal 01 — obtención de datos)
**Report date**: 2026-09-21
**Plan date**: 2026-09-21
**Author**: PI: Juan Sebastian Malagón Torres · Co-I: Hermes (interactómica + DL)
**Status**: Complete

---

## 1. Summary

Se generó el archivo maestro de anotaciones `ground_truth.tsv` con 2,848 pares balanceados 1:1: 1,424 positivos (interacciones directas MI:0407 del interactoma IntAct de *A. thaliana*, self-interacciones incluidas) y 1,424 negativos muestreados del Pool A (pares aleatorios entre las proteínas del interactoma sin NINGUNA evidencia de interacción de cualquier tipo). La auditoría independiente confirmó cero colisiones de negativos contra evidencia, cero duplicados, y los 78 self-loops conservados. La hipótesis del diseño se cumple.

---

## 2. Hypothesis & Verdict

**Hypothesis (from plan):** _Es posible construir un ground truth maestro de interacciones físicas directas de A. thaliana — pares positivos MI:0407 vs. pares negativos muestreados del complemento sin evidencia — con calidad suficiente (cero colisión de evidencia en negativos, trazabilidad UniProt/AGI completa) para servir como archivo maestro de anotaciones del futuro modelo siamés con ESM-2 y cabezas no compartidas. Este experimento NO recupera secuencias._

**Verdict:** ✅ Supported

**Evidence:** 2,848 filas generadas (1,424/1,424); auditoría independiente contra el maestro MITAB: 0 negativos con evidencia, 0 duplicados, 78 self-loops positivos presentes. Trazabilidad UniProt + locus AGI con cobertura de 98.6% (27 pares positivos con al menos un locus faltante, documentados sin exclusión).

---

## 3. Experimental Setup (as run)

- **Fuente**: `data/A.thaliana_interactome.txt` (IntAct MITAB 2.7, 42 columnas, 70,798 filas; sha256 `ae19f5b90f7d…` registrado en `version.txt`)
- **Pipeline**: script único stdlib `scripts/build_ground_truth.py` — parsing MITAB (filtro taxid 3702/3702, primer accession uniprotkb, colapso de pares a `(min, max)`) → muestreo `random.Random(42)` con rechazo contra el universo de exclusión (41,474 pares con cualquier evidencia MI) → 5 hard assertions → escritura TSV + version.txt
- **Ejecución**: primer plano (< 5 s CPU), intérprete `~/miniconda3/envs/bioDL/bin/python` (stdlib puro; el env solo garantiza el runtime declarado)
- **Hardware**: CPU local
- **Deviations from plan**:
  1. ⚠️ Corrección de ruta durante la primera corrida: `ROOT` requería 5 niveles ascendentes (`../../../../..`), no 4. Corregido y re-ejecutado con éxito (commit `f5c96b9`).
  2. `conda activate bioDL` falla en esta máquina por un bug del plugin `anaconda_anon_usage` de conda 26.3.2 (`TypeError` en `_get_deactivate_scripts`); se ejecutó con el binario directo del env. Sin impacto en el resultado (stdlib puro), pero anotado para futuras corridas (usar `~/miniconda3/envs/bioDL/bin/python` o tmux con binario directo).

---

## 4. Version & Artifacts

| Artifact | Descripción |
|----------|-------------|
| `results/ground_truth.tsv` | Archivo maestro: 2,849 líneas (header + 2,848 pares), 9 columnas (`uniprot_A, uniprot_B, locus_A, locus_B, label, interaction_type, miscore_max, n_evidences, methods`) |
| `results/version.txt` | seed 42 · sha256 fuente `ae19f5b90f7d…` · git_commit `09a3d56` (script) |
| `scripts/build_ground_truth.py` | Generador determinista (commit `f5c96b9`) |

---

## 5. Results

### 5.1 Primary Metric (criterios de aceptación del diseño)

| Criterio | Esperado | Observado | ✓ |
|----------|----------|-----------|---|
| Filas de datos | 2,848 | 2,848 | ✅ |
| Balance | 1,424 / 1,424 | 1,424 positive / 1,424 negative | ✅ |
| Colisión negativos∩evidencia | 0 | **0** (auditoría independiente, no solo assert interno) | ✅ |
| Duplicados | 0 | 0 | ✅ |
| Self-loops positivos | 78 | 78 | ✅ |
| `version.txt` válido | seed+sha256+commit | 42 · ae19f5b90f7d · 09a3d56 | ✅ |

### 5.2 Secondary Metrics

- **Cobertura locus AGI**: 27/1,424 pares positivos (1.9%) con al menos un locus faltante — dentro del ~1.4–2% esperado; conservados con campo vacío según regla del diseño.
- **Proteínas únicas en el GT**: 3,086 (dimensiona la posterior descarga de secuencias).
- **Distribución miscore de positivos**: registrada por par en la columna `miscore_max` (máximo entre evidencias).

---

## 6. Statistical Analysis

- **Test used**: ninguno — población determinista (muestreo seedeado, no estocástico entre corridas).
- La reproducibilidad exacta está garantizada por seed 42 + sha256 de la fuente + commit del script.

---

## 7. Comparison to Expected Results

| Expected (DESIGN.md §8) | Observed | Match? |
|--------------------------|----------|--------|
| Colisiones = 0 → GT declarado maestro | 0 colisiones | ✅ |
| Pares sin locus conservados con campo vacío | 27 pares conservados | ✅ |

---

## 8. Missing Data & Caveats

- All planned runs completed.
- ⚠️ Caveat metodológico heredado (aceptado por consenso): los negativos del Pool A asumen "ausencia de evidencia ≈ no interacción" y comparten el sesgo de selección de las proteínas estudiadas. Validación futura contra una muestra del Pool B (proteoma completo) queda como opción.
- ⚠️ El bug de `conda activate` (plugin anaconda_anon_usage, conda 26.3.2) no afecta este resultado pero debe considerarse en los lanzamientos tmux de experimentos posteriores.

---

## 9. Conclusions & Next Steps

- **Establecido**: el ground truth maestro es válido y trazable; 3,086 proteínas únicas dimensionan la recuperación de secuencias.
- **Incierto**: calidad de los negativos (falsos negativos por ausencia de evidencia) — inherente al Pool A consensuado.
- **Siguientes pasos**: (1) `exp_02` — recuperación de secuencias UniProt de las 3,086 proteínas del GT (usar experiment-planner); (2) opción de promover el GT a `data/` compartido vía `-link-data ground_truth.tsv` cuando el PI lo decida.

---

## 10. Reproducibility Record

| Item | Status |
|------|--------|
| Seeds logged | ✅ (42, en version.txt) |
| Configs versioned | ✅ (script en Git, commit f5c96b9) |
| Version recorded | ✅ (version.txt) |
| Checkpoints saved | N/A (sin modelo) |
| Environment frozen | ⚠️ (stdlib puro; export de bioDL pendiente para exp_02) |
| Experiment tracker linked | ❌ (no aplica; trazabilidad vía version.txt) |
