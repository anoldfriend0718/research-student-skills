"""Focused regressions for manuscript block correspondence; no source edits."""
import unittest
from collections import Counter
import english_diff as diff

class AlignmentTests(unittest.TestCase):

    def test_bilingual_heading_number_once(self):
        self.assertEqual(diff.extract('## 5 中文 / 5 English title'), ['5 English title'])
        self.assertEqual(diff.extract('### 5.1 中文 / 5.1 English title'), ['5.1 English title'])
        self.assertEqual(diff.extract('## 5 中文 / English title'), ['5 English title'])
        self.assertEqual(diff.extract('## 5 中文 / 6 English title'), ['6 English title'])

    def test_moves_across_caption(self):
        a = ['1 Introduction', 'Standing waves form pressure nodes and antinodes.', 'Figure 1. Caption.', 'End.']
        b = ['1 Introduction', 'Figure 1. Caption.', 'Standing waves form periodic pressure nodes and antinodes.', 'End.']
        rows = list(diff.comparison_rows(a, b))
        self.assertTrue(any((x.startswith('Standing') and y.startswith('Standing') and move for x, y, move in rows)))
        self.assertEqual(Counter((x for x, _, _ in rows if x)), Counter(a))
        self.assertEqual([y for _, y, _ in rows if y], b)

    def test_math_render_and_atomic_diff(self):
        a = 'At $15^{\\circ}$, $\\gamma$ varies. $$x_1=2\\tag{1}$$'
        b = 'At $20^{\\circ}$, $\\gamma$ varies. $$x_1=3\\tag{1}$$'
        diff.prepare_math([a, b])
        self.assertIn('$15^{\\circ}$', diff.tokens(a))
        left, right = diff.word_diff(a, b)
        self.assertEqual(left.count('<math'), 3)
        self.assertEqual(right.count('<math'), 3)
        self.assertIn('<msup>', left)
        self.assertIn('class="eqno">(1)', left)
        self.assertNotIn('<annotation', left)
        self.assertIn('<ins><span class="formula"', right)

    def test_single_rewritten_lead_between_anchors(self):
        a = ['1 Introduction', 'Old overview.', '(1) First pathway.']
        b = ['1 Introduction', 'Completely rewritten framework.', '(1) First pathway.']
        self.assertIn((a[1], b[1]), list(diff.align(a, b)))

    def test_rewritten_numbered_item_with_inserted_lead(self):
        old = ['1 Introduction', '(4) Original description of rectification.', 'End.']
        new = ['1 Introduction', 'The second level concerns direction.', '(4) A completely rewritten account of guidance.', 'End.']
        rows = list(diff.align(old, new))
        self.assertIn((old[1], new[2]), rows)
        self.assertIn(('', new[1]), rows)

    def test_roles_survive_complete_rewriting(self):
        for old, new in [('2.1 Old title', '2.1 New title'), ('Figure 1. Old caption.', 'Figure 1. New caption.'), ('$$ x=1\\tag{2} $$', '$$ y=3\\tag{2} $$'), ('Hou [23] | 2023 | original', 'Hou [26] | 2023 | rewritten')]:
            self.assertEqual(list(diff.align([old], ['New lead.', new])), [('', 'New lead.'), (old, new)])

    def test_different_numbers_not_matched(self):
        self.assertNotIn(('(1) Shared words here.', '(2) Shared words here.'), list(diff.align(['(1) Shared words here.'], ['(2) Shared words here.'])))

    def test_reference_identity_uses_doi(self):
        a = '[1] Alpha doi:10.1234/a.'
        b = '[8] Alpha revised doi:10.1234/a.'
        self.assertEqual(list(diff.align([a], [b])), [(a, b)])
if __name__ == '__main__':
    unittest.main()
