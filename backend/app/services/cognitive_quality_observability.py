"""D156 best-effort durable cognitive quality recorder."""
from __future__ import annotations
import logging
from collections.abc import Callable
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.contracts.cognitive_quality_observability import CognitiveQualityObservation
from app.repositories.cognitive_quality_observations import CognitiveQualityObservationRepository

logger = logging.getLogger(__name__)


class CognitiveQualityRecorder:
    def __init__(self, *, session_factory: Callable[[], Session]) -> None:
        if not callable(session_factory): raise TypeError("session_factory must be callable")
        self._session_factory = session_factory
    def try_record(self, observation: CognitiveQualityObservation) -> bool:
        try:
            if not isinstance(observation, CognitiveQualityObservation): return False
            observation.__post_init__()
        except Exception:
            return False
        session = None
        try:
            session = self._session_factory()
            repo = CognitiveQualityObservationRepository(session)
            existing = repo.get_by_turn_digest(observation.turn_digest)
            if existing is not None:
                return existing.projection_fingerprint == observation.projection_fingerprint
            repo.append(observation); session.commit(); return True
        except IntegrityError:
            if session is None: return False
            try:
                session.rollback(); existing = CognitiveQualityObservationRepository(session).get_by_turn_digest(observation.turn_digest)
                return existing is not None and existing.projection_fingerprint == observation.projection_fingerprint
            except Exception:
                logger.warning("Cognitive quality idempotency verification failed"); return False
        except Exception:
            if session is not None:
                try: session.rollback()
                except Exception: pass
            logger.warning("Cognitive quality persistence failed"); return False
        finally:
            if session is not None:
                try: session.close()
                except Exception: pass
