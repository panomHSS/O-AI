"""Persistence boundary for encrypted OAuth refresh credentials."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.oauth_credential import OAuthCredentialRecord


class OAuthCredentialRepository:
    """Persist ciphertext and non-secret OAuth metadata only."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, profile_id: str) -> OAuthCredentialRecord | None:
        return self._session.get(OAuthCredentialRecord, profile_id)

    def save_active(
        self,
        *,
        profile_id: str,
        provider_id: str,
        plugin_id: str,
        plugin_version: str,
        capability_name: str,
        encrypted_refresh_token: bytes,
        encryption_nonce: bytes,
        cipher_version: str,
        granted_scopes: str,
        refresh_token_expires_at: datetime | None,
        now: datetime,
    ) -> OAuthCredentialRecord:
        record = self.get(profile_id)
        if record is None:
            record = OAuthCredentialRecord(
                profile_id=profile_id,
                provider_id=provider_id,
                plugin_id=plugin_id,
                plugin_version=plugin_version,
                capability_name=capability_name,
                encrypted_refresh_token=encrypted_refresh_token,
                encryption_nonce=encryption_nonce,
                cipher_version=cipher_version,
                granted_scopes=granted_scopes,
                status="active",
                refresh_token_expires_at=refresh_token_expires_at,
                created_at=now,
                updated_at=now,
            )
            self._session.add(record)
            self._session.flush()
            return record

        record.provider_id = provider_id
        record.plugin_id = plugin_id
        record.plugin_version = plugin_version
        record.capability_name = capability_name
        record.encrypted_refresh_token = encrypted_refresh_token
        record.encryption_nonce = encryption_nonce
        record.cipher_version = cipher_version
        record.granted_scopes = granted_scopes
        record.status = "active"
        record.refresh_token_expires_at = refresh_token_expires_at
        record.updated_at = now
        self._session.flush()
        return record

    def mark_reauthorization_required(
        self,
        profile_id: str,
        *,
        now: datetime,
    ) -> bool:
        record = self.get(profile_id)
        if record is None:
            return False
        record.status = "reauthorization_required"
        record.updated_at = now
        self._session.flush()
        return True

    def delete(self, profile_id: str) -> bool:
        record = self.get(profile_id)
        if record is None:
            return False
        self._session.delete(record)
        self._session.flush()
        return True

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
