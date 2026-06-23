# Exact Dyadic Route-Shell Dynamic Programming Specification

## 1. Scope and authority

This document freezes the mathematical contract and test vectors for a future
exact dyadic route-shell backend. It does not implement that backend and does
not change any submitted value.

The specification removes ambiguity from:

- floating-point rounding and aggregation order;
- floating-point zero tests;
- incomplete local branch enumeration;
- top-K route enumeration being mistaken for an exact Cartesian product;
- `certified_no_truncation` being mistaken for exact numeric certification.

This specification establishes way-2 mathematical and numeric requirements
only. It does not establish that an exact way-2 result may replace a value
actually produced by official way 1. That provenance question remains
`UNRESOLVED-VT-PROVENANCE` in `docs/OFFICIAL_SPEC_INTERPRETATION.md`.

## 2. S-box and Walsh orientation

The 4-bit S-box is

```text
S = [C,6,9,0,1,A,2,B,3,8,5,D,4,E,7,F].
```

For input mask \(a\) and output mask \(b\), define the Walsh numerator

\[
W[b,a]
=
\sum_{x=0}^{15}
(-1)^{\langle a,x\rangle\oplus\langle b,S(x)\rangle}.
\]

The input mask is the column index and the output mask is the row index. The
frozen machine-readable table is `tests/data/walsh_table.csv`.

The following independent program regenerates the table:

```python
from collections import Counter

SBOX = [
    0xC, 0x6, 0x9, 0x0,
    0x1, 0xA, 0x2, 0xB,
    0x3, 0x8, 0x5, 0xD,
    0x4, 0xE, 0x7, 0xF,
]

def parity4(x: int) -> int:
    return (x & 0xF).bit_count() & 1

W = []
for b in range(16):
    row = []
    for a in range(16):
        total = 0
        for x in range(16):
            bit = parity4(a & x) ^ parity4(b & SBOX[x])
            total += -1 if bit else 1
        row.append(total)
    W.append(row)

assert Counter(v for row in W for v in row) == {
    0: 123,
    -4: 52,
    4: 44,
    8: 19,
    -8: 17,
    16: 1,
}
assert all(v % 4 == 0 for row in W for v in row)
```

## 3. Frozen 16 by 16 Walsh table

```text
b\a    0   1   2   3   4   5   6   7   8   9   A   B   C   D   E   F
 0    16   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0
 1     0  -4   8  -4   0  -4   0   4   4   0  -4   0   4   0   4   8
 2     0   4   0   4   8  -4  -8  -4   0   4   0   4   0   4   0   4
 3     0   0   0   8   0   0   8   0  -4  -4  -4   4   4   4  -4   4
 4     0   0   0   0   0   0   0   0   8   0  -8   0  -8   0  -8   0
 5     0  -4  -8  -4   0  -4   0   4  -4   0   4   0  -4   0  -4   8
 6     0  -4   0  -4   0  -4   0  -4   0   4   0   4   8  -4  -8  -4
 7     0  -8   0   0   8   0   0   0  -4  -4  -4   4  -4  -4   4  -4
 8     0   8   0   0   0  -8   0   0   0  -8   0   0   0  -8   0   0
 9     0  -4  -8   4   0  -4   0  -4   4   0  -4  -8   4   0   4   0
 A     0  -4   0   4  -8   4  -8  -4   0  -4   0   4   0  -4   0   4
 B     0   0   0   0   0   0  -8   8  -4  -4  -4  -4   4   4  -4  -4
 C     0   0   0   8   0   0   0   8   0   8   0   0   0  -8   0   0
 D     0   4  -8  -4   0   4   0   4   4   0  -4   8   4   0   4   0
 E     0  -4   0   4   0  -4   0   4   8  -4   8   4   0   4   0  -4
 F     0   0   0   0   8   8   0   0   4  -4   4  -4   4  -4  -4   4
```

Its exact spectrum is:

| Walsh numerator | Count |
| ---: | ---: |
| \(16\) | 1 |
| \(8\) | 19 |
| \(-8\) | 17 |
| \(4\) | 44 |
| \(-4\) | 52 |
| \(0\) | 123 |

Thus

\[
W[b,a]\in\{0,\pm4,\pm8,16\}.
\]

Each input-mask column satisfies the local Parseval identity

\[
\forall a,\qquad \sum_b W[b,a]^2=256.
\]

Define

\[
q[b,a]=W[b,a]/4.
\]

Then

\[
q[b,a]\in\{0,\pm1,\pm2,4\},
\qquad
C^S[b,a]=\frac{W[b,a]}{16}=\frac{q[b,a]}4.
\]

## 4. Complete local branches

For an input nibble \(a\), define

\[
\mathcal B(a)=\{(b,q[b,a]):q[b,a]\ne0\}.
\]

Every list is ordered deterministically by \(b\). The complete branch counts
are:

