# Copyright (C) 2018 The NeoVintageous Team (NeoVintageous).
#
# This file is part of NeoVintageous.
#
# NeoVintageous is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# NeoVintageous is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NeoVintageous.  If not, see <https://www.gnu.org/licenses/>.

from functools import partial
from itertools import chain
import logging
import re
import time
import webbrowser

from sublime import CLASS_EMPTY_LINE
from sublime import CLASS_WORD_START
from sublime import ENCODED_POSITION
from sublime import LITERAL
from sublime import MONOSPACE_FONT
from sublime import Region
from sublime_plugin import TextCommand
from sublime_plugin import WindowCommand

from NeoVintageous.nv import rc
from NeoVintageous.nv.ex.completions import insert_best_cmdline_completion
from NeoVintageous.nv.ex.completions import on_change_cmdline_completion_prefix
from NeoVintageous.nv.ex.completions import reset_cmdline_completion_state
from NeoVintageous.nv.ex_cmds import do_ex_cmd_edit_wrap
from NeoVintageous.nv.ex_cmds import do_ex_cmdline
from NeoVintageous.nv.ex_cmds import do_ex_command
from NeoVintageous.nv.ex_cmds import do_ex_user_cmdline
from NeoVintageous.nv.goto import goto_help
from NeoVintageous.nv.goto import goto_line
from NeoVintageous.nv.goto import goto_next_change
from NeoVintageous.nv.goto import goto_next_target
from NeoVintageous.nv.goto import goto_prev_change
from NeoVintageous.nv.goto import goto_prev_target
from NeoVintageous.nv.history import history_get
from NeoVintageous.nv.history import history_get_type
from NeoVintageous.nv.history import history_len
from NeoVintageous.nv.history import history_update
from NeoVintageous.nv.jumplist import jumplist_update
from NeoVintageous.nv.mappings import Mapping
from NeoVintageous.nv.mappings import mappings_is_incomplete
from NeoVintageous.nv.mappings import mappings_resolve
from NeoVintageous.nv.state import init_state
from NeoVintageous.nv.state import State
from NeoVintageous.nv.ui import ui_blink
from NeoVintageous.nv.ui import ui_cmdline_prompt
from NeoVintageous.nv.ui import ui_highlight_yank
from NeoVintageous.nv.ui import ui_highlight_yank_clear
from NeoVintageous.nv.ui import ui_region_flags
from NeoVintageous.nv.utils import extract_file_name
from NeoVintageous.nv.utils import extract_url
from NeoVintageous.nv.utils import fix_eol_cursor
from NeoVintageous.nv.utils import get_option_scroll
from NeoVintageous.nv.utils import get_scroll_down_target_pt
from NeoVintageous.nv.utils import get_scroll_up_target_pt
from NeoVintageous.nv.utils import highest_visible_pt
from NeoVintageous.nv.utils import highlow_visible_rows
from NeoVintageous.nv.utils import lowest_visible_pt
from NeoVintageous.nv.utils import scroll_horizontally
from NeoVintageous.nv.utils import scroll_viewport_position
from NeoVintageous.nv.vi.cmd_base import ViMissingCommandDef
from NeoVintageous.nv.vi.cmd_defs import ViChangeByChars
from NeoVintageous.nv.vi.cmd_defs import ViOpenNameSpace
from NeoVintageous.nv.vi.cmd_defs import ViOpenRegister
from NeoVintageous.nv.vi.cmd_defs import ViOperatorDef
from NeoVintageous.nv.vi.cmd_defs import ViSearchBackwardImpl
from NeoVintageous.nv.vi.cmd_defs import ViSearchForwardImpl
from NeoVintageous.nv.vi.core import IrreversibleTextCommand
from NeoVintageous.nv.vi.core import ViMotionCommand
from NeoVintageous.nv.vi.core import ViTextCommandBase
from NeoVintageous.nv.vi.core import ViWindowCommandBase
from NeoVintageous.nv.vi.keys import KeySequenceTokenizer
from NeoVintageous.nv.vi.keys import to_bare_command_name
from NeoVintageous.nv.vi.search import BufferSearchBase
from NeoVintageous.nv.vi.search import ExactWordBufferSearchBase
from NeoVintageous.nv.vi.search import find_in_range
from NeoVintageous.nv.vi.search import find_wrapping
from NeoVintageous.nv.vi.search import reverse_find_wrapping
from NeoVintageous.nv.vi.search import reverse_search
from NeoVintageous.nv.vi.search import reverse_search_by_pt
from NeoVintageous.nv.vi.settings import toggle_ctrl_keys
from NeoVintageous.nv.vi.settings import toggle_side_bar
from NeoVintageous.nv.vi.settings import toggle_super_keys
from NeoVintageous.nv.vi.text_objects import find_containing_tag
from NeoVintageous.nv.vi.text_objects import find_sentences_backward
from NeoVintageous.nv.vi.text_objects import find_sentences_forward
from NeoVintageous.nv.vi.text_objects import get_closest_tag
from NeoVintageous.nv.vi.text_objects import get_text_object_region
from NeoVintageous.nv.vi.text_objects import word_end_reverse
from NeoVintageous.nv.vi.text_objects import word_reverse
from NeoVintageous.nv.vi.units import big_word_starts
from NeoVintageous.nv.vi.units import inner_lines
from NeoVintageous.nv.vi.units import lines
from NeoVintageous.nv.vi.units import next_paragraph_start
from NeoVintageous.nv.vi.units import prev_paragraph_start
from NeoVintageous.nv.vi.units import word_ends
from NeoVintageous.nv.vi.units import word_starts
from NeoVintageous.nv.vi.utils import first_sel
from NeoVintageous.nv.vi.utils import get_bol
from NeoVintageous.nv.vi.utils import get_eol
from NeoVintageous.nv.vi.utils import get_previous_selection
from NeoVintageous.nv.vi.utils import gluing_undo_groups
from NeoVintageous.nv.vi.utils import is_at_bol
from NeoVintageous.nv.vi.utils import is_at_eol
from NeoVintageous.nv.vi.utils import is_view
from NeoVintageous.nv.vi.utils import new_inclusive_region
from NeoVintageous.nv.vi.utils import next_non_blank
from NeoVintageous.nv.vi.utils import next_non_white_space_char
from NeoVintageous.nv.vi.utils import previous_non_white_space_char
from NeoVintageous.nv.vi.utils import previous_white_space_char
from NeoVintageous.nv.vi.utils import regions_transformer
from NeoVintageous.nv.vi.utils import regions_transformer_indexed
from NeoVintageous.nv.vi.utils import regions_transformer_reversed
from NeoVintageous.nv.vi.utils import replace_sel
from NeoVintageous.nv.vi.utils import resize_visual_region
from NeoVintageous.nv.vi.utils import resolve_insertion_point_at_a
from NeoVintageous.nv.vi.utils import resolve_insertion_point_at_b
from NeoVintageous.nv.vi.utils import row_at
from NeoVintageous.nv.vi.utils import row_to_pt
from NeoVintageous.nv.vi.utils import save_previous_selection
from NeoVintageous.nv.vi.utils import show_if_not_visible
from NeoVintageous.nv.vi.utils import translate_char
from NeoVintageous.nv.vim import DIRECTION_DOWN
from NeoVintageous.nv.vim import DIRECTION_UP
from NeoVintageous.nv.vim import enter_insert_mode
from NeoVintageous.nv.vim import enter_normal_mode
from NeoVintageous.nv.vim import INSERT
from NeoVintageous.nv.vim import INTERNAL_NORMAL
from NeoVintageous.nv.vim import is_visual_mode
from NeoVintageous.nv.vim import NORMAL
from NeoVintageous.nv.vim import OPERATOR_PENDING
from NeoVintageous.nv.vim import REPLACE
from NeoVintageous.nv.vim import SELECT
from NeoVintageous.nv.vim import status_message
from NeoVintageous.nv.vim import UNKNOWN
from NeoVintageous.nv.vim import VISUAL
from NeoVintageous.nv.vim import VISUAL_BLOCK
from NeoVintageous.nv.vim import VISUAL_LINE
from NeoVintageous.nv.window import window_control
from NeoVintageous.nv.window import window_open_file
from NeoVintageous.nv.window import window_tab_control


__all__ = [
    '_enter_insert_mode',
    '_enter_normal_mode',
    '_enter_normal_mode_impl',
    '_enter_replace_mode',
    '_enter_select_mode',
    '_enter_visual_block_mode',
    '_enter_visual_line_mode',
    '_enter_visual_line_mode_impl',
    '_enter_visual_mode',
    '_enter_visual_mode_impl',
    '_nv_cmdline',
    '_nv_cmdline_feed_key',
    '_nv_ex_cmd_edit_wrap',
    '_nv_feed_key',
    '_nv_process_notation',
    '_nv_replace_line',
    '_nv_run_cmds',
    '_vi_a',
    '_vi_at',
    '_vi_b',
    '_vi_backtick',
    '_vi_big_a',
    '_vi_big_b',
    '_vi_big_c',
    '_vi_big_d',
    '_vi_big_e',
    '_vi_big_g',
    '_vi_big_h',
    '_vi_big_i',
    '_vi_big_j',
    '_vi_big_l',
    '_vi_big_m',
    '_vi_big_n',
    '_vi_big_o',
    '_vi_big_p',
    '_vi_big_s',
    '_vi_big_w',
    '_vi_big_x',
    '_vi_big_z_big_q',
    '_vi_big_z_big_z',
    '_vi_c',
    '_vi_cc',
    '_vi_ctrl_b',
    '_vi_ctrl_d',
    '_vi_ctrl_e',
    '_vi_ctrl_f',
    '_vi_ctrl_g',
    '_vi_ctrl_r',
    '_vi_ctrl_r_equal',
    '_vi_ctrl_right_square_bracket',
    '_vi_ctrl_u',
    '_vi_ctrl_w',
    '_vi_ctrl_x_ctrl_l',
    '_vi_ctrl_y',
    '_vi_d',
    '_vi_dd',
    '_vi_dollar',
    '_vi_dot',
    '_vi_e',
    '_vi_enter',
    '_vi_equal',
    '_vi_equal_equal',
    '_vi_find_in_line',
    '_vi_g',
    '_vi_g__',
    '_vi_g_big_e',
    '_vi_g_big_h',
    '_vi_g_big_t',
    '_vi_g_big_u',
    '_vi_g_big_u_big_u',
    '_vi_g_tilde',
    '_vi_g_tilde_g_tilde',
    '_vi_ga',
    '_vi_ge',
    '_vi_gg',
    '_vi_gj',
    '_vi_gk',
    '_vi_gm',
    '_vi_go_to_symbol',
    '_vi_gq',
    '_vi_greater_than',
    '_vi_greater_than_greater_than',
    '_vi_gt',
    '_vi_gu',
    '_vi_guu',
    '_vi_gv',
    '_vi_gx',
    '_vi_h',
    '_vi_hat',
    '_vi_j',
    '_vi_k',
    '_vi_l',
    '_vi_left_brace',
    '_vi_left_paren',
    '_vi_left_square_bracket',
    '_vi_less_than',
    '_vi_less_than_less_than',
    '_vi_m',
    '_vi_minus',
    '_vi_modify_numbers',
    '_vi_n',
    '_vi_o',
    '_vi_octothorp',
    '_vi_p',
    '_vi_percent',
    '_vi_pipe',
    '_vi_q',
    '_vi_question_mark',
    '_vi_question_mark_impl',
    '_vi_question_mark_on_parser_done',
    '_vi_quote',
    '_vi_r',
    '_vi_repeat_buffer_search',
    '_vi_reverse_find_in_line',
    '_vi_right_brace',
    '_vi_right_paren',
    '_vi_right_square_bracket',
    '_vi_s',
    '_vi_select_big_j',
    '_vi_select_j',
    '_vi_select_k',
    '_vi_select_text_object',
    '_vi_shift_enter',
    '_vi_slash',
    '_vi_slash_impl',
    '_vi_slash_on_parser_done',
    '_vi_star',
    '_vi_tilde',
    '_vi_u',
    '_vi_underscore',
    '_vi_visual_big_u',
    '_vi_visual_o',
    '_vi_visual_u',
    '_vi_w',
    '_vi_x',
    '_vi_y',
    '_vi_yy',
    '_vi_z',
    '_vi_z_enter',
    '_vi_z_minus',
    '_vi_zero',
    '_vi_zz',
    'Neovintageous',
    'NeovintageousOpenMyRcFileCommand',
    'NeovintageousReloadMyRcFileCommand',
    'NeovintageousToggleSideBarCommand',
    'SequenceCommand'
]


_log = logging.getLogger(__name__)


class _nv_cmdline_feed_key(TextCommand):

    LAST_HISTORY_ITEM_INDEX = None

    def run(self, edit, key):
        if self.view.size() == 0:
            raise RuntimeError('expected a non-empty command-line')

        if self.view.size() == 1 and key not in ('<up>', '<C-n>', '<down>', '<C-p>', '<C-c>', '<C-[>', '<tab>'):
            return

        if key == '<tab>':
            insert_best_cmdline_completion(self.view, edit)

        elif key in ('<up>', '<C-p>'):
            # Recall older command-line from history, whose beginning matches
            # the current command-line.
            self._next_history(edit, backwards=True)

        elif key in ('<down>', '<C-n>'):
            # Recall more recent command-line from history, whose beginning
            # matches the current command-line.
            self._next_history(edit, backwards=False)

        elif key in ('<C-b>', '<home>'):
            # Cursor to beginning of command-line.
            self.view.sel().clear()
            self.view.sel().add(1)

        elif key in ('<C-c>', '<C-[>'):
            # Quit command-line without executing.
            self.view.window().run_command('hide_panel', {'cancel': True})

        elif key in ('<C-e>', '<end>'):
            # Cursor to end of command-line.
            self.view.sel().clear()
            self.view.sel().add(self.view.size())

        elif key == '<C-h>':
            # Delete the character in front of the cursor.
            pt_end = self.view.sel()[0].b
            pt_begin = pt_end - 1
            self.view.erase(edit, Region(pt_begin, pt_end))

        elif key == '<C-u>':
            # Remove all characters between the cursor position and the
            # beginning of the line.
            self.view.erase(edit, Region(1, self.view.sel()[0].end()))

        elif key == '<C-w>':
            # Delete the |word| before the cursor.
            word_region = self.view.word(self.view.sel()[0].begin())
            word_region = self.view.expand_by_class(self.view.sel()[0].begin(), CLASS_WORD_START)
            word_start_pt = word_region.begin()
            caret_end_pt = self.view.sel()[0].end()
            word_part_region = Region(max(word_start_pt, 1), caret_end_pt)
            self.view.erase(edit, word_part_region)
        else:
            raise NotImplementedError('unknown key')

    def _next_history(self, edit, backwards):
        if self.view.size() == 0:
            raise RuntimeError('expected a non-empty command-line')

        firstc = self.view.substr(0)
        if not history_get_type(firstc):
            raise RuntimeError('expected a valid command-line')

        if _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX is None:
            _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX = -1 if backwards else 0
        else:
            _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX += -1 if backwards else 1

        count = history_len(firstc)
        if count == 0:
            _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX = None

            return ui_blink()

        if abs(_nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX) > count:
            _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX = -count

            return ui_blink()

        if _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX >= 0:
            _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX = 0

            if self.view.size() > 1:
                return self.view.erase(edit, Region(1, self.view.size()))
            else:
                return ui_blink()

        if self.view.size() > 1:
            self.view.erase(edit, Region(1, self.view.size()))

        item = history_get(firstc, _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX)
        if item:
            self.view.insert(edit, 1, item)

    @staticmethod
    def reset_last_history_index():  # type: () -> None
        _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX = None


class _nv_run_cmds(TextCommand):

    def run(self, edit, commands):
        # Run a list of commands one after the other.
        #
        # Args:
        #   commands (list): A list of commands.
        for cmd, args in commands:
            self.view.run_command(cmd, args)


class _nv_feed_key(ViWindowCommandBase):

    def run(self, key, repeat_count=None, do_eval=True, check_user_mappings=True):
        start_time = time.time()

        _log.info('key evt: %s repeat_count=%s do_eval=%s check_user_mappings=%s', key, repeat_count, do_eval, check_user_mappings)  # noqa: E501

        try:
            self._feed_key(key, repeat_count, do_eval, check_user_mappings)
        except Exception as e:
            print('NeoVintageous: An error occurred during key press handle:')
            _log.exception(e)

            import sublime
            for window in sublime.windows():
                for view in window.views():
                    settings = view.settings()
                    settings.set('command_mode', False)
                    settings.set('inverse_caret_state', False)
                    settings.erase('vintage')

        _log.debug('key evt took %ss (key=%s repeat_count=%s do_eval=%s check_user_mappings=%s)', '{:.4f}'.format(time.time() - start_time), key, repeat_count, do_eval, check_user_mappings)  # noqa: E501

    def _feed_key(self, key, repeat_count=None, do_eval=True, check_user_mappings=True):
        # Args:
        #   key (str): Key pressed.
        #   repeat_count (int): Count to be used when repeating through the '.' command.
        #   do_eval (bool): Whether to evaluate the global state when it's in a
        #       runnable state. Most of the time, the default value of `True` should
        #       be used. Set to `False` when you want to manually control the global
        #       state's evaluation. For example, this is what the _nv_feed_key
        #       command does.
        #   check_user_mappings (bool):
        state = self.state

        mode = state.mode

        _log.debug('mode: %s', mode)

        # If the user has made selections with the mouse, we may be in an
        # inconsistent state. Try to remedy that.
        if (state.view.has_non_empty_selection_region() and mode not in (VISUAL, VISUAL_LINE, VISUAL_BLOCK, SELECT)):
            init_state(state.view)

        if key.lower() == '<esc>':
            enter_normal_mode(self.window, mode)
            state.reset_command_data()
            return

        state.sequence += key
        state.display_status()

        if state.must_capture_register_name:
            _log.debug('capturing register name...')
            state.register = key
            state.partial_sequence = ''

            return

        if state.must_collect_input:
            _log.debug('collecting input...')
            state.process_input(key)
            if state.runnable():
                _log.debug('state is runnable')
                if do_eval:
                    _log.debug('evaluating state...')
                    state.eval()
                    state.reset_command_data()

            return

        if repeat_count:
            state.action_count = str(repeat_count)

        if self._handle_count(state, key, repeat_count):
            _log.debug('handled count')

            return

        state.partial_sequence += key

        if check_user_mappings and mappings_is_incomplete(state.mode, state.partial_sequence):
            _log.debug('found incomplete mapping')

            return

        command = mappings_resolve(state, check_user_mappings=check_user_mappings)

        if isinstance(command, ViOpenRegister):
            state.must_capture_register_name = True
            return

        if isinstance(command, Mapping):
            # TODO Review What happens if Mapping + do_eval=False
            if do_eval:
                _log.debug('evaluating user mapping (mode=%s)...', state.mode)

                # TODO Review Why does rhs of mapping need to be resequenced in OPERATOR PENDING mode?
                rhs = command.rhs
                if state.mode == OPERATOR_PENDING:
                    rhs = state.sequence[:-len(state.partial_sequence)] + command.rhs

                # TODO Review Why does state need to be reset before running user mapping?
                reg = state.register
                acount = state.action_count
                mcount = state.motion_count
                state.reset_command_data()
                state.register = reg
                state.motion_count = mcount
                state.action_count = acount

                _log.info('user mapping %s -> %s', command.lhs, rhs)

                if ':' in rhs:
                    do_ex_user_cmdline(self.window, rhs)

                    return

                self.window.run_command('_nv_process_notation', {'keys': rhs, 'check_user_mappings': False})

            return

        if isinstance(command, ViOpenNameSpace):
            return

        if isinstance(command, ViMissingCommandDef):

            # TODO We shouldn't need to try resolve the command again. The
            # resolver should handle commands correctly the first time. The
            # reason this logic is still needed is because we might be looking
            # at a command like 'dd', which currently doesn't resolve properly.
            # The first 'd' is mapped for NORMAL mode, but 'dd' is not mapped in
            # OPERATOR PENDING mode, so we get a missing command, and here we
            # try to fix that (user mappings are excluded, since they've already
            # been given a chance to evaluate).

            bare_seq = to_bare_command_name(state.sequence)
            if state.mode == OPERATOR_PENDING:
                # We might be looking at a command like 'dd'. The first 'd' is
                # mapped for normal mode, but the second is missing in
                # operator pending mode, so we get a missing command. Try to
                # build the full command now.
                #
                # Exclude user mappings, since they've already been given a
                # chance to evaluate.
                command = mappings_resolve(state, sequence=bare_seq, mode=NORMAL, check_user_mappings=False)
            else:
                command = mappings_resolve(state, sequence=bare_seq)

            if isinstance(command, ViMissingCommandDef):
                _log.debug('unmapped sequence %s', state.sequence)
                state.mode = NORMAL
                state.reset_command_data()

                return ui_blink()

        if (state.mode == OPERATOR_PENDING and isinstance(command, ViOperatorDef)):
            _log.info('found operator pending...')
            # TODO: This may be unreachable code by now. ???
            # we're expecting a motion, but we could still get an action.
            # For example, dd, g~g~ or g~~
            # remove counts
            action_seq = to_bare_command_name(state.sequence)
            _log.debug('action sequence %s', action_seq)
            command = mappings_resolve(state, sequence=action_seq, mode=NORMAL)
            if isinstance(command, ViMissingCommandDef):
                _log.debug('unmapped sequence %s', state.sequence)
                state.reset_command_data()

                return

            if not command['motion_required']:
                state.mode = NORMAL

        state.set_command(command)

        if state.mode == OPERATOR_PENDING:
            state.reset_partial_sequence()

        if do_eval:
            state.eval()

    def _handle_count(self, state, key, repeat_count):
        """Return True if the processing of the current key needs to stop."""
        if not state.action and key.isdigit():
            if not repeat_count and (key != '0' or state.action_count):
                _log.debug('action count digit %s', key)
                state.action_count += key

                return True

        if (state.action and (state.mode == OPERATOR_PENDING) and key.isdigit()):
            if not repeat_count and (key != '0' or state.motion_count):
                _log.debug('motion count digit %s', key)
                state.motion_count += key

                return True


