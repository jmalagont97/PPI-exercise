import argparse
import csv
import datetime as dt
import hashlib
import os
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
DEFAULT_GROUND_TRUTH = os.path.join(ROOT, "goals/01/experiments/exp_01/results/ground_truth.tsv")
DEFAULT_FASTA = os.path.join(ROOT, "goals/01/experiments/exp_02/results/sequences.fasta")
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "../results")


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def read_fasta(path):
    sequences = {}
    duplicate_ids = set()
    current_id = None
    current_sequence = []
    with open(path) as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current_id is not None:
                    sequence = "".join(current_sequence).upper()
                    if current_id in sequences:
                        duplicate_ids.add(current_id)
                    sequences[current_id] = sequence
                current_id = line[1:].split()[0]
                current_sequence = []
            elif current_id is None:
                raise ValueError(f"FASTA sequence before header at line {line_number}")
            else:
                current_sequence.append(line)
    if current_id is not None:
        sequence = "".join(current_sequence).upper()
        if current_id in sequences:
            duplicate_ids.add(current_id)
        sequences[current_id] = sequence
    if duplicate_ids:
        raise ValueError(f"Duplicate FASTA headers: {len(duplicate_ids)}")
    return {identifier for identifier, sequence in sequences.items() if sequence}


def write_version(output_dir, ground_truth, fasta, counts, commit):
    with open(os.path.join(output_dir, "version.txt"), "w") as handle:
        handle.write(f"date_utc: {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M:%S UTC}\n")
        handle.write(f"ground_truth: {os.path.relpath(ground_truth, ROOT)}\n")
        handle.write(f"ground_truth_sha256: {sha256(ground_truth)}\n")
        handle.write(f"fasta: {os.path.relpath(fasta, ROOT)}\n")
        handle.write(f"fasta_sha256: {sha256(fasta)}\n")
        handle.write(f"git_commit: {commit}\n")
        for key, value in counts.items():
            handle.write(f"{key}: {value}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ground-truth", default=DEFAULT_GROUND_TRUTH)
    parser.add_argument("--fasta", default=DEFAULT_FASTA)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    available = read_fasta(args.fasta)
    with open(args.ground_truth, newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"uniprot_A", "uniprot_B"}
        if not required.issubset(reader.fieldnames or set()):
            raise ValueError(f"Missing columns: {sorted(required - set(reader.fieldnames or []))}")
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    kept = []
    removed = []
    audit = []
    for row_number, row in enumerate(rows, start=2):
        a = row["uniprot_A"]
        b = row["uniprot_B"]
        a_available = a in available
        b_available = b in available
        if a_available and b_available:
            decision, reason = "kept", "both_sequences_available"
            kept.append(row)
        else:
            decision = "removed"
            if not a_available and not b_available:
                reason = "sequence_missing_A_and_B"
            elif not a_available:
                reason = "sequence_missing_A"
            else:
                reason = "sequence_missing_B"
            removed.append({"source_row": row_number, "uniprot_A": a, "uniprot_B": b, "label": row.get("label", ""), "reason": reason})
        audit.append({"source_row": row_number, "uniprot_A": a, "uniprot_B": b, "label": row.get("label", ""), "a_sequence": a_available, "b_sequence": b_available, "decision": decision, "reason": reason})

    filtered_path = os.path.join(args.output_dir, "ground_truth_filtered.tsv")
    with open(filtered_path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(kept)

    with open(os.path.join(args.output_dir, "filter_audit.tsv"), "w", newline="") as handle:
        fields = ["source_row", "uniprot_A", "uniprot_B", "label", "a_sequence", "b_sequence", "decision", "reason"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(audit)

    with open(os.path.join(args.output_dir, "removed_interactions.tsv"), "w", newline="") as handle:
        fields = ["source_row", "uniprot_A", "uniprot_B", "label", "reason"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(removed)

    labels_before = {label: sum(row.get("label") == label for row in rows) for label in sorted({row.get("label", "") for row in rows})}
    labels_after = {label: sum(row.get("label") == label for row in kept) for label in labels_before}
    summary_path = os.path.join(args.output_dir, "summary.tsv")
    with open(summary_path, "w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["metric", "value"])
        writer.writerow(["input_rows", len(rows)])
        writer.writerow(["kept_rows", len(kept)])
        writer.writerow(["removed_rows", len(removed)])
        writer.writerow(["available_proteins", len(available)])
        writer.writerow(["rows_with_both_sequences", len(kept)])
        writer.writerow(["rows_missing_A", sum(not item["a_sequence"] for item in audit)])
        writer.writerow(["rows_missing_B", sum(not item["b_sequence"] for item in audit)])
        for label, count in labels_before.items():
            writer.writerow([f"input_label_{label}", count])
            writer.writerow([f"filtered_label_{label}", labels_after[label]])

    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError:
        commit = "unavailable"
    write_version(args.output_dir, args.ground_truth, args.fasta, {
        "input_rows": len(rows),
        "kept_rows": len(kept),
        "removed_rows": len(removed),
        "available_proteins": len(available),
    }, commit)
    print(f"[done] input_rows={len(rows)} kept_rows={len(kept)} removed_rows={len(removed)} available_proteins={len(available)}", flush=True)


if __name__ == "__main__":
    main()
