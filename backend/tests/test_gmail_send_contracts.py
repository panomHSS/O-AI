from __future__ import annotations

import unittest
import unicodedata
from dataclasses import FrozenInstanceError, fields

from app.contracts.gmail_send import (
    GMAIL_SEND_CONTRACT_VERSION,
    GMAIL_SEND_MAX_BODY_BYTES,
    GMAIL_SEND_MAX_RECIPIENT_BYTES,
    GMAIL_SEND_MAX_SUBJECT_BYTES,
    GMAIL_SEND_OPERATION,
    GmailSendDraft,
    GmailSendRequest,
)


class GmailSendContractTests(unittest.TestCase):
    def make_draft(
        self,
        *,
        recipient: str = "alice@example.com",
        subject: str = "Subject",
        body: str = "Body",
    ) -> GmailSendDraft:
        return GmailSendDraft(
            recipient=recipient,
            subject=subject,
            body=body,
        )

    def test_valid_request_is_exact_immutable_and_slotted(self) -> None:
        draft = self.make_draft(
            recipient="Alice.Project+tag@Example.COM",
            subject="รายงานประจำวัน",
            body="  สวัสดีครับ\nนี่คือรายงานวันนี้\tขอบคุณครับ  \n",
        )
        request = GmailSendRequest(message=draft)

        self.assertEqual(request.contract_version, "1")
        self.assertEqual(request.operation, "send_message")
        self.assertIs(request.message, draft)
        self.assertEqual(
            draft.recipient,
            "Alice.Project+tag@Example.COM",
        )
        self.assertEqual(draft.subject, "รายงานประจำวัน")
        self.assertEqual(
            draft.body,
            "  สวัสดีครับ\nนี่คือรายงานวันนี้\tขอบคุณครับ  \n",
        )
        self.assertFalse(hasattr(draft, "__dict__"))
        self.assertFalse(hasattr(request, "__dict__"))

        with self.assertRaises(FrozenInstanceError):
            draft.subject = "changed"  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            request.message = draft  # type: ignore[misc]

    def test_contract_identity_and_exact_field_surface(self) -> None:
        self.assertEqual(GMAIL_SEND_CONTRACT_VERSION, "1")
        self.assertEqual(GMAIL_SEND_OPERATION, "send_message")
        self.assertEqual(GMAIL_SEND_MAX_RECIPIENT_BYTES, 320)
        self.assertEqual(GMAIL_SEND_MAX_SUBJECT_BYTES, 1024)
        self.assertEqual(GMAIL_SEND_MAX_BODY_BYTES, 16 * 1024)

        self.assertEqual(
            tuple(field.name for field in fields(GmailSendDraft)),
            ("recipient", "subject", "body"),
        )
        self.assertEqual(
            tuple(field.name for field in fields(GmailSendRequest)),
            ("message", "contract_version", "operation"),
        )

    def test_recipient_accepts_exact_single_ascii_mailbox_without_rewrite(self) -> None:
        for recipient in (
            "alice@example.com",
            "team.ops@example.co.th",
            "user+project@example.com",
            "UPPER.Case+Tag@Example.COM",
        ):
            with self.subTest(recipient=recipient):
                draft = self.make_draft(recipient=recipient)
                self.assertEqual(draft.recipient, recipient)

    def test_recipient_rejects_multiple_display_name_and_separator_forms(self) -> None:
        invalid = (
            "Alice <alice@example.com>",
            "alice@example.com,bob@example.com",
            "alice@example.com, bob@example.com",
            "alice@example.com;bob@example.com",
            "alice@example.com; bob@example.com",
            "alice@example.com bob@example.com",
            "alice@example.com\nbob@example.com",
            "alice@example.com\tbob@example.com",
        )
        for recipient in invalid:
            with self.subTest(recipient=repr(recipient)):
                with self.assertRaisesRegex(
                    ValueError,
                    "^gmail_send_recipient_invalid$",
                ):
                    self.make_draft(recipient=recipient)

    def test_recipient_rejects_empty_whitespace_unicode_and_invalid_syntax(self) -> None:
        invalid = (
            "",
            " ",
            " alice@example.com",
            "alice@example.com ",
            "alice",
            "@company.com",
            "alice@",
            "alice@example",
            ".alice@example.com",
            "alice..test@example.com",
            "alice@-example.com",
            "alice@example-.com",
            "ผู้ใช้@example.com",
            "alice@ตัวอย่าง.com",
            "alice@example.com\r",
            "alice@example.com\x00",
            "alice@example.com\x1b",
        )
        for recipient in invalid:
            with self.subTest(recipient=repr(recipient)):
                with self.assertRaisesRegex(
                    ValueError,
                    "^gmail_send_recipient_invalid$",
                ):
                    self.make_draft(recipient=recipient)

    def test_recipient_byte_limit_is_enforced_exactly(self) -> None:
        suffix = "@example.com"
        exact = "a" * (
            GMAIL_SEND_MAX_RECIPIENT_BYTES - len(suffix.encode("utf-8"))
        ) + suffix
        self.assertEqual(
            len(exact.encode("utf-8")),
            GMAIL_SEND_MAX_RECIPIENT_BYTES,
        )
        self.assertEqual(self.make_draft(recipient=exact).recipient, exact)

        over = "a" + exact
        self.assertEqual(
            len(over.encode("utf-8")),
            GMAIL_SEND_MAX_RECIPIENT_BYTES + 1,
        )
        with self.assertRaisesRegex(
            ValueError,
            "^gmail_send_recipient_invalid$",
        ):
            self.make_draft(recipient=over)

    def test_subject_rejects_empty_whitespace_edges_and_header_injection(self) -> None:
        invalid = (
            "",
            " ",
            "   ",
            " Subject",
            "Subject ",
            "\tSubject",
            "Subject\t",
            "\nSubject",
            "Subject\n",
            "Hello\nBcc: attacker@example.com",
            "Hello\rBcc: attacker@example.com",
            "Hello\r\nBcc: attacker@example.com",
            "Hello\x00World",
            "Hello\x1bWorld",
            "Hello\x7fWorld",
        )
        for subject in invalid:
            with self.subTest(subject=repr(subject)):
                with self.assertRaisesRegex(
                    ValueError,
                    "^gmail_send_subject_invalid$",
                ):
                    self.make_draft(subject=subject)

    def test_subject_utf8_byte_boundaries_and_unicode_preservation(self) -> None:
        exact_ascii = "a" * GMAIL_SEND_MAX_SUBJECT_BYTES
        self.assertEqual(
            len(exact_ascii.encode("utf-8")),
            GMAIL_SEND_MAX_SUBJECT_BYTES,
        )
        self.assertEqual(
            self.make_draft(subject=exact_ascii).subject,
            exact_ascii,
        )

        with self.assertRaisesRegex(
            ValueError,
            "^gmail_send_subject_invalid$",
        ):
            self.make_draft(
                subject="a" * (GMAIL_SEND_MAX_SUBJECT_BYTES + 1)
            )

        thai_char = "ก"
        over_thai = thai_char * (
            GMAIL_SEND_MAX_SUBJECT_BYTES
            // len(thai_char.encode("utf-8"))
            + 1
        )
        self.assertGreater(
            len(over_thai.encode("utf-8")),
            GMAIL_SEND_MAX_SUBJECT_BYTES,
        )
        with self.assertRaisesRegex(
            ValueError,
            "^gmail_send_subject_invalid$",
        ):
            self.make_draft(subject=over_thai)

        composed = "Café"
        decomposed = unicodedata.normalize("NFD", composed)
        self.assertNotEqual(composed, decomposed)
        self.assertEqual(self.make_draft(subject=composed).subject, composed)
        self.assertEqual(
            self.make_draft(subject=decomposed).subject,
            decomposed,
        )

    def test_body_allows_only_newline_and_tab_control_characters(self) -> None:
        allowed = "line one\n\tline two"
        self.assertEqual(self.make_draft(body=allowed).body, allowed)

        forbidden_controls = (
            "\x00",
            "\x01",
            "\x08",
            "\x0b",
            "\x0c",
            "\r",
            "\x1b",
            "\x7f",
        )
        for control in forbidden_controls:
            body = f"before{control}after"
            with self.subTest(control=repr(control)):
                with self.assertRaisesRegex(
                    ValueError,
                    "^gmail_send_body_invalid$",
                ):
                    self.make_draft(body=body)

    def test_body_rejects_empty_or_whitespace_only_but_preserves_edges(self) -> None:
        for body in (
            "",
            " ",
            "   ",
            "\n",
            "\t",
            "\n\t",
            " \n \t ",
        ):
            with self.subTest(body=repr(body)):
                with self.assertRaisesRegex(
                    ValueError,
                    "^gmail_send_body_invalid$",
                ):
                    self.make_draft(body=body)

        preserved = "  Body starts here\nBody ends here  \n"
        self.assertEqual(
            self.make_draft(body=preserved).body,
            preserved,
        )

    def test_body_utf8_byte_boundaries_and_no_normalization(self) -> None:
        exact_ascii = "a" * GMAIL_SEND_MAX_BODY_BYTES
        self.assertEqual(
            len(exact_ascii.encode("utf-8")),
            GMAIL_SEND_MAX_BODY_BYTES,
        )
        self.assertEqual(
            self.make_draft(body=exact_ascii).body,
            exact_ascii,
        )

        with self.assertRaisesRegex(
            ValueError,
            "^gmail_send_body_invalid$",
        ):
            self.make_draft(
                body="a" * (GMAIL_SEND_MAX_BODY_BYTES + 1)
            )

        thai_char = "ก"
        over_thai = thai_char * (
            GMAIL_SEND_MAX_BODY_BYTES // len(thai_char.encode("utf-8")) + 1
        )
        self.assertGreater(
            len(over_thai.encode("utf-8")),
            GMAIL_SEND_MAX_BODY_BYTES,
        )
        with self.assertRaisesRegex(
            ValueError,
            "^gmail_send_body_invalid$",
        ):
            self.make_draft(body=over_thai)

        composed = "Café body"
        decomposed = unicodedata.normalize("NFD", composed)
        self.assertNotEqual(composed, decomposed)
        self.assertEqual(self.make_draft(body=composed).body, composed)
        self.assertEqual(self.make_draft(body=decomposed).body, decomposed)

    def test_request_rejects_wrong_draft_types_fail_closed(self) -> None:
        for invalid in (
            None,
            object(),
            {},
            {"recipient": "alice@example.com"},
            "alice@example.com",
        ):
            with self.subTest(invalid=type(invalid).__name__):
                with self.assertRaisesRegex(
                    ValueError,
                    "^gmail_send_draft_invalid$",
                ):
                    GmailSendRequest(message=invalid)  # type: ignore[arg-type]

    def test_contract_version_and_operation_are_not_caller_settable(self) -> None:
        draft = self.make_draft()
        with self.assertRaises(TypeError):
            GmailSendRequest(
                message=draft,
                contract_version="2",  # type: ignore[call-arg]
            )
        with self.assertRaises(TypeError):
            GmailSendRequest(
                message=draft,
                operation="other",  # type: ignore[call-arg]
            )

    def test_contract_exposes_no_out_of_scope_send_surface(self) -> None:
        draft = self.make_draft()
        request = GmailSendRequest(message=draft)
        forbidden = (
            "sender",
            "from_address",
            "to",
            "recipients",
            "cc",
            "bcc",
            "html",
            "mime",
            "raw",
            "attachments",
            "reply_to",
            "thread_id",
            "message_id",
            "draft_id",
            "schedule_at",
            "credential",
            "credential_profile",
            "oauth_scope",
            "approval_id",
            "write_digest",
            "capability_id",
            "adapter_id",
            "retry",
        )
        for name in forbidden:
            with self.subTest(name=name):
                self.assertFalse(hasattr(draft, name))
                self.assertFalse(hasattr(request, name))


if __name__ == "__main__":
    unittest.main()
