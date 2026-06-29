#include <algorithm>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

#include "cli_utils.hpp"
#include "exact.hpp"

using namespace hs;

namespace {
struct Args {
    int rounds = -1;
    std::string queries_path;
    std::optional<std::string> out_path;
    std::uint64_t start = 0;
    std::optional<std::uint64_t> end;
    std::optional<std::uint64_t> limit;
    std::size_t threads = 1;
};

std::string trim(std::string s) {
    const char* ws = " \t\r\n";
    const auto b = s.find_first_not_of(ws);
    if (b == std::string::npos) return "";
    const auto e = s.find_last_not_of(ws);
    return s.substr(b, e - b + 1);
}

std::vector<std::string> split_commas(const std::string& line) {
    std::vector<std::string> out;
    std::string cur;
    std::istringstream iss(line);
    while (std::getline(iss, cur, ',')) out.push_back(trim(cur));
    return out;
}

std::vector<std::string> split_ws(const std::string& line) {
    std::vector<std::string> out;
    std::istringstream iss(line);
    std::string cur;
    while (iss >> cur) out.push_back(cur);
    return out;
}

void usage(const char* prog) {
    std::cerr << "Usage: " << prog << " --r R --queries FILE [--threads N] [--out FILE]\n"
              << "       " << prog << " --r R --queries FILE --start A --end B --threads N\n\n"
              << "Query formats: CSV with u,v columns, CSV with r,u,v columns, or whitespace lines: r u v / u v.\n"
              << "Ranges are half-open [start,end). Without --start/--end this enumerates the full 2^32 domain.\n";
}

Args parse_args(int argc, char** argv) {
    Args args;
    for (int i = 1; i < argc; ++i) {
        const std::string opt = argv[i];
        if (opt == "--r") args.rounds = std::stoi(require_arg(i, argc, argv, opt));
        else if (opt == "--queries") args.queries_path = require_arg(i, argc, argv, opt);
        else if (opt == "--out") args.out_path = require_arg(i, argc, argv, opt);
        else if (opt == "--threads") args.threads = static_cast<std::size_t>(parse_u64(require_arg(i, argc, argv, opt)));
        else if (opt == "--start") args.start = parse_u64(require_arg(i, argc, argv, opt));
        else if (opt == "--end") args.end = parse_u64(require_arg(i, argc, argv, opt));
        else if (opt == "--limit") args.limit = parse_u64(require_arg(i, argc, argv, opt));
        else if (opt == "--help" || opt == "-h") { usage(argv[0]); std::exit(0); }
        else throw std::invalid_argument("unknown option: " + opt);
    }
    if (args.rounds < 0) throw std::invalid_argument("missing --r");
    if (args.queries_path.empty()) throw std::invalid_argument("missing --queries");
    if (args.end.has_value() && args.limit.has_value()) throw std::invalid_argument("--end and --limit are mutually exclusive");
    return args;
}

std::map<std::string, std::size_t> header_map(const std::vector<std::string>& fields) {
    std::map<std::string, std::size_t> out;
    for (std::size_t i = 0; i < fields.size(); ++i) out[fields[i]] = i;
    return out;
}

std::vector<ExactBatchQuery> read_queries(const Args& args) {
    std::ifstream fin(args.queries_path);
    if (!fin) throw std::runtime_error("cannot open queries file: " + args.queries_path);

    std::vector<ExactBatchQuery> queries;
    std::map<std::string, std::size_t> csv_header;
    std::string line;
    while (std::getline(fin, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#') continue;

        const bool csv = line.find(',') != std::string::npos;
        const auto fields = csv ? split_commas(line) : split_ws(line);
        if (fields.empty()) continue;

        if (csv && csv_header.empty() && (fields[0] == "r" || fields[0] == "u" || fields[0] == "v")) {
            csv_header = header_map(fields);
            if (csv_header.count("u") == 0 || csv_header.count("v") == 0) {
                throw std::runtime_error("CSV queries need u and v columns");
            }
            continue;
        }

        int rr = args.rounds;
        std::string us;
        std::string vs;
        if (csv && !csv_header.empty()) {
            us = fields.at(csv_header.at("u"));
            vs = fields.at(csv_header.at("v"));
            const auto rit = csv_header.find("r");
            if (rit != csv_header.end()) rr = std::stoi(fields.at(rit->second));
        } else if (fields.size() >= 3) {
            rr = std::stoi(fields[0]);
            us = fields[1];
            vs = fields[2];
        } else if (fields.size() == 2) {
            us = fields[0];
            vs = fields[1];
        } else {
            throw std::runtime_error("bad query line: " + line);
        }
        if (rr != args.rounds) throw std::runtime_error("query round does not match --r: " + line);
        queries.push_back({parse_mask(us), parse_mask(vs)});
    }
    return queries;
}

std::string status_name(const ExactResult& res) {
    return res.truncated ? "partial" : "exact";
}
}

int main(int argc, char** argv) {
    try {
        const Args args = parse_args(argc, argv);
        std::uint64_t end = args.end.value_or(kExactFullDomainSize);
        if (args.limit.has_value()) end = std::min(kExactFullDomainSize, args.start + *args.limit);
        const auto queries = read_queries(args);
        const auto results = compute_exact_batch(queries, args.rounds, args.start, end, args.threads);

        std::ofstream fout;
        std::ostream* out = &std::cout;
        if (args.out_path.has_value()) {
            fout.open(*args.out_path);
            if (!fout) throw std::runtime_error("cannot open output: " + *args.out_path);
            out = &fout;
        }

        *out << std::setprecision(24);
        *out << "r,u,v,numerator,denominator,VT,seconds,status\n";
        for (const auto& res : results) {
            *out << res.rounds << ',' << hex32(res.u) << ',' << hex32(res.v) << ','
                 << res.numerator << ',' << res.denominator << ',' << res.value << ','
                 << res.seconds << ',' << status_name(res) << '\n';
        }
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
