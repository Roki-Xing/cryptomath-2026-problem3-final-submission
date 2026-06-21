#include <algorithm>
#include <cmath>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <cctype>
#include <string>
#include <vector>

#include "beam_search.hpp"
#include "cli_utils.hpp"
#include "packing.hpp"

using namespace hs;

namespace {
struct Args {
    int r_start = 1;
	    int r_end = 4;
	    int max_active = 1;
	    std::size_t max_u = 200;
	    std::string u_list;
	    std::size_t u_offset = 0;
	    std::size_t u_count = std::numeric_limits<std::size_t>::max();
	    std::size_t top_v = 8;
    bool emit_all = false;
    long double min_proxy_score = -std::numeric_limits<long double>::infinity();
    bool require_certified = false;
    std::string out = "candidates_approx.csv";
    BeamParams params;
};

void usage(const char* prog) {
    std::cerr << "Usage: " << prog << " [options]\n"
              << "Options:\n"
	              << "  --r-start R --r-end R      round range (default 1..4)\n"
	              << "  --max-active A             max active nibbles in generated u (default 1)\n"
	              << "  --max-u N                  cap number of u masks (default 200)\n"
	              << "  --u-list FILE              read u masks from file (one per line) instead of generating low-active masks\n"
	              << "  --u-offset N               skip N generated u masks after sorting (default 0)\n"
	              << "  --u-count N                process at most N u masks after offset (default all)\n"
	              << "  --top-v N                  keep N endpoint masks per u (default 8)\n"
              << "  --emit-all                 emit every final-beam endpoint instead of only top-v\n"
              << "  --min-proxy-score X        strict lower bound for emitted proxy score\n"
              << "  --require-certified        emit rows only when the estimator reports no truncation\n"
              << "  --out FILE                 output CSV (default candidates_approx.csv)\n"
              << "  --beam N --trans N --branch N  estimator parameters\n"
              << "  --mode aggregate|routes    estimator mode\n";
}

void gen_masks_rec(int pos, int remaining, Mask cur, const std::vector<Nibble>& vals,
                   std::vector<Mask>& out) {
    if (remaining == 0) {
        if (cur != 0) out.push_back(cur);
        return;
    }
    if (pos >= 8) return;
    gen_masks_rec(pos + 1, remaining, cur, vals, out);
    for (Nibble v : vals) gen_masks_rec(pos + 1, remaining - 1, set_nibble(cur, pos, v), vals, out);
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

std::string trim_copy(std::string s) {
    auto is_ws = [](unsigned char c) { return std::isspace(c) != 0; };
    while (!s.empty() && is_ws(static_cast<unsigned char>(s.front()))) s.erase(s.begin());
    while (!s.empty() && is_ws(static_cast<unsigned char>(s.back()))) s.pop_back();
    return s;
}

std::vector<Mask> load_u_list(const std::string& path) {
    std::ifstream fin(path);
    if (!fin) throw std::runtime_error("cannot open --u-list file: " + path);
    std::vector<Mask> out;
    std::string line;
    while (std::getline(fin, line)) {
        const auto hash = line.find('#');
        if (hash != std::string::npos) line = line.substr(0, hash);
        line = trim_copy(line);
        if (line.empty()) continue;
        const Mask u = parse_mask(line);
        if (u != 0) out.push_back(u);
    }
    std::sort(out.begin(), out.end(), [](Mask x, Mask y) {
        if (active_nibbles(x) != active_nibbles(y)) return active_nibbles(x) < active_nibbles(y);
        if (__builtin_popcount(x) != __builtin_popcount(y)) return __builtin_popcount(x) < __builtin_popcount(y);
        return x < y;
    });
    out.erase(std::unique(out.begin(), out.end()), out.end());
    return out;
}

std::string mode_name(const BeamParams& params) {
    return params.aggregate_by_mask ? "aggregate" : "routes";
}

std::vector<BeamItem> sorted_final_beam(std::vector<BeamItem> items) {
    items.erase(std::remove_if(items.begin(), items.end(), [](const BeamItem& item) {
        return item.mask == 0 || item.value == 0.0L || !std::isfinite(static_cast<double>(item.value));
    }), items.end());
    std::sort(items.begin(), items.end(), [](const BeamItem& x, const BeamItem& y) {
        const long double ax = std::abs(x.value);
        const long double ay = std::abs(y.value);
        if (ax != ay) return ax > ay;
        return x.mask < y.mask;
    });
    return items;
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
	            else if (opt == "--u-list") args.u_list = require_arg(i, argc, argv, opt);
	            else if (opt == "--u-offset") args.u_offset = static_cast<std::size_t>(parse_u64(require_arg(i, argc, argv, opt)));
	            else if (opt == "--u-count") args.u_count = static_cast<std::size_t>(parse_u64(require_arg(i, argc, argv, opt)));
	            else if (opt == "--top-v") { args.top_v = static_cast<std::size_t>(parse_u64(require_arg(i, argc, argv, opt))); args.params.top_outputs = args.top_v; }
	            else if (opt == "--emit-all") args.emit_all = true;
            else if (opt == "--min-proxy-score") args.min_proxy_score = parse_ld(require_arg(i, argc, argv, opt));
            else if (opt == "--require-certified") args.require_certified = true;
            else if (opt == "--out") args.out = require_arg(i, argc, argv, opt);
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

	        auto all_us = args.u_list.empty() ? generate_u_masks(args.max_active, args.max_u) : load_u_list(args.u_list);
	        if (all_us.size() > args.max_u) all_us.resize(args.max_u);
	        if (args.u_offset > all_us.size()) throw std::invalid_argument("--u-offset exceeds generated u mask count");
	        const std::size_t remaining = all_us.size() - args.u_offset;
	        const std::size_t take = std::min(args.u_count, remaining);
        const std::vector<Mask> us(all_us.begin() + static_cast<std::ptrdiff_t>(args.u_offset),
                                   all_us.begin() + static_cast<std::ptrdiff_t>(args.u_offset + take));
        BeamSearch bs;
        std::ofstream fout(args.out);
        if (!fout) throw std::runtime_error("cannot open output: " + args.out);
        fout << std::setprecision(24);
        fout << "r,u,v,VE,proxy_score,beam,trans,branch,mode,expanded_states,generated_transitions,final_beam_size,certified_no_truncation\n";

        for (int r = args.r_start; r <= args.r_end; ++r) {
            std::size_t u_idx = 0;
            for (Mask u : us) {
                ++u_idx;
                const auto t0 = std::chrono::steady_clock::now();
                auto res = bs.estimate(r, u, std::nullopt, args.params);
                const auto t1 = std::chrono::steady_clock::now();
                const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(t1 - t0).count();

                std::cerr << "r=" << r
                          << " u=" << hex32(u)
                          << " (" << u_idx << "/" << us.size() << ")"
                          << " certified=" << (res.certified_no_truncation ? 1 : 0)
                          << " expanded_states=" << res.expanded_states
                          << " generated_transitions=" << res.generated_transitions
                          << " final_beam=" << res.final_beam.size()
                          << " ms=" << ms
                          << "\n";
                if (args.require_certified && !res.certified_no_truncation) continue;

                const auto endpoints = args.emit_all ? sorted_final_beam(res.final_beam) : res.top_outputs;
                for (const auto& it : endpoints) {
                    if (it.mask == 0 || it.value == 0.0L) continue;
                    const long double proxy_score = score_of_estimate(r, it.value);
                    if (!(proxy_score > args.min_proxy_score)) continue;
                    fout << r << ',' << hex32(u) << ',' << hex32(it.mask) << ',' << it.value << ','
                         << proxy_score << ','
                         << args.params.beam_size << ','
                         << args.params.max_sbox_transitions_per_state << ','
                         << args.params.max_branch_per_nibble << ','
                         << mode_name(args.params) << ','
                         << res.expanded_states << ','
                         << res.generated_transitions << ','
                         << res.final_beam.size() << ','
                         << (res.certified_no_truncation ? 1 : 0) << '\n';
                }
                // Persist partial results for long-running sweeps.
                fout.flush();
            }
        }

        std::cerr << "wrote " << args.out << " with way-2 candidates only\n";
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
