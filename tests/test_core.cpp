#include <cassert>
#include <cmath>
#include <iostream>
#include <random>

#include "beam_search.hpp"
#include "exact.hpp"
#include "linear_layer.hpp"
#include "packing.hpp"
#include "sbox_corr.hpp"

using namespace hs;

int main() {
    SboxCorr corr;

    // Basic Walsh-table sanity checks.
    assert(corr.numerator(0, 0) == 16);
    for (int x = 1; x < 16; ++x) {
        assert(corr.numerator(0, static_cast<Nibble>(x)) == 0);
        assert(corr.numerator(static_cast<Nibble>(x), 0) == 0);
    }
    assert(corr.candidates(0).size() == 1);
    assert(corr.candidates(2).size() == 4);

    // Big-endian nibble packing.
    assert(get_nibble(0x12345678u, 0) == 0x1);
    assert(get_nibble(0x12345678u, 7) == 0x8);
    assert(pack_nibbles(unpack_nibbles(0xdeadbeefu)) == 0xdeadbeefu);

    // algorithm_generic_rounds: interfaces accept any non-negative round count.
    const Mask generic_x = 0x12345678u;
    assert(permute(generic_x, 0) == generic_x);
    Mask four_rounds = generic_x;
    for (int i = 0; i < 4; ++i) four_rounds = round_apply_state(four_rounds);
    assert(permute(generic_x, 4) == four_rounds);

    BeamSearch generic_bs;
    BeamParams generic_params;
    generic_params.beam_size = 1;
    generic_params.max_sbox_transitions_per_state = 1;
    generic_params.max_branch_per_nibble = 1;
    generic_params.top_outputs = 1;
    const auto zero_round_beam = generic_bs.estimate(0, 0, 0, generic_params);
    assert(zero_round_beam.round_stats.empty());
    assert(zero_round_beam.ve == 1.0L);
    const auto four_round_beam = generic_bs.estimate(4, 0, 0, generic_params);
    assert(four_round_beam.round_stats.size() == 4);
    assert(four_round_beam.ve == 1.0L);

    const auto zero_round_exact = compute_exact_correlation(1, 1, 0, 16);
    assert(zero_round_exact.rounds == 0);
    assert(zero_round_exact.numerator == 16);
    const auto four_round_exact = compute_exact_correlation(0, 0, 4, 1);
    assert(four_round_exact.rounds == 4);
    assert(four_round_exact.numerator == 1);
    const auto four_round_batch = compute_exact_batch({{0, 0}}, 4, 0, 1, 1);
    assert(four_round_batch.size() == 1);
    assert(four_round_batch[0].rounds == 4);
    assert(four_round_batch[0].numerator == 1);

    // Inverse-transpose maps really are inverses of the transposes.
    std::mt19937 rng(1234567);
    for (int i = 0; i < 10000; ++i) {
        const Mask u = rng();
        assert(sr_transpose_mask(sr_inv_transpose_mask(u)) == u);
        assert(mc_transpose_mask(mc_inv_transpose_mask(u)) == u);
    }

    // Check the defining property: <u,x> = <(L^T)^-1 u, L x>.
    for (int i = 0; i < 10000; ++i) {
        const Mask u = rng();
        const Mask x = rng();
        const Mask vsr = sr_inv_transpose_mask(u);
        const Mask vmc = mc_inv_transpose_mask(u);
        assert(dot(u, x) == dot(vsr, sr_apply_state(x)));
        assert(dot(u, x) == dot(vmc, mc_apply_state(x)));
    }

    // One-round estimator is exact when all S-layer branches are retained.
    BeamSearch bs;
    BeamParams p;
    p.beam_size = 10000;
    p.max_sbox_transitions_per_state = 10000;
    p.max_branch_per_nibble = 16;
    p.aggregate_by_mask = true;
    const Mask u = 0x10000000u;
    for (std::uint64_t raw_v = 0; raw_v <= 0x0fffffffULL; raw_v += 0x01111111ULL) {
        const Mask v = static_cast<Mask>(raw_v);
        const long double vt = one_round_exact_from_corr(u, v, corr);
        const auto er = bs.estimate(1, u, v, p);
        assert(std::abs(vt - er.ve) < 1e-18L);
    }

    // Also test every actual one-round endpoint from the beam for the same u.
    const auto er = bs.estimate(1, u, std::nullopt, p);
    for (const auto& it : er.final_beam) {
        const long double vt = one_round_exact_from_corr(u, it.mask, corr);
        assert(std::abs(vt - it.value) < 1e-18L);
    }

    // Low-active r=2 examples can be certified as untruncated sparse-DP evaluations.
    const auto certified = bs.estimate(2, 0x00002000u, 0x08880000u, p);
    assert(certified.certified_no_truncation);
    assert(certified.round_stats.size() == 2);
    assert(certified.round_stats[0].branch_truncated_states == 0);
    assert(certified.round_stats[0].tuple_truncated_states == 0);
    assert(!certified.round_stats[0].beam_pruned);
    assert(std::abs(certified.ve - 1.0L) < 1e-18L);

    const auto trace = bs.trace(2, 0x00002000u, 0x08880000u, p, 100);
    assert(!trace.routes.empty());
    assert(std::abs(trace.kept_sum - certified.ve) < 1e-18L);
    for (const auto& route : trace.routes) {
        assert(route.masks.size() == 3);
        assert(route.masks.front() == 0x00002000u);
        assert(route.masks.back() == 0x08880000u);
    }

    BeamParams truncated = p;
    truncated.max_sbox_transitions_per_state = 1;
    const auto not_certified = bs.estimate(2, 0x00002000u, 0x08880000u, truncated);
    assert(!not_certified.certified_no_truncation);
    assert(not_certified.round_stats[0].tuple_truncated_states > 0 ||
           not_certified.round_stats[1].tuple_truncated_states > 0);

    // Batched exact validation should match independent small-range oracle calls.
    const std::vector<ExactBatchQuery> queries = {
        {0x10000000u, 0x00000008u},
        {0x00002000u, 0x08880000u},
        {0x20000000u, 0x00000888u},
    };
    const auto batch_1t = compute_exact_batch(queries, 1, 0, 4096, 1);
    const auto batch_4t = compute_exact_batch(queries, 1, 0, 4096, 4);
    assert(batch_1t.size() == queries.size());
    assert(batch_4t.size() == queries.size());
    for (std::size_t i = 0; i < queries.size(); ++i) {
        const auto single = compute_exact_correlation(queries[i].u, queries[i].v, 1, 4096);
        assert(batch_1t[i].numerator == single.numerator);
        assert(batch_1t[i].denominator == single.denominator);
        assert(batch_4t[i].numerator == single.numerator);
        assert(batch_4t[i].denominator == single.denominator);
        assert(batch_1t[i].truncated);
        assert(batch_4t[i].truncated);
    }

    std::cout << "all core tests passed\n";
    return 0;
}
