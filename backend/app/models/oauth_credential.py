"""Encrypted durable OAuth credential metadata."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OAuthCredentialRecord(Base):
    """One encrypted refresh-token record for one exact credential profile."""

    __tablename__ = "oauth_credentials"
    __table_args__ = (
        CheckConstraint(
            "cipher_version = 'aesgcm-v1'",
            name="ck_oauth_credentials_cipher_version",
        ),
        CheckConstraint(
            "status IN ('active', 'reauthorization_required')",
            name="ck_oauth_credentials_status",
        ),
    )

    profile_id: Mapped[str] = mapped_column(Text, primary_key=True)
    provider_id: Mapped[str] = mapped_column(Text, nullable=False)
    plugin_id: Mapped[str] = mapped_column(Text, nullable=False)
    plugin_version: Mapped[str] = mapped_column(Text, nullable=False)
    capability_name: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_refresh_token: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )
    encryption_nonce: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )
    cipher_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    granted_scopes: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