class _nv_process_notation(ViWindowCommandBase):

    def run(self, keys, repeat_count=None, check_user_mappings=True):
        # Args:
        #   keys (str): Key sequence to be run.
        #   repeat_count (int): Count to be applied when repeating through the
        #       '.' command.
        #   check_user_mappings (bool): Whether user mappings should be
        #       consulted to expand key sequences.
        state = self.state
        initial_mode = state.mode
        # Disable interactive prompts. For example, to supress interactive
        # input collection in /foo<CR>.
        state.non_interactive = True

        _log.debug('process notation keys %s for initial mode %s', keys, initial_mode)

        # First, run any motions coming before the first action. We don't keep
        # these in the undo stack, but they will still be repeated via '.'.
        # This ensures that undoing will leave the caret where the  first
        # editing action started. For example, 'lldl' would skip 'll' in the
        # undo history, but store the full sequence for '.' to use.
        leading_motions = ''
        for key in KeySequenceTokenizer(keys).iter_tokenize():
            self.window.run_command('_nv_feed_key', {
                'key': key,
                'do_eval': False,
                'repeat_count': repeat_count,
                'check_user_mappings': check_user_mappings
            })
            if state.action:
                # The last key press has caused an action to be primed. That
                # means there are no more leading motions. Break out of here.
                _log.debug('first action found in %s', state.sequence)
                state.reset_command_data()
                if state.mode == OPERATOR_PENDING:
                    state.mode = NORMAL

                break

            elif state.runnable():
                # Run any primed motion.
                leading_motions += state.sequence
                state.eval()
                state.reset_command_data()

            else:
                state.eval()

        if state.must_collect_input:
            # State is requesting more input, so this is the last command in
            # the sequence and it needs more input.
            self.collect_input()
            return

        # Strip the already run commands
        if leading_motions:
            if ((len(leading_motions) == len(keys)) and (not state.must_collect_input)):
                state.non_interactive = False
                return

            _log.debug('original keys/leading-motions: %s/%s', keys, leading_motions)
            keys = keys[len(leading_motions):]
            _log.debug('keys stripped to %s', keys)

        if not (state.motion and not state.action):
            with gluing_undo_groups(self.window.active_view(), state):
                try:
                    for key in KeySequenceTokenizer(keys).iter_tokenize():
                        if key.lower() == '<esc>':
                            # XXX: We should pass a mode here?
                            enter_normal_mode(self.window, None)
                            continue

                        elif state.mode not in (INSERT, REPLACE):
                            self.window.run_command('_nv_feed_key', {
                                'key': key,
                                'repeat_count': repeat_count,
                                'check_user_mappings': check_user_mappings
                            })
                        else:
                            self.window.run_command('insert', {
                                'characters': translate_char(key)
                            })

                    if not state.must_collect_input:
                        return

                finally:
                    state.non_interactive = False
                    # Ensure we set the full command for "." to use, but don't
                    # store "." alone.
                    if (leading_motions + keys) not in ('.', 'u', '<C-r>'):
                        state.repeat_data = ('vi', (leading_motions + keys), initial_mode, None)

        # We'll reach this point if we have a command that requests input whose
        # input parser isn't satistied. For example, `/foo`. Note that
        # `/foo<CR>`, on the contrary, would have satisfied the parser.

        _log.debug('unsatisfied parser action = %s, motion=%s', state.action, state.motion)

        if (state.action and state.motion):
            # We have a parser an a motion that can collect data. Collect data
            # interactively.
            motion_data = state.motion.translate(state) or None

            if motion_data is None:
                state.reset_command_data()

                return ui_blink()

            motion_data['motion_args']['default'] = state.motion.inp

            self.window.run_command(motion_data['motion'], motion_data['motion_args'])

            return

        self.collect_input()

    def collect_input(self):
        try:
            command = None
            if self.state.motion and self.state.action:
                if self.state.motion.accept_input:
                    command = self.state.motion
                else:
                    command = self.state.action
            else:
                command = self.state.action or self.state.motion

            parser_def = command.input_parser
            if parser_def.interactive_command:

                self.window.run_command(
                    parser_def.interactive_command,
                    {parser_def.input_param: command.inp}
                )
        except IndexError:
            _log.debug('could not find a command to collect more user input')
            ui_blink()
        finally:
            self.state.non_interactive = False


class _nv_replace_line(TextCommand):

    def run(self, edit, with_what):
        b = self.view.line(self.view.sel()[0].b).a
        pt = next_non_white_space_char(self.view, b, white_space=' \t')
        self.view.replace(edit, Region(pt, self.view.line(pt).b), with_what)


class _nv_ex_cmd_edit_wrap(TextCommand):

    # This command is required to wrap ex commands that need a Sublime Text edit
    # token. Edit tokens can only be obtained from a TextCommand. Some ex
    # commands don't need an edit token, those commands don't need to be wrapped
    # by a text command.

    def run(self, edit, **kwargs):
        do_ex_cmd_edit_wrap(self, edit, **kwargs)


class _nv_cmdline(WindowCommand):

    def _is_valid_cmdline(self, cmdline):
        return isinstance(cmdline, str) and len(cmdline) > 0 and cmdline[0] == ':'

    def is_enabled(self):
        return bool(self.window.active_view())

    def run(self, initial_text=None):
        reset_cmdline_completion_state()
        state = State(self.window.active_view())
        state.reset_during_init = False

        if initial_text is None:
            if is_visual_mode(state.mode):
                initial_text = ":'<,'>"
            else:
                initial_text = ':'

        if not self._is_valid_cmdline(initial_text):
            raise ValueError('invalid cmdline initial text')

        ui_cmdline_prompt(
            self.window,
            initial_text=initial_text,
            on_done=self.on_done,
            on_change=self.on_change,
            on_cancel=self.on_cancel
        )

    def on_change(self, cmdline):
        if not self._is_valid_cmdline(cmdline):
            return self.on_cancel(force=True)

        on_change_cmdline_completion_prefix(self.window, cmdline)

    def on_done(self, cmdline):
        if not self._is_valid_cmdline(cmdline):
            return self.on_cancel(force=True)

        _nv_cmdline_feed_key.reset_last_history_index()

        history_update(cmdline)
        do_ex_cmdline(self.window, cmdline)

    def on_cancel(self, force=False):
        _nv_cmdline_feed_key.reset_last_history_index()

        if force:
            self.window.run_command('hide_panel', {'cancel': True})


class Neovintageous(WindowCommand):

    def run(self, action, **kwargs):
        if action == 'open_rc_file':
            rc.open(self.window)
        elif action == 'reload_rc_file':
            rc.reload()
        elif action == 'toggle_ctrl_keys':
            toggle_ctrl_keys()
        elif action == 'toggle_side_bar':
            toggle_side_bar(self.window)
        elif action == 'toggle_super_keys':
            toggle_super_keys()


# DEPRECATED use 'neovintageous action=open_rc_file' instead
class NeovintageousOpenMyRcFileCommand(Neovintageous):

    def run(self):
        super().run(action='open_rc_file')


# DEPRECATED use 'neovintageous action=reload_rc_file' instead
class NeovintageousReloadMyRcFileCommand(Neovintageous):

    def run(self):
        super().run(action='reload_rc_file')


# DEPRECATED use 'neovintageous action=toggle_side_bar' instead
class NeovintageousToggleSideBarCommand(Neovintageous):

    def run(self):
        super().run(action='toggle_side_bar')


# DEPRECATED Use _nv_run_cmds instead
class SequenceCommand(TextCommand):

    def run(self, edit, commands):
        # Run a list of commands one after the other.
        #
        # Args:
        #   commands (list): A list of commands.
        for cmd, args in commands:
            self.view.run_command(cmd, args)


class _vi_g_big_u(ViTextCommandBase):

    def run(self, edit, mode=None, count=1, motion=None):
        def f(view, s):
            view.replace(edit, s, view.substr(s).upper())
            # Reverse region so that entering NORMAL mode collapses selection.
            return Region(s.b, s.a)

        if mode == INTERNAL_NORMAL:
            if motion is None:
                raise ValueError('motion data required')

            self.save_sel()
            self.view.run_command(motion['motion'], motion['motion_args'])

            if self.has_sel_changed():
                regions_transformer(self.view, f)
            else:
                ui_blink()
        else:
            regions_transformer(self.view, f)

        enter_normal_mode(self.view, mode)


class _vi_gu(ViTextCommandBase):

    def run(self, edit, mode=None, count=1, motion=None):
        def f(view, s):
            view.replace(edit, s, view.substr(s).lower())
            # Reverse region so that entering NORMAL mode collapses selection.
            return Region(s.b, s.a)

        if mode == INTERNAL_NORMAL:
            if motion is None:
                raise ValueError('motion data required')

            self.save_sel()
            self.view.run_command(motion['motion'], motion['motion_args'])

            if self.has_sel_changed():
                regions_transformer(self.view, f)
            else:
                ui_blink()
        else:
            regions_transformer(self.view, f)

        enter_normal_mode(self.view, mode)


class _vi_gq(ViTextCommandBase):

    def run(self, edit, mode=None, count=1, motion=None):
        def get_wrap_lines_command(view):
            if view.settings().get('WrapPlus.include_line_endings') is not None:
                return 'wrap_lines_plus'
            else:
                return 'wrap_lines'

        def reverse(view, s):
            return Region(s.end(), s.begin())

        def shrink(view, s):
            if view.substr(s.b - 1) == '\n':
                return Region(s.a, s.b - 1)

            return s

        if mode in (VISUAL, VISUAL_LINE):
            sel = tuple(self.view.sel())
            regions_transformer(self.view, shrink)
            regions_transformer(self.view, reverse)
            self.view.run_command(get_wrap_lines_command(self.view))
            self.view.sel().clear()
            for s in sel:
                # Cursors should move to the first non-blank character of the line.
                line = self.view.line(s.begin())
                first_non_ws_char_region = self.view.find('[^\\s]', line.begin())
                self.view.sel().add(first_non_ws_char_region.begin())

        elif mode == INTERNAL_NORMAL:
            if motion is None:
                raise ValueError('motion data required')

            self.save_sel()
            self.view.run_command(motion['motion'], motion['motion_args'])

            if self.has_sel_changed():
                self.save_sel()
                self.view.run_command(get_wrap_lines_command(self.view))
                self.view.sel().clear()

                if 'is_jump' in motion and motion['is_jump']:
                    # Cursors should move to end position of motion (exclusive-linewise).
                    self.view.sel().add_all(self.old_sel)
                else:
                    # Cursors should move to start position of motion.
                    for s in self.old_sel:
                        self.view.sel().add(s.begin())
            else:
                ui_blink()

        enter_normal_mode(self.view, mode)


class _vi_u(ViWindowCommandBase):

    def run(self, count=1, **kwargs):
        for i in range(count):
            self.view.run_command('undo')

        if self.view.has_non_empty_selection_region():
            def reverse(view, s):
                return Region(s.end(), s.begin())

            regions_transformer(self.view, reverse)
            enter_normal_mode(self.window, VISUAL)  # TODO Review: Why explicitly from VISUAL mode?

        # Ensure regions are clear of any highlighted yanks. For example, ddyyu
        # would otherwise show the restored line as previously highlighted.
        ui_highlight_yank_clear(self.view)


class _vi_ctrl_r(ViWindowCommandBase):

    def run(self, count=1, **kwargs):
        change_count_before = self.view.change_count()

        for i in range(count):
            self.view.run_command('redo')

        if self.view.change_count() == change_count_before:
            return ui_blink()

        # Fix EOL issue.
        # See https://github.com/SublimeTextIssues/Core/issues/2121.
        def fixup_eol(view, s):
            pt = s.b
            char = view.substr(pt)
            if (char == '\n' and not view.line(pt).empty()):
                return Region(pt - 1)

            if char == '\x00' and pt == view.size():
                return Region(s.b - 1)

            return s

        regions_transformer(self.view, fixup_eol)


class _vi_a(ViTextCommandBase):

    def run(self, edit, count=1, mode=None):
        def f(view, s):
            if view.substr(s.b) != '\n' and s.b < view.size():
                return Region(s.b + 1)

            return s

        state = State(self.view)

        # Abort if the *actual* mode is insert mode. This prevents _vi_a from
        # adding spaces between text fragments when used with a count, as in
        # 5aFOO. In that case, we only need to run 'a' the first time, not for
        # every iteration.
        if state.mode == INSERT:
            return

        if mode is None:
            raise ValueError('mode required')
        elif mode != INTERNAL_NORMAL:
            return

        regions_transformer(self.view, f)
        self.view.window().run_command('_enter_insert_mode', {
            'mode': mode,
            'count': state.normal_insert_count
        })


class _vi_c(ViTextCommandBase):

    def run(self, edit, count=1, mode=None, motion=None, register=None):
        def compact(view, s):
            if view.substr(s).strip():
                if s.b > s.a:
                    pt = previous_non_white_space_char(view, s.b - 1, white_space=' \t\n')

                    return Region(s.a, pt + 1)

                pt = previous_non_white_space_char(view, s.a - 1, white_space=' \t\n')

                return Region(pt + 1, s.b)

            return s

        if mode is None:
            raise ValueError('mode required')

        if mode == INTERNAL_NORMAL and motion is None:
            raise ValueError('motion data required')

        self.save_sel()

        if motion:
            self.view.run_command(motion['motion'], motion['motion_args'])

            # Vim ignores trailing white space for c. XXX Always?
            if mode == INTERNAL_NORMAL:
                regions_transformer(self.view, compact)

            if not self.has_sel_changed():
                enter_insert_mode(self.view, mode)
                return

            # If we ci' and the target is an empty pair of quotes, we should
            # not delete anything.
            # FIXME: This will not work well with multiple selections.
            if all(s.empty() for s in self.view.sel()):
                enter_insert_mode(self.view, mode)
                return

        self.state.registers.op_change(register=register, linewise=(mode == VISUAL_LINE))
        self.view.run_command('right_delete')
        enter_insert_mode(self.view, mode)


class _enter_normal_mode(ViTextCommandBase):
    """
    The equivalent of pressing the Esc key in Vim.

    @mode
      The mode we're coming from, which should still be the current mode.

    @from_init
      Whether _enter_normal_mode has been called from init_state. This
      is important to know in order to not hide output panels when the user
      is only navigating files or clicking around, not pressing Esc.
    """

    def run(self, edit, mode=None, from_init=False):
        _log.debug('_enter_normal_mode mode=%s, from_init=%s', mode, from_init)

        state = self.state

        self.view.window().run_command('hide_auto_complete')
        self.view.window().run_command('hide_overlay')

        if ((not from_init and (mode == NORMAL) and not state.sequence) or not is_view(self.view)):
            # When _enter_normal_mode is requested from init_state, we
            # should not hide output panels; hide them only if the user
            # pressed Esc and we're not cancelling partial state data, or if a
            # panel has the focus.
            # XXX: We are assuming that state.sequence will always be empty
            #      when we do the check above. Is that so?
            # XXX: The 'not is_view(self.view)' check above seems to be
            #      redundant, since those views should be ignored by
            #      NeoVintageous altogether.
            if len(self.view.sel()) < 2:
                # Don't hide panel if multiple cursors
                if not from_init:
                    self.view.window().run_command('hide_panel', {'cancel': True})

        self.view.settings().set('command_mode', True)
        self.view.settings().set('inverse_caret_state', True)

        # Exit replace mode
        self.view.set_overwrite_status(False)

        state.enter_normal_mode()

        # XXX: st bug? if we don't do this, selections won't be redrawn
        self.view.run_command('_enter_normal_mode_impl', {'mode': mode})

        if state.glue_until_normal_mode and not state.processing_notation:
            if self.view.is_dirty():
                self.view.window().run_command('glue_marked_undo_groups')
                # We're exiting from insert mode or replace mode. Capture
                # the last native command as repeat data.
                state.repeat_data = ('native', self.view.command_history(0)[:2], mode, None)
                # Required here so that the macro gets recorded.
                state.glue_until_normal_mode = False
                state.add_macro_step(*self.view.command_history(0)[:2])
                state.add_macro_step('_enter_normal_mode', {'mode': mode, 'from_init': from_init})
            else:
                state.add_macro_step('_enter_normal_mode', {'mode': mode, 'from_init': from_init})
                self.view.window().run_command('unmark_undo_groups_for_gluing')
                state.glue_until_normal_mode = False

        if mode == INSERT and int(state.normal_insert_count) > 1:
            state.enter_insert_mode()
            # TODO: Calculate size the view has grown by and place the caret after the newly inserted text.
            sels = list(self.view.sel())
            self.view.sel().clear()
            new_sels = [Region(s.b + 1) if self.view.substr(s.b) != '\n' else s for s in sels]
            self.view.sel().add_all(new_sels)
            times = int(state.normal_insert_count) - 1
            state.normal_insert_count = '1'
            self.view.window().run_command('_vi_dot', {
                'count': times,
                'mode': mode,
                'repeat_data': state.repeat_data,
            })
            self.view.sel().clear()
            self.view.sel().add_all(new_sels)

        state.update_xpos(force=True)
        state.reset_status()
        fix_eol_cursor(self.view, state.mode)

        # When the commands o and O are immediately followed by <Esc>, then if
        # the current line is only whitespace it should be erased, and the xpos
        # offset by 1 to account for transition from INSERT to NORMAL mode.
        if mode == INSERT and self.view.is_dirty():
            if self.view.command_history(0)[0] in ('_vi_big_o', '_vi_o'):
                for s in reversed(list(self.view.sel())):
                    line = self.view.line(s.b)
                    line_str = self.view.substr(line)
                    if re.match('^\\s+$', line_str):
                        self.view.erase(edit, line)
                        col = self.view.rowcol(line.b)[1]
                        state.xpos = col + 1


