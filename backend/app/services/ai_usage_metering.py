"""D155 best-effort AI usage metering over authorized runtime results."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.contracts.ai import AIResult
from app.contracts.ai_route import CHATGPT_DEFAULT_ADAPTER_ID, LOCAL_AI_ADAPTER_ID
from app.contracts.ai_usage import (
    AI_USAGE_METADATA_KEY,
    AI_USAGE_PRICING_MODE_NOT_APPLICABLE,
    AI_USAGE_PRICING_MODE_UNKNOWN,
    AI_USAGE_PROVIDER_LOCAL,
    AI_USAGE_PROVIDER_OPENAI,
    AI_USAGE_PROVIDER_UNKNOWN,
    AIUsageMeasurement,
    AIUsageObservation,
)
from app.repositories.ai_usage_events import AIUsageEventRepository
from app.services.ai_usage_pricing import AIUsagePricing


logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _request_digest(request_id: str) -> str:
    if type(request_id) is not str or not request_id:
        raise ValueError("AI usage request identity must be a non-empty string.")
    return hashlib.sha256(
        (f"{request_id}\no-ai.d155.ai-usage.request.v1").encode("utf-8")
    ).hexdigest()


def ai_usage_invocation_digest(
    *,
    request_id: str,
    plan_digest: str,
    adapter_id: str,
    authorized_model_id: str,
) -> str:
    if type(request_id) is not str or not request_id:
        raise ValueError("AI usage request identity must be a non-empty string.")
    values = (plan_digest, adapter_id, authorized_model_id)
    if any(type(value) is not str or not value or value != value.strip() for value in values):
        raise ValueError("AI usage invocation identity inputs must be trimmed strings.")
    return hashlib.sha256(
        (
            f"{request_id}\n{plan_digest}\n{adapter_id}\n{authorized_model_id}\n"
            "o-ai.d155.ai-usage.invocation.v1"
        ).encode("utf-8")
    ).hexdigest()


class AIUsageMeter:
    """Persist one safe usage observation without affecting AI success semantics."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        pricing: AIUsagePricing | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        if not callable(session_factory):
            raise TypeError("session_factory must be callable.")
        if not callable(clock):
            raise TypeError("clock must be callable.")
        self._session_factory = session_factory
        self._pricing = pricing or AIUsagePricing()
        self._clock = clock

    def build_observation(
        self,
        *,
        request_id: str,
        plan_digest: str,
        adapter_id: str,
        authorized_model_id: str,
        result: AIResult,
    ) -> AIUsageObservation:
        if not isinstance(result, AIResult):
            raise TypeError("result must be an AIResult.")
        invocation_digest = ai_usage_invocation_digest(
            request_id=request_id,
            plan_digest=plan_digest,
            adapter_id=adapter_id,
            authorized_model_id=authorized_model_id,
        )
        request_digest = _request_digest(request_id)
        occurred_at = self._clock()
        if not isinstance(occurred_at, datetime):
            raise ValueError("AI usage meter clock must return datetime.")

        if adapter_id == LOCAL_AI_ADAPTER_ID:
            return AIUsageObservation(
                invocation_digest=invocation_digest,
                request_digest=request_digest,
                plan_digest=plan_digest,
                adapter_id=adapter_id,
                authorized_model_id=authorized_model_id,
                provider_id=AI_USAGE_PROVIDER_LOCAL,
                model_id=authorized_model_id,
                pricing_mode=AI_USAGE_PRICING_MODE_NOT_APPLICABLE,
                usage_status="not_applicable",
                billing_status="not_applicable",
                occurred_at=occurred_at,
            )

        measurement = result.metadata.get(AI_USAGE_METADATA_KEY)
        if not isinstance(measurement, AIUsageMeasurement):
            provider_id = (
                AI_USAGE_PROVIDER_OPENAI
                if adapter_id == CHATGPT_DEFAULT_ADAPTER_ID
                else AI_USAGE_PROVIDER_UNKNOWN
            )
            return AIUsageObservation(
                invocation_digest=invocation_digest,
                request_digest=request_digest,
                plan_digest=plan_digest,
                adapter_id=adapter_id,
                authorized_model_id=authorized_model_id,
                provider_id=provider_id,
                model_id=authorized_model_id,
                pricing_mode=AI_USAGE_PRICING_MODE_UNKNOWN,
                usage_status="unavailable",
                billing_status="unknown",
                occurred_at=occurred_at,
            )

        price = self._pricing.price(measurement)
        return AIUsageObservation(
            invocation_digest=invocation_digest,
            request_digest=request_digest,
            plan_digest=plan_digest,
            adapter_id=adapter_id,
            authorized_model_id=authorized_model_id,
            provider_id=measurement.provider_id,
            model_id=measurement.model_id,
            pricing_mode=measurement.pricing_mode,
            usage_status="measured",
            billing_status=price.status,  # type: ignore[arg-type]
            input_tokens=measurement.input_tokens,
            cached_input_tokens=measurement.cached_input_tokens,
            cache_write_tokens=measurement.cache_write_tokens,
            output_tokens=measurement.output_tokens,
            reasoning_tokens=measurement.reasoning_tokens,
            total_tokens=measurement.total_tokens,
            pricing_version=price.pricing_version,
            estimated_cost_nano_usd=price.estimated_cost_nano_usd,
            occurred_at=occurred_at,
        )

    def try_record_success(
        self,
        *,
        request_id: str,
        plan_digest: str,
        adapter_id: str,
        authorized_model_id: str,
        result: AIResult,
    ) -> bool:
        """Record once; every failure is isolated from the successful AI result."""
        try:
            observation = self.build_observation(
                request_id=request_id,
                plan_digest=plan_digest,
                adapter_id=adapter_id,
                authorized_model_id=authorized_model_id,
                result=result,
            )
        except Exception:
            logger.warning("AI usage observation construction failed")
            return False

        session: Session | None = None
        try:
            session = self._session_factory()
            repository = AIUsageEventRepository(session)
            if repository.get_by_invocation_digest(observation.invocation_digest) is not None:
                return True
            repository.append(observation)
            session.commit()
            return True
        except IntegrityError:
            if session is None:
                logger.warning("AI usage persistence failed")
                return False
            try:
                session.rollback()
                repository = AIUsageEventRepository(session)
                return repository.get_by_invocation_digest(
                    observation.invocation_digest
                ) is not None
            except Exception:
                logger.warning("AI usage idempotency verification failed")
                return False
        except Exception:
            if session is not None:
                try:
                    session.rollback()
                except Exception:
                    pass
            logger.warning("AI usage persistence failed")
            return False
        finally:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass
