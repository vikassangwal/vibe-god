"""
Role-Based Access Control (RBAC) with Attribute-Based Access Control (ABAC) extensions
"""
import os
from typing import Dict, List, Set, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import asyncio

from .secrets import get_json_secret


class ResourceType(str, Enum):
    """Resource types for fine-grained permissions."""
    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    API = "api"
    DATABASE = "database"
    STORAGE = "storage"
    CONFIGURATION = "configuration"
    AUDIT_LOG = "audit_log"
    METRICS = "metrics"
    TRACES = "traces"
    SECRETS = "secrets"
    DEPLOYMENT = "deployment"
    SERVICE = "service"


class Action(str, Enum):
    """Actions that can be performed on resources."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class Permission:
    """Permission definition."""
    name: str
    resource_type: ResourceType
    action: Action
    description: str = ""
    conditions: Dict[str, Any] = field(default_factory=dict)  # ABAC conditions

    def __str__(self) -> str:
        return f"{self.resource_type.value}:{self.action.value}"

    @classmethod
    def from_string(cls, perm_str: str) -> "Permission":
        """Create permission from string like 'user:read'."""
        parts = perm_str.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid permission format: {perm_str}")
        return cls(
            name=perm_str,
            resource_type=ResourceType(parts[0]),
            action=Action(parts[1]),
        )


@dataclass
class Role:
    """Role definition with permissions."""
    name: str
    description: str = ""
    permissions: Set[str] = field(default_factory=set)  # Permission names
    inherits: List[str] = field(default_factory=list)  # Parent role names
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_permission(self, permission: str) -> None:
        self.permissions.add(permission)

    def remove_permission(self, permission: str) -> None:
        self.permissions.discard(permission)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions


class RBACManager:
    """
    RBAC Manager with ABAC support.
    Supports role inheritance, dynamic permissions, and context-aware authorization.
    """

    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.permissions: Dict[str, Permission] = {}
        self._permission_cache: Dict[str, Set[str]] = {}  # role -> effective permissions
        self._initialized = False

        # Default permissions
        self._register_default_permissions()
        # Default roles
        self._register_default_roles()

    def _register_default_permissions(self) -> None:
        """Register default permissions."""
        default_perms = [
            # User management
            Permission("user:create", ResourceType.USER, Action.CREATE, "Create users"),
            Permission("user:read", ResourceType.USER, Action.READ, "Read user info"),
            Permission("user:update", ResourceType.USER, Action.UPDATE, "Update users"),
            Permission("user:delete", ResourceType.USER, Action.DELETE, "Delete users"),
            Permission("user:list", ResourceType.USER, Action.LIST, "List users"),
            Permission("user:admin", ResourceType.USER, Action.ADMIN, "Full user admin"),

            # Role management
            Permission("role:create", ResourceType.ROLE, Action.CREATE, "Create roles"),
            Permission("role:read", ResourceType.ROLE, Action.READ, "Read roles"),
            Permission("role:update", ResourceType.ROLE, Action.UPDATE, "Update roles"),
            Permission("role:delete", ResourceType.ROLE, Action.DELETE, "Delete roles"),
            Permission("role:admin", ResourceType.ROLE, Action.ADMIN, "Full role admin"),

            # Permission management
            Permission("permission:create", ResourceType.PERMISSION, Action.CREATE, "Create permissions"),
            Permission("permission:read", ResourceType.PERMISSION, Action.READ, "Read permissions"),
            Permission("permission:admin", ResourceType.PERMISSION, Action.ADMIN, "Full permission admin"),

            # API access
            Permission("api:read", ResourceType.API, Action.READ, "Read API"),
            Permission("api:execute", ResourceType.API, Action.EXECUTE, "Execute API"),
            Permission("api:admin", ResourceType.API, Action.ADMIN, "Full API admin"),

            # Database
            Permission("database:read", ResourceType.DATABASE, Action.READ, "Read database"),
            Permission("database:write", ResourceType.DATABASE, Action.UPDATE, "Write database"),
            Permission("database:admin", ResourceType.DATABASE, Action.ADMIN, "Full database admin"),

            # Storage
            Permission("storage:read", ResourceType.STORAGE, Action.READ, "Read storage"),
            Permission("storage:write", ResourceType.STORAGE, Action.UPDATE, "Write storage"),
            Permission("storage:admin", ResourceType.STORAGE, Action.ADMIN, "Full storage admin"),

            # Configuration
            Permission("configuration:read", ResourceType.CONFIGURATION, Action.READ, "Read config"),
            Permission("configuration:write", ResourceType.CONFIGURATION, Action.UPDATE, "Write config"),
            Permission("configuration:admin", ResourceType.CONFIGURATION, Action.ADMIN, "Full config admin"),

            # Audit logs
            Permission("audit_log:read", ResourceType.AUDIT_LOG, Action.READ, "Read audit logs"),
            Permission("audit_log:admin", ResourceType.AUDIT_LOG, Action.ADMIN, "Full audit log admin"),

            # Observability
            Permission("metrics:read", ResourceType.METRICS, Action.READ, "Read metrics"),
            Permission("traces:read", ResourceType.TRACES, Action.READ, "Read traces"),
            Permission("observability:admin", ResourceType.METRICS, Action.ADMIN, "Full observability admin"),

            # Secrets
            Permission("secrets:read", ResourceType.SECRETS, Action.READ, "Read secrets"),
            Permission("secrets:write", ResourceType.SECRETS, Action.UPDATE, "Write secrets"),
            Permission("secrets:admin", ResourceType.SECRETS, Action.ADMIN, "Full secrets admin"),

            # Deployment
            Permission("deployment:read", ResourceType.DEPLOYMENT, Action.READ, "Read deployments"),
            Permission("deployment:execute", ResourceType.DEPLOYMENT, Action.EXECUTE, "Execute deployments"),
            Permission("deployment:admin", ResourceType.DEPLOYMENT, Action.ADMIN, "Full deployment admin"),

            # Service management
            Permission("service:read", ResourceType.SERVICE, Action.READ, "Read services"),
            Permission("service:write", ResourceType.SERVICE, Action.UPDATE, "Write services"),
            Permission("service:admin", ResourceType.SERVICE, Action.ADMIN, "Full service admin"),
        ]

        for perm in default_perms:
            self.register_permission(perm)

    def _register_default_roles(self) -> None:
        """Register default roles."""
        default_roles = [
            Role(
                name="super_admin",
                description="Super administrator with all permissions",
                permissions=set(self.permissions.keys()),
            ),
            Role(
                name="admin",
                description="Administrator with most permissions",
                permissions={
                    "user:create", "user:read", "user:update", "user:list",
                    "role:read", "role:update",
                    "permission:read",
                    "api:read", "api:execute",
                    "database:read", "database:write",
                    "storage:read", "storage:write",
                    "configuration:read", "configuration:write",
                    "audit_log:read",
                    "metrics:read", "traces:read",
                    "secrets:read",
                    "deployment:read", "deployment:execute",
                    "service:read", "service:write",
                },
            ),
            Role(
                name="operator",
                description="Operations role for day-to-day tasks",
                permissions={
                    "user:read", "user:list",
                    "role:read",
                    "permission:read",
                    "api:read", "api:execute",
                    "database:read",
                    "storage:read",
                    "configuration:read",
                    "audit_log:read",
                    "metrics:read", "traces:read",
                    "deployment:read",
                    "service:read",
                },
            ),
            Role(
                name="developer",
                description="Developer role for development tasks",
                permissions={
                    "user:read",
                    "role:read",
                    "permission:read",
                    "api:read", "api:execute",
                    "database:read", "database:write",
                    "storage:read", "storage:write",
                    "configuration:read",
                    "metrics:read", "traces:read",
                    "service:read", "service:write",
                },
            ),
            Role(
                name="viewer",
                description="Read-only access",
                permissions={
                    "user:read", "user:list",
                    "role:read",
                    "permission:read",
                    "api:read",
                    "database:read",
                    "storage:read",
                    "configuration:read",
                    "audit_log:read",
                    "metrics:read", "traces:read",
                    "service:read",
                },
            ),
            Role(
                name="user",
                description="Basic user role",
                permissions={
                    "user:read",  # Own profile
                    "api:read", "api:execute",
                },
            ),
        ]

        for role in default_roles:
            self.register_role(role)

    def register_permission(self, permission: Permission) -> None:
        """Register a permission."""
        self.permissions[permission.name] = permission
        self._invalidate_cache()

    def register_role(self, role: Role) -> None:
        """Register a role."""
        self.roles[role.name] = role
        self._invalidate_cache()

    def get_permission(self, name: str) -> Optional[Permission]:
        """Get permission by name."""
        return self.permissions.get(name)

    def get_role(self, name: str) -> Optional[Role]:
        """Get role by name."""
        return self.roles.get(name)

    def get_effective_permissions(self, role_name: str) -> Set[str]:
        """Get all effective permissions for a role (including inherited)."""
        if role_name in self._permission_cache:
            return self._permission_cache[role_name]

        role = self.roles.get(role_name)
        if not role:
            return set()

        effective = set(role.permissions)
        for parent_name in role.inherits:
            effective.update(self.get_effective_permissions(parent_name))

        self._permission_cache[role_name] = effective
        return effective

    def user_has_permission(
        self,
        user_roles: List[str],
        permission: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if user has permission (with ABAC context)."""
        for role_name in user_roles:
            effective_perms = self.get_effective_permissions(role_name)
            if permission in effective_perms:
                # Check ABAC conditions
                perm = self.permissions.get(permission)
                if perm and perm.conditions:
                    if not self._evaluate_conditions(perm.conditions, context or {}):
                        continue
                return True
        return False

    def user_has_any_permission(
        self,
        user_roles: List[str],
        permissions: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if user has any of the permissions."""
        return any(
            self.user_has_permission(user_roles, p, context)
            for p in permissions
        )

    def user_has_all_permissions(
        self,
        user_roles: List[str],
        permissions: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Check if user has all permissions."""
        return all(
            self.user_has_permission(user_roles, p, context)
            for p in permissions
        )

    def _evaluate_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate ABAC conditions."""
        for key, expected in conditions.items():
            actual = context.get(key)
            if isinstance(expected, dict):
                # Complex condition
                operator = expected.get("operator", "eq")
                value = expected.get("value")
                if not self._compare(actual, operator, value):
                    return False
            else:
                # Simple equality
                if actual != expected:
                    return False
        return True

    def _compare(self, actual: Any, operator: str, expected: Any) -> bool:
        """Compare values with operator."""
        if operator == "eq":
            return actual == expected
        elif operator == "ne":
            return actual != expected
        elif operator == "gt":
            return actual > expected
        elif operator == "gte":
            return actual >= expected
        elif operator == "lt":
            return actual < expected
        elif operator == "lte":
            return actual <= expected
        elif operator == "in":
            return actual in expected
        elif operator == "not_in":
            return actual not in expected
        elif operator == "contains":
            return expected in actual if actual else False
        return False

    def _invalidate_cache(self) -> None:
        """Invalidate permission cache."""
        self._permission_cache.clear()

    def add_role_to_user(self, user_roles: List[str], role_name: str) -> List[str]:
        """Add role to user's roles."""
        if role_name not in self.roles:
            raise ValueError(f"Role not found: {role_name}")
        if role_name not in user_roles:
            user_roles.append(role_name)
        return user_roles

    def remove_role_from_user(self, user_roles: List[str], role_name: str) -> List[str]:
        """Remove role from user's roles."""
        return [r for r in user_roles if r != role_name]

    def get_user_permissions(self, user_roles: List[str]) -> Set[str]:
        """Get all permissions for user's roles."""
        all_perms = set()
        for role_name in user_roles:
            all_perms.update(self.get_effective_permissions(role_name))
        return all_perms

    async def load_from_config(self, config_path: str) -> None:
        """Load roles and permissions from config file."""
        config = await get_json_secret(config_path)
        if not config:
            return

        # Load permissions
        for perm_data in config.get("permissions", []):
            perm = Permission(**perm_data)
            self.register_permission(perm)

        # Load roles
        for role_data in config.get("roles", []):
            role = Role(**role_data)
            self.register_role(role)

    def export_config(self) -> Dict[str, Any]:
        """Export current configuration."""
        return {
            "permissions": [
                {
                    "name": p.name,
                    "resource_type": p.resource_type.value,
                    "action": p.action.value,
                    "description": p.description,
                    "conditions": p.conditions,
                }
                for p in self.permissions.values()
            ],
            "roles": [
                {
                    "name": r.name,
                    "description": r.description,
                    "permissions": list(r.permissions),
                    "inherits": r.inherits,
                    "metadata": r.metadata,
                }
                for r in self.roles.values()
            ],
        }


# Global instance
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """Get or create global RBAC manager."""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


# Decorators for FastAPI
def require_permission(permission: str):
    """FastAPI dependency to require permission."""
    from fastapi import Depends, HTTPException
    from .auth import get_current_active_user, User

    async def checker(current_user: User = Depends(get_current_active_user)) -> User:
        rbac = get_rbac_manager()
        if not rbac.user_has_permission(current_user.roles, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission} required"
            )
        return current_user
    return checker


