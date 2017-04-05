import unittest

from Vintageous.ex.parser.parser import ParserState


class ParserState_Tests(unittest.TestCase):
    def testCanInstantiate(self):
        parser_state = ParserState("foobar")
        self.assertEqual(parser_state.scanner.state.source, "foobar")
