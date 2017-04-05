from Vintageous.vi.utils import modes

from Vintageous.state import State

from Vintageous.tests import get_sel
from Vintageous.tests import first_sel
from Vintageous.tests import ViewTest

from Vintageous.ex_commands import CURRENT_LINE_RANGE


class Test_ex_copy_Copying_InNormalMode_SingleLine_DefaultStart(ViewTest):
    def testCanCopyDefaultLineRange(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'command_line': 'copy3'})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nxxx\nabc\nxxx\nabc'
        self.assertEqual(expected, actual)

    def testCanCopyToEof(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'command_line': 'copy4'})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nxxx\nabc\nabc\nxxx'
        self.assertEqual(expected, actual)

    def testCanCopyToBof(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'command_line': 'copy0'})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'xxx\nabc\nxxx\nabc\nabc'
        self.assertEqual(expected, actual)

    def testCanCopyToEmptyLine(self):
        self.write('abc\nxxx\nabc\n\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'command_line': 'copy4'})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nxxx\nabc\n\nxxx\nabc'
        self.assertEqual(expected, actual)

    def testCanCopyToSameLine(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'command_line': 'copy2'})

        actual = self.view.substr(self.R(0, self.view.size()))
        expected = 'abc\nxxx\nxxx\nabc\nabc'
        self.assertEqual(expected, actual)


class Test_ex_copy_Copying_InNormalMode_MultipleLines(ViewTest):
    def setUp(self):
        super().setUp()
        self.range = {'left_ref': '.','left_offset': 0, 'left_search_offsets': [],
                      'right_ref': '.', 'right_offset': 1, 'right_search_offsets': []}

    def testCanCopyDefaultLineRange(self):
        self.write('abc\nxxx\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'command_line': '.,.+1copy4'})

        expected = 'abc\nxxx\nxxx\nabc\nxxx\nxxx\nabc'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)

    def testCanCopyToEof(self):
        self.write('abc\nxxx\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'command_line': '.,.+1copy5'})

        expected = 'abc\nxxx\nxxx\nabc\nabc\nxxx\nxxx'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)

    def testCanCopyToBof(self):
        self.write('abc\nxxx\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'command_line': '.,.+1copy0'})

        expected = 'xxx\nxxx\nabc\nxxx\nxxx\nabc\nabc'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)

    def testCanCopyToEmptyLine(self):
        self.write('abc\nxxx\nxxx\nabc\n\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'command_line': '.,.+1copy5'})

        expected = 'abc\nxxx\nxxx\nabc\n\nxxx\nxxx\nabc'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)

    def testCanCopyToSameLine(self):
        self.write('abc\nxxx\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'command_line': '.,.+1copy2'})

        expected = 'abc\nxxx\nxxx\nxxx\nxxx\nabc\nabc'
        actual = self.view.substr(self.R(0, self.view.size()))
        self.assertEqual(expected, actual)


class Test_ex_copy_InNormalMode_CaretPosition(ViewTest):
    def testCanRepositionCaret(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        self.view.run_command('ex_copy', {'command_line': 'copy3'})

        actual = list(self.view.sel())
        expected = [self.R((3, 0), (3, 0))]
        self.assertEqual(expected, actual)


class Test_ex_copy_ModeTransition(ViewTest):
    def testFromNormalModeToNormalMode(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 0)))

        state = State(self.view)
        state.enter_normal_mode()

        self.view.run_command('vi_enter_normal_mode')
        prev_mode = state.mode

        self.view.run_command('ex_copy', {'address': '3'})

        state = State(self.view)
        new_mode = state.mode
        self.assertEqual(prev_mode, new_mode, modes.NORMAL)

    def testFromVisualModeToNormalMode(self):
        self.write('abc\nxxx\nabc\nabc')
        self.clear_sel()
        self.add_sel(self.R((1, 0), (1, 1)))

        state = State(self.view)
        state.enter_visual_mode()
        prev_mode = state.mode

        self.view.run_command('ex_copy', {'command_line': 'copy3'})

        state = State(self.view)
        new_mode = state.mode
        self.assertNotEqual(prev_mode, new_mode)
        self.assertEqual(new_mode, modes.NORMAL)
