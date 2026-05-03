from __future__ import annotations

from dataclasses import dataclass

from ifp_ast import (
    CHARS,
    CHARS_DECODED,
    TBinOp,
    TBool,
    TIf,
    TInt,
    TLam,
    TString,
    TUnOp,
    TVar,
    Term,
)


@dataclass(frozen=True)
class ParseError(Exception):
    kind: str
    index: int | None = None
    ch: str | None = None

    def __str__(self) -> str:
        if self.kind == "UnexpectedChar":
            return f"UnexpectedChar({self.ch!r}, {self.index})"
        if self.kind == "UnusedInput":
            return f"UnusedInput({self.index})"
        return "UnexpectedEOF"


def p_term(inp: str) -> Term:
    def parse_next(i: int) -> tuple[Term, int]:
        if i >= len(inp):
            raise ParseError("UnexpectedEOF", i)
        
        # Tìm khoảng trắng tiếp theo
        end = inp.find(" ", i)
        if end == -1:
            end = len(inp)
            next_i = end
        else:
            next_i = end + 1
            
        tok_str = inp[i:end]
        if not tok_str:
            raise ParseError("UnexpectedChar", i, " ")
            
        ind = tok_str[0]
        body = tok_str[1:]
        
        def check_body_empty():
            if body: raise ParseError("UnexpectedChar", i + 1, body[0])
            
        def check_body_not_empty():
            if not body: raise ParseError("UnexpectedEOF", i + 1)
            
        if ind == 'T':
            check_body_empty()
            return TBool(True), next_i
        elif ind == 'F':
            check_body_empty()
            return TBool(False), next_i
        elif ind == 'I':
            check_body_not_empty()
            val = 0
            for j, c in enumerate(body):
                if not (33 <= ord(c) <= 126):
                    raise ParseError("UnexpectedChar", i + 1 + j, c)
                val = val * 94 + (ord(c) - 33)
            return TInt(val), next_i
        elif ind == 'S':
            res = []
            for j, c in enumerate(body):
                if not (33 <= ord(c) <= 126):
                    raise ParseError("UnexpectedChar", i + 1 + j, c)
                res.append(CHARS_DECODED[ord(c) - 33])
            return TString("".join(res)), next_i
        elif ind == 'v':
            check_body_not_empty()
            val = 0
            for j, c in enumerate(body):
                if not (33 <= ord(c) <= 126):
                    raise ParseError("UnexpectedChar", i + 1 + j, c)
                val = val * 94 + (ord(c) - 33)
            return TVar(val), next_i
        elif ind == 'U':
            check_body_not_empty()
            if len(body) != 1:
                raise ParseError("UnexpectedChar", i + 2, body[1])
            op = body[0]
            term, next_next_i = parse_next(next_i)
            return TUnOp(op, term), next_next_i
        elif ind == 'B':
            check_body_not_empty()
            if len(body) != 1:
                raise ParseError("UnexpectedChar", i + 2, body[1])
            op = body[0]
            left, next_next_i = parse_next(next_i)
            right, final_next = parse_next(next_next_i)
            return TBinOp(left, op, right), final_next
        elif ind == '?':
            check_body_empty()
            cond, next_next_i = parse_next(next_i)
            true_b, next_next_next_i = parse_next(next_next_i)
            false_b, final_next = parse_next(next_next_next_i)
            return TIf(cond, true_b, false_b), final_next
        elif ind == 'L':
            check_body_not_empty()
            val = 0
            for j, c in enumerate(body):
                if not (33 <= ord(c) <= 126):
                    raise ParseError("UnexpectedChar", i + 1 + j, c)
                val = val * 94 + (ord(c) - 33)
            term, next_next_i = parse_next(next_i)
            return TLam(val, term), next_next_i
        else:
            raise ParseError("UnexpectedChar", i, ind)

    ast, final_i = parse_next(0)
    
    # Kiểm tra xem có token/chữ cái nào thừa ở cuối không
    if final_i < len(inp):
        end = inp.find(" ", final_i)
        if end == -1: end = len(inp)
        tok_str = inp[final_i:end]
        if not tok_str:
            raise ParseError("UnexpectedChar", final_i, " ")
        raise ParseError("UnusedInput", final_i)

    return ast