class _enter_normal_mode_impl(ViTextCommandBase):

    def run(self, edit, mode=None):
        _log.debug('_enter_normal_mode_impl mode=%s', mode)

        def f(view, s):
            if mode == INSERT:
                if view.line(s.b).a != s.b:
                    return Region(s.b - 1)

                return Region(s.b)

            if mode == INTERNAL_NORMAL:
                return Region(s.b)

            if mode == VISUAL:
                save_previous_selection(self.view, mode)

                if s.a < s.b:
                    pt = s.b - 1
                    if view.line(pt).empty():
                        return Region(pt)

                    if view.substr(pt) == '\n':
                        pt -= 1

                    return Region(pt)

                return Region(s.b)

            if mode in (VISUAL_LINE, VISUAL_BLOCK):
                save_previous_selection(self.view, mode)

                if s.a < s.b:
                    pt = s.b - 1
                    if (view.substr(pt) == '\n') and not view.line(pt).empty():
                        pt -= 1

                    return Region(pt)
                else:
                    return Region(s.b)

            if mode == SELECT:
                return Region(s.begin())

            return Region(s.b)

        if mode == UNKNOWN:
            return

        if (len(self.view.sel()) > 1) and (mode == NORMAL):
            sel = self.view.sel()[0]
            self.view.sel().clear()
            self.view.sel().add(sel)

        regions_transformer(self.view, f)

        if mode == VISUAL_BLOCK and len(self.view.sel()) > 1:
            sel = self.view.sel()[-1]
            self.view.sel().clear()
            self.view.sel().add(Region(sel.b))

        self.view.erase_regions('vi_search')
        self.view.erase_regions('vi_search_current')
        fix_eol_cursor(self.view, mode)


class _enter_select_mode(ViWindowCommandBase):

    def run(self, mode=None, count=1):
        self.state.enter_select_mode()

        view = self.window.active_view()

        # If there are no visual selections, do some work work for the user.
        if not view.has_non_empty_selection_region():
            self.window.run_command('find_under_expand')

        state = State(view)
        state.display_status()


class _enter_insert_mode(ViTextCommandBase):

    def run(self, edit, mode=None, count=1):
        self.view.settings().set('inverse_caret_state', False)
        self.view.settings().set('command_mode', False)
        self.state.enter_insert_mode()
        self.state.normal_insert_count = str(count)
        self.state.display_status()


class _enter_visual_mode(ViTextCommandBase):

    def run(self, edit, mode=None, force=False):
        state = self.state

        # TODO If all selections are non-zero-length, we may be looking at a
        # pseudo-visual selection, like the ones that are created pressing
        # Alt+Enter when using ST's built-in search dialog. What shall we really
        # do in that case?

        # XXX: In response to the above, we would probably already be in visual
        # mode, but we should double-check that.

        if state.mode == VISUAL and not force:
            enter_normal_mode(self.view, mode)
            return

        self.view.run_command('_enter_visual_mode_impl', {'mode': mode})

        if any(s.empty() for s in self.view.sel()):
            return

        # Sometimes we'll call this command without the global state knowing
        # its metadata. For example, when shift-clicking with the mouse to
        # create visual selections. Always update xpos to cover this case.
        state.update_xpos(force=True)
        state.enter_visual_mode()
        state.display_status()


class _enter_visual_mode_impl(ViTextCommandBase):
    """
    Transform the view's selections.

    We don't do this inside the EnterVisualMode window command because ST seems
    to neglect to repaint the selections. (bug?)
    """

    def run(self, edit, mode=None):
        def f(view, s):
            if mode == VISUAL_LINE:
                return Region(s.a, s.b)
            else:
                if s.empty() and (s.b == self.view.size()):
                    ui_blink()

                    return s

                # Extending from s.a to s.b because we may be looking at
                # selections with len>0. For example, if it's been created
                # using the mouse. Normally, though, the selection will be
                # empty when we reach here.
                end = s.b
                # Only extend .b by 1 if we're looking at empty sels.
                if not view.has_non_empty_selection_region():
                    end += 1

                return Region(s.a, end)

        regions_transformer(self.view, f)


class _enter_visual_line_mode(ViTextCommandBase):

    def run(self, edit, mode=None, force=False):
        state = self.state

        if state.mode == VISUAL_LINE and not force:
            enter_normal_mode(self.view, mode)
            return

        if mode in (NORMAL, INTERNAL_NORMAL):
            # Special-case: If cursor is at the very EOF, then try backup the
            # selection one character so the line, or previous line, is selected
            # (currently only handles non multiple-selections).
            if self.view.size() > 0 and len(self.view.sel()) == 1:
                s = self.view.sel()[0]
                if self.view.substr(s.b) == '\x00':
                    self.view.sel().clear()
                    self.view.sel().add(s.b - 1)

            # Abort if we are at EOF -- no newline char to hold on to.
            if any(s.b == self.view.size() for s in self.view.sel()):
                return ui_blink()

        self.view.run_command('_enter_visual_line_mode_impl', {'mode': mode})
        state.enter_visual_line_mode()
        state.display_status()


class _enter_visual_line_mode_impl(ViTextCommandBase):

    def run(self, edit, mode=None):
        def f(view, s):
            if mode == VISUAL:
                if s.a < s.b:
                    if view.substr(s.b - 1) != '\n':
                        return Region(view.line(s.a).a, view.full_line(s.b - 1).b)
                    else:
                        return Region(view.line(s.a).a, s.b)
                else:
                    if view.substr(s.a - 1) != '\n':
                        return Region(view.full_line(s.a - 1).b, view.line(s.b).a)
                    else:
                        return Region(s.a, view.line(s.b).a)
            else:
                return view.full_line(s.b)

        regions_transformer(self.view, f)


class _enter_replace_mode(ViTextCommandBase):

    def run(self, edit, **kwargs):
        def f(view, s):
            return Region(s.b)

        state = self.state
        state.settings.view['command_mode'] = False
        state.settings.view['inverse_caret_state'] = False
        state.view.set_overwrite_status(True)
        state.enter_replace_mode()
        regions_transformer(self.view, f)
        state.display_status()
        state.reset()


class _vi_dot(ViWindowCommandBase):

    def run(self, mode=None, count=None, repeat_data=None):
        state = self.state
        state.reset_command_data()

        if state.mode == INTERNAL_NORMAL:
            state.mode = NORMAL

        if repeat_data is None:
            ui_blink()
            return

        # TODO: Find out if the user actually meant '1'.
        if count and count == 1:
            count = None

        type_, seq_or_cmd, old_mode, visual_data = repeat_data
        _log.debug('type=%s, seq or cmd=%s, old mode=%s', type_, seq_or_cmd, old_mode)

        if visual_data and (mode != VISUAL):
            state.restore_visual_data(visual_data)
        elif not visual_data and (mode == VISUAL):
            # Can't repeat normal mode commands in visual mode.
            return ui_blink()
        elif mode not in (VISUAL, VISUAL_LINE, NORMAL, INTERNAL_NORMAL, INSERT):
            return ui_blink()

        if type_ == 'vi':
            self.window.run_command('_nv_process_notation', {'keys': seq_or_cmd, 'repeat_count': count})
        elif type_ == 'native':
            sels = list(self.window.active_view().sel())
            # FIXME: We're not repeating as we should. It's the motion that
            # should receive this count.
            for i in range(count or 1):
                self.window.run_command(*seq_or_cmd)
            # FIXME: What happens in visual mode?
            self.window.active_view().sel().clear()
            self.window.active_view().sel().add_all(sels)
        else:
            raise ValueError('bad repeat data')

        enter_normal_mode(self.window, mode)
        state.repeat_data = repeat_data
        state.update_xpos()


class _vi_dd(ViTextCommandBase):

    def run(self, edit, mode=None, count=1, register='"'):
        def do_motion(view, s):
            if mode != INTERNAL_NORMAL:
                return s

            return lines(view, s, count)

        def fixup_sel_pos():
            old = [s.a for s in list(self.view.sel())]
            self.view.sel().clear()
            size = self.view.size()
            new = []
            for pt in old:
                # If on the last char, then pur cursor on previous line
                if pt == size and self.view.substr(pt) == '\x00':
                    pt = self.view.text_point(self.view.rowcol(pt)[0], 0)
                pt = next_non_white_space_char(self.view, pt)
                new.append(pt)
            self.view.sel().add_all(new)

        regions_transformer(self.view, do_motion)
        self.state.registers.op_delete(register=register, linewise=True)
        self.view.run_command('right_delete')
        fixup_sel_pos()


class _vi_cc(ViTextCommandBase):

    def run(self, edit, mode=None, count=1, register='"'):
        def do_motion(view, s):
            if mode != INTERNAL_NORMAL:
                return s

            if view.line(s.b).empty():
                return s

            return inner_lines(view, s, count)

        regions_transformer(self.view, do_motion)
        self.state.registers.op_change(register=register, linewise=True)

        if not all(s.empty() for s in self.view.sel()):
            self.view.run_command('right_delete')

        enter_insert_mode(self.view, mode)

        try:
            self.state.xpos = self.view.rowcol(self.view.sel()[0].b)[1]
        except Exception as e:
            raise ValueError('could not set xpos:' + str(e))


class _vi_visual_o(ViTextCommandBase):

    def run(self, edit, mode=None, count=1):
        def f(view, s):
            if mode in (VISUAL, VISUAL_LINE):
                return Region(s.b, s.a)

            return s

        regions_transformer(self.view, f)
        self.view.show(self.view.sel()[0].b, False)


class _vi_yy(ViTextCommandBase):

    def run(self, edit, mode=None, count=1, register=None):
        def select(view, s):

            if mode == INTERNAL_NORMAL:
                if count > 1:
                    row, col = self.view.rowcol(s.b)
                    end = view.text_point(row + count - 1, 0)

                    return Region(view.line(s.a).a, view.full_line(end).b)

                if view.line(s.b).empty():
                    return Region(s.b, min(view.size(), s.b + 1))

                return view.full_line(s.b)

            elif mode == VISUAL:
                startline = view.line(s.begin())
                endline = view.line(s.end() - 1)

                return Region(startline.a, endline.b)

            return s

        def restore():
            self.view.sel().clear()
            self.view.sel().add_all(list(self.old_sel))

        if mode not in (INTERNAL_NORMAL, VISUAL):
            enter_normal_mode(self.view, mode)
            ui_blink()
            return

        self.save_sel()
        regions_transformer(self.view, select)
        ui_highlight_yank(self.view)
        self.state.registers.op_yank(register=register, linewise=True)
        restore()
        enter_normal_mode(self.view, mode)


class _vi_y(ViTextCommandBase):

    def run(self, edit, mode=None, count=1, motion=None, register=None):
        def f(view, s):
            return Region(next_non_blank(self.view, s.begin()))

        linewise = (mode == VISUAL_LINE)

        if mode == INTERNAL_NORMAL:
            if motion is None:
                raise ValueError('motion data required')

            self.view.run_command(motion['motion'], motion['motion_args'])

            # Some text object motions should be treated as a linewise
            # operation, but only if the motion contains a newline.
            if 'text_object' in motion['motion_args']:
                if motion['motion_args']['text_object'] in '%()`/?nN{}':
                    if not linewise:
                        linewise = 'maybe'

        elif mode not in (VISUAL, VISUAL_LINE, VISUAL_BLOCK):
            return

        ui_highlight_yank(self.view)

        self.state.registers.op_yank(register=register, linewise=linewise)
        regions_transformer(self.view, f)
        enter_normal_mode(self.view, mode)


class _vi_d(ViTextCommandBase):

    def run(self, edit, count=1, mode=None, motion=None, register=None):
        if mode not in (INTERNAL_NORMAL, VISUAL, VISUAL_LINE):
            raise ValueError('wrong mode')

        if mode == INTERNAL_NORMAL and not motion:
            raise ValueError('motion data required')

        if motion:
            self.save_sel()
            self.view.run_command(motion['motion'], motion['motion_args'])

            if not self.has_sel_changed():
                enter_normal_mode(self.view, mode)
                ui_blink()
                return

            if all(s.empty() for s in self.view.sel()):
                enter_normal_mode(self.view, mode)
                ui_blink()
                return

        self.state.registers.op_delete(register=register, linewise=(mode == VISUAL_LINE))
        self.view.run_command('left_delete')
        fix_eol_cursor(self.view, mode)
        enter_normal_mode(self.view, mode)

        def advance_to_text_start(view, s):
            if motion:
                if 'motion' in motion:
                    if motion['motion'] == '_vi_e':
                        return Region(s.begin())
                    elif motion['motion'] == '_vi_dollar':
                        return Region(s.begin())
                    elif motion['motion'] == '_vi_find_in_line':
                        return Region(s.begin())

            return Region(next_non_white_space_char(self.view, s.b))

        if mode == INTERNAL_NORMAL:
            regions_transformer(self.view, advance_to_text_start)

        if mode == VISUAL_LINE:
            def f(view, s):
                return Region(next_non_blank(self.view, s.b))

            regions_transformer(self.view, f)

        fix_eol_cursor(self.view, mode)


class _vi_big_a(ViTextCommandBase):

    def run(self, edit, mode=None, count=1):
        def f(view, s):
            if mode == VISUAL_BLOCK:
                if self.view.substr(s.b - 1) == '\n':
                    return Region(s.end() - 1)
                return Region(s.end())

            elif mode == VISUAL:
                pt = s.b
                if self.view.substr(s.b - 1) == '\n':
                    pt -= 1
                if s.a > s.b:
                    pt = s.b

                return Region(pt)

            elif mode == VISUAL_LINE:
                if self.view.substr(s.b - 1) == '\n':
                    return Region(s.b - 1)
                else:
                    return Region(s.b)

            elif mode != INTERNAL_NORMAL:
                return s

            if s.b == view.size():
                return s

            hard_eol = self.view.line(s.b).end()
            return Region(hard_eol, hard_eol)

        if mode == SELECT:
            self.view.window().run_command('find_all_under')
            return

        regions_transformer(self.view, f)
        enter_insert_mode(self.view, mode)


class _vi_big_i(ViTextCommandBase):

    def run(self, edit, count=1, mode=None):
        def f(view, s):
            if mode == VISUAL_BLOCK:
                return Region(s.begin())
            elif mode == VISUAL:
                return Region(view.line(s.a).a)
            elif mode == VISUAL_LINE:
                return Region(next_non_white_space_char(view, view.line(s.begin()).a))
            elif mode != INTERNAL_NORMAL:
                return s

            return Region(next_non_white_space_char(view, view.line(s.b).a))

        regions_transformer(self.view, f)
        enter_insert_mode(self.view, mode)


class _vi_m(ViTextCommandBase):

    def run(self, edit, mode=None, count=1, character=None):
        state = self.state
        state.marks.add(character, self.view)
        enter_normal_mode(self.view, mode)


class _vi_quote(ViTextCommandBase):

    def run(self, edit, mode=None, character=None, count=1):
        def f(view, s):
            if mode in (VISUAL, VISUAL_LINE, VISUAL_BLOCK):
                if s.a <= s.b:
                    if address.b < s.b:
                        return Region(s.a + 1, address.b)
                    else:
                        return Region(s.a, address.b)
                else:
                    return Region(s.a + 1, address.b)

            elif mode == NORMAL:
                return address

            elif mode == INTERNAL_NORMAL:
                if s.a < address.a:
                    return Region(view.full_line(s.b).a, view.line(address.b).b)
                return Region(view.full_line(s.b).b, view.line(address.b).a)

            return s

        state = self.state
        address = state.marks.get_as_encoded_address(character)

        if address is None:
            return

        if isinstance(address, str):
            if not address.startswith('<command'):
                self.view.window().open_file(address, ENCODED_POSITION)
            else:
                # We get a command in this form: <command _vi_double_quote>
                self.view.run_command(address.split(' ')[1][:-1])
            return

        jumplist_update(self.view)
        regions_transformer(self.view, f)
        jumplist_update(self.view)

        if not self.view.visible_region().intersects(address):
            self.view.show_at_center(address)


class _vi_backtick(ViTextCommandBase):

    def run(self, edit, count=1, mode=None, character=None):
        def f(view, s):
            if mode == VISUAL:
                if s.a <= s.b:
                    if address.b < s.b:
                        return Region(s.a + 1, address.b)
                    else:
                        return Region(s.a, address.b)
                else:
                    return Region(s.a + 1, address.b)
            elif mode == NORMAL:
                return address
            elif mode == INTERNAL_NORMAL:
                return Region(s.a, address.b)

            return s

        state = self.state
        address = state.marks.get_as_encoded_address(character, exact=True)

        if address is None:
            return

        if isinstance(address, str):
            if not address.startswith('<command'):
                self.view.window().open_file(address, ENCODED_POSITION)
            return

        # This is a motion in a composite command.
        jumplist_update(self.view)
        regions_transformer(self.view, f)
        jumplist_update(self.view)


class _vi_big_d(ViTextCommandBase):

    def run(self, edit, mode=None, count=1, register=None):
        def f(view, s):
            if mode == INTERNAL_NORMAL:
                if count == 1:
                    if view.line(s.b).size() > 0:
                        return Region(s.b, view.line(s.b).b)

            elif mode == VISUAL:
                startline = view.line(s.begin())
                endline = view.full_line(s.end())

                return Region(startline.a, endline.b)

            return s

        self.save_sel()
        regions_transformer(self.view, f)

        self.state.registers.op_delete(register=register, linewise=is_visual_mode(mode))
        self.view.run_command('left_delete')

        if mode == VISUAL:
            # TODO Refactor set position cursor after operation into reusable api.
            new_sels = []
            update = False
            for sel in self.view.sel():
                line = self.view.line(sel.b)
                if line.size() > 0:
                    pt = self.view.find('^\\s*', line.begin()).end()
                    new_sels.append(pt)
                    if pt != line.begin():
                        update = True

            if update and new_sels:
                self.view.sel().clear()
                self.view.sel().add_all(new_sels)

        enter_normal_mode(self.view, mode)


class _vi_big_c(ViTextCommandBase):

    def run(self, edit, mode=None, count=1, register=None):
        def f(view, s):
            if mode == INTERNAL_NORMAL:
                if count == 1:
                    if view.line(s.b).size() > 0:
                        eol = view.line(s.b).b
                        return Region(s.b, eol)
                    return s
            return s

        self.save_sel()
        regions_transformer(self.view, f)
        self.state.registers.op_change(register=register, linewise=is_visual_mode(mode))

        empty = [s for s in list(self.view.sel()) if s.empty()]
        self.view.add_regions('vi_empty_sels', empty)
        for r in empty:
            self.view.sel().subtract(r)

        self.view.run_command('right_delete')
        self.view.sel().add_all(self.view.get_regions('vi_empty_sels'))
        self.view.erase_regions('vi_empty_sels')
        enter_insert_mode(self.view, mode)


class _vi_big_s(ViTextCommandBase):

    def run(self, edit, mode=None, count=1, register=None):
        def sel_line(view, s):
            if mode == INTERNAL_NORMAL:
                if count == 1:
                    if view.line(s.b).size() > 0:
                        eol = view.line(s.b).b
                        begin = view.line(s.b).a
                        begin = next_non_white_space_char(view, begin, white_space=' \t')
                        return Region(begin, eol)
                    return s
            return s

        regions_transformer(self.view, sel_line)
        self.state.registers.op_change(register=register, linewise=True)

        empty = [s for s in list(self.view.sel()) if s.empty()]
        self.view.add_regions('vi_empty_sels', empty)
        for r in empty:
            self.view.sel().subtract(r)

        self.view.run_command('right_delete')
        self.view.sel().add_all(self.view.get_regions('vi_empty_sels'))
        self.view.erase_regions('vi_empty_sels')
        self.view.run_command('reindent', {'force_indent': False})
        enter_insert_mode(self.view, mode)


class _vi_s(ViTextCommandBase):

    def run(self, edit, mode=None, count=1, register=None):
        def select(view, s):
            if mode == INTERNAL_NORMAL:
                line = view.line(s.b)
                if line.empty():
                    return Region(s.b)

                # Should not delete past eol.
                return Region(s.b, min(s.b + count, line.b))

            if mode == VISUAL_LINE:
                return Region(s.begin(), s.end() - 1)

            return Region(s.begin(), s.end())

        if mode not in (VISUAL, VISUAL_LINE, VISUAL_BLOCK, INTERNAL_NORMAL):
            enter_normal_mode(self.view, mode)
            ui_blink()
            return

        self.save_sel()
        regions_transformer(self.view, select)

        if not self.has_sel_changed() and mode == INTERNAL_NORMAL:
            enter_insert_mode(self.view, mode)
            return

        self.state.registers.op_delete(register=register, linewise=(mode == VISUAL_LINE))
        self.view.run_command('right_delete')
        enter_insert_mode(self.view, mode)


