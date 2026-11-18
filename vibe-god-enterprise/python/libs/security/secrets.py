"""
Secrets Management with Multiple Backend Support
Supports: SOPS, HashiCorp Vault, AWS Secrets Manager, Environment Variables, Local Files
"""
import os
import json
import base64
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache

import yaml
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


@dataclass
class SecretMetadata:
    """Metadata for a secret."""
    key: str
    version: int
    created_at: str
    updated_at: str
    labels: Dict[str, str]


class SecretsBackend(ABC):
    """Abstract base class for secrets backends."""

    @abstractmethod
    async def get_secret(self, key: str) -> Optional[str]:
        """Get a secret value."""
        pass

    @abstractmethod
    async def set_secret(self, key: str, value: str, metadata: Optional[Dict[str, str]] = None) -> None:
        """Set a secret value."""
        pass

    @abstractmethod
    async def delete_secret(self, key: str) -> None:
        """Delete a secret."""
        pass

    @abstractmethod
    async def list_secrets(self, prefix: str = "") -> List[str]:
        """List secret keys."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check backend health."""
        pass


class EnvironmentBackend(SecretsBackend):
    """Environment variables backend (highest priority)."""

    async def get_secret(self, key: str) -> Optional[str]:
        # Convert key to env var format (e.g., db.password -> DB_PASSWORD)
        env_key = key.upper().replace(".", "_").replace("-", "_")
        return os.getenv(env_key)

    async def set_secret(self, key: str, value: str, metadata: Optional[Dict[str, str]] = None) -> None:
        raise NotImplementedError("Environment backend is read-only")

    async def delete_secret(self, key: str) -> None:
        raise NotImplementedError("Environment backend is read-only")

    async def list_secrets(self, prefix: str = "") -> List[str]:
        env_prefix = prefix.upper().replace(".", "_").replace("-", "_")
        return [k for k in os.environ.keys() if k.startswith(env_prefix)]

    async def health_check(self) -> bool:
        return True


class FileBackend(SecretsBackend):
    """Encrypted file backend (for local development)."""

    def __init__(self, path: str, encryption_key: Optional[bytes] = None):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self._fernet = self._init_fernet(encryption_key)

    def _init_fernet(self, key: Optional[bytes]) -> Fernet:
        if key:
            return Fernet(key)
        # Derive key from environment or generate
        env_key = os.getenv("SECRETS_ENCRYPTION_KEY")
        if env_key:
            return Fernet(env_key.encode() if isinstance(env_key, str) else env_key)
        # Generate a key (not persistent - for dev only)
        return Fernet(Fernet.generate_key())

    def _get_file_path(self, key: str) -> Path:
        safe_key = key.replace("/", "_").replace(".", "_")
        return self.path / f"{safe_key}.enc"

    async def get_secret(self, key: str) -> Optional[str]:
        file_path = self._get_file_path(key)
        if not file_path.exists():
            return None
        try:
            encrypted = file_path.read_bytes()
            return self._fernet.decrypt(encrypted).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt secret {key}: {e}")
            return None

    async def set_secret(self, key: str, value: str, metadata: Optional[Dict[str, str]] = None) -> None:
        file_path = self._get_file_path(key)
        encrypted = self._fernet.encrypt(value.encode())
        file_path.write_bytes(encrypted)
        # Set restrictive permissions
        file_path.chmod(0o600)

    async def delete_secret(self, key: str) -> None:
        file_path = self._get_file_path(key)
        if file_path.exists():
            file_path.unlink()

    async def list_secrets(self, prefix: str = "") -> List[str]:
        prefix_safe = prefix.replace("/", "_").replace(".", "_")
        return [
            f.stem.replace("_", ".").replace("_", "/")
            for f in self.path.glob(f"{prefix_safe}*.enc")
        ]

    async def health_check(self) -> bool:
        return self.path.exists() and os.access(self.path, os.R_OK | os.W_OK)


class SOPSFileBackend(SecretsBackend):
    """SOPS-encrypted YAML/JSON file backend (for GitOps)."""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self._cache: Dict[str, Any] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        if not self.file_path.exists():
            self._cache = {}
            self._loaded = True
            return
        try:
            import subprocess
            result = subprocess.run(
                ["sops", "-d", str(self.file_path)],
                capture_output=True,
                text=True,
                check=True
            )
            if self.file_path.suffix in [".yaml", ".yml"]:
                self._cache = yaml.safe_load(result.stdout) or {}
            else:
                self._cache = json.loads(result.stdout)
        except Exception as e:
            logger.error(f"Failed to load SOPS file: {e}")
            self._cache = {}
        self._loaded = True

    async def get_secret(self, key: str) -> Optional[str]:
        self._load()
        # Navigate nested keys (e.g., "db.password" -> cache["db"]["password"])
        keys = key.split(".")
        value = self._cache
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        return str(value) if value is not None else None

    async def set_secret(self, key: str, value: str, metadata: Optional[Dict[str, str]] = None) -> None:
        raise NotImplementedError("SOPS backend is read-only (encrypt externally)")

    async def delete_secret(self, key: str) -> None:
        raise NotImplementedError("SOPS backend is read-only")

    async def list_secrets(self, prefix: str = "") -> List[str]:
        self._load()
        results = []

        def flatten(d: Dict, parent_key: str = "") -> None:
            for k, v in d.items():
                new_key = f"{parent_key}.{k}" if parent_key else k
                if isinstance(v, dict):
                    flatten(v, new_key)
                else:
                    if not prefix or new_key.startswith(prefix):
                        results.append(new_key)

        flatten(self._cache)
        return results

    async def health_check(self) -> bool:
        try:
            import subprocess
            result = subprocess.run(["sops", "--version"], capture_output=True)
            return result.returncode == 0 and self.file_path.exists()
        except Exception:
            return False


