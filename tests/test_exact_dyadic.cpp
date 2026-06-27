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
            assert(result.exact_cartesian_complete);
            assert(result.no_state_pruning);
            assert(result.exact_integer_backend);
            assert(result.no_overflow);
            assert(result.all_rounds_completed);
            assert(result.completed_rounds == 1);
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

    {
        ExactDyadicResult synthetic;
        synthetic.rounds = 3;
        synthetic.completed_normally = true;
        synthetic.exact_cartesian_complete = true;
        synthetic.no_state_pruning = true;
        synthetic.exact_integer_backend = true;
        synthetic.no_overflow = true;
        synthetic.completed_rounds = 3;
        synthetic.sum_squares = 7;
        synthetic.expected_sum_squares = 8;
        finalize_exact_dyadic_certification(synthetic);
        assert(synthetic.certified_no_truncation);
        assert(synthetic.certified_exact_dyadic);
        assert(!synthetic.parseval_pass);
    }

    {
        ExactDyadicResult incomplete;
        incomplete.rounds = 3;
        incomplete.completed_normally = true;
        incomplete.exact_cartesian_complete = true;
        incomplete.no_state_pruning = true;
        incomplete.exact_integer_backend = true;
        incomplete.no_overflow = true;
        incomplete.completed_rounds = 2;
        incomplete.sum_squares = 1;
        incomplete.expected_sum_squares = 1;
        finalize_exact_dyadic_certification(incomplete);
        assert(!incomplete.all_rounds_completed);
        assert(!incomplete.certified_no_truncation);
        assert(!incomplete.certified_exact_dyadic);
        assert(incomplete.parseval_pass);
    }

    {
        ExactDyadicResult overflow;
        overflow.rounds = 2;
        overflow.completed_normally = true;
        overflow.exact_cartesian_complete = true;
        overflow.no_state_pruning = true;
        overflow.exact_integer_backend = true;
        overflow.no_overflow = false;
        overflow.completed_rounds = 2;
        overflow.sum_squares = 1;
        overflow.expected_sum_squares = 1;
        finalize_exact_dyadic_certification(overflow);
        assert(!overflow.certified_exact_dyadic);
        assert(overflow.parseval_pass);
    }

    {
        ExactDyadicResult fake_parseval;
        fake_parseval.rounds = 1;
        fake_parseval.completed_normally = false;
        fake_parseval.exact_cartesian_complete = true;
        fake_parseval.no_state_pruning = true;
        fake_parseval.exact_integer_backend = true;
        fake_parseval.no_overflow = true;
        fake_parseval.completed_rounds = 1;
        fake_parseval.sum_squares = 4;
        fake_parseval.expected_sum_squares = 4;
        finalize_exact_dyadic_certification(fake_parseval);
        assert(fake_parseval.parseval_pass);
        assert(!fake_parseval.certified_exact_dyadic);
    }

    ExactDyadicOptions interrupted;
    interrupted.rounds = 2;
    interrupted.u = 0x00002000u;
    interrupted.backend = ExactNumericBackend::CppInt;
    interrupted.max_generated_transitions = 1;
    const auto failed = compute_exact_dyadic(interrupted);
    assert(!failed.completed_normally);
    assert(!failed.exact_cartesian_complete);
    assert(!failed.exact_integer_backend);
    assert(!failed.no_overflow);
    assert(!failed.all_rounds_completed);
    assert(failed.completed_rounds == 0);
    assert(!failed.certified_no_truncation);
    assert(!failed.certified_exact_dyadic);
    assert(!failed.failure_reason.empty());
    assert(failed.states.empty());

    ExactDyadicOptions cancelled;
    cancelled.rounds = 2;
    cancelled.u = 0x00002000u;
    cancelled.backend = ExactNumericBackend::CppInt;
    bool stop = false;
    cancelled.should_cancel = [&stop] {
        if (!stop) {
            stop = true;
            return false;
        }
        return true;
    };
    const auto cancelled_result = compute_exact_dyadic(cancelled);
    assert(!cancelled_result.completed_normally);
    assert(!cancelled_result.certified_no_truncation);
    assert(!cancelled_result.certified_exact_dyadic);

    ExactDyadicOptions limited_states;
    limited_states.rounds = 1;
    limited_states.u = 0x00000001u;
    limited_states.backend = ExactNumericBackend::CppInt;
    limited_states.max_states = 1;
    const auto limited = compute_exact_dyadic(limited_states);
    assert(!limited.completed_normally);
    assert(!limited.certified_no_truncation);
    assert(!limited.certified_exact_dyadic);

    ExactDyadicOptions overflow_run;
    overflow_run.rounds = 3;
    overflow_run.u = 0x00002000u;
    overflow_run.backend = ExactNumericBackend::Int128Checked;
    const auto overflow_result = compute_exact_dyadic(overflow_run);
    if (!overflow_result.completed_normally) {
        assert(!overflow_result.no_overflow);
        assert(!overflow_result.certified_exact_dyadic);
    }
}
