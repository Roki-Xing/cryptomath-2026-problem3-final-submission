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

enum class ExactBatchVariant {
    Current,
    GroupedU,
    GroupedUV,
};

struct ExactBatchMetrics {
    std::uint64_t plaintext_count = 0;
    std::uint64_t permutation_evaluations = 0;
    std::uint64_t u_parity_evaluations = 0;
    std::uint64_t v_parity_evaluations = 0;
    std::uint64_t logical_query_updates = 0;
    std::size_t unique_u = 0;
    std::size_t unique_v = 0;
};

ExactResult compute_exact_correlation(Mask u, Mask v, int rounds, std::optional<std::uint64_t> limit = std::nullopt);
std::vector<ExactResult> compute_exact_batch(const std::vector<ExactBatchQuery>& queries,
                                             int rounds,
                                             std::uint64_t start,
                                             std::uint64_t end,
                                             std::size_t threads);
std::vector<ExactResult> compute_exact_batch_variant(
    const std::vector<ExactBatchQuery>& queries,
    int rounds,
    std::uint64_t start,
    std::uint64_t end,
    std::size_t threads,
    ExactBatchVariant variant,
    ExactBatchMetrics* metrics = nullptr);
std::vector<ExactResult> compute_exact_batch_grouped_u(
    const std::vector<ExactBatchQuery>& queries,
    int rounds,
    std::uint64_t start,
    std::uint64_t end,
    std::size_t threads,
    ExactBatchMetrics* metrics = nullptr);
std::vector<ExactResult> compute_exact_batch_grouped_uv(
    const std::vector<ExactBatchQuery>& queries,
    int rounds,
    std::uint64_t start,
    std::uint64_t end,
    std::size_t threads,
    ExactBatchMetrics* metrics = nullptr);

} // namespace hs
