#include <chrono>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/resource.h>
#include <unistd.h>
#include <vector>

#include "cli_utils.hpp"
#include "exact_dyadic.hpp"
#include "packing.hpp"

using namespace hs;

namespace {

struct QueryRow {
    std::string row_id;
    int rounds = 0;
    Mask u = 0;
    Mask v = 0;
};

std::string trim(std::string value) {
    while (!value.empty() &&
           (value.back() == '\n' || value.back() == '\r' || value.back() == ' ' ||
            value.back() == '\t')) {
        value.pop_back();
    }
    std::size_t offset = 0;
    while (offset < value.size() && (value[offset] == ' ' || value[offset] == '\t')) ++offset;
    if (offset != 0) value.erase(0, offset);
    return value;
}

std::string read_command(const std::string& command) {
    std::string output;
    FILE* pipe = popen(command.c_str(), "r");
    if (pipe == nullptr) return output;
    char buffer[256];
    while (fgets(buffer, sizeof(buffer), pipe) != nullptr) output += buffer;
    if (pclose(pipe) != 0) return "";
    return trim(output);
}

bool valid_commit_hash(const std::string& commit) {
    if (commit.size() != 40 && commit.size() != 64) return false;
    for (char ch : commit) {
        if (!std::isxdigit(static_cast<unsigned char>(ch))) return false;
    }
    return true;
}

std::string source_commit() {
#ifdef HS_SOURCE_COMMIT
    const std::string macro = trim(HS_SOURCE_COMMIT);
    if (!valid_commit_hash(macro)) throw std::runtime_error("invalid build-time HS_SOURCE_COMMIT");
    return macro;
#else
    const std::string commit = read_command("git rev-parse HEAD 2>/dev/null");
    if (!valid_commit_hash(commit)) throw std::runtime_error("cannot resolve source commit");
    return commit;
#endif
}

std::string sha256_text(const std::string& text) {
    char path[] = "/tmp/recompute_frozen_exact_sha256_XXXXXX";
    const int fd = mkstemp(path);
    if (fd < 0) throw std::runtime_error("cannot create SHA-256 temporary file");
    std::size_t offset = 0;
    while (offset < text.size()) {
        const ssize_t written = write(fd, text.data() + offset, text.size() - offset);
        if (written <= 0) {
            close(fd);
            std::remove(path);
            throw std::runtime_error("cannot write SHA-256 temporary file");
        }
        offset += static_cast<std::size_t>(written);
    }
    close(fd);
    const std::string output = read_command(std::string("sha256sum ") + path);
    std::remove(path);
    if (output.size() < 64) throw std::runtime_error("sha256sum did not return a digest");
    return output.substr(0, 64);
}

std::string sha256_file(const std::string& path) {
    const std::string output = read_command(std::string("sha256sum ") + path);
    if (output.size() < 64) throw std::runtime_error("sha256sum did not return a digest");
    return output.substr(0, 64);
}

std::string json_escape(const std::string& input) {
    std::ostringstream out;
    for (char ch : input) {
        switch (ch) {
        case '\\':
            out << "\\\\";
            break;
        case '"':
            out << "\\\"";
            break;
        case '\n':
            out << "\\n";
            break;
        case '\r':
            out << "\\r";
            break;
        case '\t':
            out << "\\t";
            break;
        default:
            out << ch;
            break;
        }
    }
    return out.str();
}

std::string now_utc() {
    const auto now = std::chrono::system_clock::now();
    const std::time_t current = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};
    gmtime_r(&current, &tm);
    std::ostringstream out;
    out << std::put_time(&tm, "%Y-%m-%dT%H:%M:%SZ");
    return out.str();
}

std::uint64_t peak_rss_bytes() {
    rusage usage{};
    getrusage(RUSAGE_SELF, &usage);
#if defined(__APPLE__)
    return static_cast<std::uint64_t>(usage.ru_maxrss);
#else
    return static_cast<std::uint64_t>(usage.ru_maxrss) * 1024ull;
#endif
}