class _vi_x(ViTextCommandBase):

    def run(self, edit, mode=None, count=1, register=None):
        def select(view, s):
            if mode == INTERNAL_NORMAL:
                return Region(s.b, min(s.b + count, get_eol(view, s.b)))

            return s

        if mode not in (VISUAL, VISUAL_LINE, VISUAL_BLOCK, INTERNAL_NORMAL):
            enter_normal_mode(self.view, mode)
            ui_blink()
            return

        if mode == INTERNAL_NORMAL and all(self.view.line(s.b).empty() for s in self.view.sel()):
            return

        regions_transformer(self.view, select)
        self.state.registers.op_delete(register=register, linewise=(mode == VISUAL_LINE))
        self.view.run_command('right_delete')
        enter_normal_mode(self.view, mode)


class _vi_r(ViTextCommandBase):

    def make_replacement_text(self, char, r):
        frags = self.view.split_by_newlines(r)
        new_frags = []
        for fr in frags:
            new_frags.append(char * len(fr))

        return '\n'.join(new_frags)

    def run(self, edit, mode=None, count=1, register=None, char=None):
        def f(view, s):
            if mode == INTERNAL_NORMAL:
                pt = s.b + count
                text = self.make_replacement_text(char, Region(s.a, pt))
                view.replace(edit, Region(s.a, pt), text)

                if char == '\n':
                    return Region(s.b + 1)
                else:
                    return Region(s.b)

            if mode in (VISUAL, VISUAL_LINE, VISUAL_BLOCK):
                ends_in_newline = (view.substr(s.end() - 1) == '\n')
                text = self.make_replacement_text(char, s)
                if ends_in_newline:
                    text += '\n'

                view.replace(edit, s, text)

                if char == '\n':
                    return Region(s.begin() + 1)
                else:
                    return Region(s.begin())

        if char is None:
            raise ValueError('bad parameters')

        char = translate_char(char)
        regions_transformer(self.view, f)
        enter_normal_mode(self.view, mode)


class _vi_less_than_less_than(ViTextCommandBase):

    def run(self, edit, mode=None, count=None):
        def motion(view, s):
            if mode != INTERNAL_NORMAL:
                return s

            if count <= 1:
                return s

            a = get_bol(view, s.a)
            pt = view.text_point(row_at(view, a) + (count - 1), 0)
            return Region(a, get_eol(view, pt))

        def action(view, s):
            bol = get_bol(view, s.begin())
            pt = next_non_white_space_char(view, bol, white_space='\t ')
            return Region(pt)

        regions_transformer(self.view, motion)
        self.view.run_command('unindent')
        regions_transformer(self.view, action)


class _vi_equal_equal(ViTextCommandBase):

    def run(self, edit, mode=None, count=1):
        def f(view, s):
            return Region(s.begin())

        def select(view):
            s0 = first_sel(self.view)
            end_row = row_at(view, s0.b) + (count - 1)
            view.sel().clear()
            view.sel().add(Region(s0.begin(), view.text_point(end_row, 1)))

        if count > 1:
            select(self.view)

        self.view.run_command('reindent', {'force_indent': False})
        regions_transformer(self.view, f)
        enter_normal_mode(self.view, mode)


class _vi_greater_than_greater_than(ViTextCommandBase):

    def run(self, edit, mode=None, count=1):
        def f(view, s):
            bol = get_bol(view, s.begin())
            pt = next_non_white_space_char(view, bol, white_space='\t ')
            return Region(pt)

        def select(view):
            s0 = first_sel(view)
            end_row = row_at(view, s0.b) + (count - 1)
            replace_sel(view, Region(s0.begin(), view.text_point(end_row, 1)))

        if count > 1:
            select(self.view)

        self.view.run_command('indent')
        regions_transformer(self.view, f)
        enter_normal_mode(self.view, mode)


class _vi_greater_than(ViTextCommandBase):

    def run(self, edit, mode=None, count=1, motion=None):
        def f(view, s):
            bol = get_bol(view, s.begin())
            pt = next_non_white_space_char(view, bol, white_space='\t ')

            return Region(pt)

        def indent_from_begin(view, s, level=1):
            block = '\t' if not translate else ' ' * size
            self.view.insert(edit, s.begin(), block * level)
            return Region(s.begin() + 1)

        if mode == VISUAL_BLOCK:
            translate = self.view.settings().get('translate_tabs_to_spaces')
            size = self.view.settings().get('tab_size')
            indent = partial(indent_from_begin, level=count)

            regions_transformer_reversed(self.view, indent)
            regions_transformer(self.view, f)

            # Restore only the first sel.
            s = first_sel(self.view)
            replace_sel(self.view, s.a + 1)
            enter_normal_mode(self.view, mode)
            return

        if motion:
            self.view.run_command(motion['motion'], motion['motion_args'])
        elif mode not in (VISUAL, VISUAL_LINE):
            return ui_blink()

        for i in range(count):
            self.view.run_command('indent')

        regions_transformer(self.view, f)
        enter_normal_mode(self.view, mode)


class _vi_less_than(ViTextCommandBase):

    def run(self, edit, mode=None, count=1, motion=None):
        def f(view, s):
            bol = get_bol(view, s.begin())
            pt = next_non_white_space_char(view, bol, white_space='\t ')

            return Region(pt)

        # Note: Vim does not unindent in visual block mode.

        if motion:
            self.view.run_command(motion['motion'], motion['motion_args'])
        elif mode not in (VISUAL, VISUAL_LINE):
            return ui_blink()

        for i in range(count):
            self.view.run_command('unindent')

        regions_transformer(self.view, f)
        enter_normal_mode(self.view, mode)


class _vi_equal(ViTextCommandBase):

    def run(self, edit, mode=None, count=1, motion=None):
        def f(view, s):
            return Region(s.begin())

        if motion:
            self.view.run_command(motion['motion'], motion['motion_args'])
        elif mode not in (VISUAL, VISUAL_LINE):
            return ui_blink()

        self.view.run_command('reindent', {'force_indent': False})

        regions_transformer(self.view, f)
        enter_normal_mode(self.view, mode)


class _vi_big_o(ViTextCommandBase):

    def run(self, edit, count=1, mode=None):
        def create_selections(view, sel, index):
            real_sel = Region(sel.a + index * count, sel.b + index * count)
            start_of_line = view.full_line(real_sel).begin()
            view.insert(edit, start_of_line, "\n" * count)
            new = []
            for i in range(0, count):
                new.append(Region(start_of_line + i, start_of_line + i))
            return new

        regions_transformer_indexed(self.view, create_selections)
        enter_insert_mode(self.view, mode)
        self.view.run_command('reindent', {'force_indent': False})


class _vi_o(ViTextCommandBase):
    def run(self, edit, count=1, mode=None):
        def create_selections(view, sel, index):
            real_sel = sel if index == 0 else Region(sel.a + index * count, sel.b + index * count)
            end_of_line = view.line(real_sel).end()
            view.insert(edit, end_of_line, "\n" * count)
            new = []
            for i in range(1, count + 1):
                new.append(Region(end_of_line + i, end_of_line + i))
            return new

        regions_transformer_indexed(self.view, create_selections)
        enter_insert_mode(self.view, mode)
        self.view.run_command('reindent', {'force_indent': False})


class _vi_big_x(ViTextCommandBase):

    def line_start(self, pt):
        return self.view.line(pt).begin()

    def run(self, edit, count=1, mode=None, register=None):
        def select(view, s):
            nonlocal abort
            if mode == INTERNAL_NORMAL:
                if view.line(s.b).empty():
                    abort = True
                return Region(s.b, max(s.b - count, self.line_start(s.b)))
            elif mode == VISUAL:
                if s.a < s.b:
                    if view.line(s.b - 1).empty() and s.size() == 1:
                        abort = True
                    return Region(view.full_line(s.b - 1).b, view.line(s.a).a)

                if view.line(s.b).empty() and s.size() == 1:
                    abort = True
                return Region(view.line(s.b).a, view.full_line(s.a - 1).b)
            return Region(s.begin(), s.end())

        abort = False
        regions_transformer(self.view, select)

        self.state.registers.op_delete(register=register, linewise=True)

        if not abort:
            self.view.run_command('left_delete')

        enter_normal_mode(self.view, mode)


class _vi_big_z_big_q(WindowCommand):

    def run(self):
        do_ex_command(self.window, 'quit', {'forceit': True})


class _vi_big_z_big_z(WindowCommand):

    def run(self):
        do_ex_command(self.window, 'exit')


class _vi_big_p(ViTextCommandBase):

    def run(self, edit, register=None, count=1, mode=None):
        if len(self.view.sel()) > 1:
            return  # TODO Support multiple selections

        state = self.state

        text, linewise = state.registers.get_for_big_p(register, state.mode)
        if not text:
            return status_message('E353: Nothing in register ' + register)

        sel = self.view.sel()[0]

        if mode == INTERNAL_NORMAL:

            # If register content is from a linewise operation, then the cursor
            # is put on the first non-blank character of the first line of the
            # content after the content is inserted.
            if linewise:
                row = self.view.rowcol(self.view.line(sel.a).a)[0]
                pt = self.view.text_point(row, 0)

                self.view.insert(edit, pt, text)

                pt = next_non_white_space_char(self.view, pt)

                self.view.sel().clear()
                self.view.sel().add(pt)

            # If register is charactwise but contains a newline, then the cursor
            # is put at the start of of the text pasted, otherwise the cursor is
            # put on the last character of the text pasted.
            else:
                if '\n' in text:
                    pt = sel.a
                else:
                    pt = sel.a + len(text) - 1

                self.view.insert(edit, sel.a, text)
                self.view.sel().clear()
                self.view.sel().add(pt)

            enter_normal_mode(self.view, mode)

        elif mode == VISUAL:
            self.view.replace(edit, sel, text)
            enter_normal_mode(self.view, mode)

            # If register content is linewise, then the cursor is put on the
            # first non blank of the line.
            if linewise:
                def selection_first_non_blank(view, s):
                    return Region(next_non_white_space_char(view, view.line(s).a))

                regions_transformer(self.view, selection_first_non_blank)


class _vi_p(ViTextCommandBase):

    def run(self, edit, register=None, count=1, mode=None):
        state = self.state

        register_values, linewise = state.registers.get_for_p(register, state.mode)
        if not register_values:
            return status_message('E353: Nothing in register ' + register)

        sels = list(self.view.sel())
        # If we have the same number of pastes and selections, map 1:1,
        # otherwise paste paste[0] to all target selections.
        if len(sels) == len(register_values):
            sel_to_frag_mapped = zip(sels, register_values)
        else:
            sel_to_frag_mapped = zip(sels, [register_values[0], ] * len(sels))

        # FIXME: Fix this mess. Separate linewise from charwise pasting.
        pasting_linewise = True
        offset = 0
        paste_locations = []
        for selection, fragment in reversed(list(sel_to_frag_mapped)):
            fragment = self.prepare_fragment(fragment)
            if fragment.startswith('\n'):
                # Pasting linewise...
                # If pasting at EOL or BOL, make sure we paste before the newline character.
                if (is_at_eol(self.view, selection) or is_at_bol(self.view, selection)):
                    pa = self.paste_all(edit, selection, self.view.line(selection.b).b, fragment, count)
                    paste_locations.append(pa)
                else:
                    pa = self.paste_all(edit, selection, self.view.line(selection.b - 1).b, fragment, count)
                    paste_locations.append(pa)
            else:
                pasting_linewise = False
                # Pasting charwise...
                # If pasting at EOL, make sure we don't paste after the newline character.
                if self.view.substr(selection.b) == '\n':
                    pa = self.paste_all(edit, selection, selection.b + offset, fragment, count)
                    paste_locations.append(pa)
                else:
                    pa = self.paste_all(edit, selection, selection.b + offset + 1, fragment, count)
                    paste_locations.append(pa)
                offset += len(fragment) * count

        if pasting_linewise:
            self.reset_carets_linewise(paste_locations)
        else:
            self.reset_carets_charwise(paste_locations, len(fragment))

        enter_normal_mode(self.view, mode)

    def reset_carets_charwise(self, pts, paste_len):
        # FIXME: Won't work for multiple jagged pastes...
        b_pts = [s.b for s in list(self.view.sel())]
        if len(b_pts) > 1:
            self.view.sel().clear()
            self.view.sel().add_all([Region(ploc + paste_len - 1, ploc + paste_len - 1)
                                    for ploc in pts])
        else:
            self.view.sel().clear()
            self.view.sel().add(Region(pts[0] + paste_len - 1, pts[0] + paste_len - 1))

    def reset_carets_linewise(self, pts):
        self.view.sel().clear()

        if self.state.mode == VISUAL_LINE:
            self.view.sel().add_all([Region(loc) for loc in pts])
            return

        pts = [next_non_white_space_char(self.view, pt + 1) for pt in pts]

        self.view.sel().add_all([Region(pt) for pt in pts])

    def prepare_fragment(self, text):
        if text.endswith('\n') and text != '\n':
            text = '\n' + text[0:-1]
        return text

    # TODO: Improve this signature.
    def paste_all(self, edit, sel, at, text, count):
        state = self.state

        if state.mode not in (VISUAL, VISUAL_LINE):
            # TODO: generate string first, then insert?
            # Make sure we can paste at EOF.
            at = at if at <= self.view.size() else self.view.size()
            for x in range(count):
                self.view.insert(edit, at, text)
            return at

        else:
            if text.startswith('\n'):
                text = text * count
                if not text.endswith('\n'):
                    text = text + '\n'
            else:
                text = text * count

            if state.mode == VISUAL_LINE:
                if text.startswith('\n'):
                    text = text[1:]

            self.view.replace(edit, sel, text)
            return sel.begin()


class _vi_ga(WindowCommand):

    def run(self, **kwargs):
        def char_to_notation(char):
            # Convert a char to a key notation. Uses vim key notation.
            # See https://vimhelp.appspot.com/intro.txt.html#key-notation
            char_notation_map = {
                '\0': "Nul",
                ' ': "Space",
                '\t': "Tab",
                '\n': "NL"
            }

            if char in char_notation_map:
                char = char_notation_map[char]

            return "<" + char + ">"

        view = self.window.active_view()

        for region in view.sel():
            c_str = view.substr(region.begin())
            c_ord = ord(c_str)
            c_hex = hex(c_ord)
            c_oct = oct(c_ord)
            c_not = char_to_notation(c_str)
            status_message('%7s %3s,  Hex %4s,  Octal %5s' % (c_not, c_ord, c_hex, c_oct))


class _vi_gt(WindowCommand):

    def run(self, count=0, mode=None):
        if count > 0:
            window_tab_control(self.window, action='goto', index=count)
        else:
            window_tab_control(self.window, action='next')

        enter_normal_mode(self.window, mode)


class _vi_g_big_t(WindowCommand):

    def run(self, count=1, mode=None):
        window_tab_control(self.window, action='previous')
        enter_normal_mode(self.window, mode)


class _vi_g(TextCommand):

    def run(self, edit, action, **kwargs):
        if action == 'f':
            file_name = extract_file_name(self.view)
            if file_name:
                window_open_file(self.view.window(), file_name)
        else:
            raise ValueError('unknown action')


class _vi_ctrl_right_square_bracket(WindowCommand):

    def run(self):
        view = self.window.active_view()
        if view and view.score_selector(0, 'text.neovintageous.help') > 0:
            goto_help(self.window)
        else:
            self.window.run_command('goto_definition')


class _vi_ctrl_w(WindowCommand):

    def run(self, **kwargs):
        window_control(self.window, **kwargs)


class _vi_z_enter(IrreversibleTextCommand):

    def run(self, count=1, mode=None):
        pt = resolve_insertion_point_at_b(first_sel(self.view))
        home_line = self.view.line(pt)
        taget_pt = self.view.text_to_layout(home_line.begin())
        self.view.set_viewport_position(taget_pt)


class _vi_z_minus(IrreversibleTextCommand):

    def run(self, count=1, mode=None):
        layout_coord = self.view.text_to_layout(first_sel(self.view).b)
        viewport_extent = self.view.viewport_extent()
        new_pos = (0.0, layout_coord[1] - viewport_extent[1])
        self.view.set_viewport_position(new_pos)


class _vi_zz(IrreversibleTextCommand):

    def run(self, count=1, mode=None):
        first_sel = self.view.sel()[0]
        current_position = self.view.text_to_layout(first_sel.b)
        viewport_dim = self.view.viewport_extent()
        new_pos = (0.0, current_position[1] - viewport_dim[1] / 2)
        self.view.set_viewport_position(new_pos)


class _vi_z(TextCommand):

    def run(self, edit, action, count, **kwargs):
        if action == 'c':
            self.view.run_command('fold')
            self._clear_visual_selection()
        elif action in ('h', '<left>'):
            scroll_horizontally(self.view, edit, amount=-count)
        elif action in ('l', '<right>'):
            scroll_horizontally(self.view, edit, amount=count)
        elif action == 'o':
            self.view.run_command('unfold')
            self._clear_visual_selection()
        elif action == 'H':
            scroll_horizontally(self.view, edit, amount=-count, half_screen=True)
        elif action == 'L':
            scroll_horizontally(self.view, edit, amount=count, half_screen=True)
        elif action == 'M':
            self.view.run_command('fold_all')
        elif action == 'R':
            self.view.run_command('unfold_all')
        else:
            raise ValueError('unknown action')

    def _clear_visual_selection(self):
        sels = []
        for sel in self.view.sel():
            sels.append(self.view.text_point(self.view.rowcol(sel.begin())[0], 0))
        if sels:
            self.view.sel().clear()
            self.view.sel().add_all(sels)


class _vi_modify_numbers(ViTextCommandBase):

    DIGIT_PAT = re.compile('(\\D+?)?(-)?(\\d+)(\\D+)?')
    NUM_PAT = re.compile('\\d')

    def get_editable_data(self, pt):
        sign = -1 if (self.view.substr(pt - 1) == '-') else 1
        end = pt
        while self.view.substr(end).isdigit():
            end += 1

        return (sign, int(self.view.substr(Region(pt, end))), Region(end, self.view.line(pt).b))

    def find_next_num(self, regions):
        # Modify selections that are inside a number already.
        for i, r in enumerate(regions):
            a = r.b

            while self.view.substr(a).isdigit():
                a -= 1

            if a != r.b:
                a += 1

            regions[i] = Region(a)

        lines = [self.view.substr(Region(r.b, self.view.line(r.b).b)) for r in regions]
        matches = [_vi_modify_numbers.NUM_PAT.search(text) for text in lines]
        if all(matches):
            return [(reg.b + ma.start()) for (reg, ma) in zip(regions, matches)]

        return []

    def run(self, edit, count=1, mode=None, subtract=False):
        # TODO Implement {Visual}CTRL-A
        # TODO Implement {Visual}CTRL-X
        if mode != INTERNAL_NORMAL:
            return

        # TODO Implement CTRL-A and CTRL-X  octal, hex, etc. numbers

        regs = list(self.view.sel())
        pts = self.find_next_num(regs)

        if not pts:
            return ui_blink()

        end_sels = []
        count = count if not subtract else -count
        for pt in reversed(pts):
            sign, num, tail = self.get_editable_data(pt)

            num_as_text = str((sign * num) + count)
            new_text = num_as_text + self.view.substr(tail)

            offset = 0
            if sign == -1:
                offset = -1
                self.view.replace(edit, Region(pt - 1, tail.b), new_text)
            else:
                self.view.replace(edit, Region(pt, tail.b), new_text)

            rowcol = self.view.rowcol(pt + len(num_as_text) - 1 + offset)
            end_sels.append(rowcol)

        self.view.sel().clear()
        for (row, col) in end_sels:
            self.view.sel().add(Region(self.view.text_point(row, col)))


