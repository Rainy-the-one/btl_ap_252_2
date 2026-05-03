import unittest

import interpreter
from parser import ParseError, p_term
from ifp_ast import CHARS, TBool, TInt, TString, TUnOp, TBinOp, TIf, TLam, TVar
from interpreter import (
    ArithmeticError_,
    BetaReductionLimit,
    InterpreterError,
    ScopeError,
    TypeError_,
    UnknownBinOp,
    UnknownUnOp,
    interpret,
)
from printer import pp_term

class TestParser(unittest.TestCase):

    def assertParseError(self, inp: str, kind: str, index: int | None = None, ch: str | None = None):
        with self.assertRaises(ParseError) as cm:
            p_term(inp)
        exc = cm.exception
        self.assertEqual(exc.kind, kind)
        if index is not None:
            self.assertEqual(exc.index, index)
        if ch is not None:
            self.assertEqual(exc.ch, ch)

    def test_booleans(self):
        """Test parsing of true and false boolean constants."""
        term_true = p_term("T")
        self.assertIsInstance(term_true, TBool)
        self.assertTrue(term_true.value)

        term_false = p_term("F")
        self.assertIsInstance(term_false, TBool)
        self.assertFalse(term_false.value)

    def test_integers(self):
        """Test parsing of base-94 integer conversion."""
        term = p_term("I/6")  # 14 * 94 + 21 = 1337
        self.assertIsInstance(term, TInt)
        self.assertEqual(term.value, 1337)

    def test_strings(self):
        """Test parsing of strings with alphabet decoding."""
        # 'B' -> 'H', '%' -> 'e', ',' -> 'l', ',' -> 'l', '/' -> 'o'
        term = p_term("SB%,,/")
        self.assertIsInstance(term, TString)
        self.assertEqual(term.value, "Hello")

    def test_unary_and_binary_operators(self):
        """Test parsing of nested operators like unary negation and binary addition."""
        # Equivalent to: -3
        unary_term = p_term("U- I$")
        self.assertIsInstance(unary_term, TUnOp)
        self.assertEqual(unary_term.op, "-")
        self.assertIsInstance(unary_term.term, TInt)
        self.assertEqual(unary_term.term.value, 3)

        # Equivalent to: 2 + 3
        binary_term = p_term("B+ I# I$")
        self.assertIsInstance(binary_term, TBinOp)
        self.assertEqual(binary_term.op, "+")
        self.assertEqual(binary_term.left.value, 2)
        self.assertEqual(binary_term.right.value, 3)

    def test_conditional_expression(self):
        """Test parsing of ternary conditions (? cond then else)."""
        # Equivalent to: if true then "yes" else "no"
        term = p_term("? T S9%3 S./")
        self.assertIsInstance(term, TIf)
        self.assertIsInstance(term.cond, TBool)
        self.assertEqual(term.cond.value, True)
        self.assertIsInstance(term.true_branch, TString)
        self.assertEqual(term.true_branch.value, "yes")
        self.assertIsInstance(term.false_branch, TString)
        self.assertEqual(term.false_branch.value, "no")

    def test_lambda_and_variables(self):
        """Test parsing of lambda definitions and scoped variable tokens."""
        # Equivalent to: \v2 -> v2
        term = p_term("L# v#")
        self.assertIsInstance(term, TLam)
        self.assertEqual(term.var, 2)
        self.assertIsInstance(term.body, TVar)
        self.assertEqual(term.body.value, 2)

    def test_empty_string_token(self):
        """Test parsing of an empty string token and trailing-space delimiter."""
        term = p_term("S")
        self.assertIsInstance(term, TString)
        self.assertEqual(term.value, "")

        term_trailing_space = p_term("S ")
        self.assertIsInstance(term_trailing_space, TString)
        self.assertEqual(term_trailing_space.value, "")

    def test_parse_spec_example(self):
        """Test parsing the spec example ? B> I# I$ S9%3 S./."""
        term = p_term("? B> I# I$ S9%3 S./")
        self.assertIsInstance(term, TIf)
        self.assertIsInstance(term.cond, TBinOp)
        self.assertEqual(term.cond.op, ">")
        self.assertEqual(term.cond.left.value, 2)
        self.assertEqual(term.cond.right.value, 3)
        self.assertIsInstance(term.true_branch, TString)
        self.assertEqual(term.true_branch.value, "yes")
        self.assertIsInstance(term.false_branch, TString)
        self.assertEqual(term.false_branch.value, "no")

    def test_parse_error_unexpected_eof(self):
        """Test parser errors when a token body is missing."""
        self.assertParseError("I", "UnexpectedEOF", 1)
        self.assertParseError("U", "UnexpectedEOF", 1)
        self.assertParseError("B", "UnexpectedEOF", 1)
        self.assertParseError("L", "UnexpectedEOF", 1)
        self.assertParseError("v", "UnexpectedEOF", 1)
        self.assertParseError("? T", "UnexpectedEOF", len("? T"))

    def test_parse_error_unexpected_char(self):
        """Test parser errors for invalid indicator and malformed tokens."""
        self.assertParseError("Z", "UnexpectedChar", 0, "Z")
        self.assertParseError("?x T S9%3 S./", "UnexpectedChar", 1, "x")
        self.assertParseError("U-- I$", "UnexpectedChar", 2, "-")
        self.assertParseError("T  F", "UnexpectedChar", 2, " ")

    def test_parse_error_unused_input(self):
        """Test parser errors for leftover tokens after a complete parse."""
        self.assertParseError("T F", "UnusedInput", 2)
        self.assertParseError("I/6 T", "UnusedInput", 4)

