"""
StorageProvider -- abstract interface for local and cloud storage tiers.

Phase 1 V2 rebuild: replaces all GDrive sync with explicit API calls.
Every byte moves through this interface. No side doors.

LocalProvider: hot tier (local disk)
GCSProvider:  cold tier (Google Cloud Storage, Autoclass, versioned)
"""
from __future__ import annotations

import hashlib
import logging
import shutil
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class StorageRef:
    """Unambiguous pointer to a stored object."""
    tier: str
    bucket_or_root: str
    key: str
    generation: Optional[int] = None

    @property
    def uri(self) -> str:
        if self.tier == "gcs":
            return f"gs://{self.bucket_or_root}/{self.key}#{self.generation or 'latest'}"
        return f"file://{self.bucket_or_root}/{self.key}"

    def __hash__(self) -> int:
        return hash((self.tier, self.bucket_or_root, self.key, self.generation))


@dataclass
class StorageStat:
    """File metadata returned by stat()."""
    size_bytes: int
    content_hash: str
    tier: str
    last_modified: float = field(default_factory=time.time)


class StorageProvider(ABC):
    """Abstract storage backend. Implementations: LocalProvider, GCSProvider."""

    @abstractmethod
    def put(self, local_path: Path, key: str) -> StorageRef:
        """Upload a file from local disk to this tier."""
        ...

    @abstractmethod
    def get(self, ref: StorageRef, dest: Path) -> Path:
        """Download a file from this tier to local disk."""
        ...

    @abstractmethod
    def move(self, ref: StorageRef, new_key: str) -> StorageRef:
        """Rename / move within this tier. GCS: server-side copy+delete."""
        ...

    @abstractmethod
    def delete(self, ref: StorageRef) -> None:
        """Delete an object from this tier."""
        ...

    @abstractmethod
    def exists(self, ref: StorageRef) -> bool:
        """Check if an object exists."""
        ...

    @abstractmethod
    def stat(self, ref: StorageRef) -> StorageStat:
        """Return metadata (size, hash, tier)."""
        ...

    @abstractmethod
    def stream_url(self, ref: StorageRef, ttl_s: int = 3600) -> str:
        """Return a signed/download URL for UI previews."""
        ...


class LocalProvider(StorageProvider):
    """Local filesystem storage (hot tier)."""

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root).resolve() if root else Path.home() / "Documents" / "AI-Organized"
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        safe = Path(key).name if "/" in key or "\\" in key else key
        return self.root / safe

    def _hash_file(self, path: Path) -> str:
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def put(self, local_path: Path, key: str) -> StorageRef:
        dest = self._resolve(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dest)
        logger.info(f"LocalProvider.put: {local_path} -> {dest}")
        return StorageRef(tier="local", bucket_or_root=str(self.root), key=key)

    def get(self, ref: StorageRef, dest: Path) -> Path:
        src = self._resolve(ref.key)
        if not src.exists():
            raise FileNotFoundError(f"Local object not found: {src}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return dest

    def move(self, ref: StorageRef, new_key: str) -> StorageRef:
        src = self._resolve(ref.key)
        dst = self._resolve(new_key)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return StorageRef(tier="local", bucket_or_root=str(self.root), key=new_key)

    def delete(self, ref: StorageRef) -> None:
        path = self._resolve(ref.key)
        if path.exists():
            path.unlink()

    def exists(self, ref: StorageRef) -> bool:
        return self._resolve(ref.key).exists()

    def stat(self, ref: StorageRef) -> StorageStat:
        path = self._resolve(ref.key)
        if not path.exists():
            raise FileNotFoundError(f"Local object not found: {path}")
        st = path.stat()
        return StorageStat(
            size_bytes=st.st_size,
            content_hash=self._hash_file(path),
            tier="local",
            last_modified=st.st_mtime,
        )

    def stream_url(self, ref: StorageRef, ttl_s: int = 3600) -> str:
        path = self._resolve(ref.key)
        if not path.exists():
            raise FileNotFoundError(f"Local object not found: {path}")
        return f"file://{path}"


class GCSProvider(StorageProvider):
    """
    Google Cloud Storage provider.
    Auth via Application Default Credentials (ADC).
    Assumes bucket exists with Autoclass + object versioning enabled.
    """

    def __init__(self, bucket_name: str, project: Optional[str] = None):
        self.bucket_name = bucket_name
        self.project = project
        self._client = None
        self._bucket = None

    @property
    def client(self):
        if self._client is None:
            from google.cloud import storage
            self._client = storage.Client(project=self.project)
        return self._client

    @property
    def bucket(self):
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket

    def _blob(self, key: str, generation: Optional[int] = None):
        return self.bucket.blob(key, generation=generation)

    def put(self, local_path: Path, key: str) -> StorageRef:
        blob = self._blob(key)
        blob.upload_from_filename(str(local_path))
        blob.reload()
        generation = blob.generation
        logger.info(f"GCSProvider.put: {local_path} -> gs://{self.bucket_name}/{key} (gen {generation})")
        return StorageRef(tier="gcs", bucket_or_root=self.bucket_name, key=key, generation=generation)

    def get(self, ref: StorageRef, dest: Path) -> Path:
        blob = self._blob(ref.key, ref.generation)
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(str(dest))
        logger.info(f"GCSProvider.get: gs://{self.bucket_name}/{ref.key} -> {dest}")
        return dest

    def move(self, ref: StorageRef, new_key: str) -> StorageRef:
        src_blob = self._blob(ref.key, ref.generation)
        dst_blob = self.bucket.blob(new_key)
        token = None
        while True:
            token, bytes_rewritten, total = dst_blob.rewrite(src_blob, token=token)
            if token is None:
                break
        dst_blob.reload()
        generation = dst_blob.generation
        src_blob.delete()
        logger.info(f"GCSProvider.move: {ref.key} -> {new_key} (gen {generation})")
        return StorageRef(tier="gcs", bucket_or_root=self.bucket_name, key=new_key, generation=generation)

    def delete(self, ref: StorageRef) -> None:
        blob = self._blob(ref.key, ref.generation)
        blob.delete()
        logger.info(f"GCSProvider.delete: gs://{self.bucket_name}/{ref.key}")

    def exists(self, ref: StorageRef) -> bool:
        blob = self.bucket.get_blob(ref.key, generation=ref.generation)
        return blob is not None

    def stat(self, ref: StorageRef) -> StorageStat:
        blob = self._blob(ref.key, ref.generation)
        blob.reload()
        return StorageStat(
            size_bytes=blob.size,
            content_hash=blob.md5_hash or "",
            tier="gcs",
            last_modified=blob.updated.timestamp() if blob.updated else 0,
        )

    def stream_url(self, ref: StorageRef, ttl_s: int = 3600) -> str:
        """Return a signed URL. Requires service account key; falls back to gs:// URI."""
        try:
            blob = self._blob(ref.key, ref.generation)
            return blob.generate_signed_url(expiration=ttl_s)
        except Exception as e:
            logger.warning(f"Signed URL requires service account key: {e}")
            return f"gs://{self.bucket_name}/{ref.key}?generation={ref.generation or 0}"