std::vector<QueryRow> load_queries(const std::string& path, int rounds, Mask u) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("cannot open queries CSV");
    std::string line;
    if (!std::getline(input, line)) throw std::runtime_error("queries CSV is empty");
    std::vector<std::string> header;
    {
        std::stringstream parser(line);
        std::string cell;
        while (std::getline(parser, cell, ',')) header.push_back(trim(cell));
    }
    int row_index = 0;
    int r_pos = -1;
    int u_pos = -1;
    int v_pos = -1;
    int row_id_pos = -1;
    for (int index = 0; index < static_cast<int>(header.size()); ++index) {
        if (header[index] == "r") r_pos = index;
        if (header[index] == "u") u_pos = index;
        if (header[index] == "v") v_pos = index;
        if (header[index] == "row_id") row_id_pos = index;
    }
    if (r_pos < 0 || u_pos < 0 || v_pos < 0) throw std::runtime_error("queries CSV missing r/u/v");

    std::vector<QueryRow> rows;
    while (std::getline(input, line)) {
        ++row_index;
        std::stringstream parser(line);
        std::vector<std::string> cells;
        std::string cell;
        while (std::getline(parser, cell, ',')) cells.push_back(trim(cell));
        if (static_cast<int>(cells.size()) <= std::max(r_pos, std::max(u_pos, v_pos))) {
            throw std::runtime_error("queries CSV row has too few columns");
        }
        const int row_rounds = std::stoi(cells[r_pos]);
        const Mask row_u = parse_mask(cells[u_pos]);
        if (row_rounds != rounds || row_u != u) continue;
        QueryRow row;
        row.row_id = row_id_pos >= 0 && row_id_pos < static_cast<int>(cells.size()) && !cells[row_id_pos].empty()
                         ? cells[row_id_pos]
                         : "FQ" + [&]() {
                               std::ostringstream out;
                               out << std::setw(6) << std::setfill('0') << row_index;
                               return out.str();
                           }();
        row.rounds = row_rounds;
        row.u = row_u;
        row.v = parse_mask(cells[v_pos]);
        rows.push_back(row);
    }
    if (rows.empty()) throw std::runtime_error("queries CSV has no frozen endpoints for requested (r,u)");
    return rows;
}

void write_atomic(const std::string& path, const std::string& content) {
    const std::string temporary = path + ".tmp." + std::to_string(getpid());
    {
        std::ofstream output(temporary, std::ios::binary);
        if (!output) throw std::runtime_error("cannot open temporary output: " + temporary);
        output << content;
        output.flush();
        if (!output) {
            output.close();
            std::remove(temporary.c_str());
            throw std::runtime_error("cannot serialize temporary output");
        }
    }
    if (std::rename(temporary.c_str(), path.c_str()) != 0) {
        std::remove(temporary.c_str());
        throw std::runtime_error("cannot atomically publish output: " + path);
    }
}

std::string canonical_digest(const std::map<Mask, cpp_int>& states) {
    std::ostringstream payload;
    for (const auto& [mask, numerator] : states) {
        payload << hex32(mask) << '\t' << numerator << '\n';
    }
    return sha256_text(payload.str());
}

std::string make_endpoints_csv(const std::vector<QueryRow>& rows, const ExactDyadicResult& result) {
    std::ostringstream out;
    out << "row_id,r,u,v,numerator,denominator_exp2,exact_fraction,way1_normalized_numerator\n";
    for (const auto& row : rows) {
        const auto state = result.states.find(row.v);
        const cpp_int numerator = state == result.states.end() ? cpp_int(0) : state->second;
        out << row.row_id << ',' << row.rounds << ',' << hex32(row.u) << ',' << hex32(row.v) << ','
            << numerator << ',' << result.denominator_exp2 << ",\"" << numerator << "/2^"
            << result.denominator_exp2 << "\",\"" << to_way1_numerator(numerator, row.rounds)
            << "\"\n";
    }
    return out.str();
}

std::string make_column_json(const ExactDyadicResult& result,
                             ExactNumericBackend backend,
                             const std::vector<QueryRow>& rows,
                             const std::string& commit,
                             const std::string& binary_sha,
                             const std::string& input_sha,
                             const std::string& command_sha,
                             const std::string& endpoints_sha,
                             const std::string& canonical_column_digest,
                             const std::string& start_utc,
                             const std::string& end_utc,
                             double wall_seconds,
                             std::uint64_t peak_rss) {
    std::ostringstream out;
    out << "{\n"
        << "  \"r\": " << result.rounds << ",\n"
        << "  \"u\": \"" << hex32(result.u) << "\",\n"
        << "  \"backend\": \"" << exact_numeric_backend_name(backend) << "\",\n"
        << "  \"source_commit\": \"" << commit << "\",\n"
        << "  \"binary_sha256\": \"" << binary_sha << "\",\n"
        << "  \"input_sha256\": \"" << input_sha << "\",\n"
        << "  \"command_sha256\": \"" << command_sha << "\",\n"
        << "  \"start_utc\": \"" << start_utc << "\",\n"
        << "  \"end_utc\": \"" << end_utc << "\",\n"
        << "  \"wall_seconds\": " << wall_seconds << ",\n"
        << "  \"peak_rss_bytes\": " << peak_rss << ",\n"
        << "  \"completed_normally\": " << (result.completed_normally ? "true" : "false") << ",\n"
        << "  \"exact_cartesian_complete\": " << (result.exact_cartesian_complete ? "true" : "false")
        << ",\n"
        << "  \"no_state_pruning\": " << (result.no_state_pruning ? "true" : "false") << ",\n"
        << "  \"exact_integer_backend\": " << (result.exact_integer_backend ? "true" : "false")
        << ",\n"
        << "  \"no_overflow\": " << (result.no_overflow ? "true" : "false") << ",\n"
        << "  \"all_rounds_completed\": " << (result.all_rounds_completed ? "true" : "false")
        << ",\n"
        << "  \"completed_rounds\": " << result.completed_rounds << ",\n"
        << "  \"certified_no_truncation\": " << (result.certified_no_truncation ? "true" : "false")
        << ",\n"
        << "  \"certified_exact_dyadic\": " << (result.certified_exact_dyadic ? "true" : "false")
        << ",\n"
        << "  \"parseval_pass\": " << (result.parseval_pass ? "true" : "false") << ",\n"
        << "  \"state_count\": " << result.states.size() << ",\n"
        << "  \"canonical_column_digest\": \"" << canonical_column_digest << "\",\n"
        << "  \"numerator_denominator_convention\": \"N[v]/2^(16r)\",\n"
        << "  \"generated_transitions\": " << result.generated_transitions << ",\n"
        << "  \"expanded_states\": " << result.expanded_states << ",\n"
        << "  \"sum_squares\": \"" << result.sum_squares << "\",\n"
        << "  \"expected_sum_squares\": \"" << result.expected_sum_squares << "\",\n"
        << "  \"frozen_endpoint_count\": " << rows.size() << ",\n"
        << "  \"endpoints_sha256\": \"" << endpoints_sha << "\",\n"
        << "  \"failure_reason\": \"" << json_escape(result.failure_reason) << "\"\n"
        << "}\n";
    return out.str();
}

