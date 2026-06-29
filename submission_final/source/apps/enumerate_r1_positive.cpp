#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <optional>
#include <string>

#include "cli_utils.hpp"
#include "linear_layer.hpp"
#include "packing.hpp"
#include "sbox_corr.hpp"

using namespace hs;

namespace {
struct Args {
    std::optional<std::string> out_path;
};

void usage(const char* prog) {
    std::cerr << "Usage: " << prog << " [--out PATH]\n"
              << "Enumerate all r=1 positive-score rows with |VE|=|VT|=0.5.\n";
}

Args parse_args(int argc, char** argv) {
    Args args;
    for (int i = 1; i < argc; ++i) {
        const std::string opt = argv[i];
        if (opt == "--out") {
            args.out_path = require_arg(i, argc, argv, opt);
        } else if (opt == "--help" || opt == "-h") {
            usage(argv[0]);
            std::exit(0);
        } else {
            throw std::invalid_argument("unknown option: " + opt);
        }
    }
    return args;
}

void write_value(std::ostream& out, int numerator) {
    if (numerator == 8) out << "0.5";
    else if (numerator == -8) out << "-0.5";
    else throw std::logic_error("unexpected numerator for positive r=1 row");
}
} // namespace

int main(int argc, char** argv) {
    try {
        const Args args = parse_args(argc, argv);
        std::ofstream fout;
        std::ostream* out = &std::cout;
        if (args.out_path.has_value()) {
            fout.open(*args.out_path);
            if (!fout) throw std::runtime_error("cannot open output file: " + *args.out_path);
            out = &fout;
        }

        SboxCorr corr;
        int rows = 0;
        for (int pos = 0; pos < 8; ++pos) {
            for (Nibble a = 1; a < 16; ++a) {
                for (Nibble b = 1; b < 16; ++b) {
                    const int num = corr.numerator(b, a);
                    if (num != 8 && num != -8) continue;
                    const Mask u = set_nibble(0, pos, a);
                    const Mask after_sc = set_nibble(0, pos, b);
                    const Mask v = round_linear_inv_transpose_after_sc(after_sc);
                    if (v == 0) continue;
                    *out << "@(1, " << hex32(u) << ", " << hex32(v) << ", ";
                    write_value(*out, num);
                    *out << ", ";
                    write_value(*out, num);
                    *out << ")\n";
                    ++rows;
                }
            }
        }
        if (!args.out_path.has_value()) {
            std::cerr << "rows=" << rows << "\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