class TestInterpreter(unittest.TestCase):
    def eval_program(self, program: str, check_max: bool = True):
        return interpret(check_max=check_max, term=p_term(program))

    def assertEvalInt(self, program: str, expected_value: int, expected_steps: int = 0):
        result, steps = self.eval_program(program)
        self.assertIsInstance(result, TInt)
        self.assertEqual(result.value, expected_value)
        self.assertEqual(steps, expected_steps)

    def assertEvalBool(self, program: str, expected_value: bool, expected_steps: int = 0):
        result, steps = self.eval_program(program)
        self.assertIsInstance(result, TBool)
        self.assertEqual(result.value, expected_value)
        self.assertEqual(steps, expected_steps)

    def assertEvalString(self, program: str, expected_value: str, expected_steps: int = 0):
        result, steps = self.eval_program(program)
        self.assertIsInstance(result, TString)
        self.assertEqual(result.value, expected_value)
        self.assertEqual(steps, expected_steps)

    def test_literal_values(self):
        self.assertEvalBool("T", True)
        self.assertEvalBool("F", False)
        self.assertEvalInt("I/6", 1337)
        self.assertEvalString("SB%,,/}Q/2,$_", "Hello World!")

    def test_unary_operators(self):
        self.assertEvalInt("U- I$", -3)
        self.assertEvalBool("U! T", False)
        self.assertEvalInt("U# S4%34", 15818151)
        self.assertEvalString("U$ I4%34", "test")

    def test_integer_binary_operators(self):
        self.assertEvalInt("B+ I# I$", 5)
        self.assertEvalInt("B- I$ I#", 1)
        self.assertEvalInt("B* I$ I#", 6)
        self.assertEvalInt("B/ U- I( I#", -3)
        self.assertEvalInt("B% U- I( I#", -1)

    def test_comparison_and_boolean_binary_operators(self):
        self.assertEvalBool("B< I$ I#", False)
        self.assertEvalBool("B> I$ I#", True)
        self.assertEvalBool("B= I$ I#", False)
        self.assertEvalBool("B= T T", True)
        self.assertEvalBool("B= T F", False)
        self.assertEvalBool("B= S4%34 S4%34", True)
        self.assertEvalBool("B| T F", True)
        self.assertEvalBool("B& T F", False)

    def test_string_binary_operators(self):
        self.assertEvalString("B. S4% S34", "test")
        self.assertEvalString("BT I$ S4%34", "tes")
        self.assertEvalString("BD I$ S4%34", "t")

    def test_conditional_evaluates_only_selected_branch(self):
        self.assertEvalString("? B> I# I$ S9%3 S./", "no")
        self.assertEvalInt("? T I# v!", 2)
        self.assertEvalInt("? F v! I$", 3)
        self.assertEvalInt("? T I$ B/ I# I!", 3)
        self.assertEvalString("? F B. SB%,,/ S}Q/2,$_ S./", "no")

    def test_lambda_application_and_step_count(self):
        self.assertEvalString("B$ B$ L# L$ v# B. SB%,,/ S}Q/2,$_ IK", "Hello World!", 2)
        self.assertEvalInt("B$ L# B$ L\" B+ v\" v\" B* I$ I# v8", 12, 2)
        self.assertEvalInt("B$ B$ L# L$ B+ v# v$ I# I$", 5, 2)

    def test_closure_captures_outer_environment(self):
        self.assertEvalInt("B$ B$ L# L$ v# I$ I%", 3, 2)

    def test_string_integer_round_trip_and_empty_string(self):
        self.assertEvalString("U$ U# S4%34", "test")
        self.assertEvalInt("U# S", 0)
        self.assertEvalInt("U# S!", 0)
        self.assertEvalString("U$ I!", "a")

    def test_take_and_drop_out_of_range(self):
        self.assertEvalString("BT I( S4%34", "test")
        self.assertEvalString("BD I( S4%34", "")

    def test_application_argument_is_re_evaluated_when_used_twice(self):
        self.assertEvalInt("B$ L# B+ v# v# B+ I# I$", 10, 1)

    def test_function_application_is_lazy_for_argument(self):
        self.assertEvalInt("B$ L# I$ B/ I# I!", 3, 1)

    def test_builtins_are_strict_except_application(self):
        with self.assertRaises(ArithmeticError_):
            self.eval_program("B+ I# B/ I# I!")
        with self.assertRaises(ArithmeticError_):
            self.eval_program("B| T B/ I# I!")

    def test_steps_count_beta_reductions_only(self):
        self.assertEvalInt("B+ B* I$ I# B- I% I#", 8, 0)
        self.assertEvalInt("B$ L# I$ I%", 3, 1)

    def test_recursive_example_step_count(self):
        program = (
            "B$ B$ L\" B$ L# B$ v\" B$ v# v# L# B$ v\" B$ v# v# L\" L# "
            "? B= v# I! I\" B$ L$ B+ B$ v\" v$ B$ v\" v$ B- v# I\" I%"
        )
        self.assertEvalInt(program, 16, 109)

    def test_interpreter_errors(self):
        with self.assertRaises(ScopeError):
            self.eval_program("v!")
        with self.assertRaises(TypeError_):
            self.eval_program("B+ T I#")
        with self.assertRaises(TypeError_):
            self.eval_program("B= I# S4%34")
        with self.assertRaises(TypeError_):
            self.eval_program("B= L# v# L# v#")
        with self.assertRaises(ArithmeticError_):
            self.eval_program("B/ I# I!")
        with self.assertRaises(ArithmeticError_):
            self.eval_program("B% I# I!")
        with self.assertRaises(ArithmeticError_):
            self.eval_program("U$ U- I#")
        with self.assertRaises(UnknownUnOp):
            self.eval_program("U~ I#")
        with self.assertRaises(UnknownBinOp):
            self.eval_program("B~ I# I$")

    def test_beta_reduction_limit(self):
        old_limit = interpreter.MAX_STEPS
        interpreter.MAX_STEPS = 0
        try:
            with self.assertRaises(BetaReductionLimit):
                self.eval_program("B$ L# v# I!", check_max=True)
        finally:
            interpreter.MAX_STEPS = old_limit


