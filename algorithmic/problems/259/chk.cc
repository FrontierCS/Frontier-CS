// Simple exact-match checker for A+B problem
#include "testlib.h"
#include <string>

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // Read expected answer
    long long expected = ans.readLong();

    // Read participant answer
    long long actual = ouf.readLong();

    if (expected == actual) {
        quitf(_ok, "Correct: %lld", actual);
    } else {
        quitf(_wa, "Expected %lld, got %lld", expected, actual);
    }
}
