#include "cc_spec_sample/math.hpp"

#include <stdexcept>

int main() {
    if (cc_spec_sample::add(2, 3) != 5) {
        return 1;
    }

    try {
        (void)cc_spec_sample::divide(4, 0);
        return 1;
    } catch (const std::invalid_argument&) {
    }

    return cc_spec_sample::divide(8, 2) == 4 ? 0 : 1;
}
