#pragma once

#include <cstdint>
#include <functional>
#include <map>
#include <string>

#include <boost/multiprecision/cpp_int.hpp>

#include "packing.hpp"

namespace hs {

using boost::multiprecision::cpp_int;

enum class ExactNumericBackend {
    CppInt,
    Int128Checked,
};

struct ExactDyadicOptions {
    int rounds = 0;
    Mask u = 0;
    ExactNumericBackend backend = ExactNumericBackend::CppInt;
    std::uint64_t max_states = 0;
    std::uint64_t max_generated_transitions = 0;
    std::function<bool()> should_cancel;
};

struct ExactDyadicResult {
    int rounds = 0;
    Mask u = 0;
    int denominator_exp2 = 0;
    std::map<Mask, cpp_int> states;
    cpp_int sum_squares = 0;
    cpp_int expected_sum_squares = 0;
    std::uint64_t expanded_states = 0;
    std::uint64_t generated_transitions = 0;
    bool completed_normally = false;
    bool exact_cartesian_complete = false;
    bool no_state_pruning = false;
    bool exact_integer_backend = false;
    bool no_overflow = false;
    bool all_rounds_completed = false;
    int completed_rounds = 0;
    bool certified_no_truncation = false;
    bool certified_exact_dyadic = false;
    bool parseval_pass = false;
    std::string failure_reason;
};

void exact_accumulate(std::map<Mask, cpp_int>& accumulator, Mask mask, const cpp_int& delta);
void finalize_exact_dyadic_certification(ExactDyadicResult& result);
ExactDyadicResult compute_exact_dyadic(const ExactDyadicOptions& options);
cpp_int to_way1_numerator(const cpp_int& dyadic_numerator, int rounds);
std::string exact_numeric_backend_name(ExactNumericBackend backend);

} // namespace hs
