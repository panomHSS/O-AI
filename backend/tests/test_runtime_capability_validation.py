import unittest

from app.plugins.default_runtime_capability_validator import (
    DefaultRuntimeCapabilityValidator,
)


class RuntimeCapabilityValidationTests(
    unittest.TestCase,
):
    """Tests for runtime capability validation."""

    def test_validator_can_be_created(
        self,
    ) -> None:
        validator = DefaultRuntimeCapabilityValidator()

        self.assertIsNotNone(
            validator,
        )