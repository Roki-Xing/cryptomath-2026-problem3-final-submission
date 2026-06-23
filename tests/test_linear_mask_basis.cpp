#include <cassert>
#include <cstdint>
#include <iostream>

#include "linear_layer.hpp"
#include "packing.hpp"

using namespace hs;

namespace {

Mask basis(int bit) {
    return static_cast<Mask>(std::uint32_t{1} << bit);
}

void check_layer(
    Mask (*apply_state)(Mask),
    Mask (*transpose_mask)(Mask),
    Mask (*inv_transpose_mask)(Mask)) {
    for (int u_bit = 0; u_bit < 32; ++u_bit) {
        const Mask u = basis(u_bit);
        const Mask v = inv_transpose_mask(u);
        assert(transpose_mask(v) == u);
        for (int x_bit = 0; x_bit < 32; ++x_bit) {
            const Mask x = basis(x_bit);
            assert(dot(u, x) == dot(v, apply_state(x)));
        }
    }
}

Mask round_linear_apply_state(Mask x) {
    return mc_apply_state(sr_apply_state(x));
}

} // namespace

int main() {
    check_layer(sr_apply_state, sr_transpose_mask, sr_inv_transpose_mask);
    check_layer(mc_apply_state, mc_transpose_mask, mc_inv_transpose_mask);

    for (int u_bit = 0; u_bit < 32; ++u_bit) {
        const Mask u = basis(u_bit);
        const Mask v = round_linear_inv_transpose_after_sc(u);
        assert(round_linear_transpose_before_sc(v) == u);
        for (int x_bit = 0; x_bit < 32; ++x_bit) {
            const Mask x = basis(x_bit);
            assert(dot(u, x) == dot(v, round_linear_apply_state(x)));
        }
    }

    std::cout << "32-bit linear mask basis tests passed\n";
    return 0;
}
