#pragma once

#include <cstdint>
#include <optional>
#include <vector>

#include "packing.hpp"

namespace hs {

constexpr std::uint64_t kExactFullDomainSize = (1ULL << 32);

struct ExactBatchQuery {
    Mask u = 0;
    Mask v = 0;
};

struct ExactResult {
    int rounds = 0;
    Mask u = 0;
    Mask v = 0;
    std::int64_t numerator = 0;       // sum_x (-1)^{u.x xor v.HS(x)} over visited x
    std::uint64_t denominator = 0;    // normally 2^32
    long double value = 0.0L;
    double seconds = 0.0;
    bool truncated = false;
};

ExactResult compute_exact_correlation(Mask u, Mask v, int rounds, std::optional<std::uint64_t> limit = std::nullopt);
std::vector<ExactResult> compute_exact_batch(const std::vector<ExactBatchQuery>& queries,
                                             int rounds,
                                             std::uint64_t start,
                                             std::uint64_t end,
                                             std::size_t threads);

} // namespace hs
