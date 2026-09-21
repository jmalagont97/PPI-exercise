# Implementation Plan: Extracción de embeddings de proteínas con ESM2-650M

**Experiment**: `goals/01/experiments/exp_04/`  
**Project**: PPI-exercise — goal 01  
**Design source**: `DESIGN.md`  
**Status**: In Progress  
**Author**: Juan Sebastian Malagón Torres

## 1. Alcance

Implementar y validar una extracción reproducible de embeddings para todas las proteínas elegibles de `exp_03`: secuencias presentes en `goals/01/experiments/exp_02/results/sequences.fasta` y con longitud `<= 1024` residuos.

La corrida utilizará `Synthyra/ESM2-650M` en modo inferencia, sin fine-tuning. Para cada proteína se conservará un único vector obtenido mediante mean pooling de las representaciones por residuo, excluyendo BOS, EOS, padding y cualquier token especial.

El plan no contempla entrenamiento, ventanas, truncamiento adicional, comparación entre modelos ni extracción de proteínas que superen 1.024 residuos.

## 2. Entradas y salidas

### 2.1 Entradas

- FASTA fuente: `../exp_02/results/sequences.fasta`.
- Regla de elegibilidad: secuencia no vacía y `len(sequence) <= 1024`.
- Modelo: `Synthyra/ESM2-650M`.
- Entorno: `bioDL`, Python 3.13, PyTorch con CUDA y Transformers disponibles.

La lista de proteínas se construirá directamente desde el FASTA, no desde las filas del ground truth, para producir un embedding por proteína y no por interacción. La expectativa actual es procesar **2.769 proteínas**.

### 2.2 Salidas principales

| Archivo | Contenido |
|---|---|
| `results/embeddings.h5` | Embeddings, IDs y longitudes en un único HDF5. |
| `results/embedding_audit.tsv` | Estado individual de cada proteína, longitud, número de tokens residuales y motivo de fallo si existe. |
| `results/summary.tsv` | Totales de entrada, elegibles, procesadas, fallidas, dimensión, tiempo y memoria. |
| `results/version.txt` | Hash de FASTA, identificador/revisión del modelo, commit Git, estado dirty, configuración y conteos. |

El HDF5 tendrá como datasets mínimos:

```text
protein_ids       [N]       UTF-8
sequence_length   [N]       int32
embeddings        [N, 1280] float32
```

Los atributos del archivo registrarán `model_id`, revisión descargada si está disponible, `pooling=mean_residue_only`, `max_sequence_length=1024`, `special_tokens_excluded=true`, `dtype=float32`, hash SHA-256 del FASTA y fecha UTC.

## 3. Componentes de implementación

### 3.1 Script principal

Crear `scripts/extract_esm2_embeddings.py` como punto de entrada único. El script deberá:

1. Resolver las rutas relativas a partir de la raíz del repositorio, sin rutas absolutas codificadas.
2. Leer y validar el FASTA, rechazando cabeceras duplicadas y secuencias vacías.
3. Separar elegibles (`<=1024`) y excluidas (`>1024`), manteniendo la lista y el motivo en la auditoría.
4. Cargar tokenizer y modelo desde `Synthyra/ESM2-650M` mediante Transformers.
5. Seleccionar automáticamente CUDA cuando esté disponible y permitir CPU mediante argumento explícito.
6. Ejecutar inferencia con `model.eval()` y `torch.inference_mode()`.
7. Tokenizar con padding por lote y sin truncar silenciosamente las secuencias elegibles.
8. Obtener la representación final por posición desde `last_hidden_state`.
9. Construir una máscara de pooling que sea verdadera sólo para residuos de la secuencia; excluir `attention_mask=0` y cualquier ID incluido en `tokenizer.all_special_ids`.
10. Calcular el promedio sobre las posiciones válidas de cada proteína.
11. Validar en memoria que cada vector tenga dimensión 1.280 y no contenga NaN ni Inf.
12. Escribir el HDF5 y las auditorías de manera determinista, conservando el orden de los IDs del FASTA.
13. Guardar los metadatos de ejecución y parámetros efectivos en `version.txt`.

El script deberá aceptar, como mínimo, argumentos para FASTA de entrada, directorio de salida, modelo, batch size, dtype de almacenamiento, dispositivo y opción explícita de sobreescritura.

### 3.2 Pooling

La operación conceptual será:

```text
embedding_i = sum(hidden_state_i[j] for j in valid_residue_positions) \
              / count(valid_residue_positions)
```

La máscara no se derivará únicamente de `attention_mask`: también debe excluir explícitamente los tokens especiales. Se comprobará que el denominador sea mayor que cero para todas las proteínas elegibles.

El cálculo podrá realizarse en el dtype de inferencia seleccionado, pero el artefacto maestro se almacenará en `float32` para conservar estabilidad numérica y facilitar el uso posterior.

### 3.3 Dependencia HDF5

`h5py` no está instalado actualmente en `bioDL`. Antes de implementar la escritura se debe añadir y verificar esta dependencia en el entorno. Crear `requirements.txt` dentro de `exp_04/` con la dependencia adicional y documentar la versión instalada en `version.txt`; no modificar otros entornos ni instalar dependencias durante la corrida sin registrarlo.

No se añadirá una dependencia HDF5 alternativa: el formato de salida requerido es HDF5 y `h5py` es suficiente para esta extracción.

### 3.4 Escritura y reanudación

Para evitar un HDF5 incompleto con apariencia de válido:

