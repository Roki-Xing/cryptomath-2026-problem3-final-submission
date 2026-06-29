#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

#include "cli_utils.hpp"
#include "exact.hpp"

using namespace hs;

namespace {
struct Args {
    std::optional<std::string> out_path;
    bool require_full = false;
    std::vector<std::string> inputs;
};

struct Accum {
    int r = 0;
    Mask u = 0;
    Mask v = 0;
    std::int64_t numerator = 0;
    std::uint64_t denominator = 0;
    double seconds = 0.0;
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

void usage(const char* prog) {
    std::cerr << "Usage: " << prog << " [--out FILE] [--require-full] part1.csv [part2.csv ...]\n";
}

Args parse_args(int argc, char** argv) {
    Args args;
    for (int i = 1; i < argc; ++i) {
        const std::string opt = argv[i];
        if (opt == "--out") args.out_path = require_arg(i, argc, argv, opt);
        else if (opt == "--require-full") args.require_full = true;
        else if (opt == "--help" || opt == "-h") { usage(argv[0]); std::exit(0); }
        else args.inputs.push_back(opt);
    }
    if (args.inputs.empty()) throw std::invalid_argument("missing input CSV files");
    return args;
}

void add_file(const std::string& path, std::map<std::tuple<int, Mask, Mask>, Accum>& rows) {
    std::ifstream fin(path);
    if (!fin) throw std::runtime_error("cannot open input: " + path);

    std::string line;
    while (std::getline(fin, line)) {
        line = trim(line);
        if (line.empty() || line[0] == '#') continue;
        if (line.rfind("r,u,v,", 0) == 0) continue;
        const auto fields = split_commas(line);
        if (fields.size() < 8) throw std::runtime_error("bad exact part row in " + path + ": " + line);

        const int r = std::stoi(fields[0]);
        const Mask u = parse_mask(fields[1]);
        const Mask v = parse_mask(fields[2]);
        const std::int64_t numerator = std::stoll(fields[3]);
        const std::uint64_t denominator = parse_u64(fields[4]);
        const double seconds = std::stod(fields[6]);

        const auto key = std::make_tuple(r, u, v);
        auto& acc = rows[key];
        if (acc.denominator == 0) {
            acc.r = r;
            acc.u = u;
            acc.v = v;
        }
        acc.numerator += numerator;
        acc.denominator += denominator;
        acc.seconds += seconds;
        if (acc.denominator > kExactFullDomainSize) {
            throw std::runtime_error("combined denominator exceeds 2^32 for " + hex32(u) + "," + hex32(v));
        }
    }
}

std::string status_name(const Accum& row) {
    return row.denominator == kExactFullDomainSize ? "exact" : "partial";
}
}

int main(int argc, char** argv) {
    try {
        const Args args = parse_args(argc, argv);
        std::map<std::tuple<int, Mask, Mask>, Accum> rows;
        for (const auto& path : args.inputs) add_file(path, rows);

        std::ofstream fout;
        std::ostream* out = &std::cout;
        if (args.out_path.has_value()) {
            fout.open(*args.out_path);
            if (!fout) throw std::runtime_error("cannot open output: " + *args.out_path);
            out = &fout;
        }

        *out << std::setprecision(24);
        *out << "r,u,v,numerator,denominator,VT,seconds,status\n";
        for (const auto& item : rows) {
            const auto& row = item.second;
            if (args.require_full && row.denominator != kExactFullDomainSize) {
                throw std::runtime_error("incomplete exact coverage for " + hex32(row.u) + "," + hex32(row.v));
            }
            const long double value =
                static_cast<long double>(row.numerator) / static_cast<long double>(row.denominator);
            *out << row.r << ',' << hex32(row.u) << ',' << hex32(row.v) << ','
                 << row.numerator << ',' << row.denominator << ',' << value << ','
                 << row.seconds << ',' << status_name(row) << '\n';
        }
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
