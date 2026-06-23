#include "exact_batch_variant_app.hpp"

int main(int argc, char** argv) {
    return hs::exact_batch_app::run(
        argc, argv, hs::ExactBatchVariant::Current, "current");
}