```text
a = 0       : 1
a in {2,4,6}: 4
other a != 0: 10
```

The absolute column sums of the normalized local correlation table are:

```text
a = 0       : 1
a in {2,4,6}: 2
other a != 0: 3
```

Therefore

\[
\max_a\sum_b|C^S[b,a]|=3.
\]

## 5. Uniform one-round denominator

For a 32-bit mask split into eight nibbles,

\[
m=(m^{(0)},\ldots,m^{(7)}),
\qquad
b=(b^{(0)},\ldots,b^{(7)}),
\]

the S-layer correlation is

\[
C_{SC}[b,m]
=
\prod_{j=0}^{7}C^S[b^{(j)},m^{(j)}]
=
\frac{Q[b,m]}{2^{16}},
\]

where

\[
Q[b,m]=\prod_{j=0}^{7}q[b^{(j)},m^{(j)}]\in\mathbb Z,
\qquad
|Q[b,m]|\le2^{16}.
\]

The uniform one-round denominator is \(2^{16}\). It need not be the reduced
denominator of every individual transition. The uniform denominator permits
direct integer aggregation, and it cannot be uniformly reduced because a
product of eight local \(q=\pm1\) factors is possible.

## 6. Exact state representation

At round \(t\), represent every state as

\[
A_t[m]=\frac{N_t[m]}{2^{16t}},
\qquad
N_t[m]\in\mathbb Z.
\]

Initialization is

\[
N_0[u]=1,
\qquad
N_0[m]=0\quad(m\ne u).
\]

The update is

\[
N_{t+1}[P(b)]
\mathrel{+}=
N_t[m]Q[b,m].
\]

The authoritative update path permits only integer multiplication, signed
integer addition, integer zero comparison, and exact integer serialization.
Floating-point values must not participate in aggregation, pruning, zero
testing, or certification.

## 7. Linear-mask direction

For a linear layer \(y=Lx\),

\[
M_L[v,u]=1
\quad\Longleftrightarrow\quad
L^\top v=u.
\]

Forward propagation of an input mask therefore uses

\[
v=(L^\top)^{-1}u.
\]

For one round

\[
F=MC\circ SR\circ SC,
\]

the successor of an S-layer output mask \(b\) is

\[
P(b)
=
(L_{MC}^{\top})^{-1}
\left((L_{SR}^{\top})^{-1}b\right).
\]

The corresponding code path is:

```cpp
mc_inv_transpose_mask(sr_inv_transpose_mask(after_sc))
```

`tests/test_linear_mask_basis.cpp` checks all 32 basis masks and the defining
identity

\[
\langle u,x\rangle
=
\langle(L^\top)^{-1}u,Lx\rangle
\]

for `SR`, `MC`, and their round composition.

## 8. Exact Cartesian product

The exact S-layer tuple set is

\[
\mathcal T(m)
=
\mathcal B(m^{(0)})\times\cdots\times\mathcal B(m^{(7)}).
\]

An exact backend must enumerate every Cartesian-product element exactly once.
It must not use top-K selection. It must not use a priority queue to cap tuple
enumeration. It must not use a beam, tuple cap, magnitude pruning, or early
termination. In particular, the exact Cartesian product implementation must
be independent of the approximate `BeamSearch` priority-queue path.

Each local list has at most 10 elements, so a single state may have as many as

\[
10^8
\]

complete tuples. Resource exhaustion, timeout, cancellation, or incomplete
serialization must abort the exact run and refuse certification; partial
output is not an exact result.

## 9. Authoritative integer backend

The authoritative backend type is:

```cpp
boost::multiprecision::cpp_int
```

Formal exact artifacts take their mathematical meaning from `cpp_int`
results. A checked signed `__int128` fast path is allowed only in a proved
range and must be cross-checked against the authoritative mode.

Let

\[
B=2^{16}3^8=429981696.
\]

The maximum absolute column sum of a one-round 32-bit correlation matrix is
\(3^8\), so

\[
\|A_t\|_1\le3^{8t},
\qquad
\sum_m|N_t[m]|\le2^{16t}3^{8t}=B^t.
\]

Hence

\[
|N_t[m]|\le B^t,
\qquad
|N_t[m]Q[b,m]|\le B^t2^{16},
\]

and every partial or final accumulator is bounded by \(B^{t+1}\), independent
of aggregation order.

| Produced round | Single product bound | Bits | Partial/final sum bound | Bits |
| ---: | ---: | ---: | ---: | ---: |
| 1 | `65536` | 17 | `429981696` | 29 |
| 2 | `28179280429056` | 45 | `184884258895036416` | 58 |
| 3 | `12116574790945106558976` | 74 | `79496847203390844133441536` | 87 |
| 4 | `5209905378321422361129224503296` | 103 | `34182189187166852111368841966125056` | 115 |

