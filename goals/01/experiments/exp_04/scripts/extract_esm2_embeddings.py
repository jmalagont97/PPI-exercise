#!/usr/bin/env python
import argparse
import csv
import hashlib
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import h5py
import torch
from transformers import AutoModel, AutoTokenizer

DEFAULT_MODEL = "Synthyra/ESM2-650M"
MAX_LENGTH = 1024


def repository_root():
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("repository root not found")


def read_fasta(path):
    sequences = {}
    current_id = None
    current_sequence = []
    with open(path) as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current_id is not None:
                    if not current_sequence:
                        raise ValueError(f"empty sequence for {current_id}")
                    if current_id in sequences:
                        raise ValueError(f"duplicate FASTA ID: {current_id}")
                    sequences[current_id] = "".join(current_sequence).upper()
                current_id = line[1:].split()[0]
                if not current_id:
                    raise ValueError(f"empty FASTA ID at line {line_number}")
                current_sequence = []
            else:
                if current_id is None:
                    raise ValueError(f"sequence before FASTA header at line {line_number}")
                current_sequence.append(line)
    if current_id is not None:
        if not current_sequence:
            raise ValueError(f"empty sequence for {current_id}")
        if current_id in sequences:
            raise ValueError(f"duplicate FASTA ID: {current_id}")
        sequences[current_id] = "".join(current_sequence).upper()
    return sequences


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def residue_pool_mask(input_ids, attention_mask, special_token_ids):
    input_ids = torch.as_tensor(input_ids)
    attention_mask = torch.as_tensor(attention_mask, dtype=torch.bool)
    mask = attention_mask.clone()
    for token_id in special_token_ids:
        mask &= input_ids != token_id
    return mask


def mean_pool_residue_embeddings(hidden_states, mask):
    hidden_states = torch.as_tensor(hidden_states)
    mask = torch.as_tensor(mask, dtype=torch.bool)
    counts = mask.sum(dim=1)
    if torch.any(counts == 0):
        raise ValueError("sequence has no valid residue")
    weights = mask.unsqueeze(-1).to(hidden_states.dtype)
    return (hidden_states * weights).sum(dim=1) / counts.unsqueeze(-1).to(hidden_states.dtype)


def parse_args():
    root = repository_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fasta", type=Path, default=root / "goals/01/experiments/exp_02/results/sequences.fasta")
    parser.add_argument("--output-dir", type=Path, default=root / "goals/01/experiments/exp_04/results")
    parser.add_argument("--model-id", default=DEFAULT_MODEL)
    parser.add_argument("--max-length", type=int, default=MAX_LENGTH)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def choose_device(requested):
    if requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    return torch.device(requested)


def write_audit(path, sequences, statuses):
    with open(path, "w", newline="") as handle:
        fields = ["protein_id", "sequence_length", "status", "reason"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for protein_id, sequence in sequences.items():
            writer.writerow({
                "protein_id": protein_id,
                "sequence_length": len(sequence),
                "status": statuses[protein_id][0],
                "reason": statuses[protein_id][1],
            })


def write_summary(path, values):
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["metric", "value"])
        writer.writerows(values.items())


def write_version(path, values):
    with open(path, "w") as handle:
        for key, value in values.items():
            handle.write(f"{key}: {value}\n")