def require_any_permission(permissions: List[str]):
    """FastAPI dependency to require any permission."""
    from fastapi import Depends, HTTPException
    from .auth import get_current_active_user, User

    async def checker(current_user: User = Depends(get_current_active_user)) -> User:
        rbac = get_rbac_manager()
        if not rbac.user_has_any_permission(current_user.roles, permissions):
            raise HTTPException(
                status_code=403,
                detail=f"One of permissions required: {', '.join(permissions)}"
            )
        return current_user
    return checker


def require_all_permissions(permissions: List[str]):
    """FastAPI dependency to require all permissions."""
    from fastapi import Depends, HTTPException
    from .auth import get_current_active_user, User

    async def checker(current_user: User = Depends(get_current_active_user)) -> User:
        rbac = get_rbac_manager()
        if not rbac.user_has_all_permissions(current_user.roles, permissions):
            raise HTTPException(
                status_code=403,
                detail=f"All permissions required: {', '.join(permissions)}"
            )
        return current_user
    return checker


# Context managers for ABAC
class AuthorizationContext:
    """Context manager for authorization with additional context."""

    def __init__(self, **context: Any):
        self.context = context
        self._previous_context: Dict[str, Any] = {}

    def __enter__(self):
        # Store in contextvars for async safety
        import contextvars
        self._auth_context_var = contextvars.ContextVar("auth_context", default={})
        self._previous_context = self._auth_context_var.get().copy()
        self._auth_context_var.set({**self._previous_context, **self.context})
        return self

    def __exit__(self, *args):
        self._auth_context_var.set(self._previous_context)


