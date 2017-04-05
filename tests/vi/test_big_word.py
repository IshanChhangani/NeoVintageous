# from Vintageous.vi.constants import _MODE_INTERNAL_NORMAL
from Vintageous.vi.constants import MODE_NORMAL
# from Vintageous.vi.constants import MODE_VISUAL
# from Vintageous.vi.constants import MODE_VISUAL_LINE

from collections import namedtuple

from Vintageous.tests import ViewTest
from Vintageous.tests import set_text
from Vintageous.tests import add_sel

from Vintageous.vi.units import next_big_word_start
from Vintageous.vi.units import big_word_starts
from Vintageous.vi.units import CLASS_VI_INTERNAL_WORD_START

# TODO: Test against folded regions.
# TODO: Ensure that we only create empty selections while testing. Add assert_all_sels_empty()?
test_data = namedtuple('test_data', 'initial_text region expected msg')
region_data = namedtuple('region_data', 'regions')


def get_text(test):
    return test.view.substr(test.R(0, test.view.size()))

def  first_sel_wrapper(test):
    return first_sel(test.view)


TESTS_MOVE_FORWARD = (
    test_data(initial_text='  foo bar\n', region=(0, 0), expected=2, msg=''),
    test_data(initial_text='  (foo)\n', region=(0, 0), expected=2, msg=''),
    test_data(initial_text='  \n\n\n', region=(0, 0), expected=3, msg=''),
    test_data(initial_text='  \n  \n\n', region=(0, 0), expected=3, msg=''),
    test_data(initial_text='  \n', region=(0, 0), expected=3, msg=''),
    test_data(initial_text='   ', region=(0, 0), expected=3, msg=''),
    test_data(initial_text='   \nfoo\nbar', region=(0, 0), expected=4, msg=''),
    test_data(initial_text='   \n foo\nbar', region=(0, 0), expected=4, msg=''),
    test_data(initial_text='  a foo bar\n', region=(0, 0), expected=2, msg=''),
    test_data(initial_text='  \na\n\n', region=(0, 0), expected=3, msg=''),
    test_data(initial_text='  \n a\n\n', region=(0, 0), expected=3, msg=''),

    test_data(initial_text='(foo) bar\n', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo) (bar)\n', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo)\n\n\n', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo)\n  \n\n', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo)\n', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo)', region=(0, 0), expected=5, msg=''),
    test_data(initial_text='(foo)\nbar\nbaz', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo)\n bar\nbaz', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo) a bar\n', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo)\na\n\n', region=(0, 0), expected=6, msg=''),
    test_data(initial_text='(foo)\n a\n\n', region=(0, 0), expected=6, msg=''),
)


class Test_big_word_all(ViewTest):
    def testAll(self):
        set_text(self.view, '  foo bar\n')

        for (i, data) in enumerate(TESTS_MOVE_FORWARD):
            self.view.sel().clear()

            self.write(data.initial_text)
            r = self.R(*data.region)
            self.add_sel(r)

            pt = next_big_word_start(self.view, r.b)
            self.assertEqual(pt, data.expected, 'failed at test index {0}'.format(i))


