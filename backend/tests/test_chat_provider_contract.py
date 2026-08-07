import unittest

from app.providers.base import (
    ChatConfigurationError as ProviderChatConfigurationError,
)
from app.providers.base import (
    ChatProvider as ProviderChatProvider,
)
from app.providers.base import (
    ChatProviderError as ProviderChatProviderError,
)
from app.services.chat import (
    ChatConfigurationError as ServiceChatConfigurationError,
)
from app.services.chat import (
    ChatProvider as ServiceChatProvider,
)
from app.services.chat import (
    ChatProviderError as ServiceChatProviderError,
)


class ChatProviderContractCompatibilityTests(
    unittest.TestCase
):
    def test_service_contract_remains_importable(
        self,
    ) -> None:
        self.assertIsNotNone(
            ServiceChatProvider,
        )

    def test_service_configuration_error_remains_importable(
        self,
    ) -> None:
        self.assertTrue(
            issubclass(
                ServiceChatConfigurationError,
                Exception,
            )
        )

    def test_service_provider_error_remains_importable(
        self,
    ) -> None:
        self.assertTrue(
            issubclass(
                ServiceChatProviderError,
                Exception,
            )
        )

    def test_neutral_chat_provider_contract_exists(
        self,
    ) -> None:
        self.assertIsNotNone(
            ProviderChatProvider,
        )

    def test_neutral_configuration_error_exists(
        self,
    ) -> None:
        self.assertTrue(
            issubclass(
                ProviderChatConfigurationError,
                Exception,
            )
        )

    def test_neutral_provider_error_exists(
        self,
    ) -> None:
        self.assertTrue(
            issubclass(
                ProviderChatProviderError,
                Exception,
            )
        )

    def test_service_chat_provider_is_neutral_contract(
        self,
    ) -> None:
        self.assertIs(
            ServiceChatProvider,
            ProviderChatProvider,
        )

    def test_service_configuration_error_is_neutral_error(
        self,
    ) -> None:
        self.assertIs(
            ServiceChatConfigurationError,
            ProviderChatConfigurationError,
        )

    def test_service_provider_error_is_neutral_error(
        self,
    ) -> None:
        self.assertIs(
            ServiceChatProviderError,
            ProviderChatProviderError,
        )


if __name__ == "__main__":
    unittest.main()