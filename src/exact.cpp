#include "exact.hpp"

#include <chrono>
#include <algorithm>
#include <limits>
#include <stdexcept>
#include <thread>
#include <unordered_map>
#include <vector>

#include "linear_layer.hpp"

namespace hs {
namespace {

struct QueryGrouping {
    std::vector<Mask> unique_u;
    std::vector<Mask> unique_v;
    std::vector<std::size_t> query_u_index;
    std::vector<std::size_t> query_v_index;
};

QueryGrouping group_queries(const std::vector<ExactBatchQuery>& queries) {
    QueryGrouping grouping;
    std::unordered_map<Mask, std::size_t> u_index;
    std::unordered_map<Mask, std::size_t> v_index;
    grouping.query_u_index.reserve(queries.size());
    grouping.query_v_index.reserve(queries.size());

    for (const auto& query : queries) {
        const auto [uit, inserted_u] = u_index.emplace(query.u, grouping.unique_u.size());
        if (inserted_u) grouping.unique_u.push_back(query.u);
        grouping.query_u_index.push_back(uit->second);

        const auto [vit, inserted_v] = v_index.emplace(query.v, grouping.unique_v.size());
        if (inserted_v) grouping.unique_v.push_back(query.v);
        grouping.query_v_index.push_back(vit->second);
    }
    return grouping;
}

} // namespace

std::vector<ExactResult> compute_exact_batch(const std::vector<ExactBatchQuery>& queries,
                                             int rounds,
                                             std::uint64_t start,
                                             std::uint64_t end,
                                             std::size_t threads) {
    return compute_exact_batch_variant(
        queries, rounds, start, end, threads, ExactBatchVariant::Current, nullptr);
}

std::vector<ExactResult> compute_exact_batch_variant(
    const std::vector<ExactBatchQuery>& queries,
    int rounds,
    std::uint64_t start,
    std::uint64_t end,
    std::size_t threads,
    ExactBatchVariant variant,
    ExactBatchMetrics* metrics) {
    if (rounds < 0) throw std::invalid_argument("rounds must be non-negative");
    if (start >= end) throw std::invalid_argument("exact range must be non-empty");
    if (end > kExactFullDomainSize) throw std::out_of_range("exact range exceeds 2^32 domain");
    if (queries.empty()) return {};

    const std::uint64_t total = end - start;
    const QueryGrouping grouping = group_queries(queries);
    const std::size_t worker_count =
        static_cast<std::size_t>(std::min<std::uint64_t>(std::max<std::size_t>(threads, 1), total));
    std::vector<std::vector<std::int64_t>> partial(worker_count, std::vector<std::int64_t>(queries.size(), 0));
    std::vector<std::thread> workers;
    workers.reserve(worker_count);

    const auto t0 = std::chrono::steady_clock::now();
    std::uint64_t lo = start;
    const std::uint64_t base = total / worker_count;
    const std::uint64_t extra = total % worker_count;
    for (std::size_t w = 0; w < worker_count; ++w) {
        const std::uint64_t span = base + (w < extra ? 1 : 0);
        const std::uint64_t block_start = lo;
        const std::uint64_t block_end = block_start + span;
        lo = block_end;
        workers.emplace_back([&, w, block_start, block_end]() {
            auto& counts = partial[w];
            std::vector<unsigned char> u_parities(grouping.unique_u.size(), 0);
            std::vector<unsigned char> v_parities(grouping.unique_v.size(), 0);
            for (std::uint64_t x = block_start; x < block_end; ++x) {
                const Mask xx = static_cast<Mask>(x);
                const Mask y = permute(xx, rounds);

                if (variant != ExactBatchVariant::Current) {
                    for (std::size_t i = 0; i < grouping.unique_u.size(); ++i) {
                        u_parities[i] = static_cast<unsigned char>(dot(grouping.unique_u[i], xx));
                    }
                }
                if (variant == ExactBatchVariant::GroupedUV) {
                    for (std::size_t i = 0; i < grouping.unique_v.size(); ++i) {
                        v_parities[i] = static_cast<unsigned char>(dot(grouping.unique_v[i], y));
                    }
                }

                for (std::size_t i = 0; i < queries.size(); ++i) {
                    const int u_parity =
                        variant == ExactBatchVariant::Current
                            ? dot(queries[i].u, xx)
                            : u_parities[grouping.query_u_index[i]];
                    const int v_parity =
                        variant == ExactBatchVariant::GroupedUV
                            ? v_parities[grouping.query_v_index[i]]
                            : dot(queries[i].v, y);
                    counts[i] += (u_parity == v_parity) ? 1 : -1;
                }
            }
        });
    }
    for (auto& worker : workers) worker.join();
    const auto t1 = std::chrono::steady_clock::now();
    const double seconds = std::chrono::duration<double>(t1 - t0).count();

    std::vector<ExactResult> out;
    out.reserve(queries.size());
    for (std::size_t i = 0; i < queries.size(); ++i) {
        std::int64_t count = 0;
        for (const auto& counts : partial) count += counts[i];
        ExactResult res;
        res.rounds = rounds;
        res.u = queries[i].u;
        res.v = queries[i].v;
        res.numerator = count;
        res.denominator = total;
        res.value = static_cast<long double>(count) / static_cast<long double>(total);
        res.seconds = seconds;
        res.truncated = (start != 0 || end != kExactFullDomainSize);
        out.push_back(res);
    }

    if (metrics != nullptr) {
        metrics->plaintext_count = total;
        metrics->permutation_evaluations = total;
        metrics->logical_query_updates = total * queries.size();
        metrics->unique_u = grouping.unique_u.size();
        metrics->unique_v = grouping.unique_v.size();
        metrics->u_parity_evaluations =
            total * (variant == ExactBatchVariant::Current ? queries.size() : grouping.unique_u.size());
        metrics->v_parity_evaluations =
            total * (variant == ExactBatchVariant::GroupedUV ? grouping.unique_v.size() : queries.size());
    }
    return out;
}

std::vector<ExactResult> compute_exact_batch_grouped_u(
    const std::vector<ExactBatchQuery>& queries,
    int rounds,
    std::uint64_t start,
    std::uint64_t end,
    std::size_t threads,
    ExactBatchMetrics* metrics) {
    return compute_exact_batch_variant(
        queries, rounds, start, end, threads, ExactBatchVariant::GroupedU, metrics);
}

std::vector<ExactResult> compute_exact_batch_grouped_uv(
    const std::vector<ExactBatchQuery>& queries,
    int rounds,
    std::uint64_t start,
    std::uint64_t end,
    std::size_t threads,
    ExactBatchMetrics* metrics) {
    return compute_exact_batch_variant(
        queries, rounds, start, end, threads, ExactBatchVariant::GroupedUV, metrics);
}

ExactResult compute_exact_correlation(Mask u, Mask v, int rounds, std::optional<std::uint64_t> limit) {
    if (rounds < 0) throw std::invalid_argument("rounds must be non-negative");
    const std::uint64_t total = limit.has_value() ? std::min(*limit, kExactFullDomainSize) : kExactFullDomainSize;

    const auto t0 = std::chrono::steady_clock::now();
    std::int64_t count = 0;
    for (std::uint64_t x = 0; x < total; ++x) {
        const Mask xx = static_cast<Mask>(x);
        const Mask y = permute(xx, rounds);
        count += (dot(u, xx) == dot(v, y)) ? 1 : -1;
    }
    const auto t1 = std::chrono::steady_clock::now();

    ExactResult res;
    res.rounds = rounds;
    res.u = u;
    res.v = v;
    res.numerator = count;
    res.denominator = total;
    res.value = static_cast<long double>(count) / static_cast<long double>(total);
    res.seconds = std::chrono::duration<double>(t1 - t0).count();
    res.truncated = (total != kExactFullDomainSize);
    return res;
}

} // namespace hs