A signed `__int128` has positive range through \(2^{127}-1\). The proof is
therefore valid for every product and accumulator with `r <= 4`. The bound for
`r = 5` exceeds the signed `__int128` range, so higher rounds require
`cpp_int`. The frozen submission contains only \(r=1,2,3\), but future formal
release artifacts still require authoritative `cpp_int` cross-validation.

## 10. Exact zero deletion and aggregation order

If

\[
N_t[m]=0,
\]

then every successor contribution from that state is exactly zero. Removing a
zero state after all contributions for a round are aggregated cannot affect
future states. The test must be `numerator == 0`, never an epsilon comparison,
and the container must permit later reinsertion of the same key.

All states at round \(t\) share denominator \(2^{16t}\), so

\[
\sum_i\frac{n_i}{2^{16t}}
=
\frac{\sum_i n_i}{2^{16t}}.
\]

Integer addition is associative and commutative. Correctly implemented
unordered iteration and multi-threaded reduction therefore cannot change the
result, and positive/negative cancellation is exact.

## 11. Relation to the full-domain way-1 numerator

Define the full-domain numerator

\[
K_r(u,v)
=
\sum_{x\in\mathbb F_2^{32}}
(-1)^{u^\top x\oplus v^\top HS_r(x)}.
\]

Then

\[
M(r)[v,u]
=
\frac{K_r(u,v)}{2^{32}}
=
\frac{N_r[v]}{2^{16r}}.
\]

Consequently:

\[
K_1(u,v)=N_1[v]2^{16},
\qquad
K_2(u,v)=N_2[v],
\]

and for \(r=3\),

\[
N_3[v]\equiv0\pmod{2^{16}},
\qquad
K_3(u,v)=N_3[v]/2^{16}.
\]

In general, if \(16r\le32\), multiply \(N_r[v]\) by \(2^{32-16r}\). If
\(16r>32\), require divisibility by \(2^{16r-32}\) and divide by that exact
factor.

## 12. Parseval column invariant

Because the S-box and the linear layers are permutations, every round function
is a permutation. Its normalized correlation matrix is orthogonal. For each
fixed input mask \(u\),

\[
\sum_v M(r)[v,u]^2=1.
\]

Substitution of the dyadic representation yields the exact integer invariant

\[
\boxed{\sum_vN_r[v]^2=2^{32r}}.
\]

The square sum must use `cpp_int`, cover a complete certified column, and use
no tolerance. Failure is a release-gate failure. Passing Parseval is a strong
consistency check but is not, by itself, proof that the enumerator is correct.

## 13. Certification semantics

`certified_no_truncation` is the existing structural condition

```text
branch_truncated_states == 0
tuple_truncated_states == 0
beam_pruned == false
```

It does not prove exact integer arithmetic, independent complete Cartesian
enumeration, absence of overflow, or Parseval.

The future certificate is:

```text
certified_exact_dyadic =
    complete_walsh_branch_table
    && exact_cartesian_complete
    && no_state_pruning
    && aggregate_by_mask
    && exact_integer_numeric_backend
    && linear_mask_direction_verified
    && no_overflow
    && run_completed_normally
```

`parseval_pass` remains a separate field. A formal exact way-2 release requires

```text
certified_exact_dyadic && parseval_pass
```

## 14. Output schema

An endpoint artifact must contain:

```text
row_id
r
u
v
numerator
denominator_exp2
value_fraction
numeric_backend
exact_cartesian_complete
no_state_pruning
certified_no_truncation
certified_exact_dyadic
parseval_pass
expanded_states
generated_transitions
source_commit
input_sha256
command_sha256
```

The required normalization is:

```text
value_fraction = "<numerator>/2^<denominator_exp2>"
denominator_exp2 = 16 * r
numeric_backend in {"cpp_int", "int128_checked"}
```

A column summary must contain:

```text
r
u
state_count
sum_squares
expected_sum_squares
parseval_pass
certified_exact_dyadic
```

Decimal display fields may be added, but they are never authoritative.

## 15. Mandatory rejection conditions

The backend must set `certified_exact_dyadic=false` if any of the following
occurs:

- the Walsh table differs from the frozen table;
- a nonzero local branch is missing or duplicated;
- the Cartesian product is incomplete;
- top-K, priority-queue caps, beam pruning, tuple caps, or magnitude pruning
  influence the authoritative result;
- a nonzero state is removed;
- floating-point arithmetic or epsilon zero tests influence aggregation;
- `__int128` is used outside the proved range or checked arithmetic overflows;
- the linear-mask direction tests fail;
- a contribution is omitted or counted more than once;
- the denominator exponent is wrong;
- the \(r=3\) way-1 divisibility invariant fails;
- Parseval fails;
- an input, source, command, or output hash does not match;
- execution is interrupted or output serialization is incomplete.

No partial artifact may be labeled as a complete exact result.
