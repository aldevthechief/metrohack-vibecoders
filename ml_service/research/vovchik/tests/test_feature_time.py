"""Exercise the existing notebook feature builder without executing training cells."""
import ast
import json
from pathlib import Path
import unittest
import numpy as np
import pandas as pd


class FeatureTimeTests(unittest.TestCase):
    def test_future_and_not_yet_received_packets_cannot_change_features(self):
        notebook = json.loads((Path(__file__).resolve().parents[1] / 'unified.ipynb').read_text(encoding='utf-8'))
        code_cells = [cell for cell in notebook['cells'] if cell['cell_type'] == 'code']
        tree = ast.parse(''.join(code_cells[1]['source']))
        definitions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                       or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {'WINDOWS', 'STOP_SPEED_KMH'} for t in n.targets))]
        ns = {'np': np, 'pd': pd}
        exec(compile(ast.Module(body=definitions, type_ignores=[]), 'notebook_features', 'exec'), ns)
        points = pd.DataFrame([dict(sample_id='a', tr_id='1', T='2026-01-01 12:00:00',
            target_stop_id='s', target_time_begin='2026-01-01 12:12:00', cur_dev_s=10)])
        plan = pd.DataFrame([dict(tr_id='1', tt_action_item_id='s', time_begin='2026-01-01 12:12:00',
                                  geom='POINT (37.5 55.7)')])
        packet = dict(tr_id='1', unit_id='1', packet_id='known', event_time='2026-01-01 11:59:00',
            receive_time='2026-01-01 11:59:01', gps_time='2026-01-01 11:59:00', speed=10.,
            is_hist_data=False, location_valid=True, lon=37.51, lat=55.71)
        known = pd.DataFrame([packet])
        future = dict(packet, packet_id='future', event_time='2026-01-01 12:00:01', receive_time='2026-01-01 12:00:02', speed=999.)
        late = dict(packet, packet_id='late', event_time='2026-01-01 11:59:30', receive_time='2026-01-01 12:00:01', speed=999.)
        a = ns['build_features'](points, plan, known)
        b = ns['build_features'](points, plan.assign(time_fact_begin='2099-01-01'), pd.DataFrame([packet, future, late]))
        pd.testing.assert_frame_equal(a, b)
        self.assertFalse({'target_delay_s','target_class','time_fact_begin'} & set(a.columns))


if __name__ == '__main__':
    unittest.main()
