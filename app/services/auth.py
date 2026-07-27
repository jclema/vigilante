from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import timezone, datetime
from typing import Any
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request

from app.config import settings
from app.models import ConnectionStatus, GbpConnection, Membership, Organization, User, UserRole

if TYPE_CHECKING:
    from app.store import Repository


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 600_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${base64.b64encode(digest).decode('ascii')}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        _, raw_iterations, salt, encoded = password_hash.split("$", 3)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(raw_iterations),
        )
        return hmac.compare_digest(base64.b64encode(digest).decode("ascii"), encoded)
    except Exception:
        return False


def _secret_key() -> bytes:
    material = (settings.session_secret or settings.dashboard_password or "vigilante-dev-secret").encode("utf-8")
    return hashlib.sha256(material).digest()


def encrypt_secret(value: str) -> str:
    key = _secret_key()
    payload = value.encode("utf-8")
    encrypted = bytes(byte ^ key[index % len(key)] for index, byte in enumerate(payload))
    return base64.urlsafe_b64encode(encrypted).decode("ascii")


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    key = _secret_key()
    payload = base64.urlsafe_b64decode(value.encode("ascii"))
    decrypted = bytes(byte ^ key[index % len(key)] for index, byte in enumerate(payload))
    return decrypted.decode("utf-8")


@dataclass(slots=True)
class ActorContext:
    user: User
    memberships: list[Membership]
    organizations: list[Organization]
    active_organization_id: str | None = None

    @property
    def active_membership(self) -> Membership | None:
        if not self.active_organization_id:
            return None
        for membership in self.memberships:
            if membership.organization_id == self.active_organization_id:
                return membership
        return None

    @property
    def roles(self) -> set[UserRole]:
        return {membership.role for membership in self.memberships}

    @property
    def is_super_admin(self) -> bool:
        return UserRole.SUPER_ADMIN in self.roles

    @property
    def is_yamaha_admin(self) -> bool:
        return UserRole.YAMAHA_ADMIN in self.roles

    @property
    def is_developer_viewer(self) -> bool:
        return UserRole.DEVELOPER_VIEWER in self.roles

    @property
    def is_dealer_admin(self) -> bool:
        return UserRole.DEALER_ADMIN in self.roles

    @property
    def can_manage_platform(self) -> bool:
        return self.is_super_admin

    @property
    def can_view_network(self) -> bool:
        return self.is_super_admin or self.is_yamaha_admin or self.is_developer_viewer

    @property
    def can_mutate_product(self) -> bool:
        return not self.is_developer_viewer

    @property
    def can_view_sensitive_settings(self) -> bool:
        return not self.is_developer_viewer

    def visible_organization_ids(self) -> set[str] | None:
        if self.can_view_network and not self.active_organization_id:
            return None
        if self.active_organization_id:
            return {self.active_organization_id}
        return {membership.organization_id for membership in self.memberships}

    def can_manage_organization(self, organization_id: str) -> bool:
        if self.is_super_admin:
            return True
        return any(
            membership.organization_id == organization_id and membership.role == UserRole.DEALER_ADMIN
            for membership in self.memberships
        )


