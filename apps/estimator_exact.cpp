#include <atomic>
#include <cctype>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include <unistd.h>

#include "cli_utils.hpp"
#include "exact_dyadic.hpp"
#include "packing.hpp"

using namespace hs;

namespace {

std::atomic<bool> interrupted{false};
constexpr const char* kCurrentRepository = "Roki-Xing/cryptomath-2026-problem3-final-submission";

void on_signal(int) {
    interrupted.store(true);
}

std::string trim(std::string value) {
    while (!value.empty() && (value.back() == '\n' || value.back() == '\r' || value.back() == ' ')) {
        value.pop_back();
    }
    std::size_t offset = 0;
    while (offset < value.size() && (value[offset] == ' ' || value[offset] == '\t')) {
        ++offset;
    }
    if (offset != 0) value.erase(0, offset);
    return value;
}

std::string normalize_key(std::string key) {
    std::string normalized;
    for (char ch : key) {
        if (std::isalnum(static_cast<unsigned char>(ch))) {
            normalized.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(ch))));
        } else if (!normalized.empty() && normalized.back() != '_') {
            normalized.push_back('_');
        }
    }
    while (!normalized.empty() && normalized.back() == '_') normalized.pop_back();
    return normalized;
}

bool valid_commit_hash(const std::string& commit) {
    if (commit.size() != 40 && commit.size() != 64) return false;
    for (char ch : commit) {
        if (!std::isxdigit(static_cast<unsigned char>(ch))) return false;
    }
    return true;
}

std::string read_command(const char* command) {
    std::string output;
    FILE* pipe = popen(command, "r");
    if (pipe == nullptr) return output;
    char buffer[256];
    while (fgets(buffer, sizeof(buffer), pipe) != nullptr) output += buffer;
    if (pclose(pipe) != 0) return "";
    return trim(output);
}

std::string sha256_text(const std::string& text) {
    char path[] = "/tmp/estimator_exact_sha256_XXXXXX";
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

    const std::string command = std::string("sha256sum ") + path;
    const std::string output = read_command(command.c_str());
    std::remove(path);
    if (output.size() < 64) throw std::runtime_error("sha256sum did not return a digest");
    return output.substr(0, 64);
}

std::optional<std::string> package_source_commit(const std::string& path) {
    std::ifstream input(path);
    if (!input) return std::nullopt;

    std::string repository;
    std::string release_commit;
    std::string source_commit_field;
    std::string pending_key;
    std::string line;
    while (std::getline(input, line)) {
        line = trim(line);
        if (line.empty()) {
            pending_key.clear();
            continue;
        }

        const std::size_t colon = line.find(':');
        if (colon != std::string::npos) {
            pending_key = normalize_key(line.substr(0, colon));
            const std::string value = trim(line.substr(colon + 1));
            if (pending_key == "repository") repository = value;
            else if (pending_key == "release_commit") release_commit = value;
            else if (pending_key == "source_commit") source_commit_field = value;
            if (!value.empty()) pending_key.clear();
            continue;
        }

        if (pending_key == "repository") repository = line;
        else if (pending_key == "release_commit") release_commit = line;
        else if (pending_key == "source_commit") source_commit_field = line;
        pending_key.clear();
    }

    if (!repository.empty() && repository != kCurrentRepository &&
        repository != std::string("https://github.com/") + kCurrentRepository) {
        return std::nullopt;
    }

    if (valid_commit_hash(release_commit)) return release_commit;
    if (valid_commit_hash(source_commit_field)) return source_commit_field;
    return std::nullopt;
}

std::string source_commit() {
#ifdef HS_SOURCE_COMMIT
    const std::string build_time_commit = trim(HS_SOURCE_COMMIT);
    if (valid_commit_hash(build_time_commit)) return build_time_commit;
    throw std::runtime_error("invalid build-time HS_SOURCE_COMMIT");
#endif
    std::string commit = read_command("git rev-parse HEAD 2>/dev/null");
    if (valid_commit_hash(commit)) return commit;
    const auto package_commit = package_source_commit("PACKAGE_SOURCE_COMMIT.txt");
    if (package_commit.has_value()) return *package_commit;
    return "";
}

std::string bool_json(bool value) {
    return value ? "true" : "false";
}

