#define main checker205_main
#include "../problems/205/chk.cc"
#undef main
#include <cassert>
#include <random>
#include <iostream>

int main() {
    disableFinalizeGuard();
    std::mt19937 random(205);
    long long comparisons = 0;
    for (int trial = 0; trial < 500; ++trial) {
        std::string original;
        for (int i = 0, n = 1 + random() % 30; i < n; ++i)
            original.insert(random() % (original.size() + 1), "()");
        ParenSequence fast(original);
        for (int step = 0; step < 300; ++step) {
            int type = 1 + random() % 6;
            int pos = int(random() % (original.size() + 3)) - 1;
            std::string expected = original, old_error, new_error;
            bool old_ok, new_ok;
            if (type <= 4) {
                old_ok = type == 1 ? tryOp1(expected, pos, old_error) :
                         type == 2 ? tryOp2(expected, pos, old_error) :
                         type == 3 ? tryOp3(expected, pos, old_error) : tryOp4(expected, pos, old_error);
                new_ok = fastTransform(fast, type, pos, new_error);
            } else if (type == 5) {
                old_ok = new_ok = pos >= 0 && pos <= int(original.size());
                if (old_ok) { expected.insert(pos, "()");fast.insertPair(pos); }
            } else {
                old_ok = new_ok = pos >= 0 && pos + 1 < int(original.size()) && original.substr(pos, 2) == "()";
                if (old_ok) { expected.erase(pos, 2);fast.erasePair(pos); }
            }
            assert(old_ok == new_ok);
            assert(fast.str() == expected);
            original = expected;
            for (int p = 0; p < int(original.size()); ++p) assert(fast.match(p) == findMatch(original, p));
            ++comparisons;
        }
    }
    std::string large;
    for (int i = 0; i < 100000; ++i) large += "()";
    ParenSequence fast(large);
    std::string error;
    for (int i = 0; i < 99998; ++i) assert(fastTransform(fast, 4, 0, error));
    auto result = fast.str();
    assert(result.size() == large.size() && isValid(result));
    std::cout << comparisons << " differential operations and n=100000 stress passed\n";
}
