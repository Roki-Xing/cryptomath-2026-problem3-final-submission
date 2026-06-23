#pragma once

#include <algorithm>
#include <cctype>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "cli_utils.hpp"
#include "exact.hpp"

namespace hs::exact_batch_app {

struct Args {
    int rounds = -1;
    std::string queries_path;
    std::string query_sha256;
    std::optional<std::string> out_path;
    std::uint64_t start = 0;
    std::optional<std::uint64_t> end;
    std::size_t threads = 1;
};

inline std::string trim(std::string value) {
    const char* whitespace = " \t\r\n";
    const auto begin = value.find_first_not_of(whitespace);
    if (begin == std::string::npos) return "";
    const auto end = value.find_last_not_of(whitespace);
    return value.substr(begin, end - begin + 1);
}

inline std::vector<std::string> split_commas(const std::string& line) {
    std::vector<std::string> fields;
    std::istringstream input(line);
    std::string field;
    while (std::getline(input, field, ',')) fields.push_back(trim(field));
    return fields;
}

inline bool valid_sha256(const std::string& value) {
    return value.size() == 64 &&
           std::all_of(value.begin(), value.end(), [](unsigned char ch) {
               return std::isxdigit(ch) != 0 && !std::isupper(ch);
           });
}

inline void usage(const char* program) {
    std::cerr << "Usage: " << program
              << " --r R --queries FILE --query-sha256 HEX"
              << " --start A --end B [--threads N] [--out FILE]\n";
}

inline Args parse_args(int argc, char** argv) {
    Args args;
    for (int i = 1; i < argc; ++i) {
        const std::string option = argv[i];
        if (option == "--r") args.rounds = std::stoi(require_arg(i, argc, argv, option));
        else if (option == "--queries") args.queries_path = require_arg(i, argc, argv, option);
        else if (option == "--query-sha256") args.query_sha256 = require_arg(i, argc, argv, option);
        else if (option == "--out") args.out_path = require_arg(i, argc, argv, option);
        else if (option == "--threads") {
            args.threads = static_cast<std::size_t>(
                parse_u64(require_arg(i, argc, argv, option)));
        } else if (option == "--start") {
            args.start = parse_u64(require_arg(i, argc, argv, option));
        } else if (option == "--end") {
            args.end = parse_u64(require_arg(i, argc, argv, option));
        } else if (option == "--help" || option == "-h") {
            usage(argv[0]);
            std::exit(0);
        } else {
            throw std::invalid_argument("unknown option: " + option);
        }
    }
    if (args.rounds < 0) throw std::invalid_argument("missing --r");
    if (args.queries_path.empty()) throw std::invalid_argument("missing --queries");
    if (!valid_sha256(args.query_sha256)) {
        throw std::invalid_argument("--query-sha256 must be 64 lowercase hexadecimal characters");
    }
    if (!args.end.has_value()) throw std::invalid_argument("missing --end");
    return args;
}

inline std::vector<ExactBatchQuery> read_queries(const Args& args) {
    std::ifstream input(args.queries_path);
    if (!input) throw std::runtime_error("cannot open queries file: " + args.queries_path);

    std::vector<ExactBatchQuery> queries;
    std::map<std::string, std::size_t> header;
    std::string line;
    while (std::getline(input, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#') continue;
        const auto fields = split_commas(line);
        if (header.empty()) {
            for (std::size_t i = 0; i < fields.size(); ++i) header[fields[i]] = i;
            if (header.count("r") == 0 || header.count("u") == 0 || header.count("v") == 0) {
                throw std::runtime_error("CSV queries need r,u,v columns");
            }
            continue;
        }
        const int row_rounds = std::stoi(fields.at(header.at("r")));
        if (row_rounds != args.rounds) {
            throw std::runtime_error("query round does not match --r: " + line);
        }
        queries.push_back({
            parse_mask(fields.at(header.at("u"))),
            parse_mask(fields.at(header.at("v"))),
        });
    }
    if (queries.empty()) throw std::runtime_error("query file contains no rows");
    return queries;
}

inline int run(int argc,
               char** argv,
               ExactBatchVariant variant,
               const std::string& implementation) {
    try {
        const Args args = parse_args(argc, argv);
        const auto queries = read_queries(args);
        ExactBatchMetrics metrics;
        const auto results = compute_exact_batch_variant(
            queries, args.rounds, args.start, *args.end, args.threads, variant, &metrics);

        std::ofstream file;
        std::ostream* output = &std::cout;
        if (args.out_path.has_value()) {
            file.open(*args.out_path);
            if (!file) throw std::runtime_error("cannot open output: " + *args.out_path);
            output = &file;
        }

        *output << "# schema=way1-exact-shard-v1\n";
        *output << "# implementation=" << implementation << '\n';
        *output << "# query_sha256=" << args.query_sha256 << '\n';
        *output << "# range_start=" << args.start << '\n';
        *output << "# range_end=" << *args.end << '\n';
        *output << "# plaintext_count=" << metrics.plaintext_count << '\n';
        *output << "# permutation_evaluations=" << metrics.permutation_evaluations << '\n';
        *output << "# u_parity_evaluations=" << metrics.u_parity_evaluations << '\n';
        *output << "# v_parity_evaluations=" << metrics.v_parity_evaluations << '\n';
        *output << "# logical_query_updates=" << metrics.logical_query_updates << '\n';
        *output << "# unique_u=" << metrics.unique_u << '\n';
        *output << "# unique_v=" << metrics.unique_v << '\n';
        *output << "# threads=" << args.threads << '\n';
        *output << "r,u,v,numerator,denominator\n";
        for (const auto& result : results) {
            *output << result.rounds << ',' << hex32(result.u) << ',' << hex32(result.v)
                    << ',' << result.numerator << ',' << result.denominator << '\n';
        }
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
    return 0;
}

} // namespace hs::exact_batch_app