class Test_next_big_word_start_InNormalMode_FromWord(ViewTest):
    def testToWordStart(self):
        set_text(self.view, '(foo) bar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToPunctuationStart(self):
        set_text(self.view, '(foo) (bar)\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToEmptyLine(self):
        set_text(self.view, '(foo)\n\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToWhitespaceLine(self):
        set_text(self.view, '(foo)\n  \n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToEofWithNewline(self):
        set_text(self.view, '(foo)\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToEof(self):
        set_text(self.view, '(foo)')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 5)

    def testToOneWordLine(self):
        set_text(self.view, '(foo)\nbar\nbaz')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '(foo)\n bar\nbaz')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToOneCharWord(self):
        set_text(self.view, '(foo) a bar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToOneCharLine(self):
        set_text(self.view, '(foo)\na\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToOneCharLineWithLeadingWhitespace(self):
        set_text(self.view, '(foo)\n a\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)


class Test_next_big_word_start_InNormalMode_FromPunctuationStart(ViewTest):
    def testToWordStart(self):
        set_text(self.view, ':foo\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 5)

    def testToPunctuationStart(self):
        set_text(self.view, ': (foo)\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToEmptyLine(self):
        set_text(self.view, ':\n\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToWhitespaceLine(self):
        set_text(self.view, ':\n  \n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToEofWithNewline(self):
        set_text(self.view, ':\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToEof(self):
        set_text(self.view, ':')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToOneWordLine(self):
        set_text(self.view, ':\nbar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, ':\n bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToOneCharWord(self):
        set_text(self.view, ':a bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToOneCharLine(self):
        set_text(self.view, ':\na\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToOneCharLineWithLeadingWhitespace(self):
        set_text(self.view, ':\n a\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)


class Test_next_big_word_start_InNormalMode_FromEmptyLine(ViewTest):
    def testToWordStart(self):
        set_text(self.view, '\nfoo\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToPunctuationStart(self):
        set_text(self.view, '\n (foo)\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToEmptyLine(self):
        set_text(self.view, '\n\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToWhitespaceLine(self):
        set_text(self.view, '\n  \n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToEofWithNewline(self):
        set_text(self.view, '\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToEof(self):
        set_text(self.view, '')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 0)

    def testToOneWordLine(self):
        set_text(self.view, '\nbar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '\n bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToOneCharWord(self):
        set_text(self.view, '\na bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToOneCharLine(self):
        set_text(self.view, '\na\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)

    def testToOneCharLineWithLeadingWhitespace(self):
        set_text(self.view, '\n a\n\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 1)


class Test_next_big_word_start_InNormalMode_FromPunctuation(ViewTest):
    def testToWordStart(self):
        set_text(self.view, '::foo\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 6)

    def testToPunctuationStart(self):
        set_text(self.view, ':: (foo)\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToEmptyLine(self):
        set_text(self.view, '::\n\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToWhitespaceLine(self):
        set_text(self.view, '::\n  \n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToEofWithNewline(self):
        set_text(self.view, '::\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToEof(self):
        set_text(self.view, '::')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 2)

    def testToOneWordLine(self):
        set_text(self.view, '::\nbar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '::\n bar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToOneCharWord(self):
        set_text(self.view, '::a bar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 4)

    def testToOneCharLine(self):
        set_text(self.view, '::\na\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)

    def testToOneCharLineWithLeadingWhitespace(self):
        set_text(self.view, '::\n a\n\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b)
        self.assertEqual(pt, 3)


class Test_next_big_word_start_InInternalNormalMode_FromWhitespace(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, '  \n  ')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 2)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '  \n foo')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 2)


class Test_next_big_word_start_InInternalNormalMode_FromWordStart(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, 'foo\n  ')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 3)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, 'foo\n bar')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 3)


class Test_next_big_word_start_InInternalNormalMode_FromWord(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, '(foo)\n  ')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 5)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '(foo)\n bar')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 5)


class Test_next_big_word_start_InInternalNormalMode_FromPunctuationStart(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, '.\n  ')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 1)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '.\n bar')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 1)


class Test_next_big_word_start_InInternalNormalMode_FromPunctuation(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, '::\n  ')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 2)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '::\n bar')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 2)


class Test_next_big_word_start_InInternalNormalMode_FromEmptyLine(ViewTest):
    def testToWhitespaceLine(self):
        set_text(self.view, '\n  ')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 0)

    def testToOneWordLineWithLeadingWhitespace(self):
        set_text(self.view, '\n bar')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = next_big_word_start(self.view, r.b, internal=True)
        self.assertEqual(pt, 0)


class Test_big_word_starts_InNormalMode(ViewTest):
    def testMove1(self):
        set_text(self.view, '(foo) bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b)
        self.assertEqual(pt, 6)

    def testMove2(self):
        set_text(self.view, '(foo) bar fizz\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, count=2)
        self.assertEqual(pt, 10)

    def testMove10(self):
        set_text(self.view, ''.join(('(foo) bar\n',) * 5))
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, count=9)
        self.assertEqual(pt, 46)


class Test_big_word_starts_InInternalNormalMode_FromEmptyLine(ViewTest):
    # We can assume the stuff tested for normal mode applies to internal normal mode, so we
    # don't bother with that. Instead, we only test the differing behavior when advancing by
    # word starts in internal normal.
    def testMove1ToLineWithLeadingWhiteSpace(self):
        set_text(self.view, '\n (bar)\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True)
        self.assertEqual(pt, 1)

    def testMove2ToLineWithLeadingWhiteSpace(self):
        set_text(self.view, '\n (bar)')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, count=2, internal=True)
        self.assertEqual(pt, 6)

    def testMove1ToWhitespaceLine(self):
        set_text(self.view, '\n  \n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, count=1, internal=True)
        self.assertEqual(pt, 1)

    def testMove2ToOneWordLine(self):
        set_text(self.view, '\n(foo)\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 7)

    def testMove3AndSwallowLastNewlineChar(self):
        set_text(self.view, '\nfoo\n (bar)\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=3)
        self.assertEqual(pt, 12)

    def testMove2ToLineWithLeadingWhiteSpace(self):
        set_text(self.view, '\n(foo)\n  \n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 7)


class Test_big_word_starts_InInternalNormalMode_FromOneWordLine(ViewTest):
    # We can assume the stuff tested for normal mode applies to internal normal mode, so we
    # don't bother with that. Instead, we only test the differing behavior when advancing by
    # word starts in internal normal.
    def testMove2ToEol(self):
        set_text(self.view, 'foo\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=1)
        self.assertEqual(pt, 3)

    def testMove2ToLineWithLeadingWhiteSpaceFromWordStart(self):
        set_text(self.view, '(foo)\n\nbar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 7)

    def testMove2ToEmptyLineFromWord(self):
        set_text(self.view, '(foo)\n\nbar\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 6)

    def testMove2ToOneWordLineFromWordStart(self):
        set_text(self.view, '(foo)\nbar\nccc\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 10)

    def testMove2ToOneWordLineFromWord(self):
        set_text(self.view, '(foo)\nbar\nccc\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 9)

    def testMove2ToWhitespaceline(self):
        set_text(self.view, '(foo)\n  \nccc\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 12)

    def testMove2ToWhitespacelineFollowedByLeadingWhitespaceFromWord(self):
        set_text(self.view, '(foo)\n  \n ccc\n')
        r = self.R((0, 1), (0, 1))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 13)

    def testMove2ToWhitespacelineFollowedByLeadingWhitespaceFromWordStart(self):
        set_text(self.view, '(foo)\n  \n ccc\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 14)


class Test_big_word_starts_InInternalNormalMode_FromLine(ViewTest):
    def testMove2ToEol(self):
        set_text(self.view, 'foo bar\n')
        r = self.R((0, 0), (0, 0))
        add_sel(self.view, r)

        pt = big_word_starts(self.view, r.b, internal=True, count=2)
        self.assertEqual(pt, 7)
