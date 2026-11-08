"""Protocol rejection controls; these synthetic rows are not the native oracle."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('swap_export', Path(__file__).with_name('export-swap-fixtures.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def protocol_rows():
    critical = {'rconf': 0, 'rblind': 0, 'fract': 0, 'rlite': 0, 'rdark': 0, 'sav': 80}
    inputs = {'currentDanger': 100, 'avoidance': 100,
              'gates': {'usesSwaps': True, 'maxDepth': 50, 'hungry': False,
                        'weak': False, 'panelCount': 0, 'nearbyUnique': False},
              'randarts': False, 'baseCritical': {'rconf': 0, 'rblind': 0, 'fract': 0},
              'candidates': {'armour': {'item': {'category': 'SHIELD', 'quantity': 1,
                  'identified': True, 'artifact': False, 'cursed': False, 'uncursable': False}}, 'weapon': None}}
    return [
        {'kind': 'entry', 'inputs': inputs, 'bindings': {'armourIndex': 0, 'weaponIndex': -1}},
        {'kind': 'evaluation', 'role': 'armour', 'ordinal': 0,
         'answer': {'rawDanger': 20, 'critical': critical}, 'nativeArmourIndex': 0, 'nativeWeaponIndex': -1},
        {'kind': 'result', 'swapped': True, 'role': 'armour', 'nativeIndex': 0,
         'evaluationCount': 1, 'keys': [119, 97], 'keyCount': 2}]


def log(rows):
    return '\n'.join('POC ' + json.dumps(row) for row in rows) + '''
DANGER armour=20 weapon=-1
DECISION swapped=1 command=119 letter=97 pack_index=0
SELECTED cold_shield=1 fire_weapon=0
OUTCOME hp_before=100 hp_after=90 hp_lost=10
native-c/CBUG-0066 finished: 1/1 passed
'''


class NativeExportProtocol(unittest.TestCase):
    def test_actual_key_consumption_and_object_selection_are_authoritative(self):
        result = MODULE.parse_observed(log(protocol_rows()), 'synthetic-protocol')
        self.assertEqual(result['observedAction'], {'kind': 'wield', 'role': 'armour'})
        self.assertEqual(result['observedInputs']['candidates']['armour']['evaluation']['rawDanger'], 20)
        self.assertIsNone(result['observedInputs']['candidates']['weapon'])
        self.assertEqual(len(result['inputSha256']), 64)

    def test_extra_evaluation_or_wrong_role_is_rejected(self):
        rows = protocol_rows()
        rows.insert(2, copy.deepcopy(rows[1]))
        with self.assertRaisesRegex(ValueError, 'order/count'):
            MODULE.parse_observed(log(rows), 'synthetic-protocol')
        rows = protocol_rows(); rows[1]['role'] = 'weapon'
        with self.assertRaisesRegex(ValueError, 'order/count'):
            MODULE.parse_observed(log(rows), 'synthetic-protocol')

    def test_trial_disagreement_and_queue_mutation_are_rejected(self):
        rows = protocol_rows(); rows[1]['answer']['rawDanger'] = 21
        with self.assertRaisesRegex(ValueError, 'trial observation'):
            MODULE.parse_observed(log(rows), 'synthetic-protocol')
        rows = protocol_rows(); rows[2]['keys'][1] = 98
        with self.assertRaisesRegex(ValueError, 'queued command'):
            MODULE.parse_observed(log(rows), 'synthetic-protocol')
        rows = protocol_rows(); rows[2]['role'] = 'weapon'
        with self.assertRaisesRegex(ValueError, 'semantic role'):
            MODULE.parse_observed(log(rows), 'synthetic-protocol')

    def test_boolean_as_score_or_changed_fixture_context_is_rejected(self):
        rows = protocol_rows(); rows[0]['inputs']['currentDanger'] = True
        with self.assertRaisesRegex(ValueError, 'integer'):
            MODULE.parse_observed(log(rows), 'synthetic-protocol')
        rows = protocol_rows(); rows[0]['inputs']['gates']['maxDepth'] = 60
        with self.assertRaisesRegex(ValueError, 'eligibility context'):
            MODULE.parse_observed(log(rows), 'synthetic-protocol')


if __name__ == '__main__': unittest.main()
