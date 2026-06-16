from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Document:
    """Normalized representation of a source document.

    Every connector — regardless of source format — must return a list of
    these. The pipeline never handles raw files; it only receives Documents.
    """

    raw_content: str
    source_id: str
    source_name: str
    author: str
    timestamp: datetime
    # Values: policy | slack | email | ticket | reference
    content_type: str
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id:
            raise ValueError("Document.source_id must be non-empty")
        if not self.raw_content:
            raise ValueError(
                f"Document.raw_content must be non-empty (source_id={self.source_id!r})"
            )
        if self.timestamp is None:
            raise ValueError(
                f"Document.timestamp must be set (source_id={self.source_id!r})"
            )


class BaseConnector(ABC):
    """Contract for all data source adapters.

    Subclasses translate a raw file on disk into a list of Document objects.
    The pipeline is decoupled from file formats through this interface.
    """

    @abstractmethod
    def load(self, path: Path) -> list[Document]:
        """Read *path* and return one or more Documents.

        Implementations must raise ValueError if any returned Document has
        an empty source_id, raw_content, or a None timestamp.
        """
        ...
