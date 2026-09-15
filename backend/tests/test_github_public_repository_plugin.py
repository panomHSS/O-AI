import json
import unittest

from app.connectors.github_public_repository import (
    GITHUB_CONNECTOR_ERROR_INVALID_REFERENCE,
    GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE,
    GITHUB_CONNECTOR_ERROR_NETWORK,
    GitHubPublicRepositoryConnectorError,
    GitHubPublicRepositoryMetadata,
)
from app.plugins.context import PluginExecutionContext
from app.plugins.github_public_repository import (
    GITHUB_PUBLIC_REPOSITORY_ADAPTER_ID,
    GITHUB_PUBLIC_REPOSITORY_CAPABILITY,
    GITHUB_PUBLIC_REPOSITORY_CAPABILITY_ID,
    GITHUB_PUBLIC_REPOSITORY_OPERATION,
    GITHUB_PUBLIC_REPOSITORY_PLUGIN_ID,
    GITHUB_PUBLIC_REPOSITORY_PLUGIN_VERSION,
    GitHubPublicRepositoryPlugin,
)
from app.plugins.request import PluginRequest


class FakeReader:
    def __init__(self, result=None, *, error=None) -> None:
        self.result = result if result is not None else self.metadata()
        self.error = error
        self.calls = 0
        self.references = []

    @staticmethod
    def metadata(**changes):
        values = {
            "full_name": "openai/openai-python",
            "description": "OpenAI Python library",
            "html_url": "https://github.com/openai/openai-python",
            "default_branch": "main",
            "language": "Python",
            "visibility": "public",
            "archived": False,
            "fork": False,
            "stargazers_count": 10,
            "forks_count": 2,
            "open_issues_count": 1,
            "license": "Apache-2.0",
            "updated_at": "2026-09-15T00:00:00Z",
        }
        values.update(changes)
        return GitHubPublicRepositoryMetadata(**values)

    def get_repository_metadata(self, reference):
        self.calls += 1
        self.references.append(reference)
        if self.error is not None:
            raise self.error
        return self.result


class GitHubPublicRepositoryPluginTests(unittest.TestCase):
    def test_identity_is_exact_and_static(self):
        plugin = GitHubPublicRepositoryPlugin(client=FakeReader())
        self.assertEqual(plugin.id, GITHUB_PUBLIC_REPOSITORY_PLUGIN_ID)
        self.assertEqual(plugin.version, GITHUB_PUBLIC_REPOSITORY_PLUGIN_VERSION)
        self.assertEqual(GITHUB_PUBLIC_REPOSITORY_CAPABILITY, "repository_metadata")
        self.assertEqual(
            GITHUB_PUBLIC_REPOSITORY_ADAPTER_ID,
            "module.plugin.github_public_repo",
        )
        self.assertEqual(
            GITHUB_PUBLIC_REPOSITORY_OPERATION,
            "get_repository_metadata",
        )
        self.assertEqual(
            GITHUB_PUBLIC_REPOSITORY_CAPABILITY_ID,
            "exec.plugin.github_public_repo.repository_metadata",
        )

    def test_execute_calls_reader_once_and_returns_canonical_json(self):
        reader = FakeReader()
        plugin = GitHubPublicRepositoryPlugin(client=reader)
        result = plugin.execute(
            PluginExecutionContext(),
            PluginRequest(content="openai/openai-python"),
        )
        self.assertEqual(reader.calls, 1)
        self.assertEqual(reader.references, ["openai/openai-python"])
        parsed = json.loads(result.content)
        self.assertEqual(parsed["full_name"], "openai/openai-python")
        self.assertEqual(parsed["visibility"], "public")
        self.assertLessEqual(len(result.content.encode("utf-8")), 16 * 1024)
        self.assertEqual(
            result.content,
            json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )

    def test_invalid_reference_is_rejected_before_reader(self):
        reader = FakeReader()
        plugin = GitHubPublicRepositoryPlugin(client=reader)
        with self.assertRaises(GitHubPublicRepositoryConnectorError) as caught:
            plugin.execute(
                PluginExecutionContext(),
                PluginRequest(content="https://github.com/openai/openai-python"),
            )
        self.assertEqual(caught.exception.code, GITHUB_CONNECTOR_ERROR_INVALID_REFERENCE)
        self.assertEqual(reader.calls, 0)

    def test_safe_connector_error_is_preserved(self):
        reader = FakeReader(
            error=GitHubPublicRepositoryConnectorError(
                GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE
            )
        )
        plugin = GitHubPublicRepositoryPlugin(client=reader)
        with self.assertRaises(GitHubPublicRepositoryConnectorError) as caught:
            plugin.execute(
                PluginExecutionContext(),
                PluginRequest(content="openai/openai-python"),
            )
        self.assertEqual(caught.exception.code, GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE)
        self.assertEqual(reader.calls, 1)

    def test_unexpected_reader_error_is_normalized(self):
        reader = FakeReader(error=RuntimeError("sensitive"))
        plugin = GitHubPublicRepositoryPlugin(client=reader)
        with self.assertRaises(GitHubPublicRepositoryConnectorError) as caught:
            plugin.execute(
                PluginExecutionContext(),
                PluginRequest(content="openai/openai-python"),
            )
        self.assertEqual(caught.exception.code, GITHUB_CONNECTOR_ERROR_NETWORK)
        self.assertNotIn("sensitive", str(caught.exception))
        self.assertEqual(reader.calls, 1)

    def test_invalid_reader_result_is_rejected(self):
        reader = FakeReader(result={"not": "metadata"})
        plugin = GitHubPublicRepositoryPlugin(client=reader)
        with self.assertRaises(GitHubPublicRepositoryConnectorError) as caught:
            plugin.execute(
                PluginExecutionContext(),
                PluginRequest(content="openai/openai-python"),
            )
        self.assertEqual(caught.exception.code, GITHUB_CONNECTOR_ERROR_INVALID_RESPONSE)

    def test_constructing_plugin_does_not_read_network(self):
        reader = FakeReader()
        GitHubPublicRepositoryPlugin(client=reader)
        self.assertEqual(reader.calls, 0)


if __name__ == "__main__":
    unittest.main()
