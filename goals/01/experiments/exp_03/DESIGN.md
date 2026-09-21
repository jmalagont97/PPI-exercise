# Experiment Design: Filtrado del ground truth por secuencia y longitud compatible con ESM2
**Experiment**: `goals/01/experiments/exp_03/` · **Project**: PPI-exercise — goal 01 · **Date**: 2026-09-21 · **Status**: Complete

## Hypothesis
Filtrar el `ground_truth.tsv` para conservar únicamente las interacciones cuyos dos participantes tienen una secuencia válida de longitud máxima 1.024 en `sequences.fasta` produce un pool íntegramente compatible con la extracción de embeddings de `ESM2-650M`.

## Setup
- **Interacciones de entrada:** `goals/01/experiments/exp_01/results/ground_truth.tsv`.
- **Secuencias de entrada:** `goals/01/experiments/exp_02/results/sequences.fasta`.
- **Regla de filtrado:** conservar una interacción sólo si `uniprot_A` y `uniprot_B` aparecen exactamente en el FASTA, tienen secuencias no vacías y ambas longitudes son `<= 1024` residuos.
- **Aplicación:** la regla se aplica por fila a positivos y negativos; se elimina toda interacción que involucre una proteína ausente o que supere el límite de longitud.
- **Salida esperada:** un `ground_truth_filtered.tsv` listo para el siguiente paso de embeddings, con auditoría de secuencias, longitudes y razones de eliminación.

## Metric & Decision
La métrica primaria es la integridad de representación: **100 % de las filas conservadas deben tener ambos participantes presentes y con longitud `<= 1024`**. Se reportarán filas conservadas/eliminadas, proteínas elegibles/excluidas por longitud, distribución de etiquetas y motivos de eliminación. El experimento se considera exitoso si la auditoría confirma la regla de filtrado, conserva el esquema original y `kept_rows + removed_rows = input_rows`.

## Next Step
Ejecutar el filtro actualizado, validar los artefactos y usar `ground_truth_filtered.tsv` como pool de entrada para la extracción de embeddings.
