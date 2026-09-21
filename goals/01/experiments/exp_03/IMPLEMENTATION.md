# Implementation Plan: Filtrado del ground truth por secuencia y longitud compatible con ESM2

**Experiment**: `goals/01/experiments/exp_03/`  
**Project**: PPI-exercise — goal 01  
**Design source**: `DESIGN.md`  
**Status**: Complete
**Author**: Juan Sebastian Malagón Torres

## 1. Objetivo

Cruzar el ground truth de `exp_01` con las secuencias de `exp_02` y conservar exclusivamente las filas cuyos dos participantes tienen una secuencia FASTA no vacía y de longitud `<= 1024` residuos. El resultado será el pool listo para extraer embeddings con ESM2-650M.

## 2. Entradas

- Interacciones originales: `../exp_01/results/ground_truth.tsv`.
- Secuencias disponibles: `../exp_02/results/sequences.fasta`.

Validaciones de entrada:

1. El TSV contiene `uniprot_A` y `uniprot_B`.
2. El FASTA es parseable y no contiene cabeceras duplicadas.
3. Cada ID disponible tiene una secuencia no vacía.
4. Los IDs se comparan literalmente.

## 3. Regla de filtrado

Para cada fila del ground truth:

```text
keep = A existe AND B existe AND len(seq_A) <= 1024 AND len(seq_B) <= 1024
```

La etiqueta no participa en la decisión. Las self-interacciones se conservan cuando su única proteína cumple la regla. Las filas eliminadas se clasifican como secuencia ausente o secuencia superior al límite, incluyendo longitudes A/B cuando están disponibles.

## 4. Salidas

Generar bajo `results/`:

| Archivo | Contenido |
|---|---|
| `ground_truth_filtered.tsv` | Filas conservadas con el esquema original. |
| `filter_audit.tsv` | Estado por fila: disponibilidad, longitudes, elegibilidad, decisión y motivo. |
| `removed_interactions.tsv` | Filas eliminadas, longitudes disponibles y motivo. |
| `summary.tsv` | Totales, proteínas elegibles/excluidas, conteos por etiqueta y motivos. |
| `version.txt` | Fecha, hashes de entradas, commit, límite usado y conteos finales. |

## 5. Parámetros

- `--max-length 1024` por defecto.
- Rutas de ground truth, FASTA y salida configurables mediante CLI.
- Sin truncamiento ni ventanas: las proteínas que superen el límite se excluyen.

## 6. Verificación

Después de ejecutar:

1. `kept_rows + removed_rows == input_rows`.
2. Cada fila conservada tiene ambos IDs en el FASTA.
3. Cada fila conservada tiene longitudes A/B `<= 1024`.
4. El encabezado y las columnas de `ground_truth_filtered.tsv` coinciden con la entrada.
5. `filter_audit.tsv` y `removed_interactions.tsv` cubren todas las filas.
6. Las razones de eliminación son consistentes con los estados auditados.
7. Los conteos de positivos y negativos se reportan antes y después.
8. Los hashes de entrada en `version.txt` corresponden a los archivos utilizados.

## 7. Ejecución

```bash
~/miniconda3/envs/bioDL/bin/python -u \
  goals/01/experiments/exp_03/scripts/filter_ground_truth_by_sequence.py \
  --max-length 1024
```

La salida reemplaza los artefactos anteriores de `exp_03`; `exp_01` y `exp_02` permanecen intactos.

## 8. Criterios de aceptación

- `ground_truth_filtered.tsv` contiene sólo pares representables por ESM2-650M con el límite fijado.
- La auditoría independiente no encuentra inconsistencias.
- Se identifican explícitamente las proteínas y filas excluidas por longitud.
- La salida conserva el esquema y el orden del ground truth original.
- `version.txt` registra el parámetro `max_sequence_length: 1024`.