def extract(args):
    if args.max_length < 1 or args.batch_size < 1:
        raise ValueError("max-length and batch-size must be positive")
    args.fasta = args.fasta.resolve()
    args.output_dir = args.output_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "embeddings.h5"
    if output_path.exists() and not args.overwrite:
        raise FileExistsError(f"output exists; pass --overwrite: {output_path}")

    sequences = read_fasta(args.fasta)
    eligible = [(protein_id, sequence) for protein_id, sequence in sequences.items() if len(sequence) <= args.max_length]
    excluded = set(sequences) - {protein_id for protein_id, _ in eligible}
    statuses = {
        protein_id: ("eligible", "within_max_length") if protein_id not in excluded else ("excluded_length", "sequence_exceeds_max_length")
        for protein_id in sequences
    }

    device = choose_device(args.device)
    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    model = AutoModel.from_pretrained(args.model_id, trust_remote_code=True)
    model.to(device)
    model.eval()
    embedding_dim = int(model.config.hidden_size)
    if embedding_dim != 1280:
        raise ValueError(f"unexpected embedding dimension: {embedding_dim}")
    special_token_ids = {token_id for token_id in tokenizer.all_special_ids if token_id is not None}
    string_dtype = h5py.string_dtype(encoding="utf-8")
    temp_path = None
    start = datetime.now(timezone.utc)
    try:
        with tempfile.NamedTemporaryFile(prefix="embeddings_", suffix=".h5", dir=args.output_dir, delete=False) as temp:
            temp_path = Path(temp.name)
        with h5py.File(temp_path, "w") as output:
            n = len(eligible)
            chunk_rows = min(args.batch_size, max(n, 1))
            output.create_dataset("protein_ids", shape=(n,), dtype=string_dtype)
            output.create_dataset("sequence_length", shape=(n,), dtype="i4")
            output.create_dataset(
                "embeddings",
                shape=(n, embedding_dim),
                dtype="f4",
                chunks=(chunk_rows, embedding_dim),
                compression="gzip",
            )
            output["protein_ids"][:] = [protein_id for protein_id, _ in eligible]
            output["sequence_length"][:] = [len(sequence) for _, sequence in eligible]
            for start_index in range(0, n, args.batch_size):
                batch = eligible[start_index : start_index + args.batch_size]
                encoded = tokenizer(
                    [sequence for _, sequence in batch],
                    return_tensors="pt",
                    padding=True,
                    truncation=False,
                    add_special_tokens=True,
                )
                input_ids = encoded["input_ids"]
                attention_mask = encoded["attention_mask"]
                encoded = {key: value.to(device) for key, value in encoded.items()}
                with torch.inference_mode():
                    hidden = model(**encoded).last_hidden_state
                mask = residue_pool_mask(input_ids, attention_mask, special_token_ids).to(device)
                pooled = mean_pool_residue_embeddings(hidden, mask)
                if pooled.shape != (len(batch), embedding_dim):
                    raise ValueError(f"unexpected batch shape: {tuple(pooled.shape)}")
                if not torch.isfinite(pooled).all():
                    raise ValueError(f"non-finite embedding in batch starting at {start_index}")
                output["embeddings"][start_index : start_index + len(batch)] = pooled.float().cpu().numpy()
            output.attrs["model_id"] = args.model_id
            output.attrs["pooling"] = "mean_residue_only"
            output.attrs["special_tokens_excluded"] = True
            output.attrs["max_sequence_length"] = args.max_length
            output.attrs["embedding_dimension"] = embedding_dim
            output.attrs["source_fasta_sha256"] = sha256(args.fasta)
            output.attrs["created_utc"] = start.isoformat()
        os.replace(temp_path, output_path)
        temp_path = None
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    end = datetime.now(timezone.utc)
    elapsed = (end - start).total_seconds()
    processed = len(eligible)
    summary = {
        "input_proteins": len(sequences),
        "processed_proteins": processed,
        "excluded_length": len(excluded),
        "failed": 0,
        "max_sequence_length": args.max_length,
        "embedding_dimension": embedding_dim,
        "batch_size": args.batch_size,
        "device": str(device),
        "elapsed_seconds": f"{elapsed:.3f}",
        "throughput_proteins_per_second": f"{processed / elapsed:.3f}" if elapsed else "inf",
    }
    write_audit(args.output_dir / "embedding_audit.tsv", sequences, statuses)
    write_summary(args.output_dir / "summary.tsv", summary)
    version = {
        "date_utc": end.isoformat(),
        "model_id": args.model_id,
        "model_hidden_size": embedding_dim,
        "fasta": str(args.fasta),
        "fasta_sha256": sha256(args.fasta),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_status_dirty": bool(git_value("status", "--porcelain")),
        **summary,
    }
    write_version(args.output_dir / "version.txt", version)
    print(f"[done] input={len(sequences)} processed={processed} excluded_length={len(excluded)} output={output_path}", flush=True)


if __name__ == "__main__":
    extract(parse_args())
