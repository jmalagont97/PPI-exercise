import argparse
import csv
import datetime as dt
import hashlib
import os
import re
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
DEFAULT_INPUT = os.path.join(ROOT, "data", "ground_truth.tsv")
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "../results")
BASE_URL = "https://rest.uniprot.org/uniprotkb/stream"
DEFAULT_BATCH_SIZE = 100
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 4
DEFAULT_PAUSE = 0.2
VALID_RESIDUES = set("ACDEFGHIKLMNPQRSTVWYBXZJUO*")


def read_ids(path):
    ids = set()
    invalid_rows = []
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"uniprot_A", "uniprot_B"}
        if not required.issubset(reader.fieldnames or set()):
            raise ValueError(f"Missing columns: {sorted(required - set(reader.fieldnames or []))}")
        for row_number, row in enumerate(reader, start=2):
            for column in ("uniprot_A", "uniprot_B"):
                value = (row[column] or "").strip()
                if value:
                    ids.add(value)
                else:
                    invalid_rows.append((row_number, column))
    return sorted(ids), invalid_rows


def parse_fasta(text):
    records = {}
    header = None
    sequence = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                records[header] = "".join(sequence)
            header = line[1:].split()[0]
            sequence = []
        else:
            sequence.append(line)
    if header is not None:
        records[header] = "".join(sequence)
    return records


def accession_from_header(header):
    parts = header.split("|")
    if len(parts) >= 2 and parts[0] in {"sp", "tr"}:
        return parts[1]
    return header.split()[0]


def fetch_batch(batch, timeout, retries, pause):
    query = " OR ".join(f"accession:{accession}" for accession in batch)
    url = f"{BASE_URL}?format=fasta&query={quote(query, safe=':()')}&compressed=false"
    last_error = "unknown error"
    for attempt in range(retries + 1):
        request = Request(url, headers={"User-Agent": "PPI-exercise/exp_02"})
        try:
            with urlopen(request, timeout=timeout) as response:
                return parse_fasta(response.read().decode("utf-8")), None
        except HTTPError as error:
            last_error = f"HTTP {error.code}"
            if error.code not in {408, 425, 429, 500, 502, 503, 504} or attempt == retries:
                return {}, last_error
            retry_after = error.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
        except (URLError, TimeoutError) as error:
            last_error = type(error).__name__
            if attempt == retries:
                return {}, last_error
            delay = 2**attempt
        time.sleep(delay)
    return {}, last_error


def write_outputs(output_dir, ids, sequences, statuses, input_path, parameters):
    os.makedirs(output_dir, exist_ok=True)
    fasta_path = os.path.join(output_dir, "sequences.fasta")
    audit_path = os.path.join(output_dir, "audit.tsv")
    missing_path = os.path.join(output_dir, "missing_ids.tsv")
    with open(fasta_path, "w") as handle:
        for accession in ids:
            if accession in sequences:
                sequence = sequences[accession]
                handle.write(f">{accession}\n")
                for start in range(0, len(sequence), 80):
                    handle.write(sequence[start:start + 80] + "\n")
    with open(audit_path, "w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["id", "status", "length", "sequence_sha256", "reason"])
        for accession in ids:
            sequence = sequences.get(accession, "")
            status, reason = statuses[accession]
            writer.writerow([accession, status, len(sequence), hashlib.sha256(sequence.encode()).hexdigest() if sequence else "", reason])
    with open(missing_path, "w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["id", "reason"])
        for accession in ids:
            if accession not in sequences:
                writer.writerow([accession, statuses[accession][1]])
    source_sha = hashlib.sha256(open(input_path, "rb").read()).hexdigest()
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError:
        commit = "unavailable"
    with open(os.path.join(output_dir, "version.txt"), "w") as handle:
        handle.write(f"date_utc: {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M:%S UTC}\n")
        handle.write(f"input: {os.path.relpath(input_path, ROOT)}\n")
        handle.write(f"input_sha256: {source_sha}\n")
        handle.write(f"git_commit: {commit}\n")
        for key, value in parameters.items():
            handle.write(f"{key}: {value}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--pause", type=float, default=DEFAULT_PAUSE)
    parser.add_argument("--limit", type=int, default=0, help="limit IDs for smoke tests; 0 means all")
    args = parser.parse_args()
    if args.batch_size < 1 or args.retries < 0:
        raise ValueError("batch-size must be positive and retries must be non-negative")
    ids, invalid_rows = read_ids(args.input)
    if args.limit < 0:
        raise ValueError("limit must be non-negative")
    if args.limit:
        ids = ids[:args.limit]
    sequences = {}
    statuses = {accession: ("pending", "") for accession in ids}
    for offset in range(0, len(ids), args.batch_size):
        batch = ids[offset:offset + args.batch_size]
        records, error = fetch_batch(batch, args.timeout, args.retries, args.pause)
        parsed = {}
        for header, sequence in records.items():
            accession = accession_from_header(header)
            if accession in batch:
                parsed[accession] = re.sub(r"\s+", "", sequence).upper()
        for accession in batch:
            sequence = parsed.get(accession, "")
            invalid = sorted(set(sequence) - VALID_RESIDUES) if sequence else []
            if sequence and not invalid:
                sequences[accession] = sequence
                statuses[accession] = ("retrieved", "")
            elif error:
                statuses[accession] = ("error", error)
            elif not sequence:
                statuses[accession] = ("missing", "not returned by UniProt")
            else:
                statuses[accession] = ("invalid", f"invalid residues: {','.join(invalid)}")
        recovered = sum(accession in sequences for accession in batch)
        print(f"[batch] {offset + 1}-{offset + len(batch)}/{len(ids)} recovered={recovered}", flush=True)
        if offset + args.batch_size < len(ids):
            time.sleep(args.pause)
    write_outputs(args.output_dir, ids, sequences, statuses, args.input, {
        "source_url": BASE_URL,
        "batch_size": args.batch_size,
        "timeout_seconds": args.timeout,
        "retries": args.retries,
        "pause_seconds": args.pause,
        "requested_ids": len(ids),
        "limit": args.limit,
        "recovered_ids": len(sequences),
        "invalid_input_rows": len(invalid_rows),
    })
    print(f"[done] requested={len(ids)} recovered={len(sequences)} missing_or_error={len(ids) - len(sequences)}", flush=True)


if __name__ == "__main__":
    main()
