"""HWP 표 계산식 엔진 (Python 포팅).

rhwp (edwardkim/rhwp, MIT License) `src/document_core/table_calc/` 의
토크나이저/파서/평가기 3단계 구조를 Python으로 이식했다.

지원:
    - 셀 참조: A1, B3, ?1 (현재 열), A? (현재 행)
    - 범위: A1:B5
    - 방향 지정자: left, right, above, below
    - 사칙 연산: +, -, *, / (우선순위·괄호 지원)
    - 단항 음수: -A1
    - 집계 함수: SUM, AVG/AVERAGE, PRODUCT, MIN, MAX, COUNT
    - 단항 수학: ABS, SQRT, EXP, LOG, LOG10, SIN, COS, TAN, ASIN, ACOS, ATAN,
                RADIAN, SIGN, INT, CEILING, FLOOR, ROUND, TRUNC
    - 이항: MOD(a, b)
    - 분기: IF(cond, true, false)

사용 예::

    from table_calc import evaluate_formula, TableContext

    def get_cell(col, row):  # 0-based 인덱스
        table = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        return table[row][col] if 0 <= row < 3 and 0 <= col < 3 else None

    ctx = TableContext(row_count=3, col_count=3, current_row=2, current_col=2)
    result = evaluate_formula("=SUM(A1:C3)", ctx, get_cell)  # 45.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, List, Optional, Union


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


# Token 종류 (간단한 tagged-union — (tag, payload))
# tag: "NUM" | "CELL" | "FN" | "DIR" | "+" | "-" | "*" | "/" | "(" | ")" | "," | ":"
Token = tuple  # (tag, *payload)


def tokenize(formula: str) -> List[Token]:
    """계산식 문자열을 토큰 리스트로 변환한다.

    선행 ``=`` 또는 ``@`` 는 제거한다. 공백은 무시한다.
    알 수 없는 문자는 건너뛴다(rhwp 원본 동작과 동일).
    """
    s = formula.strip()
    if s.startswith("=") or s.startswith("@"):
        s = s[1:]

    tokens: List[Token] = []
    i, n = 0, len(s)

    while i < n:
        ch = s[i]

        if ch.isspace():
            i += 1
            continue

        # 숫자 (정수 또는 소수)
        if ch.isdigit() or (ch == "." and i + 1 < n and s[i + 1].isdigit()):
            start = i
            while i < n and (s[i].isdigit() or s[i] == "."):
                i += 1
            try:
                tokens.append(("NUM", float(s[start:i])))
            except ValueError:
                pass
            continue

        # 단어: 셀 참조, 함수 이름, 방향 지정자
        if ch.isalpha() or ch == "?":
            start = i
            while i < n and (s[i].isalnum() or s[i] == "?" or s[i] == "_"):
                i += 1
            word = s[start:i]
            upper = word.upper()

            if upper in ("LEFT", "RIGHT", "ABOVE", "BELOW"):
                tokens.append(("DIR", upper))
                continue

            # 셀 참조: 단일 문자 열(A-Z 또는 ?) + 숫자 행 또는 ?
            if len(upper) >= 2:
                first = upper[0]
                rest = upper[1:]
                is_col_char = first.isalpha() or first == "?"
                is_row_digits = rest.isdigit()
                is_row_wild = rest == "?"
                if is_col_char and (is_row_digits or is_row_wild):
                    row = 0 if is_row_wild else int(rest)
                    tokens.append(("CELL", first, row))
                    continue

            tokens.append(("FN", upper))
            continue

        # 연산자/구분자
        if ch in "+-*/(),:":
            tokens.append((ch,))
            i += 1
            continue

        # 알 수 없는 문자 무시
        i += 1

    return tokens


# ---------------------------------------------------------------------------
# Parser (재귀 하강)
# ---------------------------------------------------------------------------


@dataclass
class Number:
    value: float


@dataclass
class CellRef:
    col: str  # 'A'..'Z' 또는 '?'
    row: int  # 1.. 또는 0=와일드카드


@dataclass
class Range:
    start: "CellRef"
    end: "CellRef"


@dataclass
class Direction:
    kind: str  # "LEFT" | "RIGHT" | "ABOVE" | "BELOW"


@dataclass
class Negate:
    inner: "FormulaNode"


@dataclass
class BinOp:
    op: str  # "+" | "-" | "*" | "/"
    left: "FormulaNode"
    right: "FormulaNode"


@dataclass
class FuncCall:
    name: str
    args: List["FormulaNode"]


FormulaNode = Union[Number, CellRef, Range, Direction, Negate, BinOp, FuncCall]


class _Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Optional[Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def advance(self) -> Optional[Token]:
        if self.pos < len(self.tokens):
            tok = self.tokens[self.pos]
            self.pos += 1
            return tok
        return None

    def expect(self, tag: str) -> bool:
        tok = self.peek()
        if tok is not None and tok[0] == tag:
            self.advance()
            return True
        return False

    def parse_expr(self) -> FormulaNode:
        left = self.parse_term()
        while True:
            tok = self.peek()
            if tok is None:
                break
            if tok[0] == "+":
                self.advance()
                left = BinOp("+", left, self.parse_term())
            elif tok[0] == "-":
                self.advance()
                left = BinOp("-", left, self.parse_term())
            else:
                break
        return left

    def parse_term(self) -> FormulaNode:
        left = self.parse_factor()
        while True:
            tok = self.peek()
            if tok is None:
                break
            if tok[0] == "*":
                self.advance()
                left = BinOp("*", left, self.parse_factor())
            elif tok[0] == "/":
                self.advance()
                left = BinOp("/", left, self.parse_factor())
            else:
                break
        return left

    def parse_factor(self) -> FormulaNode:
        tok = self.peek()
        if tok is None:
            return Number(0.0)

        tag = tok[0]

        if tag == "NUM":
            self.advance()
            return Number(tok[1])

        if tag == "CELL":
            self.advance()
            cell = CellRef(col=tok[1], row=tok[2])
            # 범위 참조 확인
            nxt = self.peek()
            if nxt is not None and nxt[0] == ":":
                self.advance()
                tok2 = self.peek()
                if tok2 is not None and tok2[0] == "CELL":
                    self.advance()
                    return Range(start=cell, end=CellRef(col=tok2[1], row=tok2[2]))
                # ':' 뒤에 셀 참조가 없으면 단일 셀
            return cell

        if tag == "FN":
            self.advance()
            self.expect("(")
            args = self.parse_arg_list()
            self.expect(")")
            return FuncCall(name=tok[1], args=args)

        if tag == "DIR":
            self.advance()
            return Direction(kind=tok[1])

        if tag == "(":
            self.advance()
            inner = self.parse_expr()
            self.expect(")")
            return inner

        if tag == "-":
            self.advance()
            return Negate(inner=self.parse_factor())

        # 파싱 실패: 0으로 대체 (rhwp 원본 동작)
        self.advance()
        return Number(0.0)

    def parse_arg_list(self) -> List[FormulaNode]:
        args: List[FormulaNode] = []
        if self.peek() is not None and self.peek()[0] == ")":
            return args
        args.append(self.parse_expr())
        while self.peek() is not None and self.peek()[0] == ",":
            self.advance()
            args.append(self.parse_expr())
        return args


def parse_formula(formula: str) -> Optional[FormulaNode]:
    tokens = tokenize(formula)
    if not tokens:
        return None
    parser = _Parser(tokens)
    return parser.parse_expr()


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


@dataclass
class TableContext:
    row_count: int
    col_count: int
    current_row: int  # 0-based
    current_col: int  # 0-based


CellValueFn = Callable[[int, int], Optional[float]]  # (col, row) → value


class FormulaError(ValueError):
    """수식 평가 실패."""


def _resolve_cell_ref(col: str, row: int, ctx: TableContext) -> tuple[int, int]:
    if col == "?":
        c = ctx.current_col
    else:
        c = ord(col.upper()) - ord("A")
        if c < 0:
            raise FormulaError(f"잘못된 열: {col}")
    if row == 0:
        r = ctx.current_row
    else:
        r = row - 1
        if r < 0:
            raise FormulaError("행은 1부터 시작")
    return c, r


def _collect_cells(arg: FormulaNode, ctx: TableContext) -> List[tuple[int, int]]:
    if isinstance(arg, Range):
        sc, sr = _resolve_cell_ref(arg.start.col, arg.start.row, ctx)
        ec, er = _resolve_cell_ref(arg.end.col, arg.end.row, ctx)
        cells = []
        for r in range(min(sr, er), max(sr, er) + 1):
            for c in range(min(sc, ec), max(sc, ec) + 1):
                cells.append((c, r))
        return cells
    if isinstance(arg, Direction):
        cells = []
        if arg.kind == "LEFT":
            cells = [(c, ctx.current_row) for c in range(0, ctx.current_col)]
        elif arg.kind == "RIGHT":
            cells = [(c, ctx.current_row) for c in range(ctx.current_col + 1, ctx.col_count)]
        elif arg.kind == "ABOVE":
            cells = [(ctx.current_col, r) for r in range(0, ctx.current_row)]
        elif arg.kind == "BELOW":
            cells = [(ctx.current_col, r) for r in range(ctx.current_row + 1, ctx.row_count)]
        return cells
    if isinstance(arg, CellRef):
        return [_resolve_cell_ref(arg.col, arg.row, ctx)]
    raise FormulaError("함수 인수가 범위/셀/방향이 아님")


def _collect_values(
    args: List[FormulaNode], ctx: TableContext, get_cell: CellValueFn
) -> List[float]:
    values: List[float] = []
    for arg in args:
        if isinstance(arg, (Range, Direction)):
            for c, r in _collect_cells(arg, ctx):
                v = get_cell(c, r)
                if v is not None:
                    values.append(float(v))
        elif isinstance(arg, CellRef):
            c, r = _resolve_cell_ref(arg.col, arg.row, ctx)
            v = get_cell(c, r)
            if v is not None:
                values.append(float(v))
        else:
            values.append(_eval_node(arg, ctx, get_cell))
    return values


_UNARY_FNS = {
    "ABS": abs,
    "SQRT": math.sqrt,
    "EXP": math.exp,
    "LOG": math.log,  # 자연로그 (rhwp 원본과 동일)
    "LOG10": math.log10,
    "SIN": math.sin,
    "COS": math.cos,
    "TAN": math.tan,
    "ASIN": math.asin,
    "ACOS": math.acos,
    "ATAN": math.atan,
    "RADIAN": lambda d: d * math.pi / 180.0,
    "SIGN": lambda v: 1.0 if v > 0 else (-1.0 if v < 0 else 0.0),
    "INT": math.trunc,
    "CEILING": math.ceil,
    "FLOOR": math.floor,
    "ROUND": round,
    "TRUNC": math.trunc,
}


def _eval_function(
    name: str, args: List[FormulaNode], ctx: TableContext, get_cell: CellValueFn
) -> float:
    if name in ("SUM",):
        return sum(_collect_values(args, ctx, get_cell))
    if name in ("AVG", "AVERAGE"):
        vals = _collect_values(args, ctx, get_cell)
        return sum(vals) / len(vals) if vals else 0.0
    if name == "PRODUCT":
        vals = _collect_values(args, ctx, get_cell)
        result = 1.0
        for v in vals:
            result *= v
        return result
    if name == "MIN":
        vals = _collect_values(args, ctx, get_cell)
        return min(vals) if vals else math.inf
    if name == "MAX":
        vals = _collect_values(args, ctx, get_cell)
        return max(vals) if vals else -math.inf
    if name == "COUNT":
        return float(len(_collect_values(args, ctx, get_cell)))
    if name in _UNARY_FNS:
        if not args:
            raise FormulaError(f"{name}: 인수 필요")
        v = _eval_node(args[0], ctx, get_cell)
        return float(_UNARY_FNS[name](v))
    if name == "MOD":
        if len(args) < 2:
            raise FormulaError("MOD는 2개 인수 필요")
        a = _eval_node(args[0], ctx, get_cell)
        b = _eval_node(args[1], ctx, get_cell)
        if b == 0.0:
            raise FormulaError("0으로 나눌 수 없음")
        return a % b
    if name == "IF":
        if len(args) < 3:
            raise FormulaError("IF는 3개 인수 필요 (조건, 참, 거짓)")
        cond = _eval_node(args[0], ctx, get_cell)
        return _eval_node(args[1], ctx, get_cell) if cond != 0.0 else _eval_node(args[2], ctx, get_cell)

    raise FormulaError(f"지원하지 않는 함수: {name}")


def _eval_node(node: FormulaNode, ctx: TableContext, get_cell: CellValueFn) -> float:
    if isinstance(node, Number):
        return node.value
    if isinstance(node, CellRef):
        c, r = _resolve_cell_ref(node.col, node.row, ctx)
        v = get_cell(c, r)
        return float(v) if v is not None else 0.0
    if isinstance(node, Negate):
        return -_eval_node(node.inner, ctx, get_cell)
    if isinstance(node, BinOp):
        lv = _eval_node(node.left, ctx, get_cell)
        rv = _eval_node(node.right, ctx, get_cell)
        if node.op == "+":
            return lv + rv
        if node.op == "-":
            return lv - rv
        if node.op == "*":
            return lv * rv
        if node.op == "/":
            if rv == 0.0:
                raise FormulaError("0으로 나눌 수 없음")
            return lv / rv
        raise FormulaError(f"알 수 없는 연산자: {node.op}")
    if isinstance(node, Range):
        raise FormulaError("범위 참조는 함수 인수로만 사용 가능")
    if isinstance(node, Direction):
        raise FormulaError("방향 지정자는 함수 인수로만 사용 가능")
    if isinstance(node, FuncCall):
        return _eval_function(node.name, node.args, ctx, get_cell)
    raise FormulaError(f"알 수 없는 노드: {node!r}")


def evaluate_formula(formula: str, ctx: TableContext, get_cell: CellValueFn) -> float:
    """계산식 문자열을 평가하여 결과를 반환한다.

    Args:
        formula: 계산식 문자열 (예: ``=SUM(A1:A5)+B3*2``). 선행 ``=`` / ``@`` 생략 가능.
        ctx: 표 정보 (행/열 수, 현재 셀).
        get_cell: ``(col, row)`` → ``float | None`` 조회 함수. col/row 모두 0-based.

    Raises:
        FormulaError: 파싱 실패, 지원하지 않는 함수, 0으로 나눔 등.
    """
    ast = parse_formula(formula)
    if ast is None:
        raise FormulaError("수식 파싱 실패 (빈 입력)")
    return _eval_node(ast, ctx, get_cell)


# ---------------------------------------------------------------------------
# 단위 테스트 (의존성 0 — `if __name__ == "__main__":` 블록)
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    # 5x5 샘플 표: 값 = (row+1)*10 + (col+1)
    def sample_cell(col: int, row: int) -> Optional[float]:
        if 0 <= col < 5 and 0 <= row < 5:
            return (row + 1) * 10.0 + (col + 1)
        return None

    ctx = TableContext(row_count=5, col_count=5, current_row=4, current_col=0)
    passed = 0
    failed = 0

    def check(name: str, expected: float, actual: float, tol: float = 1e-9) -> None:
        global passed, failed
        ok = abs(expected - actual) < tol
        if ok:
            passed += 1
            print(f"  OK   {name}: {actual}")
        else:
            failed += 1
            print(f"  FAIL {name}: expected {expected}, got {actual}")

    def check_err(name: str, formula: str) -> None:
        global passed, failed
        try:
            evaluate_formula(formula, ctx, sample_cell)
            failed += 1
            print(f"  FAIL {name}: expected error but got result")
        except FormulaError:
            passed += 1
            print(f"  OK   {name}: FormulaError raised")

    print("=== table_calc 단위 테스트 ===")

    # 리터럴/산술
    check("literal 42", 42.0, evaluate_formula("=42", ctx, sample_cell))
    check("1+2", 3.0, evaluate_formula("=1+2", ctx, sample_cell))
    check("precedence 1+2*3", 7.0, evaluate_formula("=1+2*3", ctx, sample_cell))
    check("parens (1+2)*3", 9.0, evaluate_formula("=(1+2)*3", ctx, sample_cell))
    check("negate -5", -5.0, evaluate_formula("=-5", ctx, sample_cell))
    check("no prefix", 10.0, evaluate_formula("10", ctx, sample_cell))
    check("@ prefix", 5.0, evaluate_formula("@5", ctx, sample_cell))
    check("decimal", 3.14, evaluate_formula("=3.14", ctx, sample_cell))

    # 셀 참조
    check("A1", 11.0, evaluate_formula("=A1", ctx, sample_cell))
    check("B3", 32.0, evaluate_formula("=B3", ctx, sample_cell))
    check("lowercase a1", 11.0, evaluate_formula("=a1", ctx, sample_cell))
    check("A1+B2*2", 11 + 22 * 2, evaluate_formula("=A1+B2*2", ctx, sample_cell))

    # 와일드카드 (현재 셀 = row=4, col=0)
    check("?5 (col 현재)", 51.0, evaluate_formula("=?5", ctx, sample_cell))
    check("A? (row 현재)", 51.0, evaluate_formula("=A?", ctx, sample_cell))

    # 단항 음수
    check("-A1", -11.0, evaluate_formula("=-A1", ctx, sample_cell))

    # 집계 함수
    check("SUM(A1:A3)", 11 + 21 + 31, evaluate_formula("=SUM(A1:A3)", ctx, sample_cell))
    check("AVG(A1:A3)", (11 + 21 + 31) / 3, evaluate_formula("=AVG(A1:A3)", ctx, sample_cell))
    check(
        "AVERAGE(A1:A3)", (11 + 21 + 31) / 3, evaluate_formula("=AVERAGE(A1:A3)", ctx, sample_cell)
    )
    check("PRODUCT(B1,C3)", 12 * 33, evaluate_formula("=PRODUCT(B1,C3)", ctx, sample_cell))
    check("MIN(A1:C1)", 11.0, evaluate_formula("=MIN(A1:C1)", ctx, sample_cell))
    check("MAX(A1:C1)", 13.0, evaluate_formula("=MAX(A1:C1)", ctx, sample_cell))
    check("COUNT(A1:C1)", 3.0, evaluate_formula("=COUNT(A1:C1)", ctx, sample_cell))

    # 방향 지정자 (현재 셀 (col=0, row=4))
    check(
        "SUM(above)", 11 + 21 + 31 + 41, evaluate_formula("=SUM(above)", ctx, sample_cell)
    )  # A1..A4
    # current row=4, col=0 — left는 0열 미만 없음
    check("SUM(left)", 0.0, evaluate_formula("=SUM(left)", ctx, sample_cell))

    # 중첩
    check(
        "SUM(A1:A3, AVG(B1,B2))",
        63 + (12 + 22) / 2,
        evaluate_formula("=SUM(A1:A3,AVG(B1,B2))", ctx, sample_cell),
    )

    # 수학 함수
    check("ABS(-25)", 25.0, evaluate_formula("=ABS(-25)", ctx, sample_cell))
    check("SQRT(16)", 4.0, evaluate_formula("=SQRT(16)", ctx, sample_cell))
    check("ROUND(3.7)", 4.0, evaluate_formula("=ROUND(3.7)", ctx, sample_cell))
    check("CEILING(3.1)", 4.0, evaluate_formula("=CEILING(3.1)", ctx, sample_cell))
    check("FLOOR(3.9)", 3.0, evaluate_formula("=FLOOR(3.9)", ctx, sample_cell))
    check("INT(3.7)", 3.0, evaluate_formula("=INT(3.7)", ctx, sample_cell))
    check("SIGN(-5)", -1.0, evaluate_formula("=SIGN(-5)", ctx, sample_cell))

    # MOD / IF
    check("MOD(10,3)", 1.0, evaluate_formula("=MOD(10,3)", ctx, sample_cell))
    check("IF(1,10,20)", 10.0, evaluate_formula("=IF(1,10,20)", ctx, sample_cell))
    check("IF(0,10,20)", 20.0, evaluate_formula("=IF(0,10,20)", ctx, sample_cell))

    # rhwp 원본 복합 테스트
    # a1+(b3-3)*2+sum(a1:b5,avg(c3,e5-3))
    # a1=11, b3=32, sum(a1:b5)= 11+12 + 21+22 + 31+32 + 41+42 + 51+52 = 315
    # avg(c3, e5-3) = avg(33, 52) = 42.5
    # = 11 + 58 + 315 + 42.5 = 426.5
    check(
        "복합 수식 (rhwp 원본)",
        426.5,
        evaluate_formula("=a1+(b3-3)*2+sum(a1:b5,avg(c3,e5-3))", ctx, sample_cell),
    )

    # 에러 케이스
    check_err("0으로 나눔", "=1/0")
    check_err("지원하지 않는 함수", "=FOO(1,2)")

    print(f"\n=== 결과: {passed} passed, {failed} failed ===")
    import sys

    sys.exit(0 if failed == 0 else 1)
