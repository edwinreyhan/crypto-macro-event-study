"""Turn Binance ``.zip`` files into ``.csv.gz`` files that Spark can read.

Spark reads gzip natively but **not** zip: given a zip it silently returns rows of compressed
bytes (see T10). The raw zip is left unchanged; the gzip copy goes to a separate staging folder.
"""

from __future__ import annotations

import gzip
import shutil
import zipfile
from pathlib import Path

DEFAULT_STAGING = Path("data/staging")


def staging_path(zip_path: Path, raw_root: Path, staging_root: Path = DEFAULT_STAGING) -> Path:
    """Same relative path as in ``raw_root``, with ``.zip`` replaced by ``.csv.gz``."""
    relative = zip_path.relative_to(raw_root)
    return staging_root / relative.with_suffix(".csv.gz")


def extract_to_gzip(zip_path: Path, dest: Path) -> Path:
    """Write the single CSV inside ``zip_path`` to ``dest`` as gzip. Safe to re-run."""
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n.endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"{zip_path}: expected exactly one .csv inside, found {names}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".part")
        with zf.open(names[0]) as src, gzip.open(tmp, "wb") as out:
            shutil.copyfileobj(src, out)
    tmp.replace(dest)  # only a complete file ever appears at dest
    return dest
