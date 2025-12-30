#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<vector<int>> h(N, vector<int>(N));
    long long posSum = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> h[i][j];
            if (h[i][j] > 0) posSum += h[i][j];
        }
    }

    // Build serpentine route from (0,0) to (N-1,N-1)
    vector<pair<int,int>> route;
    route.reserve(N*N);
    for (int i = 0; i < N; ++i) {
        if (i % 2 == 0) {
            for (int j = 0; j < N; ++j) route.emplace_back(i, j);
        } else {
            for (int j = N-1; j >= 0; --j) route.emplace_back(i, j);
        }
    }

    vector<string> ops;
    ops.reserve(2000);

    auto moveTo = [&](int r1, int c1, int r2, int c2) {
        // vertical moves
        while (r1 < r2) { ops.emplace_back("D"); ++r1; }
        while (r1 > r2) { ops.emplace_back("U"); --r1; }
        // horizontal moves
        while (c1 < c2) { ops.emplace_back("R"); ++c1; }
        while (c1 > c2) { ops.emplace_back("L"); --c1; }
        return pair<int,int>(r2, c2);
    };

    int r = 0, c = 0;
    long long load = 0;

    // First pass: collect all positives
    for (int k = 0; k < (int)route.size(); ++k) {
        auto [i, j] = route[k];
        if (k == 0) {
            r = i; c = j;
        } else {
            auto p = moveTo(r, c, i, j);
            r = p.first; c = p.second;
        }
        if (h[i][j] > 0) {
            ops.emplace_back("+" + to_string(h[i][j]));
            load += h[i][j];
        }
    }

    // Second pass: deliver to negatives (reverse route)
    for (int k = (int)route.size() - 1; k >= 0; --k) {
        auto [i, j] = route[k];
        if (k == (int)route.size() - 1) {
            // already at (r,c)
        } else {
            auto p = moveTo(r, c, i, j);
            r = p.first; c = p.second;
        }
        if (h[i][j] < 0) {
            int d = -h[i][j];
            if (d > 0) {
                ops.emplace_back("-" + to_string(d));
                load -= d; // load should never go negative
            }
        }
    }

    // Output operations
    for (const auto &s : ops) cout << s << '\n';
    return 0;
}