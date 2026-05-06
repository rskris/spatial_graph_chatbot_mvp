"""
Download Overture Maps data for Sierra Madre, CA.

Writes one GeoParquet file per feature type to data/.
Uses the overturemaps CLI under the hood via subprocess so the
bounding box filter is applied server-side (only transfers needed data).
"""

import subprocess
import sys
from pathlib import Path

from config import BBOX, DATA_DIR, OVERTURE_TYPES


def bbox_str(b: dict) -> str:
    return f"{b['xmin']},{b['ymin']},{b['xmax']},{b['ymax']}"


def download_type(feature_type: str, out_dir: Path) -> Path:
    out_path = out_dir / f"{feature_type}.parquet"
    if out_path.exists():
        print(f"  [skip] {feature_type}.parquet already exists")
        return out_path

    print(f"  Downloading {feature_type}...")
    cmd = [
        "overturemaps", "download",
        "--bbox", bbox_str(BBOX),
        "-f", "geoparquet",
        "--type", feature_type,
        "-o", str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr}")
        raise RuntimeError(f"Download failed for {feature_type}")
    print(f"  Saved → {out_path}")
    return out_path


def main():
    out_dir = Path(DATA_DIR)
    out_dir.mkdir(exist_ok=True)

    for ftype in OVERTURE_TYPES:
        download_type(ftype, out_dir)

    print("\nAll downloads complete.")


if __name__ == "__main__":
    main()