class _vi_select_big_j(IrreversibleTextCommand):

    # Clears multiple selections and returns to normal mode. Should be more
    # convenient than having to reach for Esc.
    def run(self, mode=None, count=1):
        s = self.view.sel()[0]
        self.view.sel().clear()
        self.view.sel().add(s)
        enter_normal_mode(self.view, mode)


class _vi_big_j(ViTextCommandBase):
    WHITE_SPACE = ' \t'

    def run(self, edit, mode=None, count=1, dont_insert_or_remove_spaces=False):
        sels = self.view.sel()
        s = Region(sels[0].a, sels[-1].b)
        if mode == INTERNAL_NORMAL:
            end_pos = self.view.line(s.b).b
            start = end = s.b
            if count > 2:
                end = self.view.text_point(row_at(self.view, s.b) + (count - 1), 0)
                end = self.view.line(end).b
            else:
                # Join current line and the next.
                end = self.view.text_point(row_at(self.view, s.b) + 1, 0)
                end = self.view.line(end).b
        elif mode in [VISUAL, VISUAL_LINE, VISUAL_BLOCK]:
            if s.a < s.b:
                end_pos = self.view.line(s.a).b
                start = s.a
                if row_at(self.view, s.b - 1) == row_at(self.view, s.a):
                    end = self.view.text_point(row_at(self.view, s.a) + 1, 0)
                else:
                    end = self.view.text_point(row_at(self.view, s.b - 1), 0)
                end = self.view.line(end).b
            else:
                end_pos = self.view.line(s.b).b
                start = s.b
                if row_at(self.view, s.b) == row_at(self.view, s.a - 1):
                    end = self.view.text_point(row_at(self.view, s.a - 1) + 1, 0)
                else:
                    end = self.view.text_point(row_at(self.view, s.a - 1), 0)
                end = self.view.line(end).b
        else:
            return s

        text_to_join = self.view.substr(Region(start, end))
        lines = text_to_join.split('\n')

        def strip_leading_comments(lines):
            shell_vars = self.view.meta_info("shellVariables", start)
            comment_start_tokens = {}
            comment_end_tokens = {}
            for var in shell_vars:
                if var['name'].startswith('TM_COMMENT_'):
                    if 'START' in var['name']:
                        comment_start_tokens[var['name']] = var['value']
                    else:
                        comment_end_tokens[var['name']] = var['value']

            # Strip any leading whitespace.
            first_line = self.view.substr(self.view.line(start)).lstrip(' \t')

            stripped = []
            for i, line in enumerate(lines):
                for name, value in comment_start_tokens.items():
                    # The first line is ignored.
                    if i < 1:
                        continue

                    # Comment definitions that have start AND end tokens are ignored.
                    end_token = comment_end_tokens.get(name.replace('_START', '_END'))
                    if end_token:
                        continue

                    # Lines are ignored if the first line is not a comment.
                    if not first_line.startswith(value):
                        continue

                    # Strip leading and trailing whitespace.
                    line_lstrip = line.lstrip(' \t')
                    line_rstrip = line.rstrip(' \t')
                    value_rstrip = value.rstrip(' \t')

                    is_comment = line_lstrip.startswith(value) or (line_rstrip == value_rstrip)
                    if is_comment:
                        line = line_lstrip[len(value):]

                stripped.append(line)

            return stripped

        lines = strip_leading_comments(lines)

        if not dont_insert_or_remove_spaces:  # J
            joined_text = lines[0]

            for line in lines[1:]:
                line = line.lstrip()
                if joined_text and joined_text[-1] not in self.WHITE_SPACE:
                    line = ' ' + line
                joined_text += line
        else:  # gJ
            joined_text = ''.join(lines)

        self.view.replace(edit, Region(start, end), joined_text)
        sels.clear()
        sels.add(Region(end_pos))
        enter_normal_mode(self.view, mode)


class _vi_gv(IrreversibleTextCommand):

    def run(self, mode=None, count=None):
        visual_sel, visual_sel_mode = get_previous_selection(self.view)
        if not visual_sel or not visual_sel_mode:
            return

        if visual_sel_mode == VISUAL:
            cmd = '_enter_visual_mode'
        elif visual_sel_mode == VISUAL_LINE:
            cmd = '_enter_visual_line_mode'
            # Ensure VISUAL LINE selections span full lines.
            for sel in visual_sel:
                if sel.a < sel.b:
                    sel.a = self.view.line(sel.a).a
                    sel.b = self.view.full_line(sel.b - 1).b
                else:
                    sel.a = self.view.full_line(sel.a - 1).b
                    sel.b = self.view.line(sel.b).a

        elif visual_sel_mode == VISUAL_BLOCK:
            cmd = '_enter_visual_block_mode'
        else:
            raise RuntimeError('unexpected visual sel mode')

        self.view.window().run_command(cmd, {'mode': mode, 'force': True})
        self.view.sel().clear()
        self.view.sel().add_all(visual_sel)


class _vi_gx(IrreversibleTextCommand):

    def run(self, **kwargs):
        url = extract_url(self.view)
        if url:
            webbrowser.open_new_tab(url)


class _vi_ctrl_e(ViTextCommandBase):

    def run(self, edit, mode=None, count=1):
        if mode == VISUAL_LINE:
            return

        extend = True if mode == VISUAL else False
        self.view.run_command('scroll_lines', {'amount': -count, 'extend': extend})


class _vi_ctrl_g(WindowCommand):

    def run(self):
        do_ex_command(self.window, 'file')


class _vi_ctrl_y(ViTextCommandBase):

    def run(self, edit, mode=None, count=1):
        if mode == VISUAL_LINE:
            return

        extend = True if mode == VISUAL else False
        self.view.run_command('scroll_lines', {'amount': count, 'extend': extend})


class _vi_ctrl_r_equal(ViTextCommandBase):

    def run(self, edit, insert=False, next_mode=None):
        def on_cancel():
            state = State(self.view)
            state.reset()

        def on_done(s):
            state = State(self.view)
            try:
                rv = [str(eval(s, None, None)), ]
                if not insert:
                    state.registers.set_expression(rv)
                else:
                    self.view.run_command('insert_snippet', {'contents': str(rv[0])})
                    state.reset()
            except Exception:
                status_message('invalid expression')
                on_cancel()

        self.view.window().show_input_panel('', '', on_done, None, on_cancel)


class _vi_q(IrreversibleTextCommand):

    _current = None

    def run(self, name=None, mode=None, count=1):
        state = State(self.view)

        try:
            if state.is_recording:
                State.macro_registers[self._current] = list(State.macro_steps)
                state.stop_recording()
                self.__class__._current = None
                return

            if name not in tuple('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"'):
                return ui_blink("E354: Invalid register name: '" + name + "'")

            state.start_recording()
            self.__class__._current = name
        except (AttributeError, ValueError):
            state.stop_recording()
            self.__class__._current = None
            ui_blink()


class _vi_at(IrreversibleTextCommand):

    _last_used = None

    def run(self, name, mode=None, count=1):
        if name not in tuple('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ".=*+@'):
            return ui_blink("E354: Invalid register name: '" + name + "'")

        if name == '@':
            name = self._last_used
            if not name:
                return ui_blink('E748: No previously used register')

        try:
            cmds = State.macro_registers[name]
        except (KeyError, ValueError):
            return ui_blink()

        if not cmds:
            ui_blink()
            return

        self.__class__._last_used = name

        state = State(self.view)

        for i in range(count):
            for cmd, args in cmds:
                # TODO Is this robust enough?
                if 'xpos' in args:
                    state.update_xpos(force=True)
                    args['xpos'] = State(self.view).xpos
                elif args.get('motion') and 'xpos' in args.get('motion'):
                    state.update_xpos(force=True)
                    motion = args.get('motion')
                    motion['motion_args']['xpos'] = State(self.view).xpos
                    args['motion'] = motion

                self.view.run_command(cmd, args)


class _enter_visual_block_mode(ViTextCommandBase):

    def run(self, edit, mode=None, force=False):
        def f(view, s):
            return Region(s.b, s.b + 1)

        if mode in (VISUAL_LINE,):
            return

        if mode == VISUAL_BLOCK and not force:
            enter_normal_mode(self.view, mode)
            return

        if mode == VISUAL:
            first = first_sel(self.view)

            if self.view.line(first.end() - 1).empty():
                enter_normal_mode(self.view, mode)
                ui_blink()
                return

            self.view.sel().clear()
            lhs_edge = self.view.rowcol(first.b)[1]  # FIXME # noqa: F841
            regs = self.view.split_by_newlines(first)

            offset_a, offset_b = self.view.rowcol(first.a)[1], self.view.rowcol(first.b)[1]
            min_offset_x = min(offset_a, offset_b)
            max_offset_x = max(offset_a, offset_b)

            new_regs = []
            for r in regs:
                if r.empty():
                    break
                row, _ = self.view.rowcol(r.end() - 1)
                a = self.view.text_point(row, min_offset_x)
                eol = self.view.rowcol(self.view.line(r.end() - 1).b)[1]
                b = self.view.text_point(row, min(max_offset_x, eol))

                if first.a <= first.b:
                    if offset_b < offset_a:
                        new_r = Region(a - 1, b + 1, eol)
                    else:
                        new_r = Region(a, b, eol)
                elif offset_b < offset_a:
                    new_r = Region(a, b, eol)
                else:
                    new_r = Region(a - 1, b + 1, eol)

                new_regs.append(new_r)

            if not new_regs:
                new_regs.append(first)

            self.view.sel().add_all(new_regs)
            state = State(self.view)
            state.enter_visual_block_mode()
            return

        # Handling multiple visual blocks seems quite hard, so ensure we only
        # have one.
        first = list(self.view.sel())[0]
        self.view.sel().clear()
        self.view.sel().add(first)

        state = State(self.view)
        state.enter_visual_block_mode()

        if not self.view.has_non_empty_selection_region():
            regions_transformer(self.view, f)

        state.display_status()


# TODO Refactor into _vi_j
class _vi_select_j(ViWindowCommandBase):

    def run(self, count=1, mode=None):
        if mode != SELECT:
            raise ValueError('wrong mode')

        for i in range(count):
            self.window.run_command('find_under_expand')


# TODO Refactor into _vi_k
class _vi_select_k(ViWindowCommandBase):

    def run(self, count=1, mode=None):
        if mode != SELECT:
            raise ValueError('wrong mode')

        for i in range(count):
            if len(self.view.sel()) > 1:
                self.window.run_command('soft_undo')
            else:
                enter_normal_mode(self.view, mode)


class _vi_tilde(ViTextCommandBase):

    def run(self, edit, count=1, mode=None, motion=None):
        def select(view, s):
            if mode == VISUAL:
                return Region(s.end(), s.begin())
            return Region(s.begin(), s.end() + count)

        def after(view, s):
            return Region(s.begin())

        regions_transformer(self.view, select)
        self.view.run_command('swap_case')

        if mode in (VISUAL, VISUAL_LINE, VISUAL_BLOCK):
            regions_transformer(self.view, after)

        enter_normal_mode(self.view, mode)


class _vi_g_tilde(ViTextCommandBase):

    def run(self, edit, count=1, mode=None, motion=None):
        def f(view, s):
            return Region(s.end(), s.begin())

        sels = []
        for s in list(self.view.sel()):
            sels.append(s.a)

        if motion:
            self.save_sel()

            self.view.run_command(motion['motion'], motion['motion_args'])

            if not self.has_sel_changed():
                ui_blink()
                enter_normal_mode(self.view, mode)
                return

        self.view.run_command('swap_case')

        if motion:
            regions_transformer(self.view, f)

        self.view.sel().clear()
        self.view.sel().add_all(sels)
        enter_normal_mode(self.view, mode)


class _vi_visual_u(ViTextCommandBase):

    def run(self, edit, mode=None, count=1):
        for s in self.view.sel():
            self.view.replace(edit, s, self.view.substr(s).lower())

        def after(view, s):
            return Region(s.begin())

        regions_transformer(self.view, after)
        enter_normal_mode(self.view, mode)


class _vi_visual_big_u(ViTextCommandBase):

    def run(self, edit, mode=None, count=1):
        for s in self.view.sel():
            self.view.replace(edit, s, self.view.substr(s).upper())

        def after(view, s):
            return Region(s.begin())

        regions_transformer(self.view, after)
        enter_normal_mode(self.view, mode)


class _vi_g_tilde_g_tilde(ViTextCommandBase):

    def run(self, edit, count=1, mode=None):
        def select(view, s):
            line = view.line(s.b)

            return Region(line.end(), line.begin())

        if mode != INTERNAL_NORMAL:
            raise ValueError('wrong mode')

        regions_transformer(self.view, select)
        self.view.run_command('swap_case')
        regions_transformer(self.view, select)
        enter_normal_mode(self.view, mode)


class _vi_g_big_u_big_u(ViTextCommandBase):

    def run(self, edit, mode=None, count=1):
        def select(view, s):
            return lines(view, s, count)

        def to_upper(view, s):
            view.replace(edit, s, view.substr(s).upper())
            return Region(next_non_blank(self.view, s.a))

        regions_transformer(self.view, select)
        regions_transformer(self.view, to_upper)
        enter_normal_mode(self.view, mode)


class _vi_guu(ViTextCommandBase):

    def run(self, edit, mode=None, count=1):
        def select(view, s):
            line = view.line(s.b)

            return Region(line.end(), line.begin())

        def to_lower(view, s):
            view.replace(edit, s, view.substr(s).lower())
            return s

        regions_transformer(self.view, select)
        regions_transformer(self.view, to_lower)
        enter_normal_mode(self.view, mode)


# Non-standard command. After a search has been performed via '/' or '?',
# selects all matches and enters select mode.
class _vi_g_big_h(ViWindowCommandBase):

    def run(self, mode=None, count=1):
        view = self.window.active_view()

        regs = view.get_regions('vi_search')
        if regs:
            view.sel().add_all(view.get_regions('vi_search'))

            self.state.enter_select_mode()
            self.state.display_status()
            return

        ui_blink()
        status_message('no available search matches')
        self.state.reset_command_data()


class _vi_ctrl_x_ctrl_l(ViTextCommandBase):
    MAX_MATCHES = 20

    def find_matches(self, prefix, end):
        escaped = re.escape(prefix)
        matches = []
        while end > 0:
            match = reverse_search(self.view, r'^\s*{0}'.format(escaped), 0, end, flags=0)
            if (match is None) or (len(matches) == self.MAX_MATCHES):
                break
            line = self.view.line(match.begin())
            end = line.begin()
            text = self.view.substr(line).lstrip()
            if text not in matches:
                matches.append(text)

        return matches

    def run(self, edit, mode=None, register='"'):
        if mode != INSERT:
            raise ValueError('wrong mode')

        if (len(self.view.sel()) > 1 or not self.view.sel()[0].empty()):
            return ui_blink()

        s = self.view.sel()[0]
        line_begin = self.view.text_point(row_at(self.view, s.b), 0)
        prefix = self.view.substr(Region(line_begin, s.b)).lstrip()
        self._matches = self.find_matches(prefix, end=self.view.line(s.b).a)
        if self._matches:
            self.show_matches(self._matches)
            state = State(self.view)
            state.reset_during_init = False
            state.reset_command_data()
            return

        ui_blink()

    def show_matches(self, items):
        self.view.window().show_quick_panel(items, self.replace, MONOSPACE_FONT)

    def replace(self, s):
        self.view.run_command('_nv_replace_line', {'with_what': self._matches[s]})
        del self.__dict__['_matches']
        pt = self.view.sel()[0].b
        self.view.sel().clear()
        self.view.sel().add(Region(pt))


class _vi_find_in_line(ViMotionCommand):

    # Contrary to *f*, *t* does not look past the caret's position, so if
    # @character is under the caret, nothing happens.
    def run(self, char=None, mode=None, count=1, inclusive=True, skipping=False):
        def f(view, s):
            if mode == VISUAL_LINE:
                raise ValueError('wrong mode')

            b = s.b
            # If we are in any visual mode, get the actual insertion point.
            if s.size() > 0:
                b = resolve_insertion_point_at_b(s)

            # Vim skips a character while performing the search
            # if the command is ';' or ',' after a 't' or 'T'
            if skipping:
                b = b + 1

            eol = view.line(b).end()

            match = Region(b + 1)
            for i in range(count):
                # Define search range as 'rest of the line to the right'.
                search_range = Region(match.end(), eol)
                match = find_in_range(view, char, search_range.a, search_range.b, LITERAL)

                # Count too high or simply no match; break.
                if match is None:
                    return s

            target_pos = match.a
            if not inclusive:
                target_pos = target_pos - 1

            if mode == NORMAL:
                return Region(target_pos)
            elif mode == INTERNAL_NORMAL:
                return Region(s.a, target_pos + 1)
            else:  # For visual modes...
                new_a = resolve_insertion_point_at_a(s)
                return new_inclusive_region(new_a, target_pos)

        if not all([char, mode]):
            raise ValueError('bad parameters')

        char = translate_char(char)

        regions_transformer(self.view, f)


class _vi_reverse_find_in_line(ViMotionCommand):

    # Contrary to *F*, *T* does not look past the caret's position, so if
    # ``character`` is right before the caret, nothing happens.
    def run(self, char=None, mode=None, count=1, inclusive=True, skipping=False):
        def f(view, s):
            if mode == VISUAL_LINE:
                raise ValueError('wrong mode')

            b = s.b
            if s.size() > 0:
                b = resolve_insertion_point_at_b(s)

            # Vim skips a character while performing the search
            # if the command is ';' or ',' after a 't' or 'T'
            if skipping:
                b = b - 1

            line_start = view.line(b).a

            try:
                match = b
                for i in range(count):
                    # line_text does not include character at match
                    line_text = view.substr(Region(line_start, match))
                    found_at = line_text.rindex(char)
                    match = line_start + found_at
            except ValueError:
                return s

            target_pos = match
            if not inclusive:
                target_pos = target_pos + 1

            if mode == NORMAL:
                return Region(target_pos)
            elif mode == INTERNAL_NORMAL:
                return Region(b, target_pos)
            else:  # For visual modes...
                new_a = resolve_insertion_point_at_a(s)
                return new_inclusive_region(new_a, target_pos)

        if not all([char, mode]):
            raise ValueError('bad parameters')

        char = translate_char(char)

        regions_transformer(self.view, f)


class _vi_slash(ViMotionCommand, BufferSearchBase):

    def _is_valid_cmdline(self, cmdline):
        return isinstance(cmdline, str) and len(cmdline) > 0 and cmdline[0] == '/'

    def run(self):
        self.state.reset_during_init = False
        # TODO Add incsearch option e.g. on_change = self.on_change if 'incsearch' else None
        ui_cmdline_prompt(
            self.view.window(),
            initial_text='/',
            on_done=self.on_done,
            on_change=self.on_change,
            on_cancel=self.on_cancel)

    def on_done(self, s):
        if not self._is_valid_cmdline(s):
            return self.on_cancel(force=True)

        history_update(s)
        _nv_cmdline_feed_key.reset_last_history_index()
        s = s[1:]

        state = self.state
        state.sequence += s + '<CR>'
        self.view.erase_regions('vi_inc_search')
        state.last_buffer_search_command = 'vi_slash'
        state.motion = ViSearchForwardImpl(term=s)

        # If s is empty, we must repeat the last search.
        state.last_buffer_search = s or state.last_buffer_search
        state.eval()

    def on_change(self, s):
        if not self._is_valid_cmdline(s):
            return self.on_cancel(force=True)

        s = s[1:]

        state = self.state
        flags = self.calculate_flags(s)
        self.view.erase_regions('vi_inc_search')
        start = self.view.sel()[0].b + 1
        end = self.view.size()

        next_hit = find_wrapping(self.view,
                                 term=s,
                                 start=start,
                                 end=end,
                                 flags=flags,
                                 times=state.count)

        if next_hit:
            if state.mode == VISUAL:
                next_hit = Region(self.view.sel()[0].a, next_hit.a + 1)

            # The scopes are prefixed with common color scopes so that color
            # schemes have sane default colors. Color schemes can progressively
            # enhance support by using the nv_* scopes.
            self.view.add_regions(
                'vi_inc_search',
                [next_hit],
                scope='support.function neovintageous_search_inc',
                flags=ui_region_flags(self.view.settings().get('neovintageous_search_inc_style'))
            )

            if not self.view.visible_region().contains(next_hit.b):
                self.view.show(next_hit.b)

    def on_cancel(self, force=False):
        state = self.state
        self.view.erase_regions('vi_inc_search')
        state.reset_command_data()
        _nv_cmdline_feed_key.reset_last_history_index()

        if not self.view.visible_region().contains(self.view.sel()[0]):
            self.view.show(self.view.sel()[0])

        if force:
            self.view.window().run_command('hide_panel', {'cancel': True})


