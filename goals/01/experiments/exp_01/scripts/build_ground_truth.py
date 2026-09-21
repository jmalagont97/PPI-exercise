import csv, random, hashlib, subprocess, datetime, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
SRC = os.path.join(ROOT, "data/A.thaliana_interactome.txt")
OUT_DIR = os.path.join(ROOT, "goals/01/experiments/exp_01/results")
SEED, TAXID, DIRECT = 42, "3702", "MI:0407"

def first_uniprot(field):
    for tok in field.split("|"):
        if tok.startswith("uniprotkb:"):
            return tok.split(":")[1].split("(")[0]
    return None

rows = list(csv.DictReader(open(SRC), delimiter="\t"))
all_pairs, direct_pairs, pair_meta, locus = set(), set(), {}, {}
n_ar = 0
for x in rows:
    if TAXID not in x["Taxid interactor A"] or TAXID not in x["Taxid interactor B"]:
        continue
    a, b = first_uniprot(x["#ID(s) interactor A"]), first_uniprot(x["ID(s) interactor B"])
    if not a or not b:
        continue
    n_ar += 1
    pair = (min(a, b), max(a, b))
    all_pairs.add(pair)
    score = float(x["Confidence value(s)"].split(":")[-1]) if x["Confidence value(s)"] else 0.0
    methods = {m.split('"')[1] for m in x["Interaction detection method(s)"].split("|") if '"' in m}
    types = {m.split('"')[1] for m in x["Interaction type(s)"].split("|") if '"' in m}
    m = pair_meta.setdefault(pair, {"score": 0.0, "n": 0, "methods": set(), "types": set()})
    m["score"], m["n"] = max(m["score"], score), m["n"] + 1
    m["methods"] |= methods
    m["types"] |= types
    if DIRECT in x["Interaction type(s)"]:
        direct_pairs.add(pair)
    for field, key in [("Alias(es) interactor A", a), ("Alias(es) interactor B", b)]:
        for tok in x[field].split("|"):
            if "(locus name)" in tok:
                locus[key] = tok.split(":")[1].split("(")[0]
print(f"[parse] {n_ar} filas {TAXID}/{TAXID} | {len(all_pairs)} pares evidencia | {len(direct_pairs)} directos")

proteins = sorted({p for pair in all_pairs for p in pair})
rng = random.Random(SEED)
negatives = set()
while len(negatives) < len(direct_pairs):
    a, b = rng.sample(proteins, 2)
    pair = (min(a, b), max(a, b))
    if pair not in all_pairs:
        negatives.add(pair)
print(f"[sample] {len(negatives)} negativos, colisiones={len(negatives & all_pairs)}")

assert len(direct_pairs) == 1424, f"positivos={len(direct_pairs)}"
assert len(negatives) == 1424, f"negativos={len(negatives)}"
assert not (negatives & all_pairs), "colision negativo-evidencia"
assert not (negatives & direct_pairs), "colision negativo-directo"
assert len(negatives | direct_pairs) == 2848, "duplicados en union"

os.makedirs(OUT_DIR, exist_ok=True)
tsv = os.path.join(OUT_DIR, "ground_truth.tsv")
with open(tsv, "w", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n")
    w.writerow(["uniprot_A", "uniprot_B", "locus_A", "locus_B", "label",
                "interaction_type", "miscore_max", "n_evidences", "methods"])
    for pair in sorted(direct_pairs):
        m = pair_meta[pair]
        w.writerow([pair[0], pair[1], locus.get(pair[0], ""), locus.get(pair[1], ""),
                    "positive", DIRECT, m["score"], m["n"], ";".join(sorted(m["methods"]))])
    for pair in sorted(negatives):
        w.writerow([pair[0], pair[1], locus.get(pair[0], ""), locus.get(pair[1], ""),
                    "negative", "none", "NA", 0, "NA"])
print(f"[write] {tsv} {len(direct_pairs) + len(negatives)} filas")

sha = hashlib.sha256(open(SRC, "rb").read()).hexdigest()
commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                        capture_output=True, text=True).stdout.strip()
utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
open(os.path.join(OUT_DIR, "version.txt"), "w").write(
    f"date: {utc}\nseed: {SEED}\nsource_sha256: {sha}\ngit_commit: {commit}\n")
print(f"[version] commit={commit} sha256={sha[:12]}...")