class AuthService:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def register_user(
        self,
        *,
        email: str,
        full_name: str,
        password: str,
        organization_name: str,
    ) -> ActorContext:
        normalized_email = email.strip().lower()
        if self.repository.find_user_by_email(normalized_email):
            raise ValueError("Ya existe un usuario con ese correo")
        organization = Organization(
            id=self.repository.next_id("org"),
            name=organization_name.strip(),
            organization_type="dealer",
        )
        user = User(
            id=self.repository.next_id("user"),
            email=normalized_email,
            full_name=full_name.strip(),
            password_hash=hash_password(password),
        )
        membership = Membership(
            id=self.repository.next_id("membership"),
            user_id=user.id,
            organization_id=organization.id,
            role=UserRole.DEALER_ADMIN,
        )
        self.repository.save_organization(organization)
        self.repository.save_user(user)
        self.repository.save_membership(membership)
        return self._actor_for_user(user.id, active_organization_id=organization.id)

    def login(self, *, email: str, password: str) -> ActorContext:
        user = self.repository.find_user_by_email(email.strip().lower())
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Credenciales inválidas")
        if not user.is_active:
            raise ValueError("Usuario inactivo")
        memberships = self.repository.list_memberships_for_user(user.id)
        role_set = {membership.role for membership in memberships}
        active_org_id = None if (UserRole.SUPER_ADMIN in role_set or UserRole.YAMAHA_ADMIN in role_set) else (
            memberships[0].organization_id if len(memberships) == 1 else None
        )
        return self._actor_for_user(user.id, active_organization_id=active_org_id)

    def login_google_user(self, *, email: str, full_name: str, google_subject: str) -> ActorContext:
        normalized_email = email.strip().lower()
        user = self.repository.find_user_by_google_subject(google_subject) or self.repository.find_user_by_email(normalized_email)
        if not user:
            user = User(
                id=self.repository.next_id("user"),
                email=normalized_email,
                full_name=full_name.strip() or normalized_email,
                google_subject=google_subject,
            )
        else:
            user.google_subject = google_subject
            if full_name:
                user.full_name = full_name.strip()
        self.repository.save_user(user)
        if normalized_email == settings.super_admin_email.strip().lower():
            self._ensure_super_admin_membership(user.id)
        memberships = self.repository.list_memberships_for_user(user.id)
        role_set = {membership.role for membership in memberships}
        active_org_id = None if (UserRole.SUPER_ADMIN in role_set or UserRole.YAMAHA_ADMIN in role_set) else (
            memberships[0].organization_id if len(memberships) == 1 else None
        )
        return self._actor_for_user(user.id, active_organization_id=active_org_id)

    def current_actor(self, request: Request) -> ActorContext | None:
        session = request.session
        user_id = session.get("user_id")
        if not user_id:
            return None
        return self._actor_for_user(user_id, active_organization_id=session.get("active_organization_id"))

    def require_actor(self, request: Request) -> ActorContext:
        actor = self.current_actor(request)
        if not actor:
            raise HTTPException(status_code=401, detail="Autenticación requerida")
        return actor

    def persist_session(self, request: Request, actor: ActorContext) -> None:
        request.session["user_id"] = actor.user.id
        request.session["active_organization_id"] = actor.active_organization_id

    def clear_session(self, request: Request) -> None:
        request.session.clear()

    def switch_organization(self, request: Request, organization_id: str | None) -> ActorContext:
        actor = self.require_actor(request)
        if organization_id and not (actor.can_view_network or organization_id in {item.organization_id for item in actor.memberships}):
            raise ValueError("No tienes acceso a esa organización")
        request.session["active_organization_id"] = organization_id
        return self._actor_for_user(actor.user.id, active_organization_id=organization_id)

    def invite_user(self, *, organization_id: str, email: str, full_name: str, role: UserRole) -> User:
        normalized_email = email.strip().lower()
        user = self.repository.find_user_by_email(normalized_email)
        generated_password = secrets.token_urlsafe(10)
        if not user:
            user = User(
                id=self.repository.next_id("user"),
                email=normalized_email,
                full_name=full_name.strip(),
                password_hash=hash_password(generated_password),
            )
        else:
            if full_name:
                user.full_name = full_name.strip()
            user.password_hash = hash_password(generated_password)
        self.repository.save_user(user)
        memberships = self.repository.list_memberships_for_user(user.id)
        exists = any(item.organization_id == organization_id and item.role == role for item in memberships)
        if not exists:
            self.repository.save_membership(
                Membership(
                    id=self.repository.next_id("membership"),
                    user_id=user.id,
                    organization_id=organization_id,
                    role=role,
                )
            )
        setattr(user, "_temporary_password", generated_password)
        return user

    def provision_developer_viewer(self, *, email: str, full_name: str) -> tuple[User, Membership, bool]:
        normalized_email = email.strip().lower()
        if not normalized_email or "@" not in normalized_email:
            raise ValueError("Correo inválido")
        normalized_name = full_name.strip()
        if not normalized_name:
            raise ValueError("Nombre requerido")
        platform = self.repository.get_organization("org-platform")
        if not platform:
            platform = self.repository.save_organization(
                Organization(
                    id="org-platform",
                    name="Vigilante Platform",
                    organization_type="platform",
                )
            )
        user = self.repository.find_user_by_email(normalized_email)
        if not user:
            user = User(
                id=self.repository.next_id("user"),
                email=normalized_email,
                full_name=normalized_name,
            )
        else:
            user.full_name = normalized_name
            user.is_active = True
        self.repository.save_user(user)
        memberships = self.repository.list_memberships_for_user(user.id)
        existing = next(
            (item for item in memberships if item.role == UserRole.DEVELOPER_VIEWER),
            None,
        )
        if existing:
            return user, existing, False
        membership = self.repository.save_membership(
            Membership(
                id=self.repository.next_id("membership"),
                user_id=user.id,
                organization_id=platform.id,
                role=UserRole.DEVELOPER_VIEWER,
            )
        )
        return user, membership, True

    def google_oauth_authorize_url(
        self,
        request: Request,
        *,
        organization_id: str | None = None,
        purpose: str = "signin",
    ) -> str:
        if not settings.google_oauth_client_id or not settings.google_oauth_redirect_uri:
            raise ValueError("Google Sign-In no está configurado")
        state_payload = {"nonce": secrets.token_urlsafe(24), "organization_id": organization_id, "purpose": purpose}
        request.session["google_oauth_state"] = state_payload
        scopes = ["openid", "email", "profile"]
        params = {
            "client_id": settings.google_oauth_client_id,
            "redirect_uri": settings.google_oauth_redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": json.dumps(state_payload),
        }
        if purpose == "gbp_connect":
            scopes.append("https://www.googleapis.com/auth/business.manage")
            params.update(
                {
                    "scope": " ".join(scopes),
                    "access_type": "offline",
                    "prompt": "consent",
                    "include_granted_scopes": "true",
                }
            )
        else:
            params["prompt"] = "select_account"
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    def exchange_google_callback(self, request: Request, *, code: str, state: str) -> dict[str, Any]:
        expected_state = request.session.get("google_oauth_state")
        if not expected_state or json.loads(state) != expected_state:
            raise ValueError("Estado OAuth inválido")
        if not settings.google_oauth_client_id or not settings.google_oauth_client_secret or not settings.google_oauth_redirect_uri:
            raise ValueError("Google Sign-In no está configurado")
        token_payload = urllib.parse.urlencode(
            {
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        token_request = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=token_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(token_request, timeout=15) as response:
            token_data = json.loads(response.read().decode("utf-8"))
        userinfo_request = urllib.request.Request(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        with urllib.request.urlopen(userinfo_request, timeout=15) as response:
            userinfo = json.loads(response.read().decode("utf-8"))
        token_data["userinfo"] = userinfo
        return token_data

    def save_gbp_connection(
        self,
        *,
        organization_id: str,
        provider_account_id: str,
        provider_email: str | None,
        refresh_token: str | None,
        scopes: list[str],
    ) -> GbpConnection:
        connection = next(
            (
                item
                for item in self.repository.list_gbp_connections(organization_id)
                if item.provider_account_id == provider_account_id
            ),
            None,
        )
        now = datetime.now(timezone.utc)
        if connection is None:
            connection = GbpConnection(
                id=self.repository.next_id("gbp-connection"),
                organization_id=organization_id,
                provider_account_id=provider_account_id,
            )
        connection.provider_email = provider_email
        connection.encrypted_refresh_token = encrypt_secret(refresh_token) if refresh_token else connection.encrypted_refresh_token
        connection.scopes = scopes
        connection.gbp_account_name = connection.gbp_account_name
        connection.status = ConnectionStatus.CONNECTED
        connection.last_error = None
        connection.last_error_at = None
        connection.updated_at = now
        self.repository.save_gbp_connection(connection)
        return connection

    def disconnect_gbp_connection(self, *, organization_id: str, connection_id: str) -> GbpConnection:
        connection = self.repository.get_gbp_connection(connection_id)
        if not connection or connection.organization_id != organization_id:
            raise ValueError("Conexión GBP no encontrada")
        connection.status = ConnectionStatus.DISCONNECTED
        connection.gbp_account_name = None
        connection.encrypted_refresh_token = None
        connection.selected_profile_ids = []
        connection.available_locations = []
        connection.last_sync_at = None
        connection.last_locations_sync_at = None
        connection.last_error = None
        connection.last_error_at = None
        connection.updated_at = datetime.now(timezone.utc)
        self.repository.save_gbp_connection(connection)
        return connection

    def _ensure_super_admin_membership(self, user_id: str) -> None:
        if not self.repository.get_organization("org-platform"):
            self.repository.save_organization(
                Organization(
                    id="org-platform",
                    name="Vigilante Platform",
                    organization_type="platform",
                )
            )
        memberships = self.repository.list_memberships_for_user(user_id)
        if any(membership.role == UserRole.SUPER_ADMIN for membership in memberships):
            return
        self.repository.save_membership(
            Membership(
                id=self.repository.next_id("membership"),
                user_id=user_id,
                organization_id="org-platform",
                role=UserRole.SUPER_ADMIN,
            )
        )

    def _actor_for_user(self, user_id: str, *, active_organization_id: str | None = None) -> ActorContext:
        user = self.repository.get_user(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        if user.email.strip().lower() == settings.super_admin_email.strip().lower():
            self._ensure_super_admin_membership(user.id)
        memberships = self.repository.list_memberships_for_user(user.id)
        organizations = [
            organization
            for membership in memberships
            if (organization := self.repository.get_organization(membership.organization_id)) is not None
        ]
        role_set = {membership.role for membership in memberships}
        if UserRole.SUPER_ADMIN in role_set or UserRole.YAMAHA_ADMIN in role_set:
            active_organization_id = active_organization_id
        elif active_organization_id is None and len(memberships) == 1:
            active_organization_id = memberships[0].organization_id
        return ActorContext(
            user=user,
            memberships=memberships,
            organizations=organizations,
            active_organization_id=active_organization_id,
        )
