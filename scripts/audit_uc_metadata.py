#!/usr/bin/env python3

"""Summarize the UC SCP259 metadata needed for first-pass benchmark design."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit SCP259 metadata and print benchmark-relevant counts."
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("data/raw/uc_scp259/all.meta2.txt"),
        help="Path to all.meta2.txt",
    )
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [row for row in reader if row.get("NAME") != "TYPE"]


def print_top_counts(title: str, counts: Counter[str], limit: int = 10) -> None:
    print(title)
    for key, value in counts.most_common(limit):
        print(f"  {key}: {value}")
    print()


def main() -> None:
    args = parse_args()
    rows = load_rows(args.metadata)

    subjects = sorted({row["Subject"] for row in rows})
    samples = sorted({row["Sample"] for row in rows})
    clusters = sorted({row["Cluster"] for row in rows})

    subject_healths: dict[str, set[str]] = defaultdict(set)
    subject_samples: dict[str, set[str]] = defaultdict(set)
    subject_locations: dict[str, set[str]] = defaultdict(set)
    sample_meta: dict[str, tuple[str, str, str]] = {}

    for row in rows:
        subject = row["Subject"]
        sample = row["Sample"]
        health = row["Health"]
        location = row["Location"]

        subject_healths[subject].add(health)
        subject_samples[subject].add(sample)
        subject_locations[subject].add(location)
        sample_meta.setdefault(sample, (subject, health, location))

    healthy_subjects = sorted(
        subject for subject, healths in subject_healths.items() if healths == {"Healthy"}
    )
    uc_subjects = sorted(
        subject for subject, healths in subject_healths.items() if healths != {"Healthy"}
    )

    print("UC SCP259 metadata audit")
    print(f"metadata_path: {args.metadata}")
    print(f"cell_rows: {len(rows)}")
    print(f"subjects: {len(subjects)}")
    print(f"healthy_only_subjects: {len(healthy_subjects)}")
    print(f"uc_subjects: {len(uc_subjects)}")
    print(f"samples: {len(samples)}")
    print(f"clusters: {len(clusters)}")
    print()

    print_top_counts("cell_counts_by_health:", Counter(row["Health"] for row in rows))
    print_top_counts("cell_counts_by_location:", Counter(row["Location"] for row in rows))
    print_top_counts("top_clusters_by_cell_count:", Counter(row["Cluster"] for row in rows))

    sample_health_counts = Counter(health for _, health, _ in sample_meta.values())
    sample_location_counts = Counter(location for _, _, location in sample_meta.values())
    sample_health_location_counts = Counter(
        (health, location) for _, health, location in sample_meta.values()
    )

    print_top_counts("sample_counts_by_health:", sample_health_counts)
    print_top_counts("sample_counts_by_location:", sample_location_counts)

    print("sample_counts_by_health_and_location:")
    for (health, location), count in sorted(sample_health_location_counts.items()):
        print(f"  {health} / {location}: {count}")
    print()

    print("subject_summary:")
    for subject in subjects:
        healths = ",".join(sorted(subject_healths[subject]))
        n_samples = len(subject_samples[subject])
        locations = ",".join(sorted(subject_locations[subject]))
        print(
            f"  {subject}: healths=[{healths}] n_samples={n_samples} "
            f"locations=[{locations}]"
        )
    print()

    print("recommended_first_pass_contract:")
    print("  primary_task: donor-level Healthy vs UC")
    print("  label_rule: UC if subject has any Non-inflamed or Inflamed sample")
    print("  row_unit: donor")
    print("  split_unit: donor")
    print("  secondary_task: sample-level Non-inflamed vs Inflamed within UC")
    print("  secondary_split_rule: GroupKFold or StratifiedGroupKFold by Subject")


if __name__ == "__main__":
    main()
