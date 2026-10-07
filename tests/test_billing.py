import copy
import unittest
from paper_workspace.billing import verify_billing


class BillingEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.now = 2000000000
        self.record = {
            'policy': 'included-allowance-v1', 'checked_at': self.now,
            'source': 'Codex app get_usage_limits',
            'purchases_authorized': False, 'resets_authorized': False,
            'usage_snapshot': {'rateLimitsByLimitId': {'codex': {
                'planType': 'pro', 'spendControlReached': False,
                'rateLimitReachedType': None, 'individualLimit': None,
                'credits': {'hasCredits': True, 'balance': '1000'},
                'primary': {'usedPercent': 1, 'resetsAt': self.now + 10000},
                'secondary': None,
            }}},
        }

    def test_fresh_included_allowance_does_not_claim_zero_credits(self):
        self.assertEqual(verify_billing(self.record, self.now), 'included-allowance-v1')
        self.assertNotIn('no_paid_credits_verified', self.record)

    def test_stale_future_and_nonfinite_timestamps_fail(self):
        for checked in (self.now - 301, self.now + 1, float('nan'), True):
            record = {**self.record, 'checked_at': checked}
            with self.assertRaises(ValueError):
                verify_billing(record, self.now)

    def test_missing_exhausted_or_high_usage_fails(self):
        for used in (None, 25, 100, -1, float('nan'), True):
            record = copy.deepcopy(self.record)
            record['usage_snapshot']['rateLimitsByLimitId']['codex']['primary']['usedPercent'] = used
            with self.assertRaises(ValueError):
                verify_billing(record, self.now)

    def test_nonzero_second_bucket_cannot_be_ignored(self):
        record = copy.deepcopy(self.record)
        record['usage_snapshot']['rateLimitsByLimitId']['other'] = {
            **record['usage_snapshot']['rateLimitsByLimitId']['codex'],
            'primary': {'usedPercent': 90, 'resetsAt': self.now + 1000}}
        with self.assertRaises(ValueError):
            verify_billing(record, self.now)

    def test_legacy_requires_recent_true_verification(self):
        self.assertEqual(verify_billing({'checked_at': self.now, 'no_paid_credits_verified': True}, self.now), 'legacy-zero-credit')
        for record in ({}, {'checked_at': self.now - 86400, 'no_paid_credits_verified': True}, {'checked_at': self.now}):
            with self.assertRaises(ValueError):
                verify_billing(record, self.now)


if __name__ == '__main__':
    unittest.main()
