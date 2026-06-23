#include <cassert>
#include <cstdint>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>

#include <boost/multiprecision/cpp_int.hpp>

#include "exact_dyadic.hpp"
#include "linear_layer.hpp"
#include "packing.hpp"
#include "sbox_corr.hpp"

using namespace hs;
using boost::multiprecision::cpp_int;

namespace {

struct Spotcheck {
    int rounds = 0;
    Mask u = 0;
    Mask v = 0;
    std::int64_t way1_numerator = 0;
};

Mask parse_mask(const std::string& text) {
    return static_cast<Mask>(std::stoul(text, nullptr, 0));
}

std::vector<Spotcheck> load_spotchecks() {
    std::ifstream input("experiments/spotcheck/exact_spotcheck.csv");
    assert(input);
    std::string line;
    std::getline(input, line);
    std::vector<Spotcheck> rows;
    while (std::getline(input, line)) {
        std::stringstream parser(line);
        std::vector<std::string> cells;
        std::string cell;
        while (std::getline(parser, cell, ',')) cells.push_back(cell);
        assert(cells.size() >= 12);
        rows.push_back({std::stoi(cells[0]), parse_mask(cells[1]), parse_mask(cells[2]),
                        std::stoll(cells[10])});
    }
    assert(rows.size() == 18);
    return rows;
}

ExactDyadicResult run(int rounds, Mask u, ExactNumericBackend backend) {
    ExactDyadicOptions options;
    options.rounds = rounds;
    options.u = u;
    options.backend = backend;
    return compute_exact_dyadic(options);
}

} // namespace

int main() {
    std::map<Mask, cpp_int> accumulator;
    exact_accumulate(accumulator, 7u, cpp_int(5));
    exact_accumulate(accumulator, 7u, cpp_int(-5));
    assert(accumulator.empty());

    const std::vector<std::tuple<Mask, int>> contributions = {
        {3u, 7}, {9u, -4}, {3u, -2}, {9u, 4}, {3u, -5}, {5u, 11},
    };
    std::map<Mask, cpp_int> forward;
    std::map<Mask, cpp_int> reverse;
    for (const auto& [mask, value] : contributions) {
        exact_accumulate(forward, mask, cpp_int(value));
    }
    for (auto it = contributions.rbegin(); it != contributions.rend(); ++it) {
        exact_accumulate(reverse, std::get<0>(*it), cpp_int(std::get<1>(*it)));
    }
    assert(forward == reverse);
    assert(forward.size() == 1);
    assert(forward.at(5u) == 11);

    const SboxCorr corr;
    for (int pos = 0; pos < 8; ++pos) {
        for (int in = 1; in < 16; ++in) {
            const Mask u = set_nibble(0, pos, static_cast<Nibble>(in));
            const auto result = run(1, u, ExactNumericBackend::CppInt);
            assert(result.completed_normally);
            assert(result.certified_no_truncation);
            assert(result.certified_exact_dyadic);
            assert(result.parseval_pass);
            assert(result.denominator_exp2 == 16);
            assert(result.states.size() == corr.candidates(static_cast<Nibble>(in)).size());

            for (const auto& [v, numerator] : result.states) {
                const Mask before_linear = round_linear_transpose_before_sc(v);
                cpp_int expected = 1;
                for (int nibble = 0; nibble < 8; ++nibble) {
                    expected *= corr.numerator(get_nibble(before_linear, nibble),
                                               get_nibble(u, nibble)) /
                                4;
                }
                assert(numerator == expected);
            }
        }
    }

    for (const auto& [rounds, u] :
         std::vector<std::pair<int, Mask>>{{1, 0x00000001u},
                                           {2, 0x00002000u},
                                           {3, 0x00002000u}}) {
        const auto authoritative = run(rounds, u, ExactNumericBackend::CppInt);
        const auto fast = run(rounds, u, ExactNumericBackend::Int128Checked);
        assert(authoritative.certified_exact_dyadic);
        assert(fast.certified_exact_dyadic);
        assert(authoritative.states == fast.states);
        assert(authoritative.sum_squares == fast.sum_squares);
    }

    const auto spotchecks = load_spotchecks();
    std::map<std::pair<int, Mask>, ExactDyadicResult> columns;
    for (const auto& row : spotchecks) {
        const auto key = std::make_pair(row.rounds, row.u);
        if (columns.find(key) == columns.end()) {
            columns.emplace(key, run(row.rounds, row.u, ExactNumericBackend::CppInt));
        }
        const auto& result = columns.at(key);
        assert(result.certified_exact_dyadic);
        assert(result.parseval_pass);
        const auto state = result.states.find(row.v);
        const cpp_int dyadic_numerator = state == result.states.end() ? cpp_int(0) : state->second;
        assert(to_way1_numerator(dyadic_numerator, row.rounds) == row.way1_numerator);
    }

    for (const auto& [key, result] : columns) {
        const int rounds = key.first;
        assert(result.denominator_exp2 == 16 * rounds);
        assert(result.sum_squares == (cpp_int(1) << (32 * rounds)));
    }

    ExactDyadicOptions interrupted;
    interrupted.rounds = 2;
    interrupted.u = 0x00002000u;
    interrupted.backend = ExactNumericBackend::CppInt;
    interrupted.max_generated_transitions = 1;
    const auto failed = compute_exact_dyadic(interrupted);
    assert(!failed.completed_normally);
    assert(!failed.exact_cartesian_complete);
    assert(!failed.certified_no_truncation);
    assert(!failed.certified_exact_dyadic);
    assert(!failed.failure_reason.empty());
    assert(failed.states.empty());
}