1. Escribir primero a un archivo temporal dentro de `results/`.
2. Completar datasets, atributos y validaciones.
3. Cerrar el archivo.
4. Renombrarlo al nombre final sólo si todas las validaciones pasan.

La primera versión no implementará reanudación parcial. Si `embeddings.h5` ya existe, el script deberá exigir `--overwrite` explícito para reemplazarlo.

## 4. Configuración inicial

Usar una configuración conservadora y modificable por CLI:

- `model_id`: `Synthyra/ESM2-650M`.
- `max_length`: `1024` residuos biológicos.
- `batch_size`: comenzar con `1` y aumentar sólo si la prueba piloto confirma memoria suficiente.
- `inference_dtype`: el dtype recomendado por la GPU; el HDF5 final será `float32`.
- `device`: `cuda` si está disponible, con fallback explícito a `cpu`.
- `pooling`: `mean_residue_only`.
- Orden de procesamiento: orden de los IDs en el FASTA.

El equipo disponible detectado es una NVIDIA RTX 3060 con 12.288 MiB; el batch size no debe asumirse seguro para secuencias cercanas a 1.024 residuos sin una prueba piloto.

## 5. Validaciones y pruebas

### 5.1 Pruebas previas

- **FASTA:** verificar IDs únicos, secuencias no vacías y clasificación correcta de longitudes `<=1024` y `>1024`.
- **Tokenización:** comprobar en un fixture corto la presencia de tokens especiales y que ninguno participe en el pooling.
- **Pooling:** comprobar con tensores sintéticos que padding, BOS y EOS no cambien el promedio.
- **Forma:** verificar que una entrada produzca `(1280,)` y un lote produzca `(batch, 1280)`.
- **HDF5:** escribir y recargar un fixture pequeño; comprobar datasets, dtype, atributos y correspondencia ID–fila.
- **Error controlado:** verificar que una secuencia vacía, un ID duplicado o un HDF5 existente sin `--overwrite` produzca un fallo explícito.

### 5.2 Prueba piloto

Procesar un subconjunto pequeño que incluya secuencias cortas, medianas y cercanas a 1.024 residuos. Confirmar tiempo, consumo de GPU, forma de salida y ausencia de NaN/Inf antes de lanzar la extracción completa.

### 5.3 Validación independiente de la corrida completa

Después de producir los artefactos:

1. Comparar los IDs del HDF5 con los 2.769 IDs elegibles del FASTA.
2. Confirmar una fila por ID y ninguna duplicación.
3. Confirmar forma `(2769, 1280)`.
4. Confirmar que `sequence_length <= 1024` para todas las filas.
5. Confirmar que todos los valores sean finitos.
6. Recargar el HDF5 en un proceso separado y repetir las comprobaciones.
7. Confirmar que el número de estados `processed`, `excluded_length` y `failed` cubra todas las proteínas del FASTA.
8. Comparar el resumen con los conteos de `exp_03`.

## 6. Ejecución y persistencia

La extracción completa puede superar un minuto y deberá lanzarse en una sesión tmux persistente, con salida sin buffer:

```bash
tmux new-session -d -s 01_exp_04 \
  "source ~/miniconda3/etc/profile.d/conda.sh && conda activate bioDL && \
   python -u goals/01/experiments/exp_04/scripts/extract_esm2_embeddings.py; bash"
```

Antes de la corrida:

- actualizar `experiments/index.md` de `draft` a `running`;
- registrar la versión del modelo y el estado Git;
- confirmar que el archivo de entrada corresponde al FASTA auditado de `exp_02`;
- comprobar que `h5py` está disponible.

Después de verificar resultados, cambiar el estado a `completed` y consolidar el resultado en `.logbook.md`.

## 7. Criterios de aceptación

La implementación se acepta si:

- se procesan las 2.769 proteínas elegibles;
- las proteínas de longitud `>1024` no aparecen en el HDF5;
- `embeddings` tiene forma `(2769, 1280)` y dtype `float32`;
- `protein_ids` y `embeddings` conservan correspondencia exacta por índice;
- no existen NaN, Inf, IDs duplicados ni filas vacías;
- el pooling excluye todos los tokens especiales;
- el HDF5 puede cerrarse y recargarse correctamente;
- `embedding_audit.tsv`, `summary.tsv` y `version.txt` son consistentes;
- el HDF5 final sólo se publica después de pasar la validación independiente.

El experimento se considera fallido o parcial si hay proteínas elegibles sin embedding, si aparecen valores no finitos, si la forma no es `(N,1280)` o si no puede demostrarse la exclusión de tokens especiales.

## 8. Archivos que se crearán o modificarán

- Crear: `goals/01/experiments/exp_04/requirements.txt`.
- Crear: `goals/01/experiments/exp_04/scripts/extract_esm2_embeddings.py`.
- Crear: `goals/01/experiments/exp_04/scripts/validate_embeddings.py`.
- Crear durante la ejecución: archivos bajo `goals/01/experiments/exp_04/results/`.
- No modificar: `exp_01`, `exp_02`, `exp_03`, el FASTA fuente ni el ground truth filtrado.

## 9. Handoff para implementación

Este plan autoriza la fase de implementación conceptual, no la instalación de dependencias ni la ejecución de la extracción. Antes de editar scripts se debe confirmar la estrategia de dtype y batch size de la prueba piloto. Una vez implementado, la corrida completa requiere actualizar el estado del índice y usar tmux según la política del proyecto.
