# Experiment Design: Filtrado del ground truth por disponibilidad de secuencias
**Experiment**: `goals/01/experiments/exp_03/` · **Project**: PPI-exercise — goal 01 · **Date**: 2026-09-21 · **Status**: Draft

## Hypothesis
Filtrar el `ground_truth.tsv` para conservar únicamente las interacciones cuyos dos participantes tienen una secuencia válida en `sequences.fasta` produce un conjunto de entrenamiento íntegramente representable por secuencias, sin introducir filas con un participante faltante.

## Setup
- **Interacciones de entrada:** `goals/01/experiments/exp_01/results/ground_truth.tsv`.
- **Secuencias de entrada:** `goals/01/experiments/exp_02/results/sequences.fasta`.
- **Regla de filtrado:** conservar una interacción sólo si `uniprot_A` y `uniprot_B` aparecen exactamente en las cabeceras FASTA y tienen secuencias no vacías.
- **Aplicación:** la regla se aplica por fila a positivos y negativos; se elimina toda interacción que involucre al menos una proteína sin secuencia.
- **Salida esperada:** un `ground_truth.tsv` filtrado, con el mismo esquema y metadatos de las filas conservadas, más un reporte de auditoría.

## Metric & Decision
La métrica primaria es la integridad de representación: **100 % de las filas conservadas deben tener secuencia válida para ambos participantes**. Se reportarán además filas conservadas/eliminadas, cobertura de proteínas y distribución de etiquetas antes y después del filtrado. El experimento se considera exitoso si no queda ninguna fila con `uniprot_A` o `uniprot_B` ausente del FASTA, los positivos y negativos eliminados quedan contabilizados explícitamente y el balance final se describe sin asumir que permanece 1:1.

## Next Step
Tras aceptar este diseño, preparar el plan de implementación para generar el ground truth filtrado y su auditoría antes de modificar archivos de implementación.
