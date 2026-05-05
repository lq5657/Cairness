#include "cc_spec_sample/math.hpp"

#include <stdexcept>

namespace cc_spec_sample {

int add(int left, int right) {
    return left + right;
}

int divide(int numerator, int denominator) {
    if (denominator == 0) {
        throw std::invalid_argument("denominator is required");
    }
    return numerator / denominator;
}

}  // namespace cc_spec_sample
