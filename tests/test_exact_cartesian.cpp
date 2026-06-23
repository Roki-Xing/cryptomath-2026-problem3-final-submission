#include <algorithm>
#include <cassert>
#include <cstdint>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#include "exact_cartesian.hpp"
#include "packing.hpp"
#include "sbox_corr.hpp"

using namespace hs;

namespace {

std::vector<std::vector<int>> load_frozen_walsh() {
    std::ifstream input("tests/data/walsh_table.csv");
    assert(input);

    std::string line;
    std::getline(input, line);
    std::vector<std::vector<int>> table;
    while (std::getline(input, line)) {
        std::stringstream row(line);
        std::string cell;
        std::getline(row, cell, ',');
        std::vector<int> values;
        while (std::getline(row, cell, ',')) values.push_back(std::stoi(cell));
        assert(values.size() == 16);
        table.push_back(std::move(values));
    }
    assert(table.size() == 16);
    return table;
}

} // namespace

int main() {
    const SboxCorr corr;
    const auto frozen = load_frozen_walsh();
    for (int out = 0; out < 16; ++out) {
        for (int in = 0; in < 16; ++in) {
            assert(corr.numerator(static_cast<Nibble>(out), static_cast<Nibble>(in)) ==
                   frozen[out][in]);
        }
    }

    for (int in = 0; in < 16; ++in) {
        int square_sum = 0;
        for (int out = 0; out < 16; ++out) square_sum += frozen[out][in] * frozen[out][in];
        assert(square_sum == 256);
    }

    const ExactBranchTable branches = build_exact_branch_table(corr);
    const auto validation = validate_exact_branch_table(branches, corr);
    assert(validation.complete);
    assert(validation.error.empty());

    for (const auto& column : branches) {
        assert(std::is_sorted(column.begin(), column.end(), [](const ExactLocalBranch& lhs,
                                                               const ExactLocalBranch& rhs) {
            return lhs.out < rhs.out;
        }));
    }

    const Mask input = 0x12000000u;
    const std::uint64_t expected =
        static_cast<std::uint64_t>(branches[1].size()) * branches[2].size();
    assert(exact_cartesian_cardinality(input, branches) == expected);

    std::vector<std::pair<Mask, int>> emitted;
    const auto stats = enumerate_exact_cartesian(
        input, branches, [&](Mask after_sbox, int q_product) {
            emitted.emplace_back(after_sbox, q_product);
            return true;
        });
    assert(stats.complete);
    assert(stats.expected == expected);
    assert(stats.emitted == expected);
    assert(emitted.size() == expected);

    auto reversed = branches;
    for (auto& column : reversed) std::reverse(column.begin(), column.end());
    std::vector<std::pair<Mask, int>> reversed_emitted;
    const auto reversed_stats = enumerate_exact_cartesian(
        input, reversed, [&](Mask after_sbox, int q_product) {
            reversed_emitted.emplace_back(after_sbox, q_product);
            return true;
        });
    assert(reversed_stats.complete);
    std::sort(emitted.begin(), emitted.end());
    std::sort(reversed_emitted.begin(), reversed_emitted.end());
    assert(emitted == reversed_emitted);

    auto duplicate = branches;
    duplicate[1].push_back(duplicate[1].front());
    assert(!validate_exact_branch_table(duplicate, corr).complete);

    auto omitted = branches;
    omitted[1].pop_back();
    assert(!validate_exact_branch_table(omitted, corr).complete);

    std::uint64_t partial_count = 0;
    const auto interrupted = enumerate_exact_cartesian(
        input, branches, [&](Mask, int) {
            ++partial_count;
            return partial_count < 2;
        });
    assert(!interrupted.complete);
    assert(interrupted.emitted == 2);
}
