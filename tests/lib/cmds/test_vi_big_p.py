from collections import namedtuple

import sublime

from NeoVintageous.lib.vi.utils import modes
from NeoVintageous.lib.vi import registers

from NeoVintageous.tests.utils import ViewTestCase


test_data = namedtuple('test_data', 'content regions in_register params expected msg')

R = sublime.Region

TESTS = (
    # INTERNAL NORMAL MODE
    test_data(content='abc',
              regions=[[(0, 0), (0, 0)]],
              in_register=['xxx'], params={'mode': modes.INTERNAL_NORMAL, 'count': 1},
              expected=('xxxabc', R(2, 2)), msg='failed in {0}'),

    # INTERNAL NORMAL MODE - linewise
    test_data(content='abc',
              regions=[[(0, 0), (0, 0)]],
              in_register=['xxx\n'], params={'mode': modes.INTERNAL_NORMAL, 'count': 1},
              expected=('xxx\nabc', R(0, 0)), msg='failed in {0}'),

    # VISUAL MODE
    test_data(content='abc',
              regions=[[(0, 0), (0, 3)]],
              in_register=['xxx'], params={'mode': modes.VISUAL, 'count': 1},
              expected=('xxx', R(2, 2)), msg='failed in {0}'),

    # VISUAL MODE - linewise
    test_data(content='aaa bbb ccc',
              regions=[[(0, 4), (0, 7)]],
              in_register=['xxx\n'], params={'mode': modes.VISUAL, 'count': 1},
              expected=('aaa \nxxx\n ccc', R(5, 5)), msg='failed in {0}'),
)


class Test__vi_big_p(ViewTestCase):
    def test_all(self):
        for (i, data) in enumerate(TESTS):
            # TODO: Perhaps we should ensure that other state is reset too?
            self.write(data.content)
            self.selectMultiple([self.R(*region) for region in data.regions])

            self.view.settings().set('vintageous_use_sys_clipboard', False)
            registers._REGISTER_DATA['"'] = data.in_register

            self.view.run_command('_vi_big_p', data.params)

            msg = "[{0}] {1}".format(i, data.msg)
            actual_1 = self.view.substr(self.R(0, self.view.size()))
            actual_2 = self.view.sel()[0]
            self.assertEqual(data.expected[0], actual_1, msg.format(i))
            self.assertEqual(data.expected[1], actual_2, msg.format(i))
