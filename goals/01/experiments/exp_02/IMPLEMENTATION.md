# Implementation Plan: Recuperación de secuencias de aminoácidos desde UniProt

**Experiment**: `goals/01/experiments/exp_02/`  
**Project**: PPI-exercise — goal 01  
**Design source**: `DESIGN.md`  
**Status**: Proposed  
**Author**: Juan Sebastian Malagón Torres

## 1. Alcance

Implementar una descarga reproducible de las secuencias de aminoácidos asociadas a los IDs UniProt presentes en `data/ground_truth.tsv`. La implementación no modificará el `ground_truth.tsv`; producirá un FASTA, un reporte de IDs no recuperados y metadatos de auditoría dentro de `exp_02/results/`.

## 2. Entradas y salidas

### Entrada

- `../../data/ground_truth.tsv`, relativo a `goals/01/experiments/exp_02/`.
- Columnas requeridas: `uniprot_A` y `uniprot_B`.
- Conjunto de consulta: unión deduplicada de ambas columnas, preservando literalmente cada ID de entrada.

### Salidas

| Archivo | Contenido |
|---|---|
| `results/sequences.fasta` | Una entrada FASTA por ID recuperado; cabecera exactamente `>{uniprot_id}`. |
| `results/missing_ids.tsv` | IDs de entrada sin secuencia recuperada y motivo clasificado. Se crea aunque esté vacío. |
| `results/audit.tsv` | Estado por ID: solicitado, recuperado, longitud, checksum de secuencia y estado HTTP/motivo. |
| `results/version.txt` | Fecha UTC, hash SHA-256 del `ground_truth.tsv`, commit Git y parámetros de descarga. |

El archivo FASTA debe escribirse de forma determinista, ordenando las cabeceras por ID UniProt. Las secuencias deben conservarse en mayúsculas y envolverse a una longitud fija por línea compatible con FASTA, sin alterar los residuos.

## 3. Componentes de implementación

### 3.1 Script de ejecución

Crear `scripts/download_uniprot_sequences.py` como único punto de entrada del experimento. El script deberá:

1. Resolver la raíz del repositorio a partir de su propia ubicación, sin rutas absolutas codificadas.
2. Leer el TSV con `csv.DictReader` y validar que las dos columnas requeridas existan.
3. Construir el conjunto único de IDs, rechazando campos vacíos y registrándolos como error de entrada si aparecen.
4. Consultar UniProt REST mediante el endpoint de recuperación de entradas por ID, solicitando formato FASTA.
5. Descargar de forma agrupada cuando la API lo permita, o por lotes pequeños; no emitir una petición independiente innecesaria para cada proteína.
6. Aplicar timeout, reintentos limitados con backoff para errores transitorios (`429`, `5xx)`) y respetar `Retry-After` cuando esté disponible.
7. Distinguir IDs no encontrados (`404`/ausencia en la respuesta), errores permanentes y errores transitorios agotados.
8. Validar que cada registro devuelto tenga un ID UniProt reconocible y una secuencia no vacía.
9. Escribir las salidas sólo después de completar la adquisición y la validación, evitando dejar un FASTA aparentemente completo si la descarga falla parcialmente.
10. Calcular y guardar el hash del archivo de entrada y el commit Git usado.

### 3.2 Requisitos de dependencia

Preferir la biblioteca estándar de Python (`csv`, `hashlib`, `datetime`, `subprocess`, `time`, `urllib`/`json`) para evitar añadir dependencias. Si la API requiere parseo FASTA especializado, documentar y fijar la dependencia en el entorno antes de implementarla; no introducirla implícitamente en el script.

### 3.3 Parámetros reproducibles

Definir en el script o mediante argumentos CLI explícitos:

- ruta de entrada;
- directorio de salida;
- tamaño de lote;
- timeout;
- máximo de reintentos;
- pausa mínima entre solicitudes;
- fecha y hora UTC de la corrida.

Los valores efectivos deberán aparecer en `version.txt`. La URL base de UniProt también debe registrarse allí.