class TestBMWPorted(unittest.TestCase):
    def run_parser(self, program: str) -> str:
        try:
            return pp_term(p_term(program))
        except ParseError as exc:
            return str(exc)

    def run_interpreter(self, program: str):
        try:
            result, steps = interpret(False, p_term(program))
            return pp_term(result), steps
        except ParseError as exc:
            return str(exc), -1
        except BetaReductionLimit:
            return "BetaReductionLimit", -1
        except ScopeError:
            return "ScopeError", -1
        except TypeError_:
            return "TypeError", -1
        except ArithmeticError_:
            return "ArithmeticError", -1
        except UnknownUnOp as exc:
            return f"UnknownUnOp({exc.op})", -1
        except UnknownBinOp as exc:
            return f"UnknownBinOp({exc.op})", -1
        except InterpreterError:
            return "InterpreterError", -1

    def test_001(self):
        self.assertEqual(self.run_parser("T"), pp_term(TBool(True)))

    def test_002(self):
        self.assertEqual(self.run_parser("F"), pp_term(TBool(False)))

    def test_003(self):
        self.assertEqual(self.run_parser("I!"), pp_term(TInt(0)))

    def test_004(self):
        self.assertEqual(self.run_parser("I/6"), pp_term(TInt(1337)))

    def test_005(self):
        self.assertEqual(self.run_parser("SB%,,/}Q/2,$_"), pp_term(TString("Hello World!")))

    def test_006(self):
        self.assertEqual(self.run_parser("U- I$"), pp_term(TUnOp("-", TInt(3))))

    def test_007(self):
        self.assertEqual(self.run_parser("U! T"), pp_term(TUnOp("!", TBool(True))))

    def test_008(self):
        self.assertEqual(self.run_parser("U# S4%34"), pp_term(TUnOp("#", TString("test"))))

    def test_009(self):
        self.assertEqual(self.run_parser("U$ I4%34"), pp_term(TUnOp("$", TInt(15818151))))

    def test_010(self):
        self.assertEqual(self.run_parser("B+ I# I$"), pp_term(TBinOp(TInt(2), "+", TInt(3))))

    def test_011(self):
        self.assertEqual(self.run_parser("B- I$ I#"), pp_term(TBinOp(TInt(3), "-", TInt(2))))

    def test_012(self):
        self.assertEqual(self.run_parser("B* I$ I#"), pp_term(TBinOp(TInt(3), "*", TInt(2))))

    def test_013(self):
        self.assertEqual(
            self.run_parser("B/ U- I( I#"),
            pp_term(TBinOp(TUnOp("-", TInt(CHARS.index("("))), "/", TInt(2))),
        )

    def test_014(self):
        self.assertEqual(
            self.run_parser("B% U- I( I#"),
            pp_term(TBinOp(TUnOp("-", TInt(CHARS.index("("))), "%", TInt(2))),
        )

    def test_015(self):
        self.assertEqual(self.run_parser("B< I$ I#"), pp_term(TBinOp(TInt(3), "<", TInt(2))))

    def test_016(self):
        self.assertEqual(self.run_parser("B> I$ I#"), pp_term(TBinOp(TInt(3), ">", TInt(2))))

    def test_017(self):
        self.assertEqual(self.run_parser("B= I$ I#"), pp_term(TBinOp(TInt(3), "=", TInt(2))))

    def test_018(self):
        self.assertEqual(self.run_parser("B| T F"), pp_term(TBinOp(TBool(True), "|", TBool(False))))

    def test_019(self):
        self.assertEqual(self.run_parser("B& T F"), pp_term(TBinOp(TBool(True), "&", TBool(False))))

    def test_020(self):
        self.assertEqual(self.run_parser("B. S4% S34"), pp_term(TBinOp(TString("te"), ".", TString("st"))))

    def test_021(self):
        self.assertEqual(self.run_parser("BT I$ S4%34"), pp_term(TBinOp(TInt(3), "T", TString("test"))))

    def test_022(self):
        self.assertEqual(self.run_parser("BD I$ S4%34"), pp_term(TBinOp(TInt(3), "D", TString("test"))))

    def test_023(self):
        self.assertEqual(
            self.run_parser("? B> I# I$ S9%3 S./"),
            pp_term(TIf(TBinOp(TInt(2), ">", TInt(3)), TString("yes"), TString("no"))),
        )

    def test_024(self):
        self.assertEqual(
            self.run_parser("B$ B$ L# L$ v# B. SB%,,/ S}Q/2,$_ IK"),
            pp_term(
                TBinOp(
                    TBinOp(TLam(2, TLam(3, TVar(2))), "$", TBinOp(TString("Hello"), ".", TString(" World!"))),
                    "$",
                    TInt(42),
                )
            ),
        )

    def test_025(self):
        self.assertEqual(
            self.run_parser("B$ L# B+ v# v# I$"),
            pp_term(TBinOp(TLam(2, TBinOp(TVar(2), "+", TVar(2))), "$", TInt(3))),
        )

    def test_026(self):
        self.assertEqual(self.run_parser("C"), "UnexpectedChar('C', 0)")

    def test_027(self):
        self.assertEqual(self.run_interpreter("B$ L# v# I$"), (pp_term(TInt(3)), 1))

    def test_028(self):
        self.assertEqual(self.run_interpreter("B$ B$ L# L$ B+ v# v$ I# I$"), (pp_term(TInt(5)), 2))

    def test_029(self):
        self.assertEqual(self.run_interpreter("B$ L# B+ v# v# B* I$ I#"), (pp_term(TInt(12)), 1))

    def test_030(self):
        self.assertEqual(self.run_interpreter("B$ L# IK B* I$ I#"), (pp_term(TInt(42)), 1))

    def test_031(self):
        self.assertEqual(self.run_interpreter("B$ L# v# B* I$ I#"), (pp_term(TInt(6)), 1))

    def test_032(self):
        self.assertEqual(self.run_interpreter("? T I# B+ B* I$ I# B* I$ I$"), (pp_term(TInt(2)), 0))
    
    def test_033(self):
        program = 'B$ B$ L" B$ L# B$ v" B$ v# v# L# B$ v" B$ v# v# L" L# ? B= v# I! I" B$ L$ B+ B$ v" v$ B$ v" v$ B- v# I" I%'
        self.assertEqual(self.run_interpreter(program), (pp_term(TInt(16)), 109))

    def test_034(self):
        self.assertEqual(self.run_interpreter("B$ L# v# v#"), ("ScopeError", -1))

    def test_035(self):
        self.assertEqual(self.run_interpreter("B$ L# v# B$ L$ v$ I&"), (pp_term(TInt(5)), 2))

if __name__ == "__main__":
    unittest.main()
