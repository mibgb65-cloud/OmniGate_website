from __future__ import annotations

import unittest

from src.modules.google.actions.google_family_status_actions import GoogleFamilyActions
from src.modules.google.models.google_action_results import GoogleFamilyMemberInfo


class TestGoogleFamilyActions(unittest.TestCase):
    def test_should_dedupe_members_by_email(self) -> None:
        action = GoogleFamilyActions(browser_actions=object())

        deduped = action._dedupe_members(
            [
                GoogleFamilyMemberInfo(
                    member_name="Pang Yiyun",
                    member_role="member",
                    member_email="pangyiyun08@gmail.com",
                    member_href="https://example.com/member/1",
                ),
                GoogleFamilyMemberInfo(
                    member_name="Pang Yiyun Duplicate",
                    member_role="manager",
                    member_email="PANGYIYUN08@gmail.com",
                    member_href="https://example.com/member/2",
                ),
                GoogleFamilyMemberInfo(
                    member_name="Another Member",
                    member_role="member",
                    member_email="another@gmail.com",
                    member_href="https://example.com/member/3",
                ),
            ]
        )

        self.assertEqual(2, len(deduped))
        self.assertEqual("pangyiyun08@gmail.com", deduped[0].member_email)
        self.assertEqual("another@gmail.com", deduped[1].member_email)
