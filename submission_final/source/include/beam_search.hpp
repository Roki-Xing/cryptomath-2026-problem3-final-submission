#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <utility>
#include <vector>

#include "linear_layer.hpp"
#include "sbox_corr.hpp"

namespace hs {

struct BeamParams {
    std::size_t beam_size = 20000;
    std::size_t max_sbox_transitions_per_state = 256;
    std::size_t max_branch_per_nibble = 16; // 16 means keep all nonzero S-box correlations.
    bool aggregate_by_mask = true;
    std::size_t top_outputs = 32;
};

struct BeamItem {
    Mask mask = 0;
    long double value = 0.0L;
};

struct SLayerTransition {
    Mask out_mask = 0;       // after SC followed by SR and MC in mask-propagation direction
    int log2_abs = 0;        // log2(abs(coefficient))
    int sign = 1;
    long double value = 0.0L;
};

struct GeneratedTransitions {
    std::vector<SLayerTransition> transitions;
    bool branch_truncated = false;
    bool tuple_truncated = false;
};

struct RoundStats {
    int round = 0;
    std::size_t input_beam_size = 0;
    std::uint64_t raw_next_terms = 0;
    std::size_t aggregated_masks = 0;
    std::size_t output_beam_size = 0;
    std::size_t branch_truncated_states = 0;
    std::size_t tuple_truncated_states = 0;
    bool beam_pruned = false;
};

struct EstimateResult {
    int rounds = 0;
    Mask u = 0;
    std::optional<Mask> v;
    long double ve = 0.0L;
    std::vector<BeamItem> final_beam;
    std::vector<BeamItem> top_outputs;
    std::uint64_t expanded_states = 0;
    std::uint64_t generated_transitions = 0;
    std::vector<RoundStats> round_stats;
    bool certified_no_truncation = false;
};

struct TraceRoute {
    std::vector<Mask> masks;
    long double value = 0.0L;
};

struct TraceResult {
    int rounds = 0;
    Mask u = 0;
    std::optional<Mask> v;
    std::vector<TraceRoute> routes;
    long double kept_sum = 0.0L;
};

class BeamSearch {
public:
    BeamSearch();

    EstimateResult estimate(int rounds, Mask u, std::optional<Mask> v, const BeamParams& params) const;
    TraceResult trace(int rounds, Mask u, std::optional<Mask> v, const BeamParams& params, std::size_t top_routes) const;
    GeneratedTransitions generate_round_transitions(Mask in_mask, const BeamParams& params) const;

    const SboxCorr& corr() const { return corr_; }

private:
    SboxCorr corr_;
};

long double one_round_exact_from_corr(Mask u, Mask v, const SboxCorr& corr);
long double score_of_estimate(int rounds, long double ve);

} // namespace hs
