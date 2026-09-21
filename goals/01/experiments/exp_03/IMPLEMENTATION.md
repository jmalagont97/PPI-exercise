# Implementation Plan: Filtrado del ground truth por disponibilidad de secuencias

**Experiment**: `goals/01/experiments/exp_03/`  
**Project**: PPI-exercise — goal 01  
**Design source**: `DESIGN.md`  
**Status**: Proposed  
**Author**: Juan Sebastian Malagón Torres

## 1. Objetivo de implementación

Crear un proceso reproducible que cruce las interacciones del ground truth original con las secuencias recuperadas en `exp_02` y conserve exclusivamente las filas cuyos dos participantes tienen una secuencia FASTA no vacía. El proceso debe tratar de igual forma las filas positivas y negativas, sin modificar los artefactos de `exp_01` ni `exp_02`.

## 2. Entradas

- Interacciones originales: `../exp_01/results/ground_truth.tsv`.
- Secuencias disponibles: `../exp_02/results/sequences.fasta`.
- Metadatos de recuperación: `../exp_02/results/version.txt`, para registrar la procedencia de las secuencias.

Validaciones de entrada:

1. Comprobar que el TSV contiene `uniprot_A` y `uniprot_B`.
2. Comprobar que el FASTA es parseable.
3. Rechazar o reportar cabeceras FASTA duplicadas.
4. Considerar disponible sólo un ID cuya secuencia tenga al menos un residuo.
5. Verificar que los IDs se comparen literalmente, sin conversión de isoformas, locus o alias.

## 3. Archivos de implementación

Crear:

- `scripts/filter_ground_truth_by_sequence.py`: punto de entrada del filtrado y la auditoría.

El script deberá resolver las rutas relativas a partir de su propia ubicación y aceptar argumentos explícitos para entrada, FASTA y directorio de salida. No se añadirán dependencias externas: se utilizará la biblioteca estándar de Python para TSV, FASTA, hashes y metadatos.

## 4. Salidas

Generar bajo `results/`:

| Archivo | Contenido |
|---|---|
| `ground_truth_filtered.tsv` | Filas conservadas, con exactamente el mismo encabezado y columnas que el ground truth original. |
| `filter_audit.tsv` | Auditoría por fila: índice original, IDs A/B, etiqueta, estado de cada secuencia, decisión y motivo. |
| `removed_interactions.tsv` | Filas eliminadas o, como mínimo, sus IDs, etiqueta, motivo y número de fila original. |
| `summary.tsv` | Totales antes/después, filas eliminadas, cobertura por participante, conteos por etiqueta y conteos por motivo. |
| `version.txt` | Fecha UTC, hashes SHA-256 de las entradas, commit Git, parámetros y conteos finales. |

El `ground_truth_filtered.tsv` conservará los valores originales de todas las columnas; no se recalcularán `miscore_max`, `n_evidences`, `methods`, `locus` ni `interaction_type`.

## 5. Regla de filtrado

Para cada fila del ground truth:

- `keep = (uniprot_A ∈ FASTA) AND (uniprot_B ∈ FASTA)`.
- Si falta cualquiera de los dos IDs, la fila se elimina.
- Si una cabecera existe pero su secuencia está vacía, se considera faltante y la fila se elimina.
- La etiqueta (`positive` o `negative`) no participa en la decisión de conservación.
- Las self-interacciones se conservan si su único ID aparece con una secuencia válida.

El orden de las filas conservadas debe permanecer idéntico al orden del ground truth original, para mantener trazabilidad directa por número de fila.

## 6. Auditoría independiente

Después de crear la salida, ejecutar una validación independiente que compruebe:

1. Todas las filas de `ground_truth_filtered.tsv` tienen ambos IDs en el conjunto FASTA.
2. Ninguna fila eliminada satisface simultáneamente la condición de disponibilidad de ambos participantes.
3. El número de filas de entrada es igual a filas conservadas más filas eliminadas.
4. El encabezado y el número de columnas de la salida coinciden exactamente con la entrada.
5. No se introdujeron ni eliminaron duplicados fuera de la regla de filtrado.
6. Las self-interacciones conservadas siguen presentes.
7. Se informa el conteo de positivos y negativos antes y después, sin asumir que el balance 1:1 se mantiene.
8. El resumen identifica por separado filas con falta de secuencia en A, en B o en ambos extremos.
9. Los hashes de entradas registrados en `version.txt` corresponden a los archivos efectivamente usados.

## 7. Pruebas previas

Antes de ejecutar sobre el conjunto completo:

- **Caso válido:** dos IDs presentes; la fila debe conservarse.
- **Falta en A:** sólo `uniprot_A` ausente; la fila debe eliminarse con motivo explícito.
- **Falta en B:** sólo `uniprot_B` ausente; la fila debe eliminarse con motivo explícito.
- **Falta en ambos:** ambos IDs ausentes; la fila debe eliminarse y clasificarse correctamente.
- **Self-interacción:** `uniprot_A == uniprot_B` presente; la fila debe conservarse.
- **Secuencia vacía:** cabecera presente sin residuos; debe tratarse como faltante.
- **Duplicación:** cabecera FASTA repetida; la auditoría debe fallar o reportarla antes del filtrado.
- **Integridad de columnas:** verificar que la salida conserve exactamente el esquema de entrada.

Las pruebas usarán fixtures temporales pequeños y no modificarán los resultados de los experimentos anteriores.

## 8. Ejecución

La transformación es determinista y debería ejecutarse en primer plano, salvo que la validación local indique un tiempo superior a un minuto. La ejecución prevista es:

```bash
~/miniconda3/envs/bioDL/bin/python -u \
  goals/01/experiments/exp_03/scripts/filter_ground_truth_by_sequence.py
```

Antes de ejecutar, actualizar `experiments/index.md` de `planned` a `running`. Después de validar los resultados, cambiarlo a `completed` y consolidar los resultados en `.logbook.md`.

## 9. Criterios de aceptación

La implementación se acepta cuando:

- `ground_truth_filtered.tsv` existe y mantiene exactamente el esquema de entrada;
- toda fila conservada tiene secuencia válida para A y B;
- toda fila eliminada tiene un motivo auditable;
- el número de filas conservadas y eliminadas suma el total de entrada;
- los conteos de positivos, negativos y self-interacciones antes/después están reportados;
- la auditoría independiente termina sin inconsistencias;
- `version.txt` contiene hashes de ambas entradas y el commit utilizado;
- los archivos originales de `exp_01` y `exp_02` permanecen intactos.

No se exige conservar el balance 1:1 después del filtrado: la posible alteración de la distribución de etiquetas debe medirse y reportarse, no corregirse mediante muestreo dentro de este experimento.

## 10. Archivos que se modificarán o crearán

- Crear: `goals/01/experiments/exp_03/scripts/filter_ground_truth_by_sequence.py`.
- Crear durante la ejecución: archivos bajo `goals/01/experiments/exp_03/results/`.
- Actualizar durante el ciclo experimental: `goals/01/experiments/index.md` y `goals/01/.logbook.md`.
- No modificar: `goals/01/experiments/exp_01/` ni `goals/01/experiments/exp_02/`.

## 11. Handoff para implementación

Tras aprobar este plan, implementar el script, ejecutar las pruebas con fixtures y realizar la corrida completa contra los artefactos existentes. El siguiente paso debe ser la revisión de la auditoría y la consolidación del experimento; no se deben iniciar todavía entrenamientos ni reequilibrar el dataset filtrado.