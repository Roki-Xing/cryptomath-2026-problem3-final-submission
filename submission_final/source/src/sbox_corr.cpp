#include "sbox_corr.hpp"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <stdexcept>

namespace hs {
namespace {
int ilog2_exact(int x) {
    if (x <= 0 || (x & (x - 1)) != 0) {
        throw std::runtime_error("ilog2_exact expects a positive power of two");
    }
    int r = 0;
    while ((1 << r) != x) ++r;
    return r;
}
}

SboxCorr::SboxCorr() {
    for (int out = 0; out < 16; ++out) {
        for (int in = 0; in < 16; ++in) {
            int s = 0;
            for (int x = 0; x < 16; ++x) {
                const int bit = parity4(static_cast<Nibble>(in & x)) ^
                                parity4(static_cast<Nibble>(out & SBOX[x]));
                s += bit ? -1 : 1;
            }
            corr_num_[out][in] = s;
        }
    }

    for (int in = 0; in < 16; ++in) {
        auto& vec = candidates_[in];
        for (int out = 0; out < 16; ++out) {
            const int num = corr_num_[out][in];
            if (num == 0) continue;
            const int abs_num = std::abs(num);
            NibbleTransition tr;
            tr.out = static_cast<Nibble>(out);
            tr.num = num;
            tr.sign = (num < 0) ? -1 : 1;
            tr.log2_abs = ilog2_exact(abs_num) - 4;
            vec.push_back(tr);
        }
        std::sort(vec.begin(), vec.end(), [](const NibbleTransition& a, const NibbleTransition& b) {
            if (a.log2_abs != b.log2_abs) return a.log2_abs > b.log2_abs;
            if (std::abs(a.num) != std::abs(b.num)) return std::abs(a.num) > std::abs(b.num);
            if (a.sign != b.sign) return a.sign > b.sign;
            return a.out < b.out;
        });
    }
}

} // namespace hs
