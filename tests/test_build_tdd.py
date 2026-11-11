"""建塔交易的 TDD 用例。先于本次异常输入校验增强编写。"""
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import unittest
from config import COLS, ROWS, PADS, TOWERS
from model import Game


class BuildTransactionTests(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.pad = 0
        self.assertTrue(self.game.can_build(self.pad))
        self.cost = TOWERS['bottle']['cost']

    def assert_rejected_without_changes(self, kind, pad):
        coins = self.game.coins
        towers = list(self.game.towers)
        self.assertIs(self.game.build(kind, pad), False)
        self.assertEqual(self.game.coins, coins)
        self.assertEqual(self.game.towers, towers)

    def test_success_charges_once_and_places_one_tower(self):
        coins = self.game.coins
        self.assertIs(self.game.build('bottle', self.pad), True)
        self.assertEqual(self.game.coins, coins - self.cost)
        self.assertEqual(len(self.game.towers), 1)
        tower = self.game.towers[0]
        self.assertEqual((tower.kind, tower.pad, tower.level), ('bottle', self.pad, 1))

    def test_exact_balance_can_purchase_and_ends_at_zero(self):
        self.game.coins = self.cost
        self.assertTrue(self.game.build('bottle', self.pad))
        self.assertEqual(self.game.coins, 0)
        self.assertEqual(len(self.game.towers), 1)

    def test_one_coin_short_rejects_without_changes(self):
        self.game.coins = self.cost - 1
        self.assert_rejected_without_changes('bottle', self.pad)

    def test_path_obstacle_and_home_cells_reject_without_changes(self):
        path_cell = next((x, y) for x, y in self.game.layout['path_cells']
                         if 0 <= x < COLS and 0 <= y < ROWS)
        home_cell = next(iter(self.game.layout['home_cells']))
        pads = (path_cell[1] * COLS + path_cell[0],
                self.game.obstacles[0].pad, home_cell[1] * COLS + home_cell[0])
        for pad in pads:
            with self.subTest(pad=pad):
                self.assert_rejected_without_changes('bottle', pad)

    def test_second_purchase_on_occupied_cell_does_not_charge_again(self):
        self.assertTrue(self.game.build('bottle', self.pad))
        self.assert_rejected_without_changes('bottle', self.pad)

    def test_invalid_tower_kinds_reject_without_changes(self):
        for kind in ('unknown', '', None, 3, True, [], {}):
            with self.subTest(kind=kind):
                self.assert_rejected_without_changes(kind, self.pad)

    def test_invalid_pad_values_and_booleans_reject_without_changes(self):
        for pad in (-1, len(PADS), None, '0', 0.0, [], {}, False, True):
            with self.subTest(pad=pad):
                self.assertIs(self.game.can_build(pad), False)
                self.assert_rejected_without_changes('bottle', pad)

    def test_won_or_lost_game_rejects_without_changes(self):
        for state in ('won', 'lost'):
            with self.subTest(state=state):
                self.game.state = state
                self.assert_rejected_without_changes('bottle', self.pad)


if __name__ == '__main__':
    unittest.main()
