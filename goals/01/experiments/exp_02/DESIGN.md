# Experiment Design: Recuperación de secuencias de aminoácidos desde UniProt
**Experiment**: `goals/01/experiments/exp_02/`  
**Project**: PPI-exercise — goal 01  
**Date**: 2026-09-21  
**Author**: Juan Sebastian Malagón Torres  
**Status**: Draft

## Hypothesis
Es posible recuperar desde UniProt una secuencia de aminoácidos para cada ID UniProt único presente en `data/ground_truth.tsv` y conservar una correspondencia exacta entre el ID del archivo de entrada y la cabecera del FASTA resultante.

## Setup
- **Entrada:** `../../data/ground_truth.tsv`, usando las columnas `uniprot_A` y `uniprot_B`.
- **Identificadores:** unión de los IDs únicos de ambas columnas; se conserva el identificador UniProt original.
- **Fuente:** UniProt REST, consulta de la secuencia proteica asociada a cada ID.
- **Salida principal:** FASTA en `results/`, con una entrada por ID recuperado y cabeceras idénticas a esos IDs.
- **Trazabilidad:** registrar hash del `ground_truth.tsv`, fuente, fecha de descarga y cobertura de recuperación.

## Metric & Decision
La métrica primaria es la **cobertura de secuencias**, definida como IDs con una secuencia FASTA válida dividido por el total de IDs únicos de entrada. El experimento se considera exitoso si cada ID único tiene exactamente una secuencia recuperada, no existen cabeceras duplicadas y todas las cabeceras conservan literalmente el ID del `ground_truth.tsv`. Los IDs no recuperados se deben reportar explícitamente, no eliminar silenciosamente.

## Next Step
Tras aceptar este diseño, preparar el plan de implementación para la consulta a UniProt, generación del FASTA y auditoría de cobertura antes de modificar archivos de implementación.
