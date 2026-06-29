#pragma once

#include <array>
#include <cstdint>
#include <vector>

#include "packing.hpp"

namespace hs {

inline constexpr std::array<Nibble, 16> SBOX = {
    0xC, 0x6, 0x9, 0x0, 0x1, 0xA, 0x2, 0xB,
    0x3, 0x8, 0x5, 0xD, 0x4, 0xE, 0x7, 0xF
};

struct NibbleTransition {
    Nibble out = 0;
    int num = 0;          // numerator of the correlation: C[out,in] = num / 16
    int sign = 1;         // sign(num)
    int log2_abs = 0;     // log2(abs(num / 16)); for this S-box it is 0, -1, or -2.
};

class SboxCorr {
public:
    SboxCorr();

    int numerator(Nibble out, Nibble in) const {
        return corr_num_[out & 0xF][in & 0xF];
    }

    long double value(Nibble out, Nibble in) const {
        return static_cast<long double>(numerator(out, in)) / 16.0L;
    }

    const std::vector<NibbleTransition>& candidates(Nibble in) const {
        return candidates_[in & 0xF];
    }

    const std::array<std::array<int, 16>, 16>& table() const { return corr_num_; }

private:
    std::array<std::array<int, 16>, 16> corr_num_{}; // [out][in]
    std::array<std::vector<NibbleTransition>, 16> candidates_{};
};

} // namespace hs