void usage(const char* program) {
    std::cerr << "Usage: " << program
              << " --r R --u MASK --queries FILE --backend cpp_int|int128_checked"
                 " --out-column FILE --out-endpoints FILE [--max-states N] [--max-transitions N]\n";
}

} // namespace

int main(int argc, char** argv) {
    try {
        ExactDyadicOptions options;
        std::string queries_path;
        std::string out_column;
        std::string out_endpoints;
        bool have_rounds = false;
        bool have_u = false;
        std::string command_material;
        for (int index = 0; index < argc; ++index) {
            if (index != 0) command_material.push_back('\0');
            command_material += argv[index];
        }

        for (int index = 1; index < argc; ++index) {
            const std::string option = argv[index];
            if (option == "--r") {
                options.rounds = std::stoi(require_arg(index, argc, argv, option));
                have_rounds = true;
            } else if (option == "--u") {
                options.u = parse_mask(require_arg(index, argc, argv, option));
                have_u = true;
            } else if (option == "--queries") {
                queries_path = require_arg(index, argc, argv, option);
            } else if (option == "--backend") {
                const std::string backend = require_arg(index, argc, argv, option);
                if (backend == "cpp_int") options.backend = ExactNumericBackend::CppInt;
                else if (backend == "int128" || backend == "int128_checked")
                    options.backend = ExactNumericBackend::Int128Checked;
                else throw std::invalid_argument("unknown backend: " + backend);
            } else if (option == "--out-column") {
                out_column = require_arg(index, argc, argv, option);
            } else if (option == "--out-endpoints") {
                out_endpoints = require_arg(index, argc, argv, option);
            } else if (option == "--max-states") {
                options.max_states = parse_u64(require_arg(index, argc, argv, option));
            } else if (option == "--max-transitions") {
                options.max_generated_transitions = parse_u64(require_arg(index, argc, argv, option));
            } else if (option == "--help" || option == "-h") {
                usage(argv[0]);
                return 0;
            } else {
                throw std::invalid_argument("unknown option: " + option);
            }
        }

        if (!have_rounds || !have_u || queries_path.empty() || out_column.empty() ||
            out_endpoints.empty()) {
            usage(argv[0]);
            return 2;
        }

        const auto queries = load_queries(queries_path, options.rounds, options.u);
        const std::string commit = source_commit();
        const std::string binary_sha = sha256_file(argv[0]);
        std::ostringstream input_material;
        for (const auto& row : queries) {
            input_material << row.row_id << '\n' << row.rounds << '\n' << hex32(row.u) << '\n'
                           << hex32(row.v) << '\n';
        }
        const std::string start_utc = now_utc();
        const auto started = std::chrono::steady_clock::now();
        const auto result = compute_exact_dyadic(options);
        const auto finished = std::chrono::steady_clock::now();
        const std::string end_utc = now_utc();
        if (!result.certified_exact_dyadic || !result.parseval_pass) {
            throw std::runtime_error("exact run rejected: " + result.failure_reason);
        }
        const std::string endpoints = make_endpoints_csv(queries, result);
        const std::string endpoints_sha = sha256_text(endpoints);
        const std::string digest = canonical_digest(result.states);
        const double wall_seconds =
            std::chrono::duration<double>(finished - started).count();
        const std::string column = make_column_json(
            result, options.backend, queries, commit, binary_sha, sha256_text(input_material.str()),
            sha256_text(command_material), endpoints_sha, digest, start_utc, end_utc, wall_seconds,
            peak_rss_bytes());
        write_atomic(out_endpoints, endpoints);
        write_atomic(out_column, column);
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