def get_auth_context() -> Dict[str, Any]:
    """Get current authorization context."""
    import contextvars
    auth_context_var = contextvars.ContextVar("auth_context", default={})
    return auth_context_var.get()


# Permission helper functions
def permission(resource: ResourceType, action: Action) -> str:
    """Create permission string."""
    return f"{resource.value}:{action.value}"


def permissions_for_resource(resource: ResourceType) -> List[str]:
    """Get all permissions for a resource type."""
    return [f"{resource.value}:{action.value}" for action in Action]


# Common permission groups
READ_ONLY_PERMISSIONS = [
    permission(ResourceType.USER, Action.READ),
    permission(ResourceType.ROLE, Action.READ),
    permission(ResourceType.PERMISSION, Action.READ),
    permission(ResourceType.API, Action.READ),
    permission(ResourceType.DATABASE, Action.READ),
    permission(ResourceType.STORAGE, Action.READ),
    permission(ResourceType.CONFIGURATION, Action.READ),
    permission(ResourceType.AUDIT_LOG, Action.READ),
    permission(ResourceType.METRICS, Action.READ),
    permission(ResourceType.TRACES, Action.READ),
    permission(ResourceType.SECRETS, Action.READ),
    permission(ResourceType.DEPLOYMENT, Action.READ),
    permission(ResourceType.SERVICE, Action.READ),
]

