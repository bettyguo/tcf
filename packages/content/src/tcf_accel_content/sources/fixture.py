"""JSONL-backed fixture source.

`FixtureSource` reads a JSONL file where every line carries a
`RawAsset`-shaped dict (`kind`, `source`, `source_id`, `license`,
`fetched_at`, and either `text` or `bytes_path` depending on `kind`).
It's used:

- In tests, to drive the pipeline end-to-end without network access.
- As the operator-tier interface: ingest scripts write JSONL manifests
  under ``data/operator/<source>/manifest.jsonl`` and the loader
  consumes them through this same module.

The fixture file itself is *not* in the redistribution allowlist —
license compatibility is determined per-record by the record's
``license`` field, and the loader's license gate filters before
ingestion (see `quality/license_check.py`).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from tcf_accel_content.types import RawAsset


@dataclass(frozen=True)
class FixtureSource:
    r"""A `Source` backed by a JSONL manifest file on disk.

    Each line of `manifest_path` is a JSON object with the keys of
    `RawAsset` (``fetched_at`` may be either an ISO-8601 string or
    omitted, in which case it defaults to the UTC epoch). Bytes
    payloads (``kind="audio"``) reference the audio file via
    ``bytes_path``, resolved relative to the manifest.

    Example:
        >>> import json
        >>> from pathlib import Path
        >>> from tempfile import TemporaryDirectory
        >>> with TemporaryDirectory() as td:
        ...     p = Path(td) / "m.jsonl"
        ...     _ = p.write_text(json.dumps({
        ...         "kind": "text", "source": "wikisource_fr",
        ...         "source_id": "1", "license": "CC-BY-SA-4.0",
        ...         "fetched_at": "2026-05-27T00:00:00+00:00",
        ...         "text": "Bonjour le monde.",
        ...     }) + "\n", encoding="utf-8")
        ...     s = FixtureSource(
        ...         name="wikisource_fr", license="CC-BY-SA-4.0",
        ...         redistributable=True, manifest_path=p,
        ...     )
        ...     assets = list(s.iter_assets())
        >>> len(assets)
        1
        >>> assets[0].text
        'Bonjour le monde.'

    Complexity: O(N) over the manifest, streamed one line at a time.
    """

    name: str
    license: str
    redistributable: bool
    manifest_path: Path

    def iter_assets(
        self,
        *,
        limit: int | None = None,
        since: datetime | None = None,
    ) -> Iterator[RawAsset]:
        """Yield each record in the manifest as a `RawAsset`.

        Args:
            limit: Maximum number of records to yield.
            since: Yield only records with ``fetched_at >= since``.

        Yields:
            `RawAsset` instances. Audio records resolve their
            ``bytes_path`` relative to the manifest's parent dir.

        Raises:
            FileNotFoundError: if the manifest does not exist.
            ValueError: on malformed JSON or a record missing required
                fields.
        """
        if not self.manifest_path.is_file():
            raise FileNotFoundError(self.manifest_path)
        yielded = 0
        manifest_dir = self.manifest_path.parent
        for lineno, raw_line in enumerate(
            self.manifest_path.read_text(encoding="utf-8").splitlines(), start=1,
        ):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                msg = f"{self.manifest_path}:{lineno}: invalid JSON: {exc}"
                raise ValueError(msg) from exc
            asset = _record_to_asset(record, manifest_dir=manifest_dir)
            if since is not None and asset.fetched_at < since:
                continue
            yield asset
            yielded += 1
            if limit is not None and yielded >= limit:
                return


def _record_to_asset(
    record: dict[str, object], *, manifest_dir: Path,
) -> RawAsset:
    """Build a `RawAsset` from a manifest record, validating shape.

    Raises:
        ValueError: if a required field is missing or wrong-typed.
    """
    required = ("kind", "source", "source_id", "license")
    for k in required:
        if k not in record:
            raise ValueError(f"manifest record missing required field {k!r}: {record}")
    kind = record["kind"]
    if kind not in {"audio", "text"}:
        raise ValueError(f"manifest record has invalid kind={kind!r}")
    fetched_at_raw = record.get("fetched_at")
    fetched_at = (
        datetime.fromisoformat(fetched_at_raw)
        if isinstance(fetched_at_raw, str)
        else _epoch()
    )
    bytes_path_raw = record.get("bytes_path")
    bytes_path = (
        (manifest_dir / bytes_path_raw).resolve()
        if isinstance(bytes_path_raw, str)
        else None
    )
    return RawAsset(
        kind=kind,
        source=str(record["source"]),
        source_id=str(record["source_id"]),
        license=str(record["license"]),
        fetched_at=fetched_at,
        text=record.get("text") if isinstance(record.get("text"), str) else None,
        bytes_path=bytes_path,
        ground_truth_transcript=record.get("ground_truth_transcript")
        if isinstance(record.get("ground_truth_transcript"), str)
        else None,
        extra={k: v for k, v in record.items() if k not in {
            "kind", "source", "source_id", "license", "fetched_at",
            "text", "bytes_path", "ground_truth_transcript",
        }},
    )


def _epoch() -> datetime:
    """Return UTC epoch as the default fetched_at for records lacking one."""
    return datetime.fromtimestamp(0, tz=UTC)


__all__ = ["FixtureSource"]
