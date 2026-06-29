#include <fstream>
#include <iomanip>
#include <iostream>
#include <optional>
#include <sstream>
#include <string>

#include "cli_utils.hpp"
#include "exact.hpp"

using namespace hs;

namespace {
void usage(const char* prog) {
    std::cerr << "Usage: " << prog << " --r R --u MASK --v MASK [--limit N]\n"
              << "       " << prog << " --batch queries.txt [--limit N]\n\n"
              << "Batch file format: one query per line: r u v\n"
              << "WARNING: without --limit this performs 2^32 plaintext evaluations per query.\n";
}

void print_result(const ExactResult& res) {
    std::cout << std::setprecision(24)
              << res.rounds << ',' << hex32(res.u) << ',' << hex32(res.v) << ','
              << res.numerator << ',' << res.denominator << ',' << res.value << ','
              << res.seconds << ',' << (res.truncated ? "truncated" : "exact") << '\n';
}
}

int main(int argc, char** argv) {
    try {
        int rounds = -1;
        Mask u = 0, v = 0;
        bool have_u = false, have_v = false;
        std::optional<std::string> batch;
        std::optional<std::uint64_t> limit;

        for (int i = 1; i < argc; ++i) {
            const std::string opt = argv[i];
            if (opt == "--r") rounds = std::stoi(require_arg(i, argc, argv, opt));
            else if (opt == "--u") { u = parse_mask(require_arg(i, argc, argv, opt)); have_u = true; }
            else if (opt == "--v") { v = parse_mask(require_arg(i, argc, argv, opt)); have_v = true; }
            else if (opt == "--batch") batch = require_arg(i, argc, argv, opt);
            else if (opt == "--limit") limit = parse_u64(require_arg(i, argc, argv, opt));
            else if (opt == "--help" || opt == "-h") { usage(argv[0]); return 0; }
            else throw std::invalid_argument("unknown option: " + opt);
        }

        std::cout << "r,u,v,numerator,denominator,VT,seconds,status\n";
        if (batch.has_value()) {
            std::ifstream fin(*batch);
            if (!fin) throw std::runtime_error("cannot open batch file: " + *batch);
            std::string line;
            while (std::getline(fin, line)) {
                if (line.empty() || line[0] == '#') continue;
                std::istringstream iss(line);
                std::string us, vs;
                int rr;
                if (!(iss >> rr >> us >> vs)) throw std::runtime_error("bad batch line: " + line);
                print_result(compute_exact_correlation(parse_mask(us), parse_mask(vs), rr, limit));
            }
        } else {
            if (rounds < 0 || !have_u || !have_v) { usage(argv[0]); return 2; }
            print_result(compute_exact_correlation(u, v, rounds, limit));
        }
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
