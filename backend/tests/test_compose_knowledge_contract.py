"""Deployment contract checks for the Docker Knowledge source boundary."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path


class ComposeKnowledgeContractTests(unittest.TestCase):
    def _render_compose(self) -> tuple[Path, dict[str, object]]:
        if shutil.which("docker") is None:
            self.skipTest("Docker Compose is required to render the deployment contract.")

        repository_root = Path(__file__).resolve().parents[2]
        completed = subprocess.run(
            ["docker", "compose", "config", "--format", "json"],
            cwd=repository_root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return repository_root, json.loads(completed.stdout)["services"]

    def test_backend_mounts_only_the_repository_knowledge_directory_read_only(self) -> None:
        repository_root, services = self._render_compose()
        backend = services["backend"]

        self.assertEqual(backend["environment"]["OAI_KNOWLEDGE_ROOT"], "/app/knowledge")
        volumes = {item["target"]: item for item in backend["volumes"]}
        self.assertIn("/app/data", volumes)
        self.assertIn("/app/knowledge", volumes)
        knowledge_mount = volumes["/app/knowledge"]
        self.assertEqual(
            os.path.normcase(knowledge_mount["source"]),
            os.path.normcase(str(repository_root / "knowledge")),
        )
        self.assertTrue(knowledge_mount["read_only"])

        knowledge_target = knowledge_mount["target"].rstrip("/")
        read_write_ancestors = [
            mount["target"]
            for mount in backend["volumes"]
            if mount["target"].rstrip("/") != knowledge_target
            and knowledge_target.startswith(f"{mount['target'].rstrip('/')}/")
            and not mount.get("read_only", False)
        ]
        self.assertEqual(read_write_ancestors, [])

    def test_frontend_and_backend_publish_only_to_loopback(self) -> None:
        _, services = self._render_compose()
        for service_name, expected_port in (("backend", 8000), ("frontend", 3000)):
            with self.subTest(service=service_name):
                self.assertEqual(
                    services[service_name]["ports"],
                    [{
                        "mode": "ingress",
                        "host_ip": "127.0.0.1",
                        "target": expected_port,
                        "published": str(expected_port),
                        "protocol": "tcp",
                    }],
                )