## 4. Auditorías y validaciones

Ejecutar validaciones antes de considerar el experimento completo:

1. Contar IDs únicos de entrada.
2. Contar cabeceras FASTA únicas.
3. Verificar que las cabeceras FASTA sean un subconjunto exacto de los IDs de entrada.
4. Verificar que no existan cabeceras duplicadas.
5. Verificar que cada secuencia sea no vacía y contenga únicamente símbolos válidos de aminoácidos según la convención seleccionada, documentando cualquier símbolo ambiguo permitido por UniProt.
6. Comprobar que `recuperados + faltantes + errores` cubra exactamente el conjunto de IDs de entrada.
7. Confirmar que `missing_ids.tsv` enumere explícitamente toda diferencia entre entrada y FASTA.
8. Comparar la cobertura primaria con el criterio de `DESIGN.md`: éxito sólo si cobertura = 100 %, una secuencia por ID y cero cabeceras duplicadas.

Las comprobaciones deben ejecutarse tanto dentro del script como mediante una validación independiente de los archivos producidos, para evitar que un error de escritura se confunda con un error de recuperación.

## 5. Pruebas antes de la corrida completa

- **Prueba de lectura:** fixture pequeño con IDs repetidos en `uniprot_A`/`uniprot_B`; verificar deduplicación.
- **Prueba de formato:** fixture con un ID ausente y un registro válido; verificar FASTA y `missing_ids.tsv`.
- **Prueba de reintentos:** respuesta simulada `429`/`5xx`; verificar backoff y clasificación final.
- **Prueba de integridad:** FASTA con una cabecera duplicada o secuencia vacía; verificar que la auditoría falle.
- **Prueba real limitada:** lote pequeño de IDs reales antes de lanzar los 3,086 IDs.

No se deben usar datos de prueba para marcar el experimento como completado; la decisión depende de la corrida completa contra `ground_truth.tsv`.

## 6. Ejecución y persistencia

La descarga completa puede exceder un minuto y debe lanzarse en una sesión `tmux` persistente usando el intérprete documentado en el logbook:

```bash
tmux new-session -d -s 01_exp_02 \
  "~/miniconda3/envs/bioDL/bin/python -u goals/01/experiments/exp_02/scripts/download_uniprot_sequences.py; bash"
```

Antes del lanzamiento, actualizar `experiments/index.md` de `planned` a `running`. No marcarla como `completed` hasta revisar los resultados y consolidar el experimento en `.logbook.md`.

## 7. Criterios de aceptación

La implementación se acepta cuando:

- `results/sequences.fasta` existe y es parseable;
- cada ID único del `ground_truth.tsv` tiene exactamente una secuencia;
- las cabeceras conservan literalmente los IDs de entrada;
- no hay duplicados ni secuencias vacías;
- la cobertura auditada es 100 %;
- `audit.tsv`, `missing_ids.tsv` y `version.txt` son consistentes con el FASTA;
- la ejecución y la validación independiente terminan sin errores;
- el hash de entrada, commit y parámetros quedan registrados.

Si la cobertura es menor de 100 %, el experimento se considera fallido o parcial, nunca exitoso por ocultar los IDs faltantes. En ese caso, los IDs y motivos de fallo se conservan para decidir posteriormente si se usa una fuente alternativa.

## 8. Archivos que se modificarán o crearán

- Crear: `goals/01/experiments/exp_02/scripts/download_uniprot_sequences.py`.
- Crear durante la ejecución: archivos bajo `goals/01/experiments/exp_02/results/`.
- No modificar: `data/ground_truth.tsv`, datos fuente del interactoma ni `goals/01/experiments/exp_01/`.

## 9. Handoff para implementación

Tras aprobar este plan, implementar el script, ejecutar primero las pruebas limitadas y después la descarga completa. La corrida completa requiere aprobación operativa para iniciar la sesión `tmux`; el plan no autoriza por sí mismo la ejecución ni modifica archivos de código.