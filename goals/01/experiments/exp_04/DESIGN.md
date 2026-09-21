# Experiment Design: Extracción de embeddings de proteínas con ESM2-650M
**Experiment**: `goals/01/experiments/exp_04/` · **Project**: PPI-exercise — goal 01 · **Date**: 2026-09-21 · **Status**: In Progress

## Hypothesis
`Synthyra/ESM2-650M` puede generar un embedding válido de dimensión 1.280 para cada una de las proteínas elegibles de `exp_03`, usando mean pooling sobre residuos biológicos y excluyendo todos los tokens especiales.

## Setup
- **Entrada:** las proteínas presentes en `goals/01/experiments/exp_02/results/sequences.fasta` con longitud `<= 1024`, identificadas mediante el filtro final de `exp_03`; no se procesarán proteínas más largas.
- **Modelo:** `Synthyra/ESM2-650M`, evaluado sin entrenamiento ni fine-tuning.
- **Pooling:** media de las representaciones de los residuos aminoacídicos reales; se excluyen BOS, EOS, padding y otros tokens especiales.
- **Salida:** archivo HDF5 con la correspondencia `protein_id`–`embedding`, longitud de secuencia y registro de cobertura.
- **⚠️ Dependencia:** el entorno actual tiene `torch` y `transformers`, pero no `h5py`; la dependencia deberá resolverse en la fase de implementación.

## Metric & Decision
La métrica primaria es la **cobertura de embeddings válidos**. El experimento tiene éxito si se obtiene un embedding para el 100 % de las proteínas elegibles, con forma `(N, 1280)`, correspondencia exacta entre IDs y filas, y cero valores NaN/Inf. Como métricas secundarias se registrarán tiempo total, throughput, memoria utilizada y tamaño del HDF5. La versión del modelo, las entradas y el estado del código se registrarán en `results/version.txt`.

## Next Step
Revisar y aceptar este diseño; después producir un plan de implementación para scripts, dependencias, configuración, extracción, pooling, escritura HDF5 y validación de resultados.
