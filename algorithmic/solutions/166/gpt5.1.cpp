#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<vector<long long>> h(N, vector<long long>(N));
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            cin >> h[i][j];

    vector<string> ops;
    int r = 0, c = 0;

    auto moveTo = [&](int tr, int tc) {
        while (r < tr) { ops.emplace_back("D"); ++r; }
        while (r > tr) { ops.emplace_back("U"); --r; }
        while (c < tc) { ops.emplace_back("R"); ++c; }
        while (c > tc) { ops.emplace_back("L"); --c; }
    };

    // Phase 1: gather soil from positive cells to (0,0)
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (i == 0 && j == 0) continue;
            long long val = h[i][j];
            if (val > 0) {
                moveTo(i, j);
                ops.emplace_back("+" + to_string(val));
                h[i][j] -= val; // becomes 0
                moveTo(0, 0);
                ops.emplace_back("-" + to_string(val));
                h[0][0] += val;
            }
        }
    }

    // Phase 2: distribute soil from (0,0) to negative cells
    r = 0; c = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (i == 0 && j == 0) continue;
            long long val = h[i][j];
            if (val < 0) {
                long long D = -val;
                moveTo(0, 0); // ensure at origin
                ops.emplace_back("+" + to_string(D));
                h[0][0] -= D;
                moveTo(i, j);
                ops.emplace_back("-" + to_string(D));
                h[i][j] += D; // becomes 0
                moveTo(0, 0);
            }
        }
    }

    for (const auto &s : ops) {
        cout << s << '\n';
    }
    return 0;
}