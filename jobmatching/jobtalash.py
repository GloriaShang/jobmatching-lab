"""Reconstruct and load the JobTalash delivery graph from Harvard Dataverse V1."""

import argparse
import csv
import hashlib
import io
import re
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import numpy as np

SOURCE_DOI = "10.7910/DVN/6YLWJ1"
ARCHIVE_MEMBER = "Data/FS_del_cleaned_unique_memidjobid_anon.dta"
MEMBER_SHA256 = "228b908225d2a4d757f13c311d4656528c3239d167a4ae33a41fe7e2841f5155"
STRUCTURE_SHA256 = "b75594f2c46e09ba88e226b293e79202a0d6b4f95be3c8ed1ca94147a850ff36"
FIELDS = ("edge_id", "memid", "job_id", "delivery_day", "delivery_quarter")


def read_structure(path):
    """Return zero-based worker and job arrays, daily dates, and quarter strings.

    IDs are remapped independently by lexically sorting the source keys. Rows
    keep the canonical edge-ID order used in the research input.
    """
    content = Path(path).read_bytes()
    if hashlib.sha256(content).hexdigest() != STRUCTURE_SHA256:
        raise ValueError("Unexpected JobTalash structure checksum. Rebuild it with jobmatching.jobtalash.")
    rows = list(csv.DictReader(io.StringIO(content.decode("utf-8"))))
    workers = np.unique([row["memid"] for row in rows], return_inverse=True)[1]
    jobs = np.unique([row["job_id"] for row in rows], return_inverse=True)[1]
    delivery = np.array([row["delivery_day"] for row in rows], dtype="datetime64[D]")
    quarter = np.array([row["delivery_quarter"] for row in rows], dtype="U6")
    return workers, jobs, delivery, quarter


def rebuild_structure(raw):
    """Filter confirmed deliveries and recreate the byte-checked research input."""
    if hashlib.sha256(raw).hexdigest() != MEMBER_SHA256:
        raise ValueError("Unexpected delivery table checksum. Use JobTalash Dataverse version 1.0.")

    try:
        import pandas as pd
    except ImportError as exc:
        raise ValueError("Install requirements-jobtalash.txt to read the Stata source table.") from exc

    frame = pd.read_stata(
        io.BytesIO(raw),
        columns=["memid", "job_id", "status_delivery", "cv_del_date"],
        convert_dates=False,
        convert_categoricals=False,
        convert_missing=True,
    )

    def normalize_id(value):
        if pd.isna(value):
            return ""
        key = str(value).strip()
        if re.fullmatch(r"\d+\.0", key):
            key = key[:-2]
        return key if re.fullmatch(r"\d{3,16}", key) else ""

    for field in ("memid", "job_id"):
        frame[field] = frame[field].map(normalize_id)
    if frame.duplicated(["memid", "job_id"]).any():
        raise ValueError("Expected one row per worker and job in the released table.")
    frame["delivery_day"] = pd.to_datetime(
        pd.to_numeric(frame["cv_del_date"], errors="coerce"),
        unit="D", origin="1960-01-01", errors="coerce",
    )
    valid = (
        frame["status_delivery"].eq(1) & frame["delivery_day"].notna()
        & frame["memid"].ne("") & frame["job_id"].ne("")
    )
    structure = frame.loc[valid, ["memid", "job_id", "delivery_day"]].copy()
    structure["edge_id"] = [
        hashlib.sha256(f"{worker}|{job}".encode()).hexdigest()[:24]
        for worker, job in zip(structure["memid"], structure["job_id"], strict=True)
    ]
    structure["delivery_quarter"] = structure["delivery_day"].dt.to_period("Q").astype(str)
    structure = structure[list(FIELDS)].sort_values("edge_id")
    content = structure.to_csv(index=False, lineterminator="\n").encode("utf-8")
    if hashlib.sha256(content).hexdigest() != STRUCTURE_SHA256:
        raise ValueError("Reconstructed delivery graph differs from the canonical JobTalash input.")
    return content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--archive", type=Path, help="Harvard Dataverse Data.zip")
    source.add_argument("--delivery-dta", type=Path, help="Delivery table extracted from Data.zip")
    parser.add_argument("--output", type=Path, required=True, help="New local CSV path")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output path.")
    try:
        if args.archive:
            with ZipFile(args.archive) as archive:
                with archive.open(ARCHIVE_MEMBER) as member:
                    raw = member.read(3 * 1024 * 1024 + 1)
        else:
            with args.delivery_dta.open("rb") as member:
                raw = member.read(3 * 1024 * 1024 + 1)
        content = rebuild_structure(raw)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as output:
            output.write(content)
    except (BadZipFile, KeyError, OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Verified 8,233 JobTalash delivery edges and wrote {args.output}")


if __name__ == "__main__":
    main()
