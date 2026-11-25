import unittest

from ledger import settlement


class ParseSharesRoundingTests(unittest.TestCase):
    def assertSumsTo(self, shares, amount):
        self.assertAlmostEqual(sum(shares.values()), amount, places=9)

    def test_equal_split_sums_exactly_to_amount(self):
        shares = settlement.parse_shares("A,B,C", 100, "A")
        self.assertSumsTo(shares, 100)
        self.assertEqual(sorted(shares.values()), [33.33, 33.33, 33.34])

    def test_weighted_split_sums_exactly_to_amount(self):
        for amount in (100, 10, 0.1, 1234.57, 99.99):
            with self.subTest(amount=amount):
                self.assertSumsTo(settlement.parse_shares("A:1,B:1,C:1", amount, "A"), amount)
                self.assertSumsTo(settlement.parse_shares("A:2,B:1,C:4", amount, "A"), amount)

    def test_balances_net_to_zero(self):
        balances = settlement.compute_balances([
            {"付款人": "A", "分攤對象": "A,B,C", "amount_twd": 100},
            {"付款人": "B", "分攤對象": "A,B,C", "amount_twd": 200},
        ])
        self.assertAlmostEqual(sum(balances.values()), 0, places=9)

    def test_empty_shares_means_payer_alone(self):
        self.assertEqual(settlement.parse_shares("", 50, "A"), {"A": 50})


if __name__ == "__main__":
    unittest.main()
