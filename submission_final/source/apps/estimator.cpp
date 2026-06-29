#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <optional>
#include <string>

#include "beam_search.hpp"
#include "cli_utils.hpp"

using namespace hs;

namespace {
void usage(const char* prog) {
    std::cerr << "Usage: " << prog << " --r R --u MASK [--v MASK] [options]\n"
              << "Options:\n"
              << "  --beam N       beam size (default 20000)\n"
              << "  --trans N      max S-layer transitions per beam state (default 256)\n"
              << "  --branch N     max candidates per active nibble, 0/all or 16/all (default 16)\n"
              << "  --top N        number of output masks to print when --v is absent (default 32)\n"
              << "  --mode aggregate|routes  aggregate by mask or keep individual route states (default aggregate)\n"
              << "  --trace        print top contributing route histories\n"
              << "  --trace-top N  number of trace routes to print (default 20)\n"
              << "  --csv          compact CSV-like output\n";
}
}

int main(int argc, char** argv) {
    try {
        int rounds = -1;
        Mask u = 0;
        bool have_u = false;
        std::optional<Mask> v;
        BeamParams params;
        bool csv = false;
        bool trace = false;
        std::size_t trace_top = 20;

        for (int i = 1; i < argc; ++i) {
            const std::string opt = argv[i];
            if (opt == "--r") rounds = std::stoi(require_arg(i, argc, argv, opt));
            else if (opt == "--u") { u = parse_mask(require_arg(i, argc, argv, opt)); have_u = true; }
            else if (opt == "--v") v = parse_mask(require_arg(i, argc, argv, opt));
            else if (opt == "--beam") params.beam_size = static_cast<std::size_t>(parse_u64(require_arg(i, argc, argv, opt)));
            else if (opt == "--trans") params.max_sbox_transitions_per_state = static_cast<std::size_t>(parse_u64(require_arg(i, argc, argv, opt)));
            else if (opt == "--branch") params.max_branch_per_nibble = static_cast<std::size_t>(parse_u64(require_arg(i, argc, argv, opt)));
            else if (opt == "--top") params.top_outputs = static_cast<std::size_t>(parse_u64(require_arg(i, argc, argv, opt)));
            else if (opt == "--trace") trace = true;
            else if (opt == "--trace-top") trace_top = static_cast<std::size_t>(parse_u64(require_arg(i, argc, argv, opt)));
            else if (opt == "--mode") {
                const std::string m = require_arg(i, argc, argv, opt);
                if (m == "aggregate") params.aggregate_by_mask = true;
                else if (m == "routes") params.aggregate_by_mask = false;
                else throw std::invalid_argument("unknown mode: " + m);
            } else if (opt == "--csv") csv = true;
            else if (opt == "--help" || opt == "-h") { usage(argv[0]); return 0; }
            else throw std::invalid_argument("unknown option: " + opt);
        }
        if (rounds < 0 || !have_u) { usage(argv[0]); return 2; }

        BeamSearch bs;
        const auto res = bs.estimate(rounds, u, v, params);

        std::cout << std::setprecision(24);
        if (csv) {
            if (v.has_value()) {
                std::cout << rounds << ',' << hex32(u) << ',' << hex32(*v) << ','
                          << static_cast<long double>(res.ve) << ','
                          << static_cast<long double>(score_of_estimate(rounds, res.ve)) << ','
                          << res.expanded_states << ',' << res.generated_transitions << '\n';
            } else {
                std::cout << "r,u,v,VE,proxy_score\n";
                for (const auto& it : res.top_outputs) {
                    std::cout << rounds << ',' << hex32(u) << ',' << hex32(it.mask) << ','
                              << it.value << ',' << score_of_estimate(rounds, it.value) << '\n';
                }
            }
            return 0;
        }

        std::cout << "Route-Shell estimator\n"
                  << "  r      = " << rounds << "\n"
                  << "  u      = " << hex32(u) << "\n";
        if (v.has_value()) {
            std::cout << "  v      = " << hex32(*v) << "\n"
                      << "  VE     = " << res.ve << "\n"
                      << "  score* = " << score_of_estimate(rounds, res.ve) << "\n";
        } else {
            std::cout << "  top output masks by |VE|:\n";
            for (const auto& it : res.top_outputs) {
                if (it.mask == 0 || it.value == 0.0L) continue;
                std::cout << "    " << hex32(it.mask)
                          << "  VE=" << it.value
                          << "  proxy_score=" << score_of_estimate(rounds, it.value) << "\n";
            }
        }
        std::cout << "  final_beam_size       = " << res.final_beam.size() << "\n"
                  << "  expanded_states       = " << res.expanded_states << "\n"
                  << "  generated_transitions = " << res.generated_transitions << "\n"
                  << "  certified_no_truncation = " << (res.certified_no_truncation ? "yes" : "no") << "\n";
        std::cout << "  round_stats:\n";
        for (const auto& st : res.round_stats) {
            std::cout << "    round=" << st.round
                      << " input_beam=" << st.input_beam_size
                      << " raw_next_terms=" << st.raw_next_terms
                      << " aggregated_masks=" << st.aggregated_masks
                      << " output_beam=" << st.output_beam_size
                      << " branch_truncated_states=" << st.branch_truncated_states
                      << " tuple_truncated_states=" << st.tuple_truncated_states
                      << " beam_pruned=" << (st.beam_pruned ? "yes" : "no")
                      << "\n";
        }
        if (trace) {
            const auto trace_res = bs.trace(rounds, u, v, params, trace_top);
            std::cout << "  route_trace:\n"
                      << "    kept_sum = " << trace_res.kept_sum << "\n"
                      << "    routes = " << trace_res.routes.size() << "\n";
            std::size_t idx = 0;
            for (const auto& route : trace_res.routes) {
                ++idx;
                std::cout << "    route " << idx << ": contribution=" << route.value << " masks=";
                for (std::size_t i = 0; i < route.masks.size(); ++i) {
                    if (i != 0) std::cout << " -> ";
                    std::cout << hex32(route.masks[i]);
                }
                std::cout << "\n";
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
