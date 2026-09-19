from tests.workspace_fixture import TEST_WORKSPACE_SCOPE

import unittest
from types import SimpleNamespace
from uuid import UUID, uuid4
from fastapi import HTTPException
from app.api.v1.chat import send_chat_message
from app.schemas.chat import ChatRequest
from app.services.chat_cross_connector import CrossConnectorChatOutcome

CID=UUID("78787878-7878-7878-7878-787878787878")
class Exploding:
    def __getattr__(self, name): raise AssertionError(f"unexpected dependency access: {name}")
class CrossStub:
    def __init__(self): self.calls=[]
    def is_request(self, message): return True
    def process(self, **kwargs): self.calls.append(kwargs); return CrossConnectorChatOutcome(conversation_id=kwargs["conversation_id"], reply="cross answer")

class CrossConnectorApiTests(unittest.TestCase):
    def call(self, payload, service, header="1"):
        return send_chat_message(
            workspace_scope=TEST_WORKSPACE_SCOPE,
            request=SimpleNamespace(state=SimpleNamespace(request_id="req-78")), payload=payload,
            command_input_pipeline=Exploding(), command_orchestrator=Exploding(),
            project_update_orchestrator=Exploding(), chat_action_bridge=Exploding(),
            cross_connector_chat_service=service, x_oai_local_request=header)

    def test_priority_skips_plugin_normal_and_project_paths(self):
        s=CrossStub(); result=self.call(ChatRequest(message="สรุปอีเมลกับปฏิทินที่เพิ่งอ่าน", conversation_id=CID), s)
        self.assertEqual(result.data.reply, "cross answer"); self.assertEqual(result.data.conversation_id, CID)
        self.assertIsNone(result.data.action); self.assertIsNone(result.data.project_update_proposal)
        self.assertEqual(s.calls[0]["request_id"], "req-78")

    def test_local_header_and_existing_conversation_are_required(self):
        s=CrossStub()
        with self.assertRaises(HTTPException) as e:
            self.call(ChatRequest(message="summarize my recent Gmail and Calendar results", conversation_id=CID), s, None)
        self.assertEqual(e.exception.status_code, 403); self.assertEqual(s.calls, [])
        with self.assertRaises(HTTPException) as e:
            self.call(ChatRequest(message="summarize my recent Gmail and Calendar results"), s)
        self.assertEqual(e.exception.status_code, 400); self.assertEqual(s.calls, [])
        with self.assertRaises(HTTPException) as e:
            self.call(ChatRequest(message="summarize my recent Gmail and Calendar results", conversation_id=CID, project_id=uuid4()), s)
        self.assertEqual(e.exception.status_code, 400); self.assertEqual(s.calls, [])

if __name__ == "__main__": unittest.main()
