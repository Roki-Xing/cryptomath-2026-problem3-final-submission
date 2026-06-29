#pragma once

#include <array>
#include <cstdint>
#include <functional>
#include <string>
#include <vector>

#include "packing.hpp"
#include "sbox_corr.hpp"

namespace hs {

struct ExactLocalBranch {
    Nibble out = 0;
    int q = 0;
};

using ExactBranchTable = std::array<std::vector<ExactLocalBranch>, 16>;

struct ExactBranchValidation {
    bool complete = false;
    std::string error;
};

struct ExactCartesianStats {
    std::uint64_t expected = 0;
    std::uint64_t emitted = 0;
    bool complete = false;
};

using ExactCartesianEmitter = std::function<bool(Mask after_sbox, int q_product)>;

ExactBranchTable build_exact_branch_table(const SboxCorr& corr);
ExactBranchValidation validate_exact_branch_table(const ExactBranchTable& branches,
                                                  const SboxCorr& corr);
std::uint64_t exact_cartesian_cardinality(Mask input, const ExactBranchTable& branches);
ExactCartesianStats enumerate_exact_cartesian(Mask input,
                                              const ExactBranchTable& branches,
                                              const ExactCartesianEmitter& emit);

} // namespace hs