WRITE_PERMISSIONS = [
    permission(ResourceType.USER, Action.CREATE),
    permission(ResourceType.USER, Action.UPDATE),
    permission(ResourceType.USER, Action.DELETE),
    permission(ResourceType.ROLE, Action.CREATE),
    permission(ResourceType.ROLE, Action.UPDATE),
    permission(ResourceType.ROLE, Action.DELETE),
    permission(ResourceType.DATABASE, Action.UPDATE),
    permission(ResourceType.STORAGE, Action.UPDATE),
    permission(ResourceType.CONFIGURATION, Action.UPDATE),
    permission(ResourceType.SECRETS, Action.UPDATE),
    permission(ResourceType.SERVICE, Action.UPDATE),
]

ADMIN_PERMISSIONS = [
    permission(ResourceType.USER, Action.ADMIN),
    permission(ResourceType.ROLE, Action.ADMIN),
    permission(ResourceType.PERMISSION, Action.ADMIN),
    permission(ResourceType.API, Action.ADMIN),
    permission(ResourceType.DATABASE, Action.ADMIN),
    permission(ResourceType.STORAGE, Action.ADMIN),
    permission(ResourceType.CONFIGURATION, Action.ADMIN),
    permission(ResourceType.AUDIT_LOG, Action.ADMIN),
    permission(ResourceType.METRICS, Action.ADMIN),
    permission(ResourceType.SECRETS, Action.ADMIN),
    permission(ResourceType.DEPLOYMENT, Action.ADMIN),
    permission(ResourceType.SERVICE, Action.ADMIN),
]