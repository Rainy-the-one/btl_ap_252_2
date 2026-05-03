from __future__ import annotations

from dataclasses import dataclass

from ifp_ast import TBinOp, TBool, TIf, TInt, TLam, TString, TUnOp, TVar, Term
from printer import encode_string, to_base94


MAX_STEPS = 10_000_000


class InterpreterError(Exception):
    pass


class BetaReductionLimit(InterpreterError):
    pass


class ScopeError(InterpreterError):
    pass


class TypeError_(InterpreterError):
    pass


class ArithmeticError_(InterpreterError):
    pass


class UnknownUnOp(InterpreterError):
    def __init__(self, op: str):
        super().__init__(f"Unknown unary operator: {op}")
        self.op = op


class UnknownBinOp(InterpreterError):
    def __init__(self, op: str):
        super().__init__(f"Unknown binary operator: {op}")
        self.op = op


@dataclass
class VInt:
    value: int


@dataclass
class VBool:
    value: bool


@dataclass
class VString:
    value: str


@dataclass
class VClosure:
    var: int
    body: Term
    env: dict[int, "Thunk"]


Value = VInt | VBool | VString | VClosure


@dataclass
class Thunk:
    kind: str
    value: Value | None = None
    steps: int = 0
    term: Term | None = None
    env: dict[int, "Thunk"] | None = None


def _to_term(v: Value) -> Term:
    if isinstance(v, VInt):
        return TInt(v.value)
    if isinstance(v, VBool):
        return TBool(v.value)
    if isinstance(v, VString):
        return TString(v.value)
    if isinstance(v, VClosure):
        return TLam(v.var, v.body)
    raise TypeError(f"Unknown value type: {type(v).__name__}")


def interpret(check_max: bool, term: Term) -> tuple[Term, int]:
    steps = 0
    
    def eval_term(t: Term, env: dict[int, Thunk]) -> Value:
        # TODO
        nonlocal steps
        if check_max and steps > MAX_STEPS:
            raise BetaReductionLimit("Exceeded maximum beta reduction steps")
        
        if isinstance(t, TInt):
            return VInt(t.value)
        
        if isinstance(t, TBool):
            return VBool(t.value)
        
        if isinstance(t, TString):
            return VString(t.value)
        
        if isinstance(t, TIf):
            cond_val = eval_term(t.cond, env)
            
            if not isinstance(cond_val, VBool):
                raise TypeError_("Condition of '?' must evaluate to a boolean")
                
            if cond_val.value is True:
                return eval_term(t.true_branch, env)
            else:
                return eval_term(t.false_branch, env)

        if isinstance(t, TLam):
            return VClosure(t.var, t.body, env.copy())

        if isinstance(t, TVar):
            if t.value not in env:
                raise ScopeError(f"Undefined variable: {t.value}")
            
            thunk = env[t.value]
            
            if thunk.kind == "value":
                steps += thunk.steps
                return thunk.value
                
            if thunk.kind == "lazy":
                steps_before = steps

                # this shit works like lazy updating of segment tree
                val = eval_term(thunk.term, thunk.env)
                
                # save cache
                thunk.value = val
                thunk.kind = "value"
                thunk.steps = steps - steps_before
                
                return val
            
        if isinstance(t, TBinOp):
            if t.op == '$':
                func = eval_term(t.left, env)
                if not isinstance(func, VClosure):
                    raise TypeError_("Left side of B$ must evaluate to a lambda")
                
                arg_thunk = Thunk(kind="lazy", term=t.right, env=env.copy())
                
                new_env = func.env.copy()
                new_env[func.var] = arg_thunk
                
                steps += 1
                
                return eval_term(func.body, new_env)
            
            left_val = eval_term(t.left, env)
            right_val = eval_term(t.right, env)

            # Math operators
            if t.op in ['+', '-', '*', '/', '%', '<', '>']:
                if not (isinstance(left_val, VInt) and isinstance(right_val, VInt)):
                    raise TypeError_(f"Operator B{t.op} requires integers")
                
                lv, rv = left_val.value, right_val.value
                
                # Calculated operators
                if t.op == '+': 
                    return VInt(lv + rv)
                if t.op == '-': 
                    return VInt(lv - rv)
                if t.op == '*': 
                    return VInt(lv * rv)
                if t.op == '/':
                    if rv == 0: raise ArithmeticError_("Division by zero")
                    return VInt(int(lv / rv)) # truncate toward 0
                if t.op == '%':
                    if rv == 0: raise ArithmeticError_("Modulo by zero")
                    res = abs(lv) % abs(rv)
                    if lv < 0: res = -res
                    return VInt(res)
                
                # Compared operators
                if t.op == '<': 
                    return VBool(lv < rv)
                if t.op == '>': 
                    return VBool(lv > rv)
            if t.op == '=':
                if type(left_val) != type(right_val):
                    raise TypeError_("Type mismatch in B=")
                if not isinstance(left_val, (VInt, VBool, VString)):
                    raise TypeError_("B= requires comparable types")
                return VBool(left_val.value == right_val.value)
            
            # Logic operators
            if t.op in ['|', '&']:
                if not (isinstance(left_val, VBool) and isinstance(right_val, VBool)):
                    raise TypeError_(f"Operator B{t.op} requires booleans")
                if t.op == '|': 
                    return VBool(left_val.value or right_val.value)
                if t.op == '&': 
                    return VBool(left_val.value and right_val.value)

            if t.op == '.':
                if not (isinstance(left_val, VString) and isinstance(right_val, VString)):
                    raise TypeError_("Operator B. requires strings")
                return VString(left_val.value + right_val.value)

            if t.op in ['T', 'D']:
                if not (isinstance(left_val, VInt) and isinstance(right_val, VString)):
                    raise TypeError_(f"Operator B{t.op} requires int and string")
                lv, rv = left_val.value, right_val.value
                if lv < 0: 
                    raise ValueError("Index must be non-negative")
                if t.op == 'T': 
                    return VString(rv[:lv])
                if t.op == 'D': 
                    return VString(rv[lv:])

            raise UnknownBinOp(t.op)
        
        if isinstance(t, TUnOp):
            val = eval_term(t.term, env)
            
            if t.op == '-':
                if not isinstance(val, VInt): raise TypeError_("U- requires int")
                return VInt(-val.value)
                
            if t.op == '!':
                if not isinstance(val, VBool): raise TypeError_("U! requires bool")
                return VBool(not val.value)
                
            if t.op == '#':
                if not isinstance(val, VString): raise TypeError_("U# requires string")
                s = val.value
                res = 0
                for c in s:
                    from ifp_ast import CHARS_DECODED
                    idx = CHARS_DECODED.find(c)
                    if idx == -1: raise InterpreterError(f"Invalid char in string to int: {c}")
                    res = res * 94 + idx
                return VInt(res)
                
            if t.op == '$':
                if not isinstance(val, VInt): 
                    raise TypeError_("U$ requires int")
                v = val.value
                if v < 0:
                    raise ArithmeticError_("U$ requires non-negative int")
                
                from ifp_ast import CHARS_DECODED
                if v == 0: 
                    return VString(CHARS_DECODED[0])
                
                res = []
                while v > 0:
                    v, rem = divmod(v, 94)
                    res.append(CHARS_DECODED[rem])
                res.reverse()
                return VString("".join(res))
                
            raise UnknownUnOp(t.op)

        raise TypeError(f"Unknown term type: {type(t).__name__}")

    result = eval_term(term, {})
    return _to_term(result), steps