class VaultBackend(SecretsBackend):
    """HashiCorp Vault backend."""

    def __init__(self, url: str, token: str, mount_point: str = "secret"):
        self.url = url.rstrip("/")
        self.token = token
        self.mount_point = mount_point
        self._session = None

    async def _get_session(self):
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession(
                headers={"X-Vault-Token": self.token}
            )
        return self._session

    async def get_secret(self, key: str) -> Optional[str]:
        session = await self._get_session()
        path = f"{self.url}/v1/{self.mount_point}/data/{key}"
        try:
            async with session.get(path) as resp:
                if resp.status == 404:
                    return None
                resp.raise_for_status()
                data = await resp.json()
                return data.get("data", {}).get("data", {}).get(key.split("/")[-1])
        except Exception as e:
            logger.error(f"Vault get_secret failed: {e}")
            return None

    async def set_secret(self, key: str, value: str, metadata: Optional[Dict[str, str]] = None) -> None:
        session = await self._get_session()
        path = f"{self.url}/v1/{self.mount_point}/data/{key}"
        payload = {"data": {key.split("/")[-1]: value}}
        if metadata:
            payload["metadata"] = metadata
        try:
            async with session.post(path, json=payload) as resp:
                resp.raise_for_status()
        except Exception as e:
            logger.error(f"Vault set_secret failed: {e}")
            raise

    async def delete_secret(self, key: str) -> None:
        session = await self._get_session()
        path = f"{self.url}/v1/{self.mount_point}/metadata/{key}"
        try:
            async with session.delete(path) as resp:
                resp.raise_for_status()
        except Exception as e:
            logger.error(f"Vault delete_secret failed: {e}")
            raise

    async def list_secrets(self, prefix: str = "") -> List[str]:
        session = await self._get_session()
        path = f"{self.url}/v1/{self.mount_point}/metadata/{prefix}?list=true"
        try:
            async with session.get(path) as resp:
                if resp.status == 404:
                    return []
                resp.raise_for_status()
                data = await resp.json()
                return data.get("data", {}).get("keys", [])
        except Exception as e:
            logger.error(f"Vault list_secrets failed: {e}")
            return []

    async def health_check(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(f"{self.url}/v1/sys/health") as resp:
                return resp.status in [200, 429, 472]  # 429=standby, 472=sealed
        except Exception:
            return False

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None


class AWSSecretsManagerBackend(SecretsBackend):
    """AWS Secrets Manager backend."""

    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self._client = None

    async def _get_client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client("secretsmanager", region_name=self.region)
        return self._client

    async def get_secret(self, key: str) -> Optional[str]:
        client = await self._get_client()
        try:
            response = client.get_secret_value(SecretId=key)
            return response.get("SecretString")
        except client.exceptions.ResourceNotFoundException:
            return None
        except Exception as e:
            logger.error(f"AWS Secrets Manager get_secret failed: {e}")
            return None

    async def set_secret(self, key: str, value: str, metadata: Optional[Dict[str, str]] = None) -> None:
        client = await self._get_client()
        try:
            client.create_secret(Name=key, SecretString=value, Tags=[{"Key": k, "Value": v} for k, v in (metadata or {}).items()])
        except client.exceptions.ResourceExistsException:
            client.update_secret(SecretId=key, SecretString=value)
        except Exception as e:
            logger.error(f"AWS Secrets Manager set_secret failed: {e}")
            raise

    async def delete_secret(self, key: str) -> None:
        client = await self._get_client()
        try:
            client.delete_secret(SecretId=key, ForceDeleteWithoutRecovery=True)
        except Exception as e:
            logger.error(f"AWS Secrets Manager delete_secret failed: {e}")
            raise

    async def list_secrets(self, prefix: str = "") -> List[str]:
        client = await self._get_client()
        try:
            paginator = client.get_paginator("list_secrets")
            results = []
            for page in paginator.paginate(Filters=[{"Key": "name", "Values": [f"{prefix}*"]}]):
                for secret in page.get("SecretList", []):
                    results.append(secret["Name"])
            return results
        except Exception as e:
            logger.error(f"AWS Secrets Manager list_secrets failed: {e}")
            return []

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            client.list_secrets(MaxResults=1)
            return True
        except Exception:
            return False


class SecretsManager:
    """
    Unified secrets manager with fallback chain.
    Priority: Environment > Vault > AWS > SOPS > File > Default
    """

    def __init__(self):
        self.backends: List[SecretsBackend] = []
        self._default_values: Dict[str, str] = {}
        self._cache: Dict[str, str] = {}
        self._cache_ttl = 300  # 5 minutes

    def add_backend(self, backend: SecretsBackend, priority: int = 0) -> None:
        """Add a backend with priority (higher = checked first)."""
        self.backends.append((priority, backend))
        self.backends.sort(key=lambda x: -x[0])

    def set_default(self, key: str, value: str) -> None:
        """Set a default value (lowest priority)."""
        self._default_values[key] = value

    async def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret with fallback chain."""
        # Check cache first
        if key in self._cache:
            return self._cache[key]

        # Check backends in priority order
        for _, backend in self.backends:
            try:
                value = await backend.get_secret(key)
                if value is not None:
                    self._cache[key] = value
                    return value
            except Exception as e:
                logger.warning(f"Backend {type(backend).__name__} failed for {key}: {e}")
                continue

        # Check defaults
        if key in self._default_values:
            return self._default_values[key]

        return default

    async def get_secret_required(self, key: str) -> str:
        """Get secret, raise if not found."""
        value = await self.get_secret(key)
        if value is None:
            raise ValueError(f"Required secret not found: {key}")
        return value

    async def get_json_secret(self, key: str, default: Optional[Dict] = None) -> Optional[Dict]:
        """Get secret and parse as JSON."""
        value = await self.get_secret(key)
        if value is None:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.error(f"Secret {key} is not valid JSON")
            return default

    async def set_secret(self, key: str, value: str, metadata: Optional[Dict[str, str]] = None) -> None:
        """Set secret on all writable backends."""
        for _, backend in self.backends:
            try:
                await backend.set_secret(key, value, metadata)
            except NotImplementedError:
                continue  # Read-only backend
            except Exception as e:
                logger.error(f"Failed to set secret on {type(backend).__name__}: {e}")

        # Invalidate cache
        self._cache.pop(key, None)

    async def delete_secret(self, key: str) -> None:
        """Delete secret from all backends."""
        for _, backend in self.backends:
            try:
                await backend.delete_secret(key)
            except NotImplementedError:
                continue
            except Exception as e:
                logger.error(f"Failed to delete secret from {type(backend).__name__}: {e}")

        self._cache.pop(key, None)

    async def list_secrets(self, prefix: str = "") -> List[str]:
        """List all secrets across backends."""
        all_secrets = set()
        for _, backend in self.backends:
            try:
                secrets = await backend.list_secrets(prefix)
                all_secrets.update(secrets)
            except Exception as e:
                logger.warning(f"Failed to list secrets from {type(backend).__name__}: {e}")
        return sorted(all_secrets)

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all backends."""
        results = {}
        for _, backend in self.backends:
            try:
                results[type(backend).__name__] = await backend.health_check()
            except Exception:
                results[type(backend).__name__] = False
        return results

    def clear_cache(self) -> None:
        """Clear the secrets cache."""
        self._cache.clear()


# Global instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get or create the global secrets manager."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
        _configure_default_backends(_secrets_manager)
    return _secrets_manager


def _configure_default_backends(manager: SecretsManager) -> None:
    """Configure default backends based on environment."""
    # 1. Environment variables (highest priority)
    manager.add_backend(EnvironmentBackend(), priority=100)

    # 2. Vault (if configured)
    vault_url = os.getenv("VAULT_ADDR")
    vault_token = os.getenv("VAULT_TOKEN")
    if vault_url and vault_token:
        manager.add_backend(VaultBackend(vault_url, vault_token), priority=90)

    # 3. AWS Secrets Manager (if configured)
    if os.getenv("AWS_SECRETS_MANAGER_ENABLED", "false").lower() == "true":
        region = os.getenv("AWS_REGION", "us-east-1")
        manager.add_backend(AWSSecretsManagerBackend(region), priority=80)

    # 4. SOPS file (if exists)
    sops_path = os.getenv("SOPS_SECRETS_FILE", "./secrets.yaml")
    if Path(sops_path).exists():
        manager.add_backend(SOPSFileBackend(sops_path), priority=70)

    # 5. Local encrypted file (lowest priority, for dev)
    file_path = os.getenv("SECRETS_FILE_PATH", "./.secrets")
    manager.add_backend(FileBackend(file_path), priority=10)


# Convenience functions
async def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get secret from global manager."""
    return await get_secrets_manager().get_secret(key, default)


async def get_secret_required(key: str) -> str:
    """Get required secret from global manager."""
    return await get_secrets_manager().get_secret_required(key)


async def get_json_secret(key: str, default: Optional[Dict] = None) -> Optional[Dict]:
    """Get JSON secret from global manager."""
    return await get_secrets_manager().get_json_secret(key, default)