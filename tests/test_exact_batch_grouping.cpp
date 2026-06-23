#include <cassert>
#include <cstdint>
#include <iostream>
#include <vector>

#include "exact.hpp"

using namespace hs;

namespace {

void assert_same_results(const std::vector<ExactResult>& lhs,
                         const std::vector<ExactResult>& rhs) {
    assert(lhs.size() == rhs.size());
    for (std::size_t i = 0; i < lhs.size(); ++i) {
        assert(lhs[i].rounds == rhs[i].rounds);
        assert(lhs[i].u == rhs[i].u);
        assert(lhs[i].v == rhs[i].v);
        assert(lhs[i].numerator == rhs[i].numerator);
        assert(lhs[i].denominator == rhs[i].denominator);
        assert(lhs[i].truncated == rhs[i].truncated);
    }
}

} // namespace

int main() {
    const std::vector<ExactBatchQuery> queries = {
        {0x00002000u, 0x08880000u},
        {0x00002000u, 0x04440000u},
        {0x20000000u, 0x08880000u},
        {0x20000000u, 0x00000888u},
    };
    constexpr std::uint64_t start = 37;
    constexpr std::uint64_t end = 4096;
    constexpr std::uint64_t plaintexts = end - start;

    ExactBatchMetrics baseline_metrics;
    ExactBatchMetrics grouped_u_metrics;
    ExactBatchMetrics grouped_uv_metrics;

    const auto baseline = compute_exact_batch_variant(
        queries, 3, start, end, 3, ExactBatchVariant::Current, &baseline_metrics);
    const auto grouped_u = compute_exact_batch_variant(
        queries, 3, start, end, 3, ExactBatchVariant::GroupedU, &grouped_u_metrics);
    const auto grouped_uv = compute_exact_batch_variant(
        queries, 3, start, end, 3, ExactBatchVariant::GroupedUV, &grouped_uv_metrics);

    assert_same_results(baseline, grouped_u);
    assert_same_results(baseline, grouped_uv);

    assert(baseline_metrics.plaintext_count == plaintexts);
    assert(baseline_metrics.permutation_evaluations == plaintexts);
    assert(baseline_metrics.logical_query_updates == plaintexts * queries.size());
    assert(baseline_metrics.u_parity_evaluations == plaintexts * queries.size());
    assert(baseline_metrics.v_parity_evaluations == plaintexts * queries.size());

    assert(grouped_u_metrics.plaintext_count == plaintexts);
    assert(grouped_u_metrics.permutation_evaluations == plaintexts);
    assert(grouped_u_metrics.logical_query_updates == plaintexts * queries.size());
    assert(grouped_u_metrics.u_parity_evaluations == plaintexts * 2);
    assert(grouped_u_metrics.v_parity_evaluations == plaintexts * queries.size());

    assert(grouped_uv_metrics.plaintext_count == plaintexts);
    assert(grouped_uv_metrics.permutation_evaluations == plaintexts);
    assert(grouped_uv_metrics.logical_query_updates == plaintexts * queries.size());
    assert(grouped_uv_metrics.u_parity_evaluations == plaintexts * 2);
    assert(grouped_uv_metrics.v_parity_evaluations == plaintexts * 3);

    ExactBatchMetrics wrapper_metrics;
    const auto wrapper = compute_exact_batch_grouped_uv(
        queries, 3, start, end, 1, &wrapper_metrics);
    assert_same_results(baseline, wrapper);
    assert(wrapper_metrics.v_parity_evaluations == plaintexts * 3);

    std::cout << "exact batch grouping tests passed\n";
    return 0;
}
