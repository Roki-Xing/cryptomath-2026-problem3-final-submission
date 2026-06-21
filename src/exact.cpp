#include "exact.hpp"

#include <chrono>
#include <algorithm>
#include <limits>
#include <stdexcept>
#include <thread>
#include <vector>

#include "linear_layer.hpp"

namespace hs {

std::vector<ExactResult> compute_exact_batch(const std::vector<ExactBatchQuery>& queries,
                                             int rounds,
                                             std::uint64_t start,
                                             std::uint64_t end,
                                             std::size_t threads) {
    if (rounds < 0) throw std::invalid_argument("rounds must be non-negative");
    if (start >= end) throw std::invalid_argument("exact range must be non-empty");
    if (end > kExactFullDomainSize) throw std::out_of_range("exact range exceeds 2^32 domain");
    if (queries.empty()) return {};

    const std::uint64_t total = end - start;
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
            for (std::uint64_t x = block_start; x < block_end; ++x) {
                const Mask xx = static_cast<Mask>(x);
                const Mask y = permute(xx, rounds);
                for (std::size_t i = 0; i < queries.size(); ++i) {
                    counts[i] += (dot(queries[i].u, xx) == dot(queries[i].v, y)) ? 1 : -1;
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
    return out;
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
