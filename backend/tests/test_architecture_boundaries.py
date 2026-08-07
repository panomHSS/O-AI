import ast
import unittest
from pathlib import Path


def find_forbidden_openai_imports_in_source(
    source: str,
    source_path: Path,
) -> list[str]:
    tree = ast.parse(
        source,
        filename=str(source_path),
    )

    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if (
                    alias.name == "openai"
                    or alias.name.startswith("openai.")
                ):
                    violations.append(
                        f"{source_path}:{node.lineno} "
                        f"imports {alias.name}"
                    )

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""

            if (
                module == "openai"
                or module.startswith("openai.")
            ):
                violations.append(
                    f"{source_path}:{node.lineno} "
                    f"imports from {module}"
                )

    return violations


def find_forbidden_openai_imports(
    source_path: Path,
) -> list[str]:
    source = source_path.read_text(
        encoding="utf-8-sig",
    )

    return find_forbidden_openai_imports_in_source(
        source,
        source_path,
    )


def find_forbidden_service_imports_in_source(
    source: str,
    source_path: Path,
) -> list[str]:
    tree = ast.parse(
        source,
        filename=str(source_path),
    )

    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if (
                    alias.name == "app.services"
                    or alias.name.startswith("app.services.")
                ):
                    violations.append(
                        f"{source_path}:{node.lineno} "
                        f"imports {alias.name}"
                    )

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""

            if (
                module == "app.services"
                or module.startswith("app.services.")
            ):
                violations.append(
                    f"{source_path}:{node.lineno} "
                    f"imports from {module}"
                )

    return violations


class ArchitectureBoundaryTests(unittest.TestCase):
    def test_services_do_not_import_openai_sdk_directly(
        self,
    ) -> None:
        services_root = (
            Path(__file__).resolve().parents[1]
            / "app"
            / "services"
        )

        violations: list[str] = []

        for source_path in services_root.rglob("*.py"):
            violations.extend(
                find_forbidden_openai_imports(
                    source_path,
                )
            )

        self.assertEqual(
            violations,
            [],
            "O-AI application services must not import "
            "the OpenAI SDK directly. External AI SDKs "
            "belong behind provider boundaries.\n"
            + "\n".join(violations),
        )

    def test_detector_rejects_direct_openai_import(
        self,
    ) -> None:
        violations = find_forbidden_openai_imports_in_source(
            "import openai\n",
            Path("synthetic_service.py"),
        )

        self.assertEqual(
            violations,
            [
                "synthetic_service.py:1 imports openai",
            ],
        )

    def test_detector_rejects_from_openai_import(
        self,
    ) -> None:
        violations = find_forbidden_openai_imports_in_source(
            "from openai import OpenAI\n",
            Path("synthetic_service.py"),
        )

        self.assertEqual(
            violations,
            [
                "synthetic_service.py:1 imports from openai",
            ],
        )

    def test_detector_allows_oai_provider_import(
        self,
    ) -> None:
        violations = find_forbidden_openai_imports_in_source(
            (
                "from app.providers.openai_provider "
                "import OpenAIChatProvider\n"
            ),
            Path("synthetic_service.py"),
        )

        self.assertEqual(
            violations,
            [],
        )

    def test_providers_do_not_import_application_services(
        self,
    ) -> None:
        providers_root = (
            Path(__file__).resolve().parents[1]
            / "app"
            / "providers"
        )

        violations: list[str] = []

        for source_path in providers_root.rglob("*.py"):
            source = source_path.read_text(
                encoding="utf-8-sig",
            )

            violations.extend(
                find_forbidden_service_imports_in_source(
                    source,
                    source_path,
                )
            )

        self.assertEqual(
            violations,
            [],
            "O-AI providers must not depend on "
            "application services.\n"
            + "\n".join(violations),
        )

    def test_provider_guardrail_rejects_service_import(
        self,
    ) -> None:
        violations = find_forbidden_service_imports_in_source(
            "import app.services.chat\n",
            Path("synthetic_provider.py"),
        )

        self.assertEqual(
            violations,
            [
                (
                    "synthetic_provider.py:1 "
                    "imports app.services.chat"
                ),
            ],
        )

    def test_provider_guardrail_rejects_from_service_import(
        self,
    ) -> None:
        violations = find_forbidden_service_imports_in_source(
            (
                "from app.services.chat "
                "import ChatService\n"
            ),
            Path("synthetic_provider.py"),
        )

        self.assertEqual(
            violations,
            [
                (
                    "synthetic_provider.py:1 "
                    "imports from app.services.chat"
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