class _vi_slash_impl(ViMotionCommand, BufferSearchBase):
    def run(self, search_string='', mode=None, count=1):
        def f(view, s):
            if mode == VISUAL:
                return Region(s.a, match.a + 1)

            elif mode == INTERNAL_NORMAL:
                return Region(s.a, match.a)

            elif mode == NORMAL:
                return Region(match.a, match.a)

            elif mode == VISUAL_LINE:
                return Region(s.a, view.full_line(match.b - 1).b)

            return s

        # This happens when we attempt to repeat the search and there's no
        # search term stored yet.
        if not search_string:
            return

        # We want to start searching right after the current selection.
        current_sel = self.view.sel()[0]
        start = current_sel.b if not current_sel.empty() else current_sel.b + 1
        end = self.view.size()
        flags = self.calculate_flags(search_string)

        match = find_wrapping(self.view,
                              term=search_string,
                              start=start,
                              end=end,
                              flags=flags,
                              times=count)
        if not match:
            return

        regions_transformer(self.view, f)
        self.hilite(search_string)


class _vi_slash_on_parser_done(WindowCommand):

    def run(self, key=None):
        state = State(self.window.active_view())
        state.motion = ViSearchForwardImpl()
        state.last_buffer_search = (state.motion.inp or state.last_buffer_search)


class _vi_l(ViMotionCommand):
    def run(self, mode=None, count=1):
        def f(view, s):
            if mode == NORMAL:
                if view.line(s.b).empty():
                    return s

                x_limit = min(view.line(s.b).b - 1, s.b + count, view.size())
                return Region(x_limit, x_limit)

            if mode == INTERNAL_NORMAL:
                x_limit = min(view.line(s.b).b, s.b + count)
                x_limit = max(0, x_limit)
                return Region(s.a, x_limit)

            if mode in (VISUAL, VISUAL_BLOCK):
                if s.a < s.b:
                    x_limit = min(view.full_line(s.b - 1).b, s.b + count)
                    return Region(s.a, x_limit)

                if s.a > s.b:
                    x_limit = min(view.full_line(s.b).b - 1, s.b + count)
                    if view.substr(s.b) == '\n':
                        return s

                    if view.line(s.a) == view.line(s.b) and count >= s.size():
                        x_limit = min(view.full_line(s.b).b, s.b + count + 1)
                        return Region(s.a - 1, x_limit)

                    return Region(s.a, x_limit)

            return s

        regions_transformer(self.view, f)


class _vi_h(ViMotionCommand):
    def run(self, count=1, mode=None):
        def f(view, s):
            if mode == INTERNAL_NORMAL:
                x_limit = max(view.line(s.b).a, s.b - count)
                return Region(s.a, x_limit)

            # TODO: Split handling of the two modes for clarity.
            elif mode in (VISUAL, VISUAL_BLOCK):

                if s.a < s.b:
                    if mode == VISUAL_BLOCK and self.view.rowcol(s.b - 1)[1] == baseline:
                        return s

                    x_limit = max(view.line(s.b - 1).a + 1, s.b - count)
                    if view.line(s.a) == view.line(s.b - 1) and count >= s.size():
                        x_limit = max(view.line(s.b - 1).a, s.b - count - 1)
                        return Region(s.a + 1, x_limit)
                    return Region(s.a, x_limit)

                if s.a > s.b:
                    x_limit = max(view.line(s.b).a, s.b - count)
                    return Region(s.a, x_limit)

            elif mode == NORMAL:
                x_limit = max(view.line(s.b).a, s.b - count)
                return Region(x_limit, x_limit)

            # XXX: We should never reach this.
            return s

        # For jagged selections (on the rhs), only those sticking out need to move leftwards.
        # Example ([] denotes the selection):
        #
        #   10 foo bar foo [bar]
        #   11 foo bar foo [bar foo bar]
        #   12 foo bar foo [bar foo]
        #
        #  Only lines 11 and 12 should move when we press h.
        baseline = 0
        if mode == VISUAL_BLOCK:
            sel = self.view.sel()[0]
            if sel.a < sel.b:
                min_ = min(self.view.rowcol(r.b - 1)[1] for r in self.view.sel())
                if any(self.view.rowcol(r.b - 1)[1] != min_ for r in self.view.sel()):
                    baseline = min_

        regions_transformer(self.view, f)


class _vi_j(ViMotionCommand):
    def folded_rows(self, pt):
        folds = self.view.folded_regions()
        try:
            fold = [f for f in folds if f.contains(pt)][0]
            fold_row_a = self.view.rowcol(fold.a)[0]
            fold_row_b = self.view.rowcol(fold.b - 1)[0]
            # Return no. of hidden lines.
            return (fold_row_b - fold_row_a)
        except IndexError:
            return 0

    def next_non_folded_pt(self, pt):
        # FIXME: If we have two contiguous folds, this method will fail.
        # Handle folded regions.
        folds = self.view.folded_regions()
        try:
            fold = [f for f in folds if f.contains(pt)][0]
            non_folded_row = self.view.rowcol(self.view.full_line(fold.b).b)[0]
            pt = self.view.text_point(non_folded_row, 0)
        except IndexError:
            pass
        return pt

    def calculate_xpos(self, start, xpos):
        size = self.view.settings().get('tab_size')
        if self.view.line(start).empty():
            return start, 0
        else:
            eol = self.view.line(start).b - 1
        pt = 0
        chars = 0
        while (pt < xpos):
            if self.view.substr(start + chars) == '\t':
                pt += size
            else:
                pt += 1
            chars += 1
        pt = min(eol, start + chars)
        return pt, chars

    def run(self, count=1, mode=None, xpos=0, no_translation=False):
        def f(view, s):
            nonlocal xpos
            if mode == NORMAL:
                current_row = view.rowcol(s.b)[0]
                target_row = min(current_row + count, view.rowcol(view.size())[0])
                invisible_rows = self.folded_rows(view.line(s.b).b + 1)
                target_pt = view.text_point(target_row + invisible_rows, 0)
                target_pt = self.next_non_folded_pt(target_pt)

                if view.line(target_pt).empty():
                    return Region(target_pt, target_pt)

                pt = self.calculate_xpos(target_pt, xpos)[0]

                return Region(pt)

            if mode == INTERNAL_NORMAL:
                current_row = view.rowcol(s.b)[0]
                target_row = min(current_row + count, view.rowcol(view.size())[0])
                target_pt = view.text_point(target_row, 0)
                return Region(view.line(s.a).a, view.full_line(target_pt).b)

            if mode == VISUAL:
                exact_position = s.b - 1 if (s.a < s.b) else s.b
                current_row = view.rowcol(exact_position)[0]
                target_row = min(current_row + count, view.rowcol(view.size())[0])
                target_pt = view.text_point(target_row, 0)
                _, xpos = self.calculate_xpos(target_pt, xpos)

                end = min(self.view.line(target_pt).b, target_pt + xpos)
                if s.a < s.b:
                    return Region(s.a, end + 1)

                if (target_pt + xpos) >= s.a:
                    return Region(s.a - 1, end + 1)

                return Region(s.a, target_pt + xpos)

            if mode == VISUAL_LINE:
                if s.a < s.b:
                    current_row = view.rowcol(s.b - 1)[0]
                    target_row = min(current_row + count, view.rowcol(view.size())[0])
                    target_pt = view.text_point(target_row, 0)

                    return Region(s.a, view.full_line(target_pt).b)

                elif s.a > s.b:
                    current_row = view.rowcol(s.b)[0]
                    target_row = min(current_row + count, view.rowcol(view.size())[0])
                    target_pt = view.text_point(target_row, 0)

                    if target_row > view.rowcol(s.a - 1)[0]:
                        return Region(view.line(s.a - 1).a, view.full_line(target_pt).b)

                    return Region(s.a, view.full_line(target_pt).a)

            return s

        state = State(self.view)

        if mode == VISUAL_BLOCK:
            if len(self.view.sel()) == 1:
                state.visual_block_direction = DIRECTION_DOWN

            # Don't do anything if we have reversed selections.
            if any((r.b < r.a) for r in self.view.sel()):
                return

            if state.visual_block_direction == DIRECTION_DOWN:
                for i in range(count):
                    # FIXME: When there are multiple rectangular selections, S3 considers sel 0 to be the
                    # active one in all cases, so we can't know the 'direction' of such a selection and,
                    # therefore, we can't shrink it when we press k or j. We can only easily expand it.
                    # We could, however, have some more global state to keep track of the direction of
                    # visual block selections.
                    row, rect_b = self.view.rowcol(self.view.sel()[-1].b - 1)

                    # Don't do anything if the next row is empty or too short. Vim does a crazy thing: it
                    # doesn't select it and it doesn't include it in actions, but you have to still navigate
                    # your way through them.
                    # TODO: Match Vim's behavior.
                    next_line = self.view.line(self.view.text_point(row + 1, 0))
                    if next_line.empty() or self.view.rowcol(next_line.b)[1] < rect_b:
                        # TODO Fix Visual block select stops at empty lines.
                        # See https://github.com/NeoVintageous/NeoVintageous/issues/227.
                        # self.view.sel().add(next_line.begin())
                        # TODO Fix Visual Block does not work across multiple indentation levels.
                        # See https://github.com/NeoVintageous/NeoVintageous/issues/195.
                        return

                    max_size = max(r.size() for r in self.view.sel())
                    row, col = self.view.rowcol(self.view.sel()[-1].a)
                    start = self.view.text_point(row + 1, col)
                    new_region = Region(start, start + max_size)
                    self.view.sel().add(new_region)
                    # FIXME: Perhaps we should scroll into view in a more general way...

                self.view.show(new_region, False)
                return

            else:
                # Must delete last sel.
                self.view.sel().subtract(self.view.sel()[0])
                return

        regions_transformer(self.view, f)


class _vi_k(ViMotionCommand):
    def previous_non_folded_pt(self, pt):
        # FIXME: If we have two contiguous folds, this method will fail.
        # Handle folded regions.
        folds = self.view.folded_regions()
        try:
            fold = [f for f in folds if f.contains(pt)][0]
            non_folded_row = self.view.rowcol(fold.a - 1)[0]
            pt = self.view.text_point(non_folded_row, 0)
        except IndexError:
            pass
        return pt

    def calculate_xpos(self, start, xpos):
        if self.view.line(start).empty():
            return start, 0
        size = self.view.settings().get('tab_size')
        eol = self.view.line(start).b - 1
        pt = 0
        chars = 0
        while (pt < xpos):
            if self.view.substr(start + chars) == '\t':
                pt += size
            else:
                pt += 1
            chars += 1
        pt = min(eol, start + chars)
        return (pt, chars)

    def run(self, count=1, mode=None, xpos=0, no_translation=False):
        def f(view, s):
            nonlocal xpos
            if mode == NORMAL:
                current_row = view.rowcol(s.b)[0]
                target_row = min(current_row - count, view.rowcol(view.size())[0])
                target_pt = view.text_point(target_row, 0)
                target_pt = self.previous_non_folded_pt(target_pt)

                if view.line(target_pt).empty():
                    return Region(target_pt, target_pt)

                pt, _ = self.calculate_xpos(target_pt, xpos)

                return Region(pt)

            if mode == INTERNAL_NORMAL:
                current_row = view.rowcol(s.b)[0]
                target_row = min(current_row - count, view.rowcol(view.size())[0])
                target_pt = view.text_point(target_row, 0)

                return Region(view.full_line(s.a).b, view.line(target_pt).a)

            if mode == VISUAL:
                exact_position = s.b - 1 if (s.a < s.b) else s.b
                current_row = view.rowcol(exact_position)[0]
                target_row = max(current_row - count, 0)
                target_pt = view.text_point(target_row, 0)
                _, xpos = self.calculate_xpos(target_pt, xpos)

                end = min(self.view.line(target_pt).b, target_pt + xpos)
                if s.b >= s.a:
                    if (self.view.line(s.a).contains(s.b - 1) and not self.view.line(s.a).contains(target_pt)):
                        return Region(s.a + 1, end)
                    else:
                        if (target_pt + xpos) < s.a:
                            return Region(s.a + 1, end)
                        else:
                            return Region(s.a, end + 1)

                return Region(s.a, end)

            if mode == VISUAL_LINE:
                if s.a < s.b:
                    current_row = view.rowcol(s.b - 1)[0]
                    target_row = min(current_row - count, view.rowcol(view.size())[0])
                    target_pt = view.text_point(target_row, 0)

                    if target_row < view.rowcol(s.begin())[0]:
                        return Region(view.full_line(s.a).b, view.full_line(target_pt).a)

                    return Region(s.a, view.full_line(target_pt).b)

                elif s.a > s.b:
                    current_row = view.rowcol(s.b)[0]
                    target_row = max(current_row - count, 0)
                    target_pt = view.text_point(target_row, 0)

                    return Region(s.a, view.full_line(target_pt).a)

        state = State(self.view)

        if mode == VISUAL_BLOCK:
            if len(self.view.sel()) == 1:
                state.visual_block_direction = DIRECTION_UP

            # Don't do anything if we have reversed selections.
            if any((r.b < r.a) for r in self.view.sel()):
                return

            if state.visual_block_direction == DIRECTION_UP:

                for i in range(count):
                    rect_b = max(self.view.rowcol(r.b - 1)[1] for r in self.view.sel())
                    row, rect_a = self.view.rowcol(self.view.sel()[0].a)
                    previous_line = self.view.line(self.view.text_point(row - 1, 0))
                    # Don't do anything if previous row is empty. Vim does crazy stuff in that case.
                    # Don't do anything either if the previous line can't accomodate a rectangular selection
                    # of the required size.
                    if (previous_line.empty() or self.view.rowcol(previous_line.b)[1] < rect_b):
                        return
                    rect_size = max(r.size() for r in self.view.sel())
                    rect_a_pt = self.view.text_point(row - 1, rect_a)
                    new_region = Region(rect_a_pt, rect_a_pt + rect_size)
                    self.view.sel().add(new_region)
                    # FIXME: We should probably scroll into view in a more general way.
                    #        Or maybe every motion should handle this on their own.

                self.view.show(new_region, False)
                return

            elif SELECT:
                # Must remove last selection.
                self.view.sel().subtract(self.view.sel()[-1])
                return
            else:
                return

        regions_transformer(self.view, f)


class _vi_gg(ViMotionCommand):
    def run(self, mode=None, count=None):
        if count:
            goto_line(self.view, mode, count)
            return

        def f(view, s):
            if mode == NORMAL:
                return Region(next_non_blank(self.view, 0))
            elif mode == VISUAL:
                if s.a < s.b:
                    return Region(s.a + 1, next_non_blank(self.view, 0))
                else:
                    return Region(s.a, next_non_blank(self.view, 0))
            elif mode == INTERNAL_NORMAL:
                return Region(view.full_line(s.b).b, 0)
            elif mode == VISUAL_LINE:
                if s.a < s.b:
                    return Region(s.b, 0)
                else:
                    return Region(s.a, 0)
            return s

        jumplist_update(self.view)
        regions_transformer(self.view, f)
        jumplist_update(self.view)


class _vi_big_g(ViMotionCommand):
    def run(self, mode=None, count=None):
        if count:
            goto_line(self.view, mode, count)
            return

        def f(view, s):
            if mode == NORMAL:
                eof_line = view.line(eof)
                if not eof_line.empty():
                    return Region(next_non_blank(self.view, eof_line.a))

                return Region(eof_line.a)
            elif mode == VISUAL:
                eof_line = view.line(eof)
                if not eof_line.empty():
                    return Region(s.a, next_non_blank(self.view, eof_line.a) + 1)

                return Region(s.a, eof_line.a)
            elif mode == INTERNAL_NORMAL:
                return Region(max(0, view.line(s.b).a), eof)
            elif mode == VISUAL_LINE:
                return Region(s.a, eof)

            return s

        jumplist_update(self.view)
        eof = self.view.size()
        regions_transformer(self.view, f)
        jumplist_update(self.view)


class _vi_dollar(ViMotionCommand):
    def run(self, mode=None, count=1):
        def f(view, s):
            target = resolve_insertion_point_at_b(s)
            if count > 1:
                target = row_to_pt(view, row_at(view, target) + (count - 1))

            eol = view.line(target).b

            if mode == NORMAL:
                return Region(eol if view.line(eol).empty() else (eol - 1))

            elif mode == VISUAL:
                # TODO is this really a special case? can we not include this
                # case in .resize_visual_region()?
                # Perhaps we should always ensure that a minimal visual sel
                # was always such that .a < .b?
                if (s.a == eol) and not view.line(eol).empty():
                    return Region(s.a - 1, eol + 1)

                return resize_visual_region(s, eol)

            elif mode == INTERNAL_NORMAL:
                # TODO perhaps create a .is_linewise_motion() helper?
                if get_bol(view, s.a) == s.a:
                    return Region(s.a, eol + 1)

                return Region(s.a, eol)

            elif mode == VISUAL_LINE:
                # TODO: Implement this. Not too useful, though.
                return s

            return s

        regions_transformer(self.view, f)


class _vi_w(ViMotionCommand):
    def run(self, mode=None, count=1):
        def f(view, s):
            if mode == NORMAL:
                pt = word_starts(view, start=s.b, count=count)
                if ((pt == view.size()) and (not view.line(pt).empty())):
                    pt = previous_non_white_space_char(view, pt - 1, white_space='\n')

                return Region(pt, pt)

            elif mode in (VISUAL, VISUAL_BLOCK):
                start = (s.b - 1) if (s.a < s.b) else s.b
                pt = word_starts(view, start=start, count=count)

                if (s.a > s.b) and (pt >= s.a):
                    return Region(s.a - 1, pt + 1)
                elif s.a > s.b:
                    return Region(s.a, pt)
                elif view.size() == pt:
                    pt -= 1

                return Region(s.a, pt + 1)

            elif mode == INTERNAL_NORMAL:
                a = s.a
                pt = word_starts(view, start=s.b, count=count, internal=True)
                if (not view.substr(view.line(s.a)).strip() and view.line(s.b) != view.line(pt)):
                    a = view.line(s.a).a

                return Region(a, pt)

            return s

        regions_transformer(self.view, f)


class _vi_big_w(ViMotionCommand):
    def run(self, mode=None, count=1):
        def f(view, s):
            if mode == NORMAL:
                pt = big_word_starts(view, start=s.b, count=count)
                if ((pt == view.size()) and (not view.line(pt).empty())):
                    pt = previous_non_white_space_char(view, pt - 1, white_space='\n')

                return Region(pt, pt)

            elif mode == VISUAL:
                pt = big_word_starts(view, start=max(s.b - 1, 0), count=count)
                if s.a > s.b and pt >= s.a:
                    return Region(s.a - 1, pt + 1)
                elif s.a > s.b:
                    return Region(s.a, pt)
                elif (view.size() == pt):
                    pt -= 1

                return Region(s.a, pt + 1)

            elif mode == INTERNAL_NORMAL:
                a = s.a
                pt = big_word_starts(view, start=s.b, count=count, internal=True)
                if (not view.substr(view.line(s.a)).strip() and view.line(s.b) != view.line(pt)):
                    a = view.line(s.a).a

                return Region(a, pt)

            return s

        regions_transformer(self.view, f)


