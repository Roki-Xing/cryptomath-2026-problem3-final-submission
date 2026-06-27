#include "exact_dyadic.hpp"

#include <algorithm>
#include <limits>
#include <stdexcept>
#include <type_traits>
#include <unordered_map>
#include <utility>
#include <vector>

#include "exact_cartesian.hpp"
#include "linear_layer.hpp"
#include "sbox_corr.hpp"

namespace hs {
namespace {

using Int128 = __int128_t;

cpp_int int128_to_cpp_int(Int128 value) {
    const bool negative = value < 0;
    const __uint128_t magnitude =
        negative ? static_cast<__uint128_t>(-(value + 1)) + 1 : static_cast<__uint128_t>(value);
    cpp_int out = static_cast<std::uint64_t>(magnitude >> 64);
    out <<= 64;
    out += static_cast<std::uint64_t>(magnitude);
    return negative ? -out : out;
}

template <typename Number>
using StateMap = std::unordered_map<Mask, Number>;

template <typename Number>
std::vector<std::pair<Mask, Number>> sorted_states(const StateMap<Number>& states) {
    std::vector<std::pair<Mask, Number>> ordered(states.begin(), states.end());
    std::sort(ordered.begin(), ordered.end(),
              [](const auto& lhs, const auto& rhs) { return lhs.first < rhs.first; });
    return ordered;
}

void fail(ExactDyadicResult& result, const std::string& reason) {
    result.failure_reason = reason;
    result.completed_normally = false;
    result.exact_cartesian_complete = false;
    result.no_state_pruning = false;
    result.exact_integer_backend = false;
    result.no_overflow = false;
    result.all_rounds_completed = false;
    result.states.clear();
    result.sum_squares = 0;
    result.expected_sum_squares = 0;
    result.completed_rounds = 0;
    finalize_exact_dyadic_certification(result);
}

bool checked_mul(Int128 lhs, int rhs, Int128& product) {
    return !__builtin_mul_overflow(lhs, static_cast<Int128>(rhs), &product);
}

bool checked_add(Int128 lhs, Int128 rhs, Int128& sum) {
    return !__builtin_add_overflow(lhs, rhs, &sum);
}

template <typename Number, typename Multiply, typename Add>
ExactDyadicResult run_backend(const ExactDyadicOptions& options,
                             const ExactBranchTable& branches,
                             bool exact_integer_backend,
                             Multiply multiply,
                             Add add) {
    ExactDyadicResult result;
    result.rounds = options.rounds;
    result.u = options.u;
    result.denominator_exp2 = 16 * options.rounds;
    result.no_state_pruning = true;
    result.exact_integer_backend = exact_integer_backend;
    result.no_overflow = true;

    StateMap<Number> current;
    current.emplace(options.u, Number(1));

    for (int round = 0; round < options.rounds; ++round) {
        if (options.should_cancel && options.should_cancel()) {
            fail(result, "execution cancelled");
            return result;
        }
        result.expanded_states += current.size();
        StateMap<Number> next;

        for (const auto& [mask, numerator] : sorted_states(current)) {
            bool arithmetic_ok = true;
            bool resource_ok = true;
            bool cancelled = false;
            const auto stats = enumerate_exact_cartesian(
                mask, branches, [&](Mask after_sbox, int q_product) {
                    if (options.should_cancel && options.should_cancel()) {
                        cancelled = true;
                        return false;
                    }
                    if (options.max_generated_transitions != 0 &&
                        result.generated_transitions >= options.max_generated_transitions) {
                        resource_ok = false;
                        return false;
                    }

                    Number contribution{};
                    if (!multiply(numerator, q_product, contribution)) {
                        arithmetic_ok = false;
                        return false;
                    }
                    const Mask successor = round_linear_inv_transpose_after_sc(after_sbox);
                    auto existing = next.find(successor);
                    if (existing == next.end()) {
                        if (contribution != 0) next.emplace(successor, contribution);
                    } else {
                        Number sum{};
                        if (!add(existing->second, contribution, sum)) {
                            arithmetic_ok = false;
                            return false;
                        }
                        if (sum == 0) {
                            next.erase(existing);
                        } else {
                            existing->second = sum;
                        }
                    }
                    ++result.generated_transitions;
                    if (options.max_states != 0 && next.size() > options.max_states) {
                        resource_ok = false;
                        return false;
                    }
                    return true;
                });

            if (!stats.complete) {
                if (!arithmetic_ok) {
                    result.no_overflow = false;
                    fail(result, "checked integer arithmetic overflow");
                } else if (cancelled) {
                    fail(result, "execution cancelled");
                } else if (!resource_ok) {
                    fail(result, "configured resource limit exceeded");
                } else {
                    fail(result, "exact Cartesian product incomplete");
                }
                return result;
            }
        }
        result.completed_rounds = round + 1;
        current = std::move(next);
    }

    result.all_rounds_completed = result.completed_rounds == options.rounds;

    for (const auto& [mask, value] : sorted_states(current)) {
        if constexpr (std::is_same_v<Number, cpp_int>) {
            result.states.emplace(mask, value);
        } else {
            result.states.emplace(mask, int128_to_cpp_int(value));
        }
    }
    for (const auto& [mask, value] : result.states) {
        (void)mask;
        result.sum_squares += value * value;
    }
    result.expected_sum_squares = 1;
    result.expected_sum_squares <<= 32 * options.rounds;
    result.completed_normally = true;
    result.exact_cartesian_complete = true;
    finalize_exact_dyadic_certification(result);
    if (!result.parseval_pass) result.failure_reason = "Parseval invariant failed";
    return result;
}

} // namespace

void exact_accumulate(std::map<Mask, cpp_int>& accumulator, Mask mask, const cpp_int& delta) {
    if (delta == 0) return;
    auto it = accumulator.find(mask);
    if (it == accumulator.end()) {
        accumulator.emplace(mask, delta);
        return;
    }
    it->second += delta;
    if (it->second == 0) accumulator.erase(it);
}

void finalize_exact_dyadic_certification(ExactDyadicResult& result) {
    result.all_rounds_completed = result.completed_rounds == result.rounds;
    result.certified_no_truncation =
        result.exact_cartesian_complete && result.no_state_pruning && result.all_rounds_completed;
    result.certified_exact_dyadic =
        result.completed_normally && result.exact_cartesian_complete && result.no_state_pruning &&
        result.exact_integer_backend && result.no_overflow && result.all_rounds_completed;
    result.parseval_pass = result.sum_squares == result.expected_sum_squares;
}

ExactDyadicResult compute_exact_dyadic(const ExactDyadicOptions& options) {
    ExactDyadicResult rejected;
    rejected.rounds = options.rounds;
    rejected.u = options.u;
    rejected.denominator_exp2 = 16 * options.rounds;
    if (options.rounds < 1 || options.rounds > 3) {
        fail(rejected, "exact dyadic backend supports frozen rounds 1 through 3");
        return rejected;
    }

    const SboxCorr corr;
    const ExactBranchTable branches = build_exact_branch_table(corr);
    const auto validation = validate_exact_branch_table(branches, corr);
    if (!validation.complete) {
        fail(rejected, validation.error);
        return rejected;
    }

    if (options.backend == ExactNumericBackend::CppInt) {
        return run_backend<cpp_int>(
            options, branches, true,
            [](const cpp_int& lhs, int rhs, cpp_int& product) {
                product = lhs * rhs;
                return true;
            },
            [](const cpp_int& lhs, const cpp_int& rhs, cpp_int& sum) {
                sum = lhs + rhs;
                return true;
            });
    }

    return run_backend<Int128>(
        options, branches, true,
        [](Int128 lhs, int rhs, Int128& product) { return checked_mul(lhs, rhs, product); },
        [](Int128 lhs, Int128 rhs, Int128& sum) { return checked_add(lhs, rhs, sum); });
}

cpp_int to_way1_numerator(const cpp_int& dyadic_numerator, int rounds) {
    if (rounds < 1) throw std::invalid_argument("rounds must be positive");
    const int exponent = 32 - 16 * rounds;
    if (exponent >= 0) {
        cpp_int scaled = dyadic_numerator;
        scaled <<= exponent;
        return scaled;
    }

    cpp_int divisor = 1;
    divisor <<= -exponent;
    if (dyadic_numerator % divisor != 0) {
        throw std::runtime_error("dyadic numerator is not divisible into way-1 normalization");
    }
    return dyadic_numerator / divisor;
}

std::string exact_numeric_backend_name(ExactNumericBackend backend) {
    return backend == ExactNumericBackend::CppInt ? "cpp_int" : "int128_checked";
}

} // namespace hs
