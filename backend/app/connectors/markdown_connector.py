from datetime import datetime, timezone
from pathlib import Path

from app.connectors.base import BaseConnector, Document


class MarkdownConnector(BaseConnector):
    """Reads a single Markdown file and returns one Document."""

    def load(self, path: Path) -> list[Document]:
        raw = path.read_text(encoding="utf-8")

        source_name = path.stem.replace("_", " ").title()
        for line in raw.splitlines():
            if line.startswith("# "):
                source_name = line[2:].strip()
                break

        author = "company"
        for line in raw.splitlines():
            if "**Owner:**" in line:
                author = line.split("**Owner:**")[-1].strip().lstrip(",").strip()
                break

        mtime = path.stat().st_mtime
        timestamp = datetime.fromtimestamp(mtime, tz=timezone.utc)

        return [
            Document(
                raw_content=raw,
                source_id=f"policy:{path.stem}",
                source_name=source_name,
                author=author,
                timestamp=timestamp,
                content_type="policy",
                metadata={"filename": path.name},
            )
        ]
