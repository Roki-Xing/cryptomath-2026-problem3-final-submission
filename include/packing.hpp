#pragma once

#include <array>
#include <cstdint>
#include <iomanip>
#include <sstream>
#include <string>

namespace hs {

using Mask = std::uint32_t;
using Nibble = std::uint8_t;

// The statement and the reference program use big-endian nibbles:
// mask = 0x x0 x1 x2 x3 x4 x5 x6 x7, where nibble 0 is bits 31..28.
inline Nibble get_nibble(Mask x, int pos) {
    return static_cast<Nibble>((x >> (28 - 4 * pos)) & 0xFu);
}

inline Mask set_nibble(Mask x, int pos, Nibble val) {
    const Mask shift = static_cast<Mask>(28 - 4 * pos);
    x &= ~(0xFu << shift);
    x |= (static_cast<Mask>(val & 0xFu) << shift);
    return x;
}

inline Mask pack_nibbles(const std::array<Nibble, 8>& a) {
    Mask x = 0;
    for (int i = 0; i < 8; ++i) x = set_nibble(x, i, a[i]);
    return x;
}

inline std::array<Nibble, 8> unpack_nibbles(Mask x) {
    std::array<Nibble, 8> a{};
    for (int i = 0; i < 8; ++i) a[i] = get_nibble(x, i);
    return a;
}

inline int parity32(Mask x) {
#if defined(__GNUG__) || defined(__clang__)
    return __builtin_parity(x);
#else
    x ^= x >> 16;
    x ^= x >> 8;
    x ^= x >> 4;
    x &= 0xFu;
    return (0x6996u >> x) & 1u;
#endif
}

inline int parity4(Nibble x) {
    x &= 0xFu;
    return (0x6996u >> x) & 1u;
}

inline int dot(Mask a, Mask b) {
    return parity32(a & b);
}

inline std::string hex32(Mask x) {
    std::ostringstream oss;
    oss << "0x" << std::hex << std::nouppercase << std::setw(8) << std::setfill('0') << x;
    return oss.str();
}

inline int active_nibbles(Mask x) {
    int c = 0;
    for (int i = 0; i < 8; ++i) c += (get_nibble(x, i) != 0);
    return c;
}

} // namespace hs
