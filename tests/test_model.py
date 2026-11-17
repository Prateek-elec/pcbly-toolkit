"""Checks PCBly's calculators against hand-worked IPC-2221 reference values.

Run from the repo root:  python -m unittest discover tests
"""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "PCBLy"))
from main import PCBModel  # noqa: E402


class TraceWidth(unittest.TestCase):
    def test_classic_reference_point(self):
        # 1 A, 1 oz (35 um), 10 C rise, external: the textbook IPC-2221 answer is ~11.8 mil (0.30 mm)
        w = PCBModel.trace_width(1, 35, 10, True)
        self.assertAlmostEqual(w, 0.300, delta=0.005)

    def test_one_amp_twenty_degrees(self):
        # 1 A, 35 um, 20 C, external -> ~7.8 mil (0.197 mm). The old code returned 0.078 mm.
        self.assertAlmostEqual(PCBModel.trace_width(1, 35, 20, True), 0.197, delta=0.004)

    def test_internal_needs_more_width(self):
        ext = PCBModel.trace_width(2, 35, 10, True)
        inner = PCBModel.trace_width(2, 35, 10, False)
        # Halving k raises the required area by 2^(1/0.725)
        self.assertAlmostEqual(inner / ext, 2 ** (1 / 0.725), places=6)

    def test_thicker_copper_means_narrower_trace(self):
        self.assertAlmostEqual(PCBModel.trace_width(3, 70, 10, True) * 2,
                               PCBModel.trace_width(3, 35, 10, True), places=9)

    def test_round_trip(self):
        w = PCBModel.trace_width(2.5, 35, 20, True)
        area_mm2 = w * 0.035
        self.assertAlmostEqual(PCBModel.ipc2221_current(area_mm2, 20, True), 2.5, places=6)


class ViaCapacity(unittest.TestCase):
    def test_capacity_is_in_amps(self):
        # 0.3 mm drill, 25 um plating -> 0.02553 mm^2 (39.6 mil^2) of copper -> ~2.6 A at 20 C.
        # The old code reported ~890 here.
        self.assertAlmostEqual(PCBModel.via_capacity(0.3, 25, 20), 2.58, delta=0.05)

    def test_barrel_area(self):
        area = math.pi / 4 * (0.35 ** 2 - 0.3 ** 2)
        self.assertAlmostEqual(PCBModel.via_capacity(0.3, 25, 20),
                               PCBModel.ipc2221_current(area, 20, True), places=9)

    def test_recommend_flags_and_parallel_vias(self):
        rows = PCBModel.via_recommend(current=5, pcb_thick=1.6, plating_um=25, temp_rise=20, n_vias=1)
        caps = [float(r[2]) for r in rows]
        self.assertEqual(caps, sorted(caps))          # bigger drill, more current
        self.assertEqual(rows[0][4], "")              # 0.2 mm single via can't carry 5 A
        two = PCBModel.via_recommend(current=5, pcb_thick=1.6, plating_um=25, temp_rise=20, n_vias=2)
        self.assertAlmostEqual(float(two[2][2]), 2 * caps[2], delta=0.011)

    def test_aspect_ratio_limit(self):
        rows = PCBModel.via_recommend(current=0.1, pcb_thick=2.4, plating_um=25, temp_rise=20)
        self.assertEqual(rows[0][4], "")  # 2.4 / 0.2 = 12:1, over the 10:1 limit


if __name__ == "__main__":
    unittest.main()
