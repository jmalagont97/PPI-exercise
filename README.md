# PPI-exercise

An academic project to explore **protein–protein interactions (PPI) in the interactome of *Arabidopsis thaliana*** (thale cress), combining curated interaction data with modern deep learning on protein language models.

## Overview

The central idea is a **siamese-style neural architecture for PPI prediction** built on top of **ESM-2** protein language model embeddings. Unlike a classic siamese network, the two projection heads **do not share weights**, allowing each branch of a protein pair to be projected independently before interaction scoring.

The model is trained and evaluated against a curated ground truth derived from the *A. thaliana* interactome hosted at [IntAct](https://www.ebi.ac.uk/intact/).

## Data

- **`data/A.thaliana_interactome.txt`** — the master source: the *A. thaliana* interactome downloaded from IntAct in PSI-MI MITAB format (70,798 raw interaction records, 42 columns).
- **`data/ground_truth.tsv`** — the master annotation file (symlink to `goals/01/experiments/exp_01/results/`): 2,848 balanced protein pairs.
  - **1,424 positives** — experimentally demonstrated *direct interactions* only (PSI-MI `MI:0407`), self-interactions included.
  - **1,424 negatives** — random protein pairs drawn from the same studied proteome with **no evidence of interaction of any kind** in the master file.

Each row carries UniProt accessions, AGI locus identifiers, the interaction label, confidence score (IntAct MI score), evidence counts, and detection methods.

## Repository Layout

```
PPI-exercise/
├── data/                  ← shared data store (source interactome + promoted ground truth)
└── goals/01/              ← active research line (dataset construction)
    ├── experiments/       ← experiment bank (exp_01: ground-truth generation, completed)
    └── pkg/, docs/        ← internal modules and references
```

The project follows a goal-based research workflow: each research line lives in its own `goals/<goal_id>/` directory with its own discussion log, experiment logbook, and experiment bank, all governed by `AGENTS.md` (session state, not tracked by Git).

## Status

- **[exp_01]** Ground-truth master file generation — **completed** (seed 42, zero evidence collisions, independent audit passed).
- **Next:** retrieval of UniProt sequences for the 3,086 unique proteins in the ground truth, then ESM-2 embedding and siamese-model prototyping.

## Author

Juan Sebastian Malagón Torres — academic/research project.
