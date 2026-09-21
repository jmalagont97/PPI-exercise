# Experiment Design: Ground Truth Maestro — Pares Directos (MI:0407) vs. Negativos Pool A
**Experiment**: experiments/exp_01/
**Project**: PPI-exercise (goal 01 — obtención de datos)
**Date**: 2026-09-21
**Author**: J. S. Malagón Torres (PI) + Co-investigador IA (rol: interactómica y deep learning)
**Status**: Draft

---

## 1. Hypothesis

Es posible construir un ground truth maestro de interacciones físicas directas de *A. thaliana* — pares positivos MI:0407 vs. pares negativos muestreados del complemento sin evidencia — con calidad suficiente (cero colisión de evidencia en negativos, trazabilidad UniProt/AGI completa) para servir como archivo maestro de anotaciones del futuro modelo siamés con ESM-2 y cabezas no compartidas. **Este experimento NO recupera secuencias** (queda para un experimento posterior).

## 2. Experimental Setup

- **Fuente maestra**: `../../data/A.thaliana_interactome.txt` (IntAct, MITAB 2.7, 70,798 evidencias; subconjunto 3702/3702 = 59,337).
- **Positivos**: pares únicos con al menos una evidencia `MI:0407` (direct interaction), **self-interacciones incluidas** (decisión metodológica en `.discussion.md`): **1,424 pares**.
- **Negativos (Pool A)**: pares aleatorios entre las 8,777 proteínas del interactoma que **no reporten NINGÚN tipo de interacción** — incluidas evidencias de baja confianza, proximity, colocalization y **reacciones enzimáticas** (MI:0217 fosforilación, MI:0203, MI:0414, etc.). El universo de exclusión son **41,474 pares con cualquier evidencia MI** (nota: incluye 12 pares con únicamente tipos fuera de la jerarquía estándar, igualmente excluidos). Cantidad: **1,424 pares (balance 1:1)**. Seed de muestreo: 42.
- **Secuencias**: FUERA DE ALCANCE de este experimento — solo se genera el ground truth (IDs UniProt + locus AGI); la recuperación de secuencias vía UniProt REST se planificará en un experimento posterior.
- **Proceso**: script determinista en `scripts/` (parsing MITAB + muestreo con seed; cómputo local < 60 s → ejecución en primer plano). Salida atómica del ground truth maestro.
- **Hardware**: CPU local (parsing + muestreo); trivial.

## 3. File Layout for This Experiment

```
goals/01/experiments/exp_01/
├── DESIGN.md                  ← este archivo
├── scripts/                   ← script generador del ground truth (decidido en IMPLEMENTATION.md)
├── results/
│   ├── ground_truth.tsv       ← ARCHIVO MAESTRO de anotaciones (positivos + negativos)
│   └── version.txt            ← hash del commit + seed de muestreo + sha256 de la fuente
└── reports/
    └── summary.md             ← consolidado tras corrida exitosa
```

El ground truth vive en `experiments/exp_01/results/`; si el PI lo promociona a dato compartido, se usa `-link-data` hacia `data/ground_truth.tsv`.

**Formato de `ground_truth.tsv`** (columnas):
`uniprot_A  uniprot_B  locus_A  locus_B  label(positive|negative)  interaction_type(MI:0407|none)  miscore_max  n_evidences  methods`

## 4. Baselines

No aplica (experimento de obtención de datos). Control de calidad interno: tasa de colisión de negativos contra el universo de evidencia debe ser **exactamente 0**.

## 5. Proposed Conditions

Una sola condición: generación determinista del ground truth con seed fija. No hay ablations ni sweeps.

## 6. Ablation Studies

No aplica.

## 7. Evaluation Protocol

- **Métrica primaria (éxito)**: archivo `ground_truth.tsv` generado con 1,424 pares `positive` (MI:0407, self-incluidas) + 1,424 pares `negative` (Pool A), **cero colisiones** de negativos contra los 41,474 pares con evidencia, y cero duplicados.
- **Métricas secundarias**: cobertura de mapeo AGI/locus (esperado ~98.6%), distribución de miscore de los positivos, conteo de proteínas únicas involucradas (para dimensionar la posterior descarga de secuencias).
- **Estadística**: no aplica (población determinista); la seed 42 se registra en `version.txt` para reproducibilidad exacta.
- **Resultados en**: `results/`.
- **Costo**: segundos de CPU local (parsing + muestreo); trivial.

## 8. Expected Results & Decision Rules

- **Si la generación es exitosa** (colisiones = 0): ground truth declarado maestro, promovible vía `-link-data`, y se procede a planificar la recuperación de secuencias (siguiente exp).
- **Si hay pares sin mapeo AGI/locus** (~1.4% esperado): se conservan con campo vacío en las columnas locus; no bloquean la generación.
- **Si la colisión de negativos > 0** (no esperado con verificación previa): regenerar con verificación estricta post-muestreo.
- **Criterio de parada**: no aplica (corrida única barata).

## 9. Risks & Mitigations

- ⚠️ **Falsos negativos por ausencia de evidencia**: el Pool A asume "sin evidencia en IntAct ≈ no interactúan". Mitigación metodológica ya consensuada: restringir a proteínas "estudiadas" (mismo sesgo de selección que los positivos); a futuro, validar contra una muestra del Pool B (proteoma completo).
- **Isoformas**: 83 accesiones con sufijo `-N` se conservan tal cual (ID estable, sin colapsar a canónica); su resolución a secuencia ocurrirá en el experimento de recuperación de secuencias.
- **Fuga de datos (futura)**: el ground truth balanceado 1:1 no debe dividirse train/test por filas sino por proteína (group split), para evitar que la misma proteína aparezca en train y test con pares distintos. ⚠️ Registrar esta restricción ahora: la implementación del split NO pertenece a este experimento, pero el ground truth debe conservar `uniprot_id` estable para habilitarla.

## 10. Reproducibility Checklist

- [x] Seed de muestreo fija (42) y registrada
- [ ] Config/script guardado en `scripts/` (según IMPLEMENTATION.md)
- [x] Fuente de datos con hash registrado (`data/A.thaliana_interactome.txt`, sha256 a registrar en `version.txt`)
- [ ] `version.txt` con hash de commit + seed + sha256 de la fuente
- [ ] Estado de Git limpio al ejecutar (commit previo de scripts)

## 11. Next Steps

1. Revisar y aceptar este plan experimental (hipótesis, protocolo de éxito, reglas de decisión).
2. Una vez aceptado, producir el **plan de implementación** (script de parsing MITAB + muestreo seedeado + verificación de colisiones) y guardarlo como `experiments/exp_01/IMPLEMENTATION.md` antes de tocar cualquier archivo de código.
3. Tras la corrida: marcar `completed` en `experiments/index.md`, consolidar con `experiment-reporter` en `reports/summary.md` y registrar en `.logbook.md`.
