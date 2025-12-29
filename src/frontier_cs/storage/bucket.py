"""
Bucket-based storage for evaluation results.

Each pair's result is stored as a separate JSON file in the bucket:
  s3://bucket/results/{solution}:{problem}.json

This approach:
- Supports concurrent workers (each writes own file)
- Preserves results across runs (unchanged files stay in bucket)
- Enables incremental sync (only download changed files)
"""

import json
import logging
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class PairResultData:
    """Result data for a single pair stored in bucket."""

    pair_id: str  # "solution:problem"
    score: Optional[float] = None
    status: str = "pending"  # pending, running, success, error, timeout, skipped
    message: Optional[str] = None
    duration_seconds: Optional[float] = None
    timestamp: Optional[str] = None
    logs: Optional[str] = None
    solution_hash: Optional[str] = None  # Hash of solution file
    problem_hash: Optional[str] = None   # Hash of problem directory

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, data: str) -> "PairResultData":
        """Deserialize from JSON string."""
        parsed = json.loads(data)
        return cls(**parsed)

    @classmethod
    def from_file(cls, path: Path) -> "PairResultData":
        """Load from a JSON file."""
        return cls.from_json(path.read_text(encoding="utf-8"))


class BucketStorage:
    """
    Storage backend using S3/GCS buckets.

    Usage:
        storage = BucketStorage("s3://my-bucket/frontier-results")

        # Sync results from bucket to local cache
        storage.sync_from_bucket()

        # Read all results
        results = storage.read_all_results()

        # Get bucket path for SkyPilot file_mounts
        bucket_path = storage.get_bucket_results_path()
    """

    def __init__(
        self,
        bucket_url: str,
        local_cache: Optional[Path] = None,
    ):
        """
        Initialize bucket storage.

        Args:
            bucket_url: Bucket URL (s3://bucket/path or gs://bucket/path)
            local_cache: Local cache directory (default: .cache/frontier-results)
        """
        self.bucket_url = bucket_url.rstrip("/")
        self.local_cache = local_cache or Path.home() / ".cache" / "frontier-results"
        self.local_cache.mkdir(parents=True, exist_ok=True)

        # Parse bucket URL
        parsed = urlparse(bucket_url)
        self.scheme = parsed.scheme  # s3 or gs
        self.bucket_name = parsed.netloc
        self.prefix = parsed.path.lstrip("/")

        if self.scheme not in ("s3", "gs"):
            raise ValueError(f"Unsupported bucket scheme: {self.scheme}. Use s3:// or gs://")

    @property
    def results_url(self) -> str:
        """Full URL to results directory in bucket."""
        return f"{self.bucket_url}/results"

    def get_pair_filename(self, pair_id: str) -> str:
        """Get filename for a pair result (solution:problem -> solution__problem.json)."""
        # Replace : with __ to avoid path issues
        safe_id = pair_id.replace(":", "__")
        return f"{safe_id}.json"

    def get_pair_bucket_path(self, pair_id: str) -> str:
        """Get full bucket path for a pair's result."""
        filename = self.get_pair_filename(pair_id)
        return f"{self.results_url}/{filename}"

    def get_local_path(self, pair_id: str) -> Path:
        """Get local cache path for a pair's result."""
        filename = self.get_pair_filename(pair_id)
        return self.local_cache / "results" / filename

    def sync_from_bucket(self, size_only: bool = True) -> int:
        """
        Sync results from bucket to local cache.

        Uses --size-only to only download changed files (much faster for large batches).

        Args:
            size_only: Use --size-only flag for incremental sync

        Returns:
            Number of files in local cache after sync
        """
        local_results = self.local_cache / "results"
        local_results.mkdir(parents=True, exist_ok=True)

        if self.scheme == "s3":
            cmd = ["aws", "s3", "sync", self.results_url, str(local_results)]
            if size_only:
                cmd.append("--size-only")
        else:  # gs
            cmd = ["gsutil", "-m", "rsync"]
            if size_only:
                cmd.append("-c")  # checksum-based for GCS
            cmd.extend([self.results_url, str(local_results)])

        try:
            logger.info(f"Syncing from {self.results_url} to {local_results}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                # Non-fatal: bucket might be empty
                if "NoSuchBucket" in result.stderr or "BucketNotFound" in result.stderr:
                    logger.warning(f"Bucket not found: {self.bucket_url}")
                    return 0
                elif "NoSuchKey" in result.stderr or "not found" in result.stderr.lower():
                    logger.info("No results in bucket yet")
                    return 0
                else:
                    logger.warning(f"Sync warning: {result.stderr}")

            # Count files
            count = len(list(local_results.glob("*.json")))
            logger.info(f"Synced {count} result files to local cache")
            return count

        except subprocess.TimeoutExpired:
            logger.error("Sync timed out")
            return 0
        except FileNotFoundError:
            logger.error(f"CLI tool not found for {self.scheme}")
            return 0

    def sync_to_bucket(self, pair_id: str, result: PairResultData) -> bool:
        """
        Upload a single result to the bucket.

        Args:
            pair_id: Pair ID (solution:problem)
            result: Result data to upload

        Returns:
            True if upload succeeded
        """
        local_path = self.get_local_path(pair_id)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to local cache first
        local_path.write_text(result.to_json(), encoding="utf-8")

        # Upload to bucket
        bucket_path = self.get_pair_bucket_path(pair_id)

        if self.scheme == "s3":
            cmd = ["aws", "s3", "cp", str(local_path), bucket_path]
        else:
            cmd = ["gsutil", "cp", str(local_path), bucket_path]

        try:
            subprocess.run(cmd, capture_output=True, timeout=60, check=True)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.error(f"Failed to upload {pair_id}: {e}")
            return False

    def read_result(self, pair_id: str) -> Optional[PairResultData]:
        """
        Read a result from local cache.

        Call sync_from_bucket() first to ensure cache is up to date.

        Args:
            pair_id: Pair ID (solution:problem)

        Returns:
            Result data or None if not found
        """
        local_path = self.get_local_path(pair_id)
        if not local_path.exists():
            return None

        try:
            return PairResultData.from_file(local_path)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse result {pair_id}: {e}")
            return None

    def read_all_results(self) -> Dict[str, PairResultData]:
        """
        Read all results from local cache.

        Call sync_from_bucket() first to ensure cache is up to date.

        Returns:
            Dict mapping pair_id to result data
        """
        results = {}
        results_dir = self.local_cache / "results"

        if not results_dir.exists():
            return results

        for path in results_dir.glob("*.json"):
            try:
                result = PairResultData.from_file(path)
                results[result.pair_id] = result
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse {path}: {e}")

        return results

    def get_skypilot_file_mount(self) -> dict:
        """
        Get SkyPilot file_mounts configuration for writing results to bucket.

        This mounts the bucket's results directory with write access.

        Returns:
            Dict for SkyPilot file_mounts
        """
        return {
            "~/results_bucket": {
                "source": self.results_url,
                "mode": "MOUNT",
            }
        }

    def list_bucket_results(self) -> List[str]:
        """
        List all result files in the bucket.

        Returns:
            List of pair IDs
        """
        if self.scheme == "s3":
            cmd = ["aws", "s3", "ls", f"{self.results_url}/"]
        else:
            cmd = ["gsutil", "ls", f"{self.results_url}/"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                return []

            pair_ids = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                # Parse filename from listing
                parts = line.split()
                filename = parts[-1] if parts else ""
                if filename.endswith(".json"):
                    # Convert filename back to pair_id
                    pair_id = filename.replace("__", ":").replace(".json", "")
                    pair_ids.append(pair_id)

            return pair_ids

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def delete_result(self, pair_id: str) -> bool:
        """
        Delete a result from both local cache and bucket.

        Args:
            pair_id: Pair ID to delete

        Returns:
            True if deletion succeeded
        """
        # Delete local
        local_path = self.get_local_path(pair_id)
        if local_path.exists():
            local_path.unlink()

        # Delete from bucket
        bucket_path = self.get_pair_bucket_path(pair_id)

        if self.scheme == "s3":
            cmd = ["aws", "s3", "rm", bucket_path]
        else:
            cmd = ["gsutil", "rm", bucket_path]

        try:
            subprocess.run(cmd, capture_output=True, timeout=60)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False
