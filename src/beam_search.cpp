#include "beam_search.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <queue>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>

namespace hs {
namespace {

long double abs_ld(long double x) { return x < 0 ? -x : x; }

bool keep_top_by_abs(std::vector<BeamItem>& items, std::size_t k) {
    items.erase(std::remove_if(items.begin(), items.end(), [](const BeamItem& it) {
        return it.value == 0.0L || !std::isfinite(static_cast<double>(it.value));
    }), items.end());
    const bool pruned = items.size() > k;
    if (items.size() > k) {
        std::nth_element(items.begin(), items.begin() + static_cast<std::ptrdiff_t>(k), items.end(),
                         [](const BeamItem& a, const BeamItem& b) {
                             return abs_ld(a.value) > abs_ld(b.value);
                         });
        items.resize(k);
    }
    std::sort(items.begin(), items.end(), [](const BeamItem& a, const BeamItem& b) {
        const long double aa = abs_ld(a.value);
        const long double bb = abs_ld(b.value);
        if (aa != bb) return aa > bb;
        return a.mask < b.mask;
    });
    return pruned;
}

void keep_top_routes_by_abs(std::vector<TraceRoute>& routes, std::size_t k) {
    routes.erase(std::remove_if(routes.begin(), routes.end(), [](const TraceRoute& route) {
        return route.value == 0.0L || !std::isfinite(static_cast<double>(route.value));
    }), routes.end());
    if (routes.size() > k) {
        std::nth_element(routes.begin(), routes.begin() + static_cast<std::ptrdiff_t>(k), routes.end(),
                         [](const TraceRoute& a, const TraceRoute& b) {
                             return abs_ld(a.value) > abs_ld(b.value);
                         });
        routes.resize(k);
    }
    std::sort(routes.begin(), routes.end(), [](const TraceRoute& a, const TraceRoute& b) {
        const long double aa = abs_ld(a.value);
        const long double bb = abs_ld(b.value);
        if (aa != bb) return aa > bb;
        return a.masks < b.masks;
    });
}

std::uint64_t encode_indices(const std::array<std::uint8_t, 8>& idx) {
    std::uint64_t code = 0;
    for (int i = 0; i < 8; ++i) code |= (static_cast<std::uint64_t>(idx[i] & 0xFu) << (4 * i));
    return code;
}

struct TupleNode {
    std::array<std::uint8_t, 8> idx{};
    int score = 0;
    std::uint64_t code = 0;
};

struct TupleNodeCmp {
    bool operator()(const TupleNode& a, const TupleNode& b) const {
        if (a.score != b.score) return a.score < b.score; // max-heap by score
        return a.code > b.code;
    }
};

struct TraceBucket {
    long double aggregate_value = 0.0L;
    std::vector<TraceRoute> routes;
};

} // namespace

BeamSearch::BeamSearch() = default;

GeneratedTransitions BeamSearch::generate_round_transitions(Mask in_mask, const BeamParams& params) const {
    std::array<std::vector<NibbleTransition>, 8> lists;
    GeneratedTransitions generated;
    int initial_score = 0;
    for (int pos = 0; pos < 8; ++pos) {
        const auto& src = corr_.candidates(get_nibble(in_mask, pos));
        if (src.empty()) return generated;
        const std::size_t lim = std::min<std::size_t>(src.size(), params.max_branch_per_nibble == 0 ? src.size() : params.max_branch_per_nibble);
        if (lim < src.size()) generated.branch_truncated = true;
        lists[pos].assign(src.begin(), src.begin() + static_cast<std::ptrdiff_t>(lim));
        initial_score += lists[pos][0].log2_abs;
    }

    std::priority_queue<TupleNode, std::vector<TupleNode>, TupleNodeCmp> pq;
    std::unordered_set<std::uint64_t> seen;
    TupleNode start;
    start.idx.fill(0);
    start.score = initial_score;
    start.code = encode_indices(start.idx);
    pq.push(start);
    seen.insert(start.code);

    generated.transitions.reserve(params.max_sbox_transitions_per_state);

    while (!pq.empty() && generated.transitions.size() < params.max_sbox_transitions_per_state) {
        const TupleNode cur = pq.top();
        pq.pop();

        Mask sc_out = 0;
        int sign = 1;
        int log2_abs = 0;
        for (int pos = 0; pos < 8; ++pos) {
            const auto& tr = lists[pos][cur.idx[pos]];
            sc_out = set_nibble(sc_out, pos, tr.out);
            sign *= tr.sign;
            log2_abs += tr.log2_abs;
        }
        SLayerTransition rt;
        rt.out_mask = round_linear_inv_transpose_after_sc(sc_out);
        rt.log2_abs = log2_abs;
        rt.sign = sign;
        rt.value = static_cast<long double>(sign) * std::ldexp(1.0L, log2_abs);
        generated.transitions.push_back(rt);

        for (int pos = 0; pos < 8; ++pos) {
            if (static_cast<std::size_t>(cur.idx[pos] + 1) >= lists[pos].size()) continue;
            TupleNode nxt = cur;
            const auto& old_tr = lists[pos][nxt.idx[pos]];
            ++nxt.idx[pos];
            const auto& new_tr = lists[pos][nxt.idx[pos]];
            nxt.score += new_tr.log2_abs - old_tr.log2_abs;
            nxt.code = encode_indices(nxt.idx);
            if (seen.insert(nxt.code).second) pq.push(nxt);
        }
    }
    generated.tuple_truncated = !pq.empty() && generated.transitions.size() == params.max_sbox_transitions_per_state;
    return generated;
}

EstimateResult BeamSearch::estimate(int rounds, Mask u, std::optional<Mask> v, const BeamParams& params) const {
    if (rounds < 0) throw std::invalid_argument("rounds must be non-negative");
    if (params.beam_size == 0) throw std::invalid_argument("beam_size must be positive");
    if (params.max_sbox_transitions_per_state == 0) throw std::invalid_argument("max_sbox_transitions_per_state must be positive");

    EstimateResult res;
    res.rounds = rounds;
    res.u = u;
    res.v = v;
    res.certified_no_truncation = true;

    std::vector<BeamItem> beam{{u, 1.0L}};
    for (int r = 0; r < rounds; ++r) {
        RoundStats stats;
        stats.round = r + 1;
        stats.input_beam_size = beam.size();
        if (params.aggregate_by_mask) {
            std::unordered_map<Mask, long double> acc;
            const std::size_t reserve_hint = std::min<std::size_t>(
                beam.size() * params.max_sbox_transitions_per_state * 2,
                static_cast<std::size_t>(1) << 24);
            acc.reserve(reserve_hint);
            for (const BeamItem& item : beam) {
                const auto generated = generate_round_transitions(item.mask, params);
                const auto& trans = generated.transitions;
                ++res.expanded_states;
                res.generated_transitions += trans.size();
                stats.raw_next_terms += trans.size();
                stats.branch_truncated_states += generated.branch_truncated ? 1 : 0;
                stats.tuple_truncated_states += generated.tuple_truncated ? 1 : 0;
                for (const auto& tr : trans) {
                    acc[tr.out_mask] += item.value * tr.value;
                }
            }
            beam.clear();
            beam.reserve(acc.size());
            for (const auto& kv : acc) beam.push_back({kv.first, kv.second});
            stats.aggregated_masks = beam.size();
            stats.beam_pruned = keep_top_by_abs(beam, params.beam_size);
        } else {
            std::vector<BeamItem> next;
            const std::size_t reserve_hint = std::min<std::size_t>(
                beam.size() * params.max_sbox_transitions_per_state,
                params.beam_size * params.max_sbox_transitions_per_state);
            next.reserve(reserve_hint);
            for (const BeamItem& item : beam) {
                const auto generated = generate_round_transitions(item.mask, params);
                const auto& trans = generated.transitions;
                ++res.expanded_states;
                res.generated_transitions += trans.size();
                stats.raw_next_terms += trans.size();
                stats.branch_truncated_states += generated.branch_truncated ? 1 : 0;
                stats.tuple_truncated_states += generated.tuple_truncated ? 1 : 0;
                for (const auto& tr : trans) next.push_back({tr.out_mask, item.value * tr.value});
            }
            stats.aggregated_masks = next.size();
            stats.beam_pruned = keep_top_by_abs(next, params.beam_size);
            beam.swap(next);
        }
        stats.output_beam_size = beam.size();
        if (stats.branch_truncated_states != 0 || stats.tuple_truncated_states != 0 || stats.beam_pruned) {
            res.certified_no_truncation = false;
        }
        res.round_stats.push_back(stats);
    }

    res.final_beam = beam;
    if (v.has_value()) {
        long double sum = 0.0L;
        for (const BeamItem& it : beam) if (it.mask == *v) sum += it.value;
        res.ve = sum;
    }

    res.top_outputs = beam;
    keep_top_by_abs(res.top_outputs, params.top_outputs);
    return res;
}

TraceResult BeamSearch::trace(int rounds, Mask u, std::optional<Mask> v, const BeamParams& params, std::size_t top_routes) const {
    if (rounds < 0) throw std::invalid_argument("rounds must be non-negative");
    if (params.beam_size == 0) throw std::invalid_argument("beam_size must be positive");
    if (params.max_sbox_transitions_per_state == 0) throw std::invalid_argument("max_sbox_transitions_per_state must be positive");
    if (top_routes == 0) throw std::invalid_argument("top_routes must be positive");

    TraceResult res;
    res.rounds = rounds;
    res.u = u;
    res.v = v;

    std::vector<TraceRoute> current{{std::vector<Mask>{u}, 1.0L}};
    const std::size_t bucket_keep = top_routes;
    for (int r = 0; r < rounds; ++r) {
        std::unordered_map<Mask, TraceBucket> buckets;
        const std::size_t reserve_hint = std::min<std::size_t>(
            current.size() * params.max_sbox_transitions_per_state * 2,
            static_cast<std::size_t>(1) << 24);
        buckets.reserve(reserve_hint);

        for (const TraceRoute& route : current) {
            const Mask in_mask = route.masks.back();
            const auto generated = generate_round_transitions(in_mask, params);
            for (const auto& tr : generated.transitions) {
                TraceRoute next = route;
                next.masks.push_back(tr.out_mask);
                next.value *= tr.value;
                auto& bucket = buckets[tr.out_mask];
                bucket.aggregate_value += next.value;
                bucket.routes.push_back(std::move(next));
                if (bucket.routes.size() > bucket_keep * 4) keep_top_routes_by_abs(bucket.routes, bucket_keep);
            }
        }

        if (params.aggregate_by_mask) {
            std::vector<BeamItem> aggregates;
            aggregates.reserve(buckets.size());
            for (auto& kv : buckets) {
                keep_top_routes_by_abs(kv.second.routes, bucket_keep);
                aggregates.push_back({kv.first, kv.second.aggregate_value});
            }
            keep_top_by_abs(aggregates, params.beam_size);

            std::unordered_set<Mask> kept_masks;
            kept_masks.reserve(aggregates.size());
            for (const auto& item : aggregates) kept_masks.insert(item.mask);
            current.clear();
            for (auto& kv : buckets) {
                if (kept_masks.count(kv.first) == 0) continue;
                for (auto& route : kv.second.routes) current.push_back(std::move(route));
            }
        } else {
            current.clear();
            for (auto& kv : buckets) {
                for (auto& route : kv.second.routes) current.push_back(std::move(route));
            }
            keep_top_routes_by_abs(current, params.beam_size);
        }
    }

    if (v.has_value()) {
        for (const auto& route : current) {
            if (route.masks.back() == *v) {
                res.kept_sum += route.value;
                res.routes.push_back(route);
            }
        }
    } else {
        res.routes = current;
        for (const auto& route : res.routes) res.kept_sum += route.value;
    }
    keep_top_routes_by_abs(res.routes, top_routes);
    return res;
}

long double one_round_exact_from_corr(Mask u, Mask v, const SboxCorr& corr) {
    const Mask before_sc_out = round_linear_transpose_before_sc(v);
    long double ans = 1.0L;
    for (int pos = 0; pos < 8; ++pos) {
        const int num = corr.numerator(get_nibble(before_sc_out, pos), get_nibble(u, pos));
        if (num == 0) return 0.0L;
        ans *= static_cast<long double>(num) / 16.0L;
    }
    return ans;
}

long double score_of_estimate(int rounds, long double ve) {
    if (ve == 0.0L) return -std::numeric_limits<long double>::infinity();
    return 2.0L * static_cast<long double>(rounds) + std::log2(abs_ld(ve));
}

} // namespace hs