class _vi_e(ViMotionCommand):
    def run(self, mode=None, count=1):
        def f(view, s):
            if mode == NORMAL:
                pt = word_ends(view, start=s.b, count=count)
                return Region(pt - 1)

            elif mode == VISUAL:
                pt = word_ends(view, start=s.b - 1, count=count)
                if (s.a > s.b) and (pt >= s.a):
                    return Region(s.a - 1, pt)
                elif (s.a > s.b):
                    return Region(s.a, pt - 1)

                return Region(s.a, pt)

            elif mode == INTERNAL_NORMAL:
                a = s.a
                pt = word_ends(view, start=s.b, count=count)
                if (not view.substr(view.line(s.a)).strip() and view.line(s.b) != view.line(pt)):
                    a = view.line(s.a).a

                return Region(a, pt)

            return s

        regions_transformer(self.view, f)


class _vi_zero(ViMotionCommand):
    def run(self, mode=None, count=1):
        def f(view, s):
            if mode == NORMAL:
                return Region(view.line(s.b).a)
            elif mode == INTERNAL_NORMAL:
                return Region(s.a, view.line(s.b).a)
            elif mode == VISUAL:
                if s.a < s.b:
                    line = view.line(s.b)
                    if s.a > line.a:
                        return Region(s.a + 1, line.a)
                    else:
                        return Region(s.a, line.a + 1)
                else:
                    return Region(s.a, view.line(s.b).a)

            return s

        regions_transformer(self.view, f)


class _vi_right_brace(ViMotionCommand):
    def run(self, mode=None, count=1):
        def f(view, s):
            if mode == NORMAL:
                par_begin = next_paragraph_start(view, s.b, count)
                # find the next non-empty row if needed
                return Region(par_begin)

            elif mode == VISUAL:
                next_start = next_paragraph_start(view, s.b, count, skip_empty=count > 1)

                return resize_visual_region(s, next_start)

            # TODO Delete previous ws in remaining start line.
            elif mode == INTERNAL_NORMAL:
                par_begin = next_paragraph_start(view, s.b, count, skip_empty=count > 1)
                if par_begin == (self.view.size() - 1):
                    return Region(s.a, self.view.size())
                if view.substr(s.a - 1) == '\n' or s.a == 0:
                    return Region(s.a, par_begin)

                return Region(s.a, par_begin - 1)

            elif mode == VISUAL_LINE:
                par_begin = next_paragraph_start(view, s.b, count, skip_empty=count > 1)
                if s.a <= s.b:
                    return Region(s.a, par_begin + 1)
                else:
                    if par_begin > s.a:
                        return Region(view.line(s.a - 1).a, par_begin + 1)

                    return Region(s.a, par_begin)

            return s

        regions_transformer(self.view, f)


class _vi_left_brace(ViMotionCommand):
    def run(self, mode=None, count=1):
        def f(view, s):
            # TODO: must skip empty paragraphs.
            start = previous_non_white_space_char(view, s.b - 1, white_space='\n \t')
            par_as_region = view.expand_by_class(start, CLASS_EMPTY_LINE)

            if mode == NORMAL:
                next_start = prev_paragraph_start(view, s.b, count)
                return Region(next_start)

            elif mode == VISUAL:
                next_start = prev_paragraph_start(view, s.b, count)
                return resize_visual_region(s, next_start)

            elif mode == INTERNAL_NORMAL:
                next_start = prev_paragraph_start(view, s.b, count)
                return Region(s.a, next_start)

            elif mode == VISUAL_LINE:
                if s.a <= s.b:
                    if par_as_region.a < s.a:
                        return Region(view.full_line(s.a).b, par_as_region.a)
                    return Region(s.a, par_as_region.a + 1)
                else:
                    return Region(s.a, par_as_region.a)

            return s

        regions_transformer(self.view, f)


class _vi_percent(ViMotionCommand):

    pairs = (
        ('(', ')'),
        ('[', ']'),
        ('{', '}'),
        ('<', '>'),
    )

    def find_tag(self, pt):
        # Args:
        #   pt (int)
        #
        # Returns:
        #   Region|None
        if (self.view.score_selector(0, 'text.html') == 0 and self.view.score_selector(0, 'text.xml') == 0):
            return None

        if any([self.view.substr(pt) in p for p in self.pairs]):
            return None

        _, closest_tag = get_closest_tag(self.view, pt)
        if not closest_tag:
            return None

        if closest_tag.contains(pt):
            begin_tag, end_tag, _ = find_containing_tag(self.view, pt)
            if begin_tag:
                return begin_tag if end_tag.contains(pt) else end_tag

        return None

    def run(self, percent=None, mode=None):
        # Args:
        #   percent (int): Percentage down in file.
        #   mode: (str)
        if percent is None:
            def move_to_bracket(view, s):
                def find_bracket_location(region):
                    # Args:
                    #   region (Region)
                    #
                    # Returns:
                    #   int|None
                    pt = region.b
                    if (region.size() > 0) and (region.b > region.a):
                        pt = region.b - 1

                    tag = self.find_tag(pt)
                    if tag:
                        return tag.a

                    bracket, brackets, bracket_pt = self.find_a_bracket(pt)
                    if not bracket:
                        return

                    if bracket == brackets[0]:
                        return self.find_balanced_closing_bracket(bracket_pt + 1, brackets)
                    else:
                        return self.find_balanced_opening_bracket(bracket_pt, brackets)

                if mode == VISUAL:
                    found = find_bracket_location(s)
                    if found is not None:
                        # Offset by 1 if s.a was upperbound but begin is not
                        begin = (s.a - 1) if (s.b < s.a and (s.a - 1) < found) else s.a
                        # Offset by 1 if begin is now upperbound but s.a was not
                        begin = (s.a + 1) if (found < s.a and s.a < s.b) else begin

                        # Testing against adjusted begin
                        end = (found + 1) if (begin <= found) else found

                        return Region(begin, end)

                if mode == VISUAL_LINE:

                    sel = s
                    if sel.a > sel.b:
                        # If selection is in reverse: b <-- a
                        # Find bracket starting at end of line of point b
                        target_pt = find_bracket_location(Region(sel.b, self.view.line(sel.b).end()))
                    else:
                        # If selection is forward: a --> b
                        # Find bracket starting at point b - 1:
                        #   Because point b for an a --> b VISUAL LINE selection
                        #   is the eol (newline) character.
                        target_pt = find_bracket_location(Region(sel.a, sel.b - 1))

                    if target_pt is not None:
                        target_full_line = self.view.full_line(target_pt)

                        if sel.a > sel.b:
                            # If REVERSE selection: b <-- a

                            if target_full_line.a > sel.a:
                                # If target is after start of selection: b <-- a --> t
                                # Keep line a, extend to end of target, and reverse: a --> t
                                a, b = self.view.line(sel.a - 1).a, target_full_line.b
                            else:
                                # If target is before or after end of selection:
                                #   Before: b     t <-- a (subtract t --> b)
                                #   After:  t <-- b <-- a (extend b --> t)
                                a, b = sel.a, target_full_line.a

                        else:
                            # If FORWARD selection: a --> b

                            if target_full_line.a < sel.a:
                                # If target is before start of selection: t <-- a --> b
                                # Keep line a, extend to start of target, and reverse: t <-- a
                                a, b = self.view.full_line(sel.a).b, target_full_line.a
                            else:
                                # If target is before or after end of selection:
                                #   Before: a --> t     b (subtract t --> b)
                                #   After:  a --> b --> t (extend b --> t)
                                a, b = s.a, target_full_line.b

                        return Region(a, b)

                elif mode == NORMAL:
                    a = find_bracket_location(s)
                    if a is not None:
                        return Region(a, a)

                # TODO: According to Vim we must swallow brackets in this case.
                elif mode == INTERNAL_NORMAL:
                    found = find_bracket_location(s)
                    if found is not None:
                        if found < s.a:
                            return Region(s.a + 1, found)
                        else:
                            return Region(s.a, found + 1)

                return s

            regions_transformer(self.view, move_to_bracket)

        else:

            row = self.view.rowcol(self.view.size())[0] * (percent / 100)

            def f(view, s):
                return Region(view.text_point(row, 0))

            regions_transformer(self.view, f)

            # FIXME Bringing the selections into view will be undesirable in
            # many cases. Maybe we should have an optional
            # .scroll_selections_into_view() step during command execution.
            self.view.show(self.view.sel()[0])

    def find_a_bracket(self, caret_pt):
        """
        Locate the next bracket after the caret in the current line.

        If None is found, execution must be aborted.

        Return (bracket, brackets, bracket_pt).

        Example ('(', ('(', ')'), 1337)).
        """
        caret_row, caret_col = self.view.rowcol(caret_pt)
        line_text = self.view.substr(Region(caret_pt, self.view.line(caret_pt).b))
        try:
            found_brackets = min([(line_text.index(bracket), bracket)
                                 for bracket in chain(*self.pairs)
                                 if bracket in line_text])
        except ValueError:
            return None, None, None

        bracket_a, bracket_b = [(a, b) for (a, b) in self.pairs if found_brackets[1] in (a, b)][0]
        return (found_brackets[1], (bracket_a, bracket_b),
                self.view.text_point(caret_row, caret_col + found_brackets[0]))

    def find_balanced_closing_bracket(self, start, brackets, unbalanced=0):
        # Returns:
        #   Region|None
        new_start = start
        for i in range(unbalanced or 1):
            next_closing_bracket = find_in_range(
                self.view,
                brackets[1],
                start=new_start,
                end=self.view.size(),
                flags=LITERAL
            )

            if next_closing_bracket is None:  # Unbalanced brackets; nothing we can do.
                return

            new_start = next_closing_bracket.end()

        nested = 0
        while True:
            next_opening_bracket = find_in_range(
                self.view,
                brackets[0],
                start=start,
                end=next_closing_bracket.end(),
                flags=LITERAL
            )

            if not next_opening_bracket:
                break

            nested += 1
            start = next_opening_bracket.end()

        if nested > 0:
            return self.find_balanced_closing_bracket(
                next_closing_bracket.end(),
                brackets,
                nested
            )
        else:
            return next_closing_bracket.begin()

    def find_balanced_opening_bracket(self, start, brackets, unbalanced=0):
        new_start = start
        for i in range(unbalanced or 1):
            prev_opening_bracket = reverse_search_by_pt(
                self.view, brackets[0],
                start=0,
                end=new_start,
                flags=LITERAL
            )

            # Unbalanced brackets; nothing we can do.
            if prev_opening_bracket is None:
                return

            new_start = prev_opening_bracket.begin()

        nested = 0
        while True:
            next_closing_bracket = reverse_search_by_pt(
                self.view, brackets[1],
                start=prev_opening_bracket.a,
                end=start,
                flags=LITERAL
            )

            if not next_closing_bracket:
                break

            nested += 1
            start = next_closing_bracket.begin()

        if nested > 0:
            return self.find_balanced_opening_bracket(
                prev_opening_bracket.begin(),
                brackets,
                nested
            )
        else:
            return prev_opening_bracket.begin()


class _vi_big_h(ViMotionCommand):
    def run(self, count=None, mode=None):
        def f(view, s):
            if mode == NORMAL:
                return Region(target_pt)
            elif mode == INTERNAL_NORMAL:
                return Region(s.a, target_pt)
            elif mode == VISUAL:
                if s.a < s.b and target_pt < s.a:
                    return Region(s.a + 1, target_pt)
                return Region(s.a, target_pt)
            elif mode == VISUAL_LINE:
                if s.b > s.a and target_pt <= s.a:
                    a = self.view.full_line(s.a).b
                    b = self.view.line(target_pt).a
                elif s.b > s.a:
                    a = s.a
                    b = self.view.full_line(target_pt).b
                else:
                    a = s.a
                    b = self.view.line(target_pt).a

                return Region(a, b)

            return s

        target_pt = next_non_blank(self.view, highest_visible_pt(self.view))
        regions_transformer(self.view, f)


class _vi_big_l(ViMotionCommand):
    def run(self, count=None, mode=None):
        def f(view, s):
            if mode == NORMAL:
                return Region(target_pt)
            elif mode == INTERNAL_NORMAL:
                if s.b >= target_pt:
                    return Region(s.a + 1, target_pt)

                return Region(s.a, target_pt)
            elif mode == VISUAL:
                if s.a > s.b and target_pt > s.a:
                    return Region(s.a - 1, target_pt + 1)

                return Region(s.a, target_pt + 1)
            elif mode == VISUAL_LINE:
                if s.a > s.b and target_pt >= s.a:
                    a = self.view.line(s.a - 1).a
                    b = self.view.full_line(target_pt).b
                elif s.a > s.b:
                    a = self.view.line(target_pt).a
                    b = s.a
                else:
                    a = s.a
                    b = self.view.full_line(target_pt).b

                return Region(a, b)
            else:
                return s

        target_pt = next_non_blank(self.view, lowest_visible_pt(self.view))
        regions_transformer(self.view, f)


class _vi_big_m(ViMotionCommand):
    def run(self, count=None, extend=False, mode=None):
        def f(view, s):
            if mode == NORMAL:
                return Region(target_pt)
            elif mode == INTERNAL_NORMAL:
                return Region(s.a, target_pt)
            elif mode == VISUAL_LINE:
                if s.b > s.a:
                    if target_pt < s.a:
                        a = self.view.full_line(s.a).b
                        b = self.view.line(target_pt).a
                    else:
                        a = s.a
                        b = self.view.full_line(target_pt).b
                else:
                    if target_pt >= s.a:
                        a = self.view.line(s.a - 1).a
                        b = self.view.full_line(target_pt).b
                    else:
                        a = s.a
                        b = self.view.full_line(target_pt).a

                return Region(a, b)
            elif mode == VISUAL:
                a = s.a
                b = target_pt

                if s.b > s.a and target_pt < s.a:
                    a += 1
                elif s.a > s.b and target_pt > s.a:
                    a -= 1
                    b += 1
                elif s.b > s.a:
                    b += 1

                return Region(a, b)
            else:
                return s

        highest_row, lowest_row = highlow_visible_rows(self.view)
        half_visible_lines = (lowest_row - highest_row) // 2
        middle_row = highest_row + half_visible_lines
        target_pt = next_non_blank(self.view, self.view.text_point(middle_row, 0))
        regions_transformer(self.view, f)


class _vi_star(ViMotionCommand, ExactWordBufferSearchBase):
    def run(self, count=1, mode=None, search_string=None):
        def f(view, s):
            pattern = self.build_pattern(query)
            flags = self.calculate_flags(query)

            if mode == INTERNAL_NORMAL:
                match = find_wrapping(view,
                                      term=pattern,
                                      start=view.word(s.end()).end(),
                                      end=view.size(),
                                      flags=flags,
                                      times=1)
            else:
                match = find_wrapping(view,
                                      term=pattern,
                                      start=view.word(s.end()).end(),
                                      end=view.size(),
                                      flags=flags,
                                      times=1)

            if match:
                if mode == INTERNAL_NORMAL:
                    return Region(s.a, match.begin())
                elif mode == VISUAL:
                    return Region(s.a, match.begin())
                elif mode == NORMAL:
                    return Region(match.begin(), match.begin())

            elif mode == NORMAL:
                pt = view.word(s.end()).begin()
                return Region(pt)

            return s

        state = self.state
        query = search_string or self.get_query()

        jumplist_update(self.view)
        regions_transformer(self.view, f)
        jumplist_update(self.view)

        if query:
            self.hilite(query)
            # Ensure n and N can repeat this search later.
            state.last_buffer_search = query

        if not search_string:
            state.last_buffer_search_command = 'vi_star'

        show_if_not_visible(self.view)


class _vi_octothorp(ViMotionCommand, ExactWordBufferSearchBase):
    def run(self, count=1, mode=None, search_string=None):
        def f(view, s):
            pattern = self.build_pattern(query)
            flags = self.calculate_flags(query)

            if mode == INTERNAL_NORMAL:
                match = reverse_find_wrapping(view,
                                              term=pattern,
                                              start=0,
                                              end=start_sel.a,
                                              flags=flags,
                                              times=1)
            else:
                match = reverse_find_wrapping(view,
                                              term=pattern,
                                              start=0,
                                              end=start_sel.a,
                                              flags=flags,
                                              times=1)

            if match:
                if mode == INTERNAL_NORMAL:
                    return Region(s.b, match.begin())
                elif mode == VISUAL:
                    return Region(s.b, match.begin())
                elif mode == NORMAL:
                    return Region(match.begin(), match.begin())

            elif mode == NORMAL:
                return Region(previous_white_space_char(view, s.b) + 1)

            return s

        state = self.state

        query = search_string or self.get_query()

        jumplist_update(self.view)
        start_sel = self.view.sel()[0]
        regions_transformer(self.view, f)
        jumplist_update(self.view)

        if query:
            self.hilite(query)
            # Ensure n and N can repeat this search later.
            state.last_buffer_search = query

        if not search_string:
            state.last_buffer_search_command = 'vi_octothorp'

        show_if_not_visible(self.view)


class _vi_b(ViMotionCommand):
    def run(self, mode=None, count=1):
        def do_motion(view, s):
            if mode == NORMAL:
                pt = word_reverse(self.view, s.b, count)
                return Region(pt)

            elif mode == INTERNAL_NORMAL:
                pt = word_reverse(self.view, s.b, count)
                return Region(s.a, pt)

            elif mode in (VISUAL, VISUAL_BLOCK):
                if s.a < s.b:
                    pt = word_reverse(self.view, s.b - 1, count)
                    if pt < s.a:
                        return Region(s.a + 1, pt)
                    return Region(s.a, pt + 1)
                elif s.b < s.a:
                    pt = word_reverse(self.view, s.b, count)
                    return Region(s.a, pt)

            return s

        regions_transformer(self.view, do_motion)


class _vi_big_b(ViMotionCommand):

    def run(self, count=1, mode=None):
        def do_motion(view, s):
            if mode == NORMAL:
                pt = word_reverse(self.view, s.b, count, big=True)
                return Region(pt)

            elif mode == INTERNAL_NORMAL:
                pt = word_reverse(self.view, s.b, count, big=True)
                return Region(s.a, pt)

            elif mode in (VISUAL, VISUAL_BLOCK):
                if s.a < s.b:
                    pt = word_reverse(self.view, s.b - 1, count, big=True)
                    if pt < s.a:
                        return Region(s.a + 1, pt)
                    return Region(s.a, pt + 1)
                elif s.b < s.a:
                    pt = word_reverse(self.view, s.b, count, big=True)
                    return Region(s.a, pt)

            return s

        regions_transformer(self.view, do_motion)


class _vi_underscore(ViMotionCommand):
    def run(self, count=None, mode=None):
        def f(view, s):
            a = s.a
            b = s.b
            if s.size() > 0:
                a = resolve_insertion_point_at_a(s)
                b = resolve_insertion_point_at_b(s)

            current_row = self.view.rowcol(b)[0]
            target_row = current_row + (count - 1)
            last_row = self.view.rowcol(self.view.size() - 1)[0]

            if target_row > last_row:
                target_row = last_row

            bol = self.view.text_point(target_row, 0)

            if mode == NORMAL:
                bol = next_non_white_space_char(self.view, bol)
                return Region(bol)

            elif mode == INTERNAL_NORMAL:
                # TODO: differentiate between 'd' and 'c'
                begin = self.view.line(b).a
                target_row_bol = self.view.text_point(target_row, 0)
                end = self.view.line(target_row_bol).b

                # XXX: There may be better ways to communicate between actions
                # and motions than by inspecting state.
                if isinstance(self.state.action, ViChangeByChars):
                    return Region(begin, end)
                else:
                    return Region(begin, end + 1)

            elif mode == VISUAL:
                bol = next_non_white_space_char(self.view, bol)
                return new_inclusive_region(a, bol)
            else:
                return s

        regions_transformer(self.view, f)


class _vi_hat(ViMotionCommand):
    def run(self, count=None, mode=None):
        def f(view, s):
            a = s.a
            b = s.b
            if s.size() > 0:
                a = resolve_insertion_point_at_a(s)
                b = resolve_insertion_point_at_b(s)

            bol = self.view.line(b).a
            bol = next_non_white_space_char(self.view, bol)

            if mode == NORMAL:
                return Region(bol)
            elif mode == INTERNAL_NORMAL:
                # The character at the "end" of the region is skipped in both
                # forward and reverse cases, so unlike other regions, no need to add 1 to it
                return Region(a, bol)
            elif mode == VISUAL:
                return new_inclusive_region(a, bol)
            else:
                return s

        regions_transformer(self.view, f)


