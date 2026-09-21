#!/usr/bin/env python
import argparse
import csv
from pathlib import Path

import h5py
import numpy as np

from extract_esm2_embeddings import read_fasta


def repository_root():
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("repository root not found")


def parse_args():
    root = repository_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fasta", type=Path, default=root / "goals/01/experiments/exp_02/results/sequences.fasta")
    parser.add_argument("--embeddings", type=Path, default=root / "goals/01/experiments/exp_04/results/embeddings.h5")
    parser.add_argument("--max-length", type=int, default=1024)
    return parser.parse_args()


def validate(args):
    sequences = read_fasta(args.fasta)
    expected_ids = [protein_id for protein_id, sequence in sequences.items() if len(sequence) <= args.max_length]
    with h5py.File(args.embeddings, "r") as handle:
        required = {"protein_ids", "sequence_length", "embeddings"}
        if set(handle) < required:
            raise ValueError(f"missing HDF5 datasets: {required - set(handle)}")
        ids = [value.decode() if isinstance(value, bytes) else str(value) for value in handle["protein_ids"][:]]
        lengths = handle["sequence_length"][:]
        embeddings = handle["embeddings"]
        if ids != expected_ids:
            raise ValueError("HDF5 protein IDs do not match eligible FASTA IDs and order")
        if embeddings.shape != (len(expected_ids), 1280):
            raise ValueError(f"unexpected embedding shape: {embeddings.shape}")
        if lengths.tolist() != [len(sequences[protein_id]) for protein_id in expected_ids]:
            raise ValueError("HDF5 sequence lengths do not match FASTA")
        if not np.isfinite(embeddings[:]).all():
            raise ValueError("HDF5 contains NaN or Inf")
        if handle.attrs["pooling"] != "mean_residue_only":
            raise ValueError("unexpected pooling attribute")
        if handle.attrs["special_tokens_excluded"] is not True:
            raise ValueError("special-token exclusion attribute is false")
    print(f"[valid] proteins={len(expected_ids)} shape=({len(expected_ids)}, 1280) finite=true", flush=True)


if __name__ == "__main__":
    validate(parse_args())