std::string make_artifact(std::uint64_t row_id,
                          Mask v,
                          ExactNumericBackend backend,
                          const ExactDyadicResult& result,
                          const std::string& commit,
                          const std::string& input_sha,
                          const std::string& command_sha) {
    const auto state = result.states.find(v);
    const cpp_int numerator = state == result.states.end() ? cpp_int(0) : state->second;
    std::ostringstream output;
    output << "{\n"
           << "  \"row_id\": " << row_id << ",\n"
           << "  \"r\": " << result.rounds << ",\n"
           << "  \"u\": \"" << hex32(result.u) << "\",\n"
           << "  \"v\": \"" << hex32(v) << "\",\n"
           << "  \"numerator\": \"" << numerator << "\",\n"
           << "  \"denominator_exp2\": " << result.denominator_exp2 << ",\n"
           << "  \"value_fraction\": \"" << numerator << "/2^" << result.denominator_exp2
           << "\",\n"
           << "  \"numeric_backend\": \"" << exact_numeric_backend_name(backend) << "\",\n"
           << "  \"exact_cartesian_complete\": " << bool_json(result.exact_cartesian_complete)
           << ",\n"
           << "  \"no_state_pruning\": " << bool_json(result.no_state_pruning) << ",\n"
           << "  \"certified_no_truncation\": "
           << bool_json(result.certified_no_truncation) << ",\n"
           << "  \"certified_exact_dyadic\": "
           << bool_json(result.certified_exact_dyadic) << ",\n"
           << "  \"parseval_pass\": " << bool_json(result.parseval_pass) << ",\n"
           << "  \"state_count\": " << result.states.size() << ",\n"
           << "  \"sum_squares\": \"" << result.sum_squares << "\",\n"
           << "  \"expected_sum_squares\": \"" << result.expected_sum_squares << "\",\n"
           << "  \"expanded_states\": " << result.expanded_states << ",\n"
           << "  \"generated_transitions\": " << result.generated_transitions << ",\n"
           << "  \"source_commit\": \"" << commit << "\",\n"
           << "  \"input_sha256\": \"" << input_sha << "\",\n"
           << "  \"command_sha256\": \"" << command_sha << "\"\n"
           << "}\n";
    return output.str();
}

void write_atomic(const std::string& path, const std::string& content) {
    const std::string temporary = path + ".tmp." + std::to_string(getpid());
    {
        std::ofstream output(temporary, std::ios::binary);
        if (!output) throw std::runtime_error("cannot open temporary artifact: " + temporary);
        output << content;
        output.flush();
        if (!output) {
            output.close();
            std::remove(temporary.c_str());
            throw std::runtime_error("cannot serialize complete artifact");
        }
    }
    if (std::rename(temporary.c_str(), path.c_str()) != 0) {
        std::remove(temporary.c_str());
        throw std::runtime_error("cannot atomically publish artifact: " + path);
    }
}

void usage(const char* program) {
    std::cerr << "Usage: " << program
              << " --r R --u MASK --v MASK [--backend cpp_int|int128]"
                 " [--row-id N] [--max-states N] [--max-transitions N] [--out FILE]\n";
}

} // namespace

int main(int argc, char** argv) {
    try {
        std::signal(SIGINT, on_signal);
        std::signal(SIGTERM, on_signal);

        ExactDyadicOptions options;
        Mask v = 0;
        bool have_rounds = false;
        bool have_u = false;
        bool have_v = false;
        std::uint64_t row_id = 1;
        std::optional<std::string> out_path;

        std::string command_material;
        for (int i = 0; i < argc; ++i) {
            if (i != 0) command_material.push_back('\0');
            command_material += argv[i];
        }

        for (int i = 1; i < argc; ++i) {
            const std::string option = argv[i];
            if (option == "--r") {
                options.rounds = std::stoi(require_arg(i, argc, argv, option));
                have_rounds = true;
            } else if (option == "--u") {
                options.u = parse_mask(require_arg(i, argc, argv, option));
                have_u = true;
            } else if (option == "--v") {
                v = parse_mask(require_arg(i, argc, argv, option));
                have_v = true;
            } else if (option == "--backend") {
                const std::string backend = require_arg(i, argc, argv, option);
                if (backend == "cpp_int") options.backend = ExactNumericBackend::CppInt;
                else if (backend == "int128") options.backend = ExactNumericBackend::Int128Checked;
                else throw std::invalid_argument("unknown exact backend: " + backend);
            } else if (option == "--row-id") {
                row_id = parse_u64(require_arg(i, argc, argv, option));
            } else if (option == "--max-states") {
                options.max_states = parse_u64(require_arg(i, argc, argv, option));
            } else if (option == "--max-transitions") {
                options.max_generated_transitions = parse_u64(require_arg(i, argc, argv, option));
            } else if (option == "--out") {
                out_path = require_arg(i, argc, argv, option);
            } else if (option == "--help" || option == "-h") {
                usage(argv[0]);
                return 0;
            } else {
                throw std::invalid_argument("unknown option: " + option);
            }
        }

        if (!have_rounds || !have_u || !have_v) {
            usage(argv[0]);
            return 2;
        }

        options.should_cancel = [] { return interrupted.load(); };
        const std::string commit = source_commit();
        if (commit.empty()) throw std::runtime_error("source commit is unavailable");
        const std::string input_material =
            "r=" + std::to_string(options.rounds) + "\nu=" + hex32(options.u) +
            "\nv=" + hex32(v) + "\nbackend=" + exact_numeric_backend_name(options.backend) + "\n";
        const auto result = compute_exact_dyadic(options);
        if (!result.certified_exact_dyadic || !result.parseval_pass) {
            throw std::runtime_error("exact run rejected: " + result.failure_reason);
        }

        const std::string artifact =
            make_artifact(row_id, v, options.backend, result, commit, sha256_text(input_material),
                          sha256_text(command_material));
        if (out_path.has_value()) {
            write_atomic(*out_path, artifact);
        } else {
            std::cout << artifact;
        }
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
