#include "exact_cartesian.hpp"

#include <limits>
#include <stdexcept>

namespace hs {

ExactBranchTable build_exact_branch_table(const SboxCorr& corr) {
    ExactBranchTable branches;
    for (int in = 0; in < 16; ++in) {
        auto& column = branches[in];
        for (int out = 0; out < 16; ++out) {
            const int numerator =
                corr.numerator(static_cast<Nibble>(out), static_cast<Nibble>(in));
            if (numerator != 0) {
                column.push_back({static_cast<Nibble>(out), numerator / 4});
            }
        }
    }
    return branches;
}

ExactBranchValidation validate_exact_branch_table(const ExactBranchTable& branches,
                                                  const SboxCorr& corr) {
    for (int in = 0; in < 16; ++in) {
        std::array<bool, 16> seen{};
        for (const auto& branch : branches[in]) {
            if (branch.out >= 16) return {false, "branch output is outside one nibble"};
            if (seen[branch.out]) return {false, "duplicate local branch"};
            seen[branch.out] = true;
            const int numerator = corr.numerator(branch.out, static_cast<Nibble>(in));
            if (numerator == 0 || numerator / 4 != branch.q) {
                return {false, "local branch differs from Walsh table"};
            }
        }
        for (int out = 0; out < 16; ++out) {
            const bool expected =
                corr.numerator(static_cast<Nibble>(out), static_cast<Nibble>(in)) != 0;
            if (seen[out] != expected) return {false, "missing nonzero local branch"};
        }
    }
    return {true, ""};
}

std::uint64_t exact_cartesian_cardinality(Mask input, const ExactBranchTable& branches) {
    std::uint64_t cardinality = 1;
    for (int pos = 0; pos < 8; ++pos) {
        const auto size = static_cast<std::uint64_t>(branches[get_nibble(input, pos)].size());
        if (size == 0) return 0;
        if (cardinality > std::numeric_limits<std::uint64_t>::max() / size) {
            throw std::overflow_error("Cartesian cardinality overflow");
        }
        cardinality *= size;
    }
    return cardinality;
}

ExactCartesianStats enumerate_exact_cartesian(Mask input,
                                              const ExactBranchTable& branches,
                                              const ExactCartesianEmitter& emit) {
    ExactCartesianStats stats;
    stats.expected = exact_cartesian_cardinality(input, branches);
    if (!emit || stats.expected == 0) return stats;

    std::array<std::size_t, 8> indices{};
    while (true) {
        Mask after_sbox = 0;
        int q_product = 1;
        for (int pos = 0; pos < 8; ++pos) {
            const auto& branch = branches[get_nibble(input, pos)][indices[pos]];
            after_sbox = set_nibble(after_sbox, pos, branch.out);
            q_product *= branch.q;
        }

        ++stats.emitted;
        if (!emit(after_sbox, q_product)) return stats;

        int pos = 7;
        for (; pos >= 0; --pos) {
            const auto& column = branches[get_nibble(input, pos)];
            ++indices[pos];
            if (indices[pos] < column.size()) break;
            indices[pos] = 0;
        }
        if (pos < 0) break;
    }

    stats.complete = stats.emitted == stats.expected;
    return stats;
}

} // namespace hs
