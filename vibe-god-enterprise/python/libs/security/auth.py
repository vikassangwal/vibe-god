"""
Authentication & Authorization with JWT/OIDC Support
"""
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field
from enum import Enum

import jwt
from jwt import PyJWKClient
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

from .secrets import get_secret_required

logger = __import__("logging").getLogger(__name__)


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


@dataclass
class User:
    """User model."""
    id: str
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    status: UserStatus = UserStatus.ACTIVE
    roles: List[str] = field(default_factory=list)
    permissions: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_any_role(self, roles: List[str]) -> bool:
        return any(r in self.roles for r in roles)

    def has_all_roles(self, roles: List[str]) -> bool:
        return all(r in self.roles for r in roles)


@dataclass
class TokenData:
    """JWT token payload."""
    sub: str  # User ID
    email: EmailStr
    username: str
    roles: List[str]
    permissions: List[str]
    exp: int
    iat: int
    jti: str  # JWT ID for revocation
    token_type: str = "access"  # access or refresh


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


class AuthManager:
    """Authentication manager with JWT and OIDC support."""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "RS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 30,
        issuer: str = "vibe-god",
        audience: str = "vibe-god-api",
        oidc_jwks_url: Optional[str] = None,
    ):
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.issuer = issuer
        self.audience = audience

        # Password hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        # JWT keys
        self._private_key: Optional[str] = None
        self._public_key: Optional[str] = None
        self._jwks_client: Optional[PyJWKClient] = None

        if secret_key:
            # Symmetric key (HS256)
            self._private_key = secret_key
            self._public_key = secret_key
            self.algorithm = "HS256"
        elif oidc_jwks_url:
            # OIDC/JWKS
            self._jwks_client = PyJWKClient(oidc_jwks_url)
        else:
            # Generate RSA keys for RS256
            self._generate_rsa_keys()

        # Token blacklist (in production, use Redis)
        self._revoked_tokens: Set[str] = set()

        # API keys (in production, store in database)
        self._api_keys: Dict[str, Dict[str, Any]] = {}

    def _generate_rsa_keys(self) -> None:
        """Generate RSA key pair for RS256."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self._private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

        public_key = private_key.public_key()
        self._public_key = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return self.pwd_context.hash(password)

    def create_access_token(self, user: User, additional_claims: Optional[Dict] = None) -> str:
        """Create JWT access token."""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        jti = str(uuid.uuid4())

        claims = {
            "sub": user.id,
            "email": user.email,
            "username": user.username,
            "roles": user.roles,
            "permissions": list(user.permissions),
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "jti": jti,
            "token_type": TokenType.ACCESS.value,
            "iss": self.issuer,
            "aud": self.audience,
        }
        if additional_claims:
            claims.update(additional_claims)

        return jwt.encode(claims, self._private_key, algorithm=self.algorithm)

    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token."""
        now = datetime.utcnow()
        expire = now + timedelta(days=self.refresh_token_expire_days)
        jti = str(uuid.uuid4())

        claims = {
            "sub": user.id,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "jti": jti,
            "token_type": TokenType.REFRESH.value,
            "iss": self.issuer,
            "aud": self.audience,
        }

        return jwt.encode(claims, self._private_key, algorithm=self.algorithm)

    def create_api_key(self, user_id: str, name: str, expires_days: Optional[int] = None) -> str:
        """Create an API key."""
        import secrets
        api_key = f"vg_{secrets.token_urlsafe(32)}"
        key_hash = self.hash_password(api_key)
        key_id = str(uuid.uuid4())

        self._api_keys[key_id] = {
            "key_hash": key_hash,
            "user_id": user_id,
            "name": name,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=expires_days) if expires_days else None,
            "last_used": None,
        }

        return api_key

    def verify_api_key(self, api_key: str) -> Optional[str]:
        """Verify API key and return user_id."""
        for key_id, key_data in self._api_keys.items():
            if self.verify_password(api_key, key_data["key_hash"]):
                # Check expiration
                if key_data["expires_at"] and datetime.utcnow() > key_data["expires_at"]:
                    return None
                # Update last used
                key_data["last_used"] = datetime.utcnow()
                return key_data["user_id"]
        return None

    def decode_token(self, token: str) -> TokenData:
        """Decode and validate JWT token."""
        try:
            if self._jwks_client:
                # OIDC verification
                signing_key = self._jwks_client.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=[self.algorithm],
                    audience=self.audience,
                    issuer=self.issuer,
                )
            else:
                # Local verification
                payload = jwt.decode(
                    token,
                    self._public_key,
                    algorithms=[self.algorithm],
                    audience=self.audience,
                    issuer=self.issuer,
                )

            # Check revocation
            jti = payload.get("jti")
            if jti and jti in self._revoked_tokens:
                raise jwt.InvalidTokenError("Token has been revoked")

            return TokenData(**payload)

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    def revoke_token(self, token: str) -> None:
        """Revoke a token (add to blacklist)."""
        try:
            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False},  # Allow expired tokens
            )
            jti = payload.get("jti")
            if jti:
                self._revoked_tokens.add(jti)
        except Exception:
            pass  # Invalid token, nothing to revoke

    def revoke_all_user_tokens(self, user_id: str) -> None:
        """Revoke all tokens for a user (requires token store)."""
        # In production, maintain a user->tokens mapping
        pass

    def get_public_key(self) -> str:
        """Get public key for external verification."""
        return self._public_key or ""

    def get_jwks(self) -> Dict[str, Any]:
        """Get JWKS for token verification."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        if self.algorithm == "HS256":
            return {"keys": []}

        public_key = serialization.load_pem_public_key(self._public_key.encode())
        if not isinstance(public_key, rsa.RSAPublicKey):
            return {"keys": []}

        numbers = public_key.public_numbers()
        import base64

        def int_to_base64url(value: int) -> str:
            byte_length = (value.bit_length() + 7) // 8
            return base64.urlsafe_b64encode(value.to_bytes(byte_length, "big")).decode().rstrip("=")

        return {
            "keys": [{
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": "vibe-god-key-1",
                "n": int_to_base64url(numbers.n),
                "e": int_to_base64url(numbers.e),
            }]
        }


# FastAPI dependencies
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_manager: AuthManager = Depends(get_auth_manager),
) -> User:
    """Get current authenticated user."""
    # Check for API key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        user_id = auth_manager.verify_api_key(api_key)
        if user_id:
            return await _get_user_by_id(user_id)
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check for Bearer token
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token_data = auth_manager.decode_token(credentials.credentials)
    if token_data.token_type != TokenType.ACCESS.value:
        raise HTTPException(status_code=401, detail="Invalid token type")

    return await _get_user_by_id(token_data.sub)


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="User account is not active")
    return current_user


def require_permission(permission: str):
    """Dependency to require a specific permission."""
    async def permission_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission} required"
            )
        return current_user
    return permission_checker


def require_role(role: str):
    """Dependency to require a specific role."""
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not current_user.has_role(role):
            raise HTTPException(
                status_code=403,
                detail=f"Role required: {role}"
            )
        return current_user
    return role_checker


def require_any_role(roles: List[str]):
    """Dependency to require any of the specified roles."""
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not current_user.has_any_role(roles):
            raise HTTPException(
                status_code=403,
                detail=f"One of roles required: {', '.join(roles)}"
            )
        return current_user
    return role_checker


# Mock user store (replace with database in production)
_user_store: Dict[str, User] = {}


async def _get_user_by_id(user_id: str) -> User:
    """Get user by ID from store."""
    if user_id in _user_store:
        return _user_store[user_id]

    # Create default user for development
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        roles=["user"],
        permissions=["read"],
    )
    _user_store[user_id] = user
    return user


def create_user(
    email: str,
    username: str,
    password: str,
    full_name: Optional[str] = None,
    roles: Optional[List[str]] = None,
    permissions: Optional[List[str]] = None,
) -> User:
    """Create a new user."""
    auth_manager = get_auth_manager()
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        username=username,
        full_name=full_name,
        roles=roles or ["user"],
        permissions=set(permissions or ["read"]),
    )
    # Store hashed password (in production, store in database)
    user.metadata["password_hash"] = auth_manager.hash_password(password)
    _user_store[user.id] = user
    return user


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user with username/password."""
    for user in _user_store.values():
        if user.username == username or user.email == username:
            password_hash = user.metadata.get("password_hash")
            if password_hash and get_auth_manager().verify_password(password, password_hash):
                user.last_login = datetime.utcnow()
                return user
    return None


# Global instance
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get or create global auth manager."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = _create_auth_manager()
    return _auth_manager


def _create_auth_manager() -> AuthManager:
    """Create auth manager with configuration from secrets."""
    import asyncio

    async def _init():
        secret_key = await get_secret_required("auth.jwt_secret")
        oidc_url = await get_secret("auth.oidc_jwks_url")
        return AuthManager(
            secret_key=secret_key,
            oidc_jwks_url=oidc_url,
        )

    try:
        return asyncio.run(_init())
    except Exception:
        # Fallback for development
        return AuthManager(secret_key="dev-secret-change-in-production")


# Pydantic models for API
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class APIKeyCreateRequest(BaseModel):
    name: str
    expires_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    key: str
    key_id: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime]