#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <regex>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>

#include "beam_search.hpp"
#include "cli_utils.hpp"
#include "packing.hpp"

using namespace hs;

namespace {
std::string trim(std::string s) {
    const char* ws = " \t\r\n";
    const auto b = s.find_first_not_of(ws);
    if (b == std::string::npos) return "";
    const auto e = s.find_last_not_of(ws);
    return s.substr(b, e - b + 1);
}

std::vector<std::string> split_commas(const std::string& s) {
    std::vector<std::string> out;
    std::string cur;
    std::istringstream iss(s);
    while (std::getline(iss, cur, ',')) out.push_back(trim(cur));
    return out;
}

bool valid_interval(long double vt, long double ve) {
    if (vt == 0.0L || ve == 0.0L) return false;
    return std::abs(ve - vt) <= std::abs(vt) * 0.25L + 1e-30L;
}

enum class DedupMode {
    None,
    Ruv,
    Uv,
};

struct Args {
    std::string submit_path;
    DedupMode dedup = DedupMode::None;
    bool positive_only = false;
};

struct Row {
    int lineno = 0;
    int r = 0;
    Mask u = 0;
    Mask v = 0;
    long double vt = 0.0L;
    long double ve = 0.0L;
    long double score = 0.0L;
    bool valid = false;
    bool kept = false;
    std::string message;
};

void usage(const char* prog) {
    std::cerr << "Usage: " << prog << " [--dedup none|ruv|uv] [--positive-only] submit.txt\n";
}

DedupMode parse_dedup(const std::string& value) {
    if (value == "none") return DedupMode::None;
    if (value == "ruv") return DedupMode::Ruv;
    if (value == "uv") return DedupMode::Uv;
    throw std::invalid_argument("unknown dedup mode: " + value);
}

Args parse_args(int argc, char** argv) {
    Args args;
    for (int i = 1; i < argc; ++i) {
        const std::string opt = argv[i];
        if (opt == "--dedup") {
            args.dedup = parse_dedup(require_arg(i, argc, argv, opt));
        } else if (opt == "--positive-only") {
            args.positive_only = true;
        } else if (opt == "--help" || opt == "-h") {
            usage(argv[0]);
            std::exit(0);
        } else if (args.submit_path.empty()) {
            args.submit_path = opt;
        } else {
            throw std::invalid_argument("unexpected argument: " + opt);
        }
    }
    if (args.submit_path.empty()) throw std::invalid_argument("missing submit file");
    return args;
}

std::string dedup_key(const Row& row, DedupMode mode) {
    std::ostringstream oss;
    if (mode == DedupMode::Ruv) {
        oss << row.r << ':' << hex32(row.u) << ':' << hex32(row.v);
    } else if (mode == DedupMode::Uv) {
        oss << hex32(row.u) << ':' << hex32(row.v);
    }
    return oss.str();
}
}

int main(int argc, char** argv) {
    try {
        const Args args = parse_args(argc, argv);
        std::ifstream fin(args.submit_path);
        if (!fin) throw std::runtime_error("cannot open input file");
        std::cout << std::setprecision(24);
        std::string line;
        int lineno = 0;
        std::vector<Row> rows;
        while (std::getline(fin, line)) {
            ++lineno;
            Row row;
            row.lineno = lineno;
            line = trim(line);
            if (line.empty() || line[0] == '#') continue;
            if (line.rfind("@(", 0) != 0 || line.back() != ')') {
                row.message = "bad format";
                rows.push_back(row);
                continue;
            }
            const std::string inside = line.substr(2, line.size() - 3);
            const auto parts = split_commas(inside);
            if (parts.size() != 5) {
                row.message = "expected 5 fields";
                rows.push_back(row);
                continue;
            }
            row.r = std::stoi(parts[0]);
            row.u = parse_mask(parts[1]);
            row.v = parse_mask(parts[2]);
            row.vt = parse_ld(parts[3]);
            row.ve = parse_ld(parts[4]);
            row.valid = (row.u != 0 && row.v != 0 && valid_interval(row.vt, row.ve));
            row.score = row.valid ? score_of_estimate(row.r, row.ve) : 0.0L;
            if (args.positive_only && row.score <= 0.0L) row.valid = false;
            rows.push_back(row);
        }

        if (args.dedup == DedupMode::None) {
            for (auto& row : rows) row.kept = row.valid;
        } else {
            std::map<std::string, std::size_t> best;
            for (std::size_t i = 0; i < rows.size(); ++i) {
                if (!rows[i].valid) continue;
                const std::string key = dedup_key(rows[i], args.dedup);
                const auto it = best.find(key);
                if (it == best.end() || rows[i].score > rows[it->second].score) best[key] = i;
            }
            for (const auto& it : best) rows[it.second].kept = true;
        }

        long double total = 0.0L;
        int valid_count = 0;
        for (const Row& row : rows) {
            if (!row.message.empty()) {
                std::cout << "line " << row.lineno << ": " << row.message << "\n";
                continue;
            }
            if (row.kept) {
                total += row.score;
                ++valid_count;
            }
            std::cout << "line " << row.lineno
                      << " r=" << row.r
                      << " u=" << hex32(row.u)
                      << " v=" << hex32(row.v)
                      << " VT=" << row.vt
                      << " VE=" << row.ve
                      << " valid=" << (row.valid ? "yes" : "no")
                      << " kept=" << (row.kept ? "yes" : "no")
                      << " score=" << row.score << '\n';
        }
        std::cout << "valid_count=" << valid_count << "\n"
                  << "total_score=" << total << "\n";
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
