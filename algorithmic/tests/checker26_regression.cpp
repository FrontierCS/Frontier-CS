// Compile with g++ -std=gnu++17 -O2 -Ialgorithmic/judge/include
// algorithmic/tests/checker26_regression.cpp -o /tmp/checker26-test
#define main checker_main
#include "../problems/26/chk.cc"
#undef main
#include <cassert>
#include <chrono>

int main(int argc, char** argv) {
    registerGen(argc, argv, 1);
    mt19937 random(20261015);
    for (int trial = 0; trial < 3000; ++trial) {
        int size = 1 + random() % 50;
        vector<int> original(size);
        iota(original.begin(), original.end(), 1);
        shuffle(original.begin(), original.end(), random);
        auto expected = original;
        vector<pair<int, int>> moves;
        long long cost = 0;
        if (trial % 2) {
            for (int i = 0; i < size; ++i) {
                int x = find(expected.begin(), expected.end(), i + 1) - expected.begin();
                moves.emplace_back(x + 1, i + 1);
                expected.erase(expected.begin() + x);
                expected.insert(expected.begin() + i, i + 1);
                cost += i + 1;
            }
        } else {
            for (int j = 0; j < 100; ++j) {
                int x = random() % size, y = random() % size;
                moves.emplace_back(x + 1, y + 1);
                int value = expected[x];
                expected.erase(expected.begin() + x);
                expected.insert(expected.begin() + y, value);
                cost += y + 1;
            }
        }
        long long actual;
        assert(validateMoves(original, moves, actual) == is_sorted(expected.begin(), expected.end()));
        assert(actual == cost);
        assert(!validateMoves(original, {{0, 1}}, actual));
        assert(!validateMoves(original, {{1, size + 1}}, actual));
    }
    // Repeated long-distance moves: quadratic with vector erase/insert.
    vector<int> original(300000);
    iota(original.begin(), original.end(), 1);
    vector<pair<int, int>> moves;
    for (int i = 0; i < 75000; ++i) {
        moves.emplace_back(1, 300000);
        moves.emplace_back(300000, 1);
    }
    long long actual;
    auto start = chrono::steady_clock::now();
    assert(validateMoves(original, moves, actual));
    assert(actual == 75000LL * 300001);
    cout << "3000 differential cases and n=300000, m=150000 passed; large case seconds="
         << chrono::duration<double>(chrono::steady_clock::now() - start).count() << '\n';
}
