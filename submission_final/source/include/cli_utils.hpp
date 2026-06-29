#pragma once

#include <cstdint>
#include <cstdlib>
#include <stdexcept>
#include <string>
#include <vector>

#include "packing.hpp"

namespace hs {

inline Mask parse_mask(const std::string& s) {
    std::size_t idx = 0;
    unsigned long v = std::stoul(s, &idx, 0);
    if (idx != s.size()) throw std::invalid_argument("bad mask: " + s);
    if (v > 0xFFFFFFFFul) throw std::out_of_range("mask does not fit uint32: " + s);
    return static_cast<Mask>(v);
}

inline long double parse_ld(const std::string& s) {
    std::size_t idx = 0;
    long double v = std::stold(s, &idx);
    if (idx != s.size()) throw std::invalid_argument("bad floating-point number: " + s);
    return v;
}

inline std::uint64_t parse_u64(const std::string& s) {
    std::size_t idx = 0;
    unsigned long long v = std::stoull(s, &idx, 0);
    if (idx != s.size()) throw std::invalid_argument("bad integer: " + s);
    return static_cast<std::uint64_t>(v);
}

inline std::string require_arg(int& i, int argc, char** argv, const std::string& opt) {
    if (i + 1 >= argc) throw std::invalid_argument("missing argument after " + opt);
    return argv[++i];
}

} // namespace hs
