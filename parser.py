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
    # TODO
    tokens : list[tuple [str, int]] = []
    i = 0
    while i < len(inp):
        while i < len(inp) and inp[i].isspace():
            i += 1
        if i >= len(inp):
            break
        start = i
        while i < len(inp) and not inp[i].isspace():
            i += 1
        tokens.append((inp[start:i], start))

    if not tokens:
        raise ParseError("UnexpectedEOF")
    
    def decode_base94(s: str, start_idx: int) -> int:
        if not s:
            raise ParseError("UnexpectedChar", start_idx, None)
        val = 0
        for j, c in enumerate(s):
            if not (33 <= ord(c) <= 126):
                raise ParseError("UnexpectedChar", start_idx + j, c)
            val = val * 94 + (ord(c) - 33)
        return val
    
    def decode_string(s: str, start_idx: int) -> str:
        res = []
        for j, c in enumerate(s):
            if not (33 <= ord(c) <= 126):
                raise ParseError("UnexpectedChar", start_idx + j, c)
            res.append(CHARS_DECODED[ord(c) - 33])
        return "".join(res)

    def parse_next(t_idx: int) -> tuple[Term, int]:
        if t_idx >= len(tokens):
            raise ParseError("UnexpectedEOF")
        
        tok_str, char_idx = tokens[t_idx]
        ind = tok_str[0]
        body = tok_str[1:]
        
        if ind == 'T':
            if body:
                raise ParseError("UnexpectedChar", char_idx + 1, body[0])
            return TBool(True), t_idx + 1
            
        elif ind == 'F':
            if body:
                raise ParseError("UnexpectedChar", char_idx + 1, body[0])
            return TBool(False), t_idx + 1
            
        elif ind == 'I':
            val = decode_base94(body, char_idx + 1)
            return TInt(val), t_idx + 1
            
        elif ind == 'S':
            val = decode_string(body, char_idx + 1)
            return TString(val), t_idx + 1
            
        elif ind == 'v':
            val = decode_base94(body, char_idx + 1)
            return TVar(val), t_idx + 1
            
        elif ind == 'U':
            if len(body) != 1:
                err_idx = char_idx + 1 if not body else char_idx + 2
                err_ch = None if not body else body[1]
                raise ParseError("UnexpectedChar", err_idx, err_ch)
            op = body[0]
            term, next_t_idx = parse_next(t_idx + 1)
            return TUnOp(op, term), next_t_idx
            
        elif ind == 'B':
            if len(body) != 1:
                err_idx = char_idx + 1 if not body else char_idx + 2
                err_ch = None if not body else body[1]
                raise ParseError("UnexpectedChar", err_idx, err_ch)
            op = body[0]
            left, next_t_idx = parse_next(t_idx + 1)
            right, next_t_idx = parse_next(next_t_idx)
            return TBinOp(left, op, right), next_t_idx
            
        elif ind == '?':
            if body:
                raise ParseError("UnexpectedChar", char_idx + 1, body[0])
            cond, next_t_idx = parse_next(t_idx + 1)
            true_b, next_t_idx = parse_next(next_t_idx)
            false_b, next_t_idx = parse_next(next_t_idx)
            return TIf(cond, true_b, false_b), next_t_idx
            
        elif ind == 'L':
            var_id = decode_base94(body, char_idx + 1)
            term, next_t_idx = parse_next(t_idx + 1)
            return TLam(var_id, term), next_t_idx
            
        else:
            raise ParseError("UnexpectedChar", char_idx, ind)

    # Khởi chạy từ token đầu tiên
    ast, final_t_idx = parse_next(0)
    
    # Kiểm tra xem có token nào bị thừa ở cuối chuỗi không
    if final_t_idx < len(tokens):
        _, unused_char_idx = tokens[final_t_idx]
        raise ParseError("UnusedInput", unused_char_idx)



    return ast