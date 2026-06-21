#include "linear_layer.hpp"

#include <array>

#include "sbox_corr.hpp"

namespace hs {

Mask sr_apply_state(Mask x) {
    const auto a = unpack_nibbles(x);
    return pack_nibbles({a[0], a[5], a[2], a[7], a[4], a[1], a[6], a[3]});
}

Mask mc_apply_state(Mask x) {
    const auto a = unpack_nibbles(x);
    return pack_nibbles({
        static_cast<Nibble>(a[0] ^ a[2] ^ a[3]),
        a[0],
        static_cast<Nibble>(a[1] ^ a[2]),
        static_cast<Nibble>(a[0] ^ a[2]),
        static_cast<Nibble>(a[4] ^ a[6] ^ a[7]),
        a[4],
        static_cast<Nibble>(a[5] ^ a[6]),
        static_cast<Nibble>(a[4] ^ a[6])
    });
}

Mask round_apply_state(Mask x) {
    auto a = unpack_nibbles(x);
    for (int i = 0; i < 8; ++i) a[i] = SBOX[a[i]];
    return mc_apply_state(sr_apply_state(pack_nibbles(a)));
}

Mask permute(Mask x, int rounds) {
    for (int r = 0; r < rounds; ++r) x = round_apply_state(x);
    return x;
}

Mask sr_transpose_mask(Mask v) {
    // SR is an involutive nibble permutation here, so L^T and (L^T)^-1 have the same formula.
    const auto a = unpack_nibbles(v);
    return pack_nibbles({a[0], a[5], a[2], a[7], a[4], a[1], a[6], a[3]});
}

Mask sr_inv_transpose_mask(Mask u) {
    const auto a = unpack_nibbles(u);
    return pack_nibbles({a[0], a[5], a[2], a[7], a[4], a[1], a[6], a[3]});
}

Mask mc_transpose_mask(Mask v) {
    const auto a = unpack_nibbles(v);
    return pack_nibbles({
        static_cast<Nibble>(a[0] ^ a[1] ^ a[3]),
        a[2],
        static_cast<Nibble>(a[0] ^ a[2] ^ a[3]),
        a[0],
        static_cast<Nibble>(a[4] ^ a[5] ^ a[7]),
        a[6],
        static_cast<Nibble>(a[4] ^ a[6] ^ a[7]),
        a[4]
    });
}

Mask mc_inv_transpose_mask(Mask u) {
    const auto a = unpack_nibbles(u);
    return pack_nibbles({
        a[3],
        static_cast<Nibble>(a[0] ^ a[1] ^ a[2]),
        a[1],
        static_cast<Nibble>(a[1] ^ a[2] ^ a[3]),
        a[7],
        static_cast<Nibble>(a[4] ^ a[5] ^ a[6]),
        a[5],
        static_cast<Nibble>(a[5] ^ a[6] ^ a[7])
    });
}

} // namespace hs