class _vi_gj(ViMotionCommand):
    def run(self, mode=None, count=1):
        if mode == NORMAL:
            for i in range(count):
                self.view.run_command('move', {'by': 'lines', 'forward': True, 'extend': False})
        elif mode == VISUAL:
            for i in range(count):
                self.view.run_command('move', {'by': 'lines', 'forward': True, 'extend': True})
        elif mode == VISUAL_LINE:
            self.view.run_command('_vi_j', {'mode': mode, 'count': count})
        elif mode == INTERNAL_NORMAL:
            for i in range(count):
                self.view.run_command('move', {'by': 'lines', 'forward': True, 'extend': False})


class _vi_gk(ViMotionCommand):
    def run(self, mode=None, count=1):
        if mode == NORMAL:
            for i in range(count):
                self.view.run_command('move', {'by': 'lines', 'forward': False, 'extend': False})
        elif mode == VISUAL:
            for i in range(count):
                self.view.run_command('move', {'by': 'lines', 'forward': False, 'extend': True})
        elif mode == VISUAL_LINE:
            self.view.run_command('_vi_k', {'mode': mode, 'count': count})
        elif mode == INTERNAL_NORMAL:
            for i in range(count):
                self.view.run_command('move', {'by': 'lines', 'forward': False, 'extend': False})


class _vi_g__(ViMotionCommand):
    def run(self, count=1, mode=None):
        def f(view, s):
            if mode == NORMAL:
                eol = view.line(s.b).b
                return Region(eol - 1, eol - 1)
            elif mode == VISUAL:
                eol = None
                if s.a < s.b:
                    eol = view.line(s.b - 1).b
                    return Region(s.a, eol)
                else:
                    eol = view.line(s.b).b
                    if eol > s.a:
                        return Region(s.a - 1, eol)
                    return Region(s.a, eol)

            elif mode == INTERNAL_NORMAL:
                eol = view.line(s.b).b
                return Region(s.a, eol)

            return s

        regions_transformer(self.view, f)


class _vi_ctrl_u(ViMotionCommand):

    def run(self, count=0, mode=None):
        def f(view, s):
            if mode == NORMAL:
                return Region(scroll_target_pt)
            elif mode == VISUAL:
                a = s.a
                b = scroll_target_pt

                if s.b > s.a:
                    if scroll_target_pt < s.a:
                        a += 1
                    else:
                        b += 1

                return Region(a, b)

                if s.a < s.b and scroll_target_pt < s.a:
                    return Region(min(s.a + 1, self.view.size()), scroll_target_pt)
                return Region(s.a, scroll_target_pt)

            elif mode == INTERNAL_NORMAL:
                return Region(s.a, scroll_target_pt)
            elif mode == VISUAL_LINE:
                if s.b > s.a:
                    if scroll_target_pt < s.a:
                        a = self.view.full_line(s.a).b
                        b = self.view.line(scroll_target_pt).a
                    else:
                        a = self.view.line(s.a).a
                        b = self.view.full_line(scroll_target_pt).b
                else:
                    a = s.a
                    b = self.view.line(scroll_target_pt).a

                return Region(a, b)
            return s

        number_of_scroll_lines = count if count >= 1 else get_option_scroll(self.view)
        scroll_target_pt = get_scroll_up_target_pt(self.view, number_of_scroll_lines)
        if scroll_target_pt is None:
            return ui_blink()

        regions_transformer(self.view, f)
        if not self.view.visible_region().contains(0):
            scroll_viewport_position(self.view, number_of_scroll_lines, forward=False)


class _vi_ctrl_d(ViMotionCommand):

    def run(self, count=0, mode=None):
        def f(view, s):
            if mode == NORMAL:
                return Region(scroll_target_pt)
            elif mode == VISUAL:
                a = s.a
                b = scroll_target_pt

                if s.b > s.a:
                    b += 1
                elif scroll_target_pt >= s.a:
                    a -= 1
                    b += 1

                return Region(a, b)
            elif mode == INTERNAL_NORMAL:
                return Region(s.a, scroll_target_pt)
            elif mode == VISUAL_LINE:
                if s.a > s.b:
                    if scroll_target_pt >= s.a:
                        a = self.view.line(s.a - 1).a
                        b = self.view.full_line(scroll_target_pt).b
                    else:
                        a = s.a
                        b = self.view.line(scroll_target_pt).a
                else:
                    a = s.a
                    b = self.view.full_line(scroll_target_pt).b

                return Region(a, b)

            return s

        number_of_scroll_lines = count if count >= 1 else get_option_scroll(self.view)
        scroll_target_pt = get_scroll_down_target_pt(self.view, number_of_scroll_lines)
        if scroll_target_pt is None:
            return ui_blink()

        regions_transformer(self.view, f)
        if not self.view.visible_region().contains(self.view.size()):
            scroll_viewport_position(self.view, number_of_scroll_lines)


class _vi_pipe(ViMotionCommand):

    def _col_to_pt(self, pt, current_col):
        if self.view.line(pt).size() < current_col:
            return self.view.line(pt).b - 1

        row = self.view.rowcol(pt)[0]

        return self.view.text_point(row, current_col) - 1

    def run(self, mode=None, count=1):
        def f(view, s):
            if mode == NORMAL:
                return Region(self._col_to_pt(s.b, count))
            elif mode == VISUAL:
                pt = self._col_to_pt(s.b - 1, count)
                if s.a < s.b:
                    if pt < s.a:
                        return Region(s.a + 1, pt)
                    else:
                        return Region(s.a, pt + 1)
                else:
                    if pt > s.a:
                        return Region(s.a - 1, pt + 1)
                    else:
                        return Region(s.a, pt)

            elif mode == INTERNAL_NORMAL:
                pt = self._col_to_pt(s.b, count)

                if s.a < s.b:
                    return Region(s.a, pt)
                else:
                    return Region(s.a + 1, pt)

            return s

        regions_transformer(self.view, f)


class _vi_ge(ViMotionCommand):
    def run(self, mode=None, count=1):
        def to_word_end(view, s):
            if mode == NORMAL:
                pt = word_end_reverse(view, s.b, count)
                return Region(pt)
            elif mode in (VISUAL, VISUAL_BLOCK):
                if s.a < s.b:
                    pt = word_end_reverse(view, s.b - 1, count)
                    if pt > s.a:
                        return Region(s.a, pt + 1)
                    return Region(s.a + 1, pt)
                pt = word_end_reverse(view, s.b, count)
                return Region(s.a, pt)
            return s

        regions_transformer(self.view, to_word_end)


class _vi_g_big_e(ViMotionCommand):
    def run(self, mode=None, count=1):
        def to_word_end(view, s):
            if mode == NORMAL:
                pt = word_end_reverse(view, s.b, count, big=True)
                return Region(pt)
            elif mode in (VISUAL, VISUAL_BLOCK):
                if s.a < s.b:
                    pt = word_end_reverse(view, s.b - 1, count, big=True)
                    if pt > s.a:
                        return Region(s.a, pt + 1)
                    return Region(s.a + 1, pt)
                pt = word_end_reverse(view, s.b, count, big=True)
                return Region(s.a, pt)
            return s

        regions_transformer(self.view, to_word_end)


class _vi_left_paren(ViMotionCommand):

    def run(self, mode=None, count=1):
        def f(view, s):
            previous_sentence = find_sentences_backward(self.view, s, count)
            if previous_sentence is None:
                return s

            if mode == NORMAL:
                return Region(previous_sentence.a)
            elif mode == VISUAL:
                return Region(s.a + 1, previous_sentence.a + 1)
            elif mode == INTERNAL_NORMAL:
                return Region(s.a, previous_sentence.a + 1)

            return s

        regions_transformer(self.view, f)


class _vi_right_paren(ViMotionCommand):

    def run(self, mode=None, count=1):
        def f(view, s):
            next_sentence = find_sentences_forward(self.view, s, count)
            if next_sentence is None:
                return s

            if mode == NORMAL:
                return Region(min(next_sentence.b, view.size() - 1))
            elif mode == VISUAL:
                return Region(s.a, min(next_sentence.b + 1, view.size() - 1))
            elif mode == INTERNAL_NORMAL:
                return Region(s.a, next_sentence.b)

            return s

        regions_transformer(self.view, f)


class _vi_question_mark_impl(ViMotionCommand, BufferSearchBase):
    def run(self, search_string, mode=None, count=1, extend=False):
        def f(view, s):
            if mode == VISUAL:
                return Region(s.end(), found.a)
            elif mode == INTERNAL_NORMAL:
                return Region(s.end(), found.a)
            elif mode == NORMAL:
                return Region(found.a, found.a)
            elif mode == VISUAL_LINE:
                return Region(s.end(), view.full_line(found.a).a)

            return s

        # This happens when we attempt to repeat the search and there's no
        # search term stored yet.
        if search_string is None:
            return

        flags = self.calculate_flags(search_string)
        # FIXME: What should we do here? Case-sensitive or case-insensitive search? Configurable?
        found = reverse_find_wrapping(self.view,
                                      term=search_string,
                                      start=0,
                                      end=self.view.sel()[0].b,
                                      flags=flags,
                                      times=count)

        if not found:
            return status_message('Pattern not found')

        regions_transformer(self.view, f)
        self.hilite(search_string)


class _vi_question_mark(ViMotionCommand, BufferSearchBase):

    def _is_valid_cmdline(self, cmdline):
        return isinstance(cmdline, str) and len(cmdline) > 0 and cmdline[0] == '?'

    def run(self):
        self.state.reset_during_init = False
        # TODO Add incsearch option e.g. on_change = self.on_change if 'incsearch' else None
        ui_cmdline_prompt(
            self.view.window(),
            initial_text='?',
            on_done=self.on_done,
            on_change=self.on_change,
            on_cancel=self.on_cancel)

    def on_done(self, s):
        if not self._is_valid_cmdline(s):
            return self.on_cancel(force=True)

        history_update(s)
        _nv_cmdline_feed_key.reset_last_history_index()
        s = s[1:]

        state = self.state
        state.sequence += s + '<CR>'
        self.view.erase_regions('vi_inc_search')
        state.last_buffer_search_command = 'vi_question_mark'
        state.motion = ViSearchBackwardImpl(term=s)

        # If s is empty, we must repeat the last search.
        state.last_buffer_search = s or state.last_buffer_search
        state.eval()

    def on_change(self, s):
        if not self._is_valid_cmdline(s):
            return self.on_cancel(force=True)

        s = s[1:]

        flags = self.calculate_flags(s)
        self.view.erase_regions('vi_inc_search')
        state = self.state
        occurrence = reverse_find_wrapping(self.view,
                                           term=s,
                                           start=0,
                                           end=self.view.sel()[0].b,
                                           flags=flags,
                                           times=state.count)
        if occurrence:
            if state.mode == VISUAL:
                occurrence = Region(self.view.sel()[0].a, occurrence.a)

            # The scopes are prefixed with common color scopes so that color
            # schemes have sane default colors. Color schemes can progressively
            # enhance support by using the nv_* scopes.
            self.view.add_regions(
                'vi_inc_search',
                [occurrence],
                scope='support.function neovintageous_search_inc',
                flags=ui_region_flags(self.view.settings().get('neovintageous_search_inc_style'))
            )

            if not self.view.visible_region().contains(occurrence):
                self.view.show(occurrence)

    def on_cancel(self, force=False):
        self.view.erase_regions('vi_inc_search')
        state = self.state
        state.reset_command_data()
        _nv_cmdline_feed_key.reset_last_history_index()

        if not self.view.visible_region().contains(self.view.sel()[0]):
            self.view.show(self.view.sel()[0])

        if force:
            self.view.window().run_command('hide_panel', {'cancel': True})


class _vi_question_mark_on_parser_done(WindowCommand):

    def run(self, key=None):
        state = State(self.window.active_view())
        state.motion = ViSearchBackwardImpl()
        state.last_buffer_search = (state.motion.inp or state.last_buffer_search)


class _vi_repeat_buffer_search(ViMotionCommand):

    commands = {
        'vi_slash': ['_vi_slash_impl', '_vi_question_mark_impl'],
        'vi_question_mark': ['_vi_question_mark_impl', '_vi_slash_impl'],
        'vi_star': ['_vi_star', '_vi_octothorp'],
        'vi_octothorp': ['_vi_octothorp', '_vi_star'],
    }

    def run(self, mode=None, count=1, reverse=False):
        state = self.state
        search_string = state.last_buffer_search
        search_command = state.last_buffer_search_command
        command = self.commands[search_command][int(reverse)]

        self.view.run_command(command, {
            'mode': mode,
            'count': count,
            'search_string': search_string
        })

        self.view.show(self.view.sel(), show_surrounds=True)


class _vi_n(ViMotionCommand):

    def run(self, mode=None, count=1, search_string=''):
        self.view.run_command('_vi_slash_impl', {'mode': mode, 'count': count, 'search_string': search_string})


class _vi_big_n(ViMotionCommand):

    def run(self, count=1, mode=None, search_string=''):
        self.view.run_command('_vi_question_mark_impl', {'mode': mode, 'count': count, 'search_string': search_string})


class _vi_big_e(ViMotionCommand):
    def run(self, mode=None, count=1):
        def do_move(view, s):
            b = s.b
            if s.a < s.b:
                b = s.b - 1

            pt = word_ends(view, b, count=count, big=True)

            if mode == NORMAL:
                return Region(pt - 1)

            elif mode == INTERNAL_NORMAL:
                return Region(s.a, pt)

            elif mode == VISUAL:
                start = s.a
                if s.b < s.a:
                    start = s.a - 1
                end = pt - 1
                if start <= end:
                    return Region(start, end + 1)
                else:
                    return Region(start + 1, end)

            elif mode == VISUAL_BLOCK:
                if s.a > s.b:
                    if pt > s.a:
                        return Region(s.a - 1, pt)
                    return Region(s.a, pt - 1)
                return Region(s.a, pt)

            return s

        regions_transformer(self.view, do_move)


class _vi_ctrl_f(ViMotionCommand):
    def run(self, mode=None, count=1):
        if mode == NORMAL:
            self.view.run_command('move', {'by': 'pages', 'forward': True})
        elif mode == VISUAL:
            self.view.run_command('move', {'by': 'pages', 'forward': True, 'extend': True})
        elif mode == VISUAL_LINE:
            self.view.run_command('move', {'by': 'pages', 'forward': True, 'extend': True})

            new_sels = []
            for sel in self.view.sel():
                line = self.view.full_line(sel.b)
                if sel.b > sel.a:
                    new_sels.append(Region(sel.a, line.end()))
                else:
                    new_sels.append(Region(sel.a, line.begin()))

            if new_sels:
                self.view.sel().clear()
                self.view.sel().add_all(new_sels)


class _vi_ctrl_b(ViMotionCommand):
    def run(self, mode=None, count=1):
        if mode == NORMAL:
            self.view.run_command('move', {'by': 'pages', 'forward': False})
        elif mode == VISUAL:
            self.view.run_command('move', {'by': 'pages', 'forward': False, 'extend': True})
        elif mode == VISUAL_LINE:
            self.view.run_command('move', {'by': 'pages', 'forward': False, 'extend': True})

            new_sels = []
            for sel in self.view.sel():
                line = self.view.full_line(sel.b)
                if sel.b > sel.a:
                    new_sels.append(Region(sel.a, line.end()))
                else:
                    new_sels.append(Region(sel.a, line.begin()))

            if new_sels:
                self.view.sel().clear()
                self.view.sel().add_all(new_sels)


class _vi_enter(ViMotionCommand):
    def run(self, mode=None, count=1):
        self.view.run_command('_vi_j', {'mode': mode, 'count': count})

        def advance(view, s):
            if mode == NORMAL:
                return Region(next_non_white_space_char(view, s.b))
            elif mode == VISUAL:
                if s.a < s.b:
                    return Region(s.a, next_non_white_space_char(view, s.b - 1))

                return Region(s.a, next_non_white_space_char(view, s.b))

            return s

        regions_transformer(self.view, advance)


class _vi_minus(ViMotionCommand):
    def run(self, mode=None, count=1):
        self.view.run_command('_vi_k', {'mode': mode, 'count': count})

        def advance(view, s):
            if mode == NORMAL:
                pt = next_non_white_space_char(view, s.b)
                return Region(pt)
            elif mode == VISUAL:
                if s.a < s.b:
                    pt = next_non_white_space_char(view, s.b - 1)
                    return Region(s.a, pt + 1)
                pt = next_non_white_space_char(view, s.b)
                return Region(s.a, pt)
            return s

        regions_transformer(self.view, advance)


class _vi_shift_enter(ViMotionCommand):
    def run(self, mode=None, count=1):
        self.view.run_command('_vi_ctrl_f', {'mode': mode, 'count': count})


class _vi_select_text_object(ViMotionCommand):
    def run(self, text_object=None, mode=None, count=1, extend=False, inclusive=False):
        def f(view, s):
            # TODO: Vim seems to swallow the delimiters if you give this command.
            if mode in (INTERNAL_NORMAL, VISUAL):

                # TODO: For the ( object, we have to abort the editing command
                # completely if no match was found. We could signal this to
                # the caller via exception.
                return get_text_object_region(view, s, text_object,
                                              inclusive=inclusive,
                                              count=count)

            return s

        regions_transformer(self.view, f)


class _vi_go_to_symbol(ViMotionCommand):
    """
    Go to local declaration.

    Differs from Vim because it leverages Sublime Text's ability to actually
    locate symbols (Vim simply searches from the top of the file).
    """

    def find_symbol(self, r, globally=False):
        query = self.view.substr(self.view.word(r))
        fname = self.view.file_name().replace('\\', '/')

        locations = self.view.window().lookup_symbol_in_index(query)
        if not locations:
            return

        try:
            if not globally:
                location = [hit[2] for hit in locations if fname.endswith(hit[1])][0]
                return location[0] - 1, location[1] - 1
            else:
                # TODO: There might be many symbols with the same name.
                return locations[0]
        except IndexError:
            return

    def run(self, count=1, mode=None, globally=False):

        def f(view, s):
            if mode == NORMAL:
                return Region(location, location)

            elif mode == VISUAL:
                return Region(s.a + 1, location)

            elif mode == INTERNAL_NORMAL:
                return Region(s.a, location)

            return s

        current_sel = self.view.sel()[0]
        self.view.sel().clear()
        self.view.sel().add(current_sel)

        location = self.find_symbol(current_sel, globally=globally)
        if not location:
            return

        if globally:
            # Global symbol; simply open the file; not a motion.
            # TODO: Perhaps must be a motion if the target file happens to be
            #       the current one?
            jumplist_update(self.view)
            self.view.window().open_file(
                location[0] + ':' + ':'.join([str(x) for x in location[2]]),
                ENCODED_POSITION
            )
            jumplist_update(self.view)

            return

        # Local symbol; select.
        location = self.view.text_point(*location)

        jumplist_update(self.view)
        regions_transformer(self.view, f)
        jumplist_update(self.view)


class _vi_gm(ViMotionCommand):
    def run(self, mode=None, count=1):
        def advance(view, s):
            line = view.line(s.b)
            if line.empty():
                return s
            mid_pt = line.size() // 2
            row_start = row_to_pt(self.view, row_at(self.view, s.b))
            return Region(min(row_start + mid_pt, line.b - 1))

        if mode != NORMAL:
            return ui_blink()

        regions_transformer(self.view, advance)


class _vi_left_square_bracket(ViMotionCommand):
    def run(self, action, mode, count=1, **kwargs):
        if action == 'c':
            goto_prev_change(self.view, mode, count, **kwargs)
        elif action == 'target':
            goto_prev_target(self.view, mode, count, **kwargs)
        else:
            raise ValueError('unknown action')


class _vi_right_square_bracket(ViMotionCommand):
    def run(self, action, mode, count=1, **kwargs):
        if action == 'c':
            goto_next_change(self.view, mode, count, **kwargs)
        elif action == 'target':
            goto_next_target(self.view, mode, count, **kwargs)
        else:
            raise ValueError('unknown action')
