#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int H = 8, W = 14;
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count()
                  ^ (uint64_t)(uintptr_t(new int))
                  ^ (uint64_t)time(nullptr);
    delete (int*)0; // no-op trick to avoid unused new warning (won't execute)
    mt19937_64 rng(seed);
    uniform_int_distribution<int> dist(0, 9);

    for (int i = 0; i < H; ++i) {
        string row;
        row.reserve(W);
        for (int j = 0; j < W; ++j) {
            row.push_back(char('0' + dist(rng)));
        }
        cout << row << "\n";
    }
    return 0;
}