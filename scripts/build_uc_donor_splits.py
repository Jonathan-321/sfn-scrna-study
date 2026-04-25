#!/usr/bin/env python3

"""Build deterministic donor-level splits for the UC SCP259 benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedKFold


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate locked donor-level CV folds for the UC benchmark."
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("data/processed/uc_scp259/donor_metadata.tsv"),
        help="Path to donor_metadata.tsv",
    )
    parser.add_argument(
        "--id-col",
        default="donor_id",
        help="Donor identifier column.",
    )
    parser.add_argument(
        "--label-col",
        default="donor_label",
        help="Label column in donor metadata.",
    )
    parser.add_argument(
        "--positive-label",
        default="UC",
        help="Label treated as the positive class.",
    )
    parser.add_argument(
        "--task-name",
        default="donor_healthy_vs_uc",
        help="Logical task name recorded in the output JSON.",
    )
    parser.add_argument("--n-splits", type=int, default=5, help="Number of CV folds.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for fold generation.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/uc_scp259/donor_healthy_vs_uc_folds.json"),
        help="Output JSON path.",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    donor_meta = pd.read_csv(args.metadata, sep="\t")

    for column in (args.id_col, args.label_col):
        if column not in donor_meta.columns:
            raise ValueError(f"Missing required column '{column}' in {args.metadata}")

    donor_meta = donor_meta[[args.id_col, args.label_col]].drop_duplicates().copy()
    if donor_meta[args.id_col].duplicated().any():
        raise ValueError("Donor IDs must be unique in donor metadata.")

    y = (donor_meta[args.label_col] == args.positive_label).astype(int)
    ids = donor_meta[args.id_col].astype(str).to_numpy()

    class_counts = y.value_counts().to_dict()
    minority_count = min(class_counts.values())
    if args.n_splits > minority_count:
        raise ValueError(
            f"Cannot build {args.n_splits} folds because the minority class only has "
            f"{minority_count} donors."
        )

    splitter = StratifiedKFold(
        n_splits=args.n_splits,
        shuffle=True,
        random_state=args.seed,
    )

    folds = []
    for fold_idx, (train_idx, test_idx) in enumerate(splitter.split(ids, y)):
        y_train = y.iloc[train_idx]
        y_test = y.iloc[test_idx]
        folds.append(
            {
                "fold": int(fold_idx),
                "train_ids": ids[train_idx].tolist(),
                "test_ids": ids[test_idx].tolist(),
                "train_size": int(len(train_idx)),
                "test_size": int(len(test_idx)),
                "train_positive_rate": float(y_train.mean()),
                "test_positive_rate": float(y_test.mean()),
            }
        )

    payload = {
        "version": "1.0",
        "created_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "task_name": args.task_name,
        "input_path": str(args.metadata),
        "input_sha256": sha256_file(args.metadata),
        "id_col": args.id_col,
        "label_col": args.label_col,
        "positive_label": args.positive_label,
        "row_count": int(len(donor_meta)),
        "class_counts": {
            "negative": int((y == 0).sum()),
            "positive": int((y == 1).sum()),
        },
        "n_splits": int(args.n_splits),
        "seed": int(args.seed),
        "folds": folds,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"[ok] Wrote donor splits: {args.output}")
    print(
        f"[ok] donors={payload['row_count']} positive={payload['class_counts']['positive']} "
        f"negative={payload['class_counts']['negative']}"
    )


if __name__ == "__main__":
    main()
