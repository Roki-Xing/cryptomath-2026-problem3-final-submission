#pragma once

#include "packing.hpp"

namespace hs {

// Data-side transformations of the cipher HS. These match the statement and the reference program.
Mask sr_apply_state(Mask x);
Mask mc_apply_state(Mask x);
Mask round_apply_state(Mask x);
Mask permute(Mask x, int rounds);

// Mask-side maps for a linear layer y = L x.
// The correlation matrix has M_L[v,u] = 1 iff L^T v = u.
// Thus, when propagating a route forward from an input mask u to an output mask v,
// use v = (L^T)^{-1} u. The *_transpose_mask functions compute L^T v.
Mask sr_transpose_mask(Mask v);
Mask sr_inv_transpose_mask(Mask u);
Mask mc_transpose_mask(Mask v);
Mask mc_inv_transpose_mask(Mask u);

inline Mask round_linear_inv_transpose_after_sc(Mask after_sc) {
    return mc_inv_transpose_mask(sr_inv_transpose_mask(after_sc));
}

inline Mask round_linear_transpose_before_sc(Mask final_mask) {
    return sr_transpose_mask(mc_transpose_mask(final_mask));
}

} // namespace hs
