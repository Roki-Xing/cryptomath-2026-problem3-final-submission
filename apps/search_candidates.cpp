#include <algorithm>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <optional>
#include <sstream>
#include <string>
#include <vector>

#include "beam_search.hpp"
#include "cli_utils.hpp"
#include "exact.hpp"
#include "packing.hpp"

using namespace hs;

namespace {
struct Args {
    int r_start = 1;
    int r_end = 4;
    int max_active = 1;
    std::size_t max_u = 200;
    std::size_t top_v = 8;
    std::string out = "candidates.csv";
    bool verify_exact = false;
    bool one_round_fast_vt = false;
    std::optional<std::uint64_t> exact_limit;
    BeamParams params;
};

void usage(const char* prog) {
    std::cerr << "Usage: " << prog << " [options]\n"
              << "Options:\n"
              << "  --r-start R --r-end R      round range (default 1..4)\n"
              << "  --max-active A             max active nibbles in generated u (default 1)\n"
              << "  --max-u N                  cap number of u masks (default 200)\n"
              << "  --top-v N                  keep N endpoint masks per u (default 8)\n"
              << "  --out FILE                 output CSV (default candidates.csv)\n"
              << "  --verify-exact             compute VT by 2^32 oracle; very slow\n"
              << "  --exact-limit N            debug-only truncated oracle limit\n"
              << "  --one-round-fast-vt        for r=1 only, compute VT from the exact one-round matrix formula\n"
              << "  --beam N --trans N --branch N  estimator parameters\n";
}

void gen_masks_rec(int pos, int remaining, Mask cur, const std::vector<Nibble>& vals,
                   std::vector<Mask>& out) {
    if (remaining == 0) {
        if (cur != 0) out.push_back(cur);
        return;
    }
    if (pos >= 8) return;
    // skip this position
    gen_masks_rec(pos + 1, remaining, cur, vals, out);
    // activate this position
    for (Nibble v : vals) {
        gen_masks_rec(pos + 1, remaining - 1, set_nibble(cur, pos, v), vals, out);
    }
}

std::vector<Mask> generate_u_masks(int max_active, std::size_t limit) {
    std::vector<Nibble> vals;
    for (int hw = 1; hw <= 4; ++hw) {
        for (int x = 1; x < 16; ++x) {
            if (__builtin_popcount(static_cast<unsigned>(x)) == hw) vals.push_back(static_cast<Nibble>(x));
        }
    }
    std::vector<Mask> out;
    for (int a = 1; a <= max_active; ++a) gen_masks_rec(0, a, 0, vals, out);
    std::sort(out.begin(), out.end(), [](Mask x, Mask y) {
        if (active_nibbles(x) != active_nibbles(y)) return active_nibbles(x) < active_nibbles(y);
        if (__builtin_popcount(x) != __builtin_popcount(y)) return __builtin_popcount(x) < __builtin_popcount(y);
        return x < y;
    });
    out.erase(std::unique(out.begin(), out.end()), out.end());
    if (out.size() > limit) out.resize(limit);
    return out;
}

bool valid_estimate(long double vt, long double ve) {
    return ve != 0.0L && std::abs(ve - vt) <= std::abs(vt) * 0.25L + 1e-30L;
}
}

int main(int argc, char** argv) {
    try {
        Args args;
        args.params.top_outputs = args.top_v;
        for (int i = 1; i < argc; ++i) {
            const std::string opt = argv[i];
            if (opt == "--r-start") args.r_start = std::stoi(require_arg(i, argc, argv, opt));
            else if (opt == "--r-end") args.r_end = std::stoi(require_arg(i, argc, argv, opt));
            else if (opt == "--max-active") args.max_active = std::stoi(require_arg(i, argc, argv, opt));
            else if (opt == "--max-u") args.max_u = static_cast<std::size_t>(parse_u64(require_arg(i, argc, argv, opt)));
            else if (opt == "--top-v") { args.top_v = static_cast<std::size_t>(parse_u64(require_arg(i, argc, argv, opt))); args.params.top_outputs = args.top_v; }
            else if (opt == "--out") args.out = require_arg(i, argc, argv, opt);
            else if (opt == "--verify-exact") args.verify_exact = true;
            else if (opt == "--exact-limit") args.exact_limit = parse_u64(require_arg(i, argc, argv, opt));
            else if (opt == "--one-round-fast-vt") args.one_round_fast_vt = true;
            else if (opt == "--beam") args.params.beam_size = static_cast<std::size_t>(parse_u64(require_arg(i, argc, argv, opt)));
            else if (opt == "--trans") args.params.max_sbox_transitions_per_state = static_cast<std::size_t>(parse_u64(require_arg(i, argc, argv, opt)));
            else if (opt == "--branch") args.params.max_branch_per_nibble = static_cast<std::size_t>(parse_u64(require_arg(i, argc, argv, opt)));
            else if (opt == "--mode") {
                const std::string m = require_arg(i, argc, argv, opt);
                if (m == "aggregate") args.params.aggregate_by_mask = true;
                else if (m == "routes") args.params.aggregate_by_mask = false;
                else throw std::invalid_argument("unknown mode: " + m);
            } else if (opt == "--help" || opt == "-h") { usage(argv[0]); return 0; }
            else throw std::invalid_argument("unknown option: " + opt);
        }
        if (args.r_start < 1 || args.r_end < args.r_start) throw std::invalid_argument("bad round range");

        const auto us = generate_u_masks(args.max_active, args.max_u);
        BeamSearch bs;
        std::ofstream fout(args.out);
        if (!fout) throw std::runtime_error("cannot open output: " + args.out);
        fout << std::setprecision(24);
        fout << "r,u,v,VE,proxy_score,VT,valid,score,status\n";

        for (int r = args.r_start; r <= args.r_end; ++r) {
            for (Mask u : us) {
                auto res = bs.estimate(r, u, std::nullopt, args.params);
                std::size_t emitted = 0;
                for (const auto& it : res.top_outputs) {
                    if (emitted >= args.top_v) break;
                    if (it.mask == 0 || it.value == 0.0L) continue;
                    ++emitted;
                    long double vt = 0.0L;
                    bool have_vt = false;
                    std::string status = "unverified";
                    if (args.verify_exact) {
                        const auto ex = compute_exact_correlation(u, it.mask, r, args.exact_limit);
                        vt = ex.value;
                        have_vt = true;
                        status = ex.truncated ? "truncated_oracle" : "exact_oracle";
                    } else if (args.one_round_fast_vt && r == 1) {
                        vt = one_round_exact_from_corr(u, it.mask, bs.corr());
                        have_vt = true;
                        status = "one_round_matrix_exact";
                    }
                    const bool ok = have_vt && u != 0 && it.mask != 0 && valid_estimate(vt, it.value);
                    const long double sc = ok ? score_of_estimate(r, it.value) : 0.0L;
                    fout << r << ',' << hex32(u) << ',' << hex32(it.mask) << ',' << it.value << ','
                         << score_of_estimate(r, it.value) << ',';
                    if (have_vt) fout << vt << ',' << (ok ? 1 : 0) << ',' << sc << ',' << status << '\n';
                    else fout << ",0,0," << status << '\n';
                }
            }
        }

        std::cerr << "wrote research candidate CSV " << args.out
                  << "; this tool never emits or modifies submit.txt\n";
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
