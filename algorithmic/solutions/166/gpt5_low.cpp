#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<vector<long long>> h(N, vector<long long>(N));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) cin >> h[i][j];
    }

    // Build serpentine path
    vector<pair<int,int>> path;
    path.reserve(N*N);
    for (int i = 0; i < N; ++i) {
        if (i % 2 == 0) {
            for (int j = 0; j < N; ++j) path.emplace_back(i, j);
        } else {
            for (int j = N - 1; j >= 0; --j) path.emplace_back(i, j);
        }
    }

    auto moveChar = [](pair<int,int> a, pair<int,int> b) -> char {
        if (b.first == a.first) {
            if (b.second == a.second + 1) return 'R';
            if (b.second == a.second - 1) return 'L';
        } else if (b.second == a.second) {
            if (b.first == a.first + 1) return 'D';
            if (b.first == a.first - 1) return 'U';
        }
        return '?'; // should not happen
    };

    vector<string> ops;
    long long load = 0;

    // Forward pass
    for (size_t k = 0; k < path.size(); ++k) {
        auto [i, j] = path[k];
        long long v = h[i][j];
        if (v > 0) {
            ops.push_back("+" + to_string(v));
            load += v;
            h[i][j] = 0;
        } else if (v < 0) {
            long long d = min(load, -v);
            if (d > 0) {
                ops.push_back("-" + to_string(d));
                load -= d;
                h[i][j] += d;
            }
        }
        if (k + 1 < path.size()) {
            char mv = moveChar(path[k], path[k+1]);
            ops.emplace_back(string(1, mv));
        }
    }

    // Backward pass
    for (int kk = (int)path.size() - 1; kk >= 0; --kk) {
        auto [i, j] = path[kk];
        long long v = h[i][j];
        if (v < 0) {
            long long d = min(load, -v);
            if (d > 0) {
                ops.push_back("-" + to_string(d));
                load -= d;
                h[i][j] += d;
            }
        }
        if (kk - 1 >= 0) {
            char mv = moveChar(path[kk], path[kk-1]);
            ops.emplace_back(string(1, mv));
        }
    }

    // Output operations
    for (auto &s : ops) cout << s << '\n';
    return 0;
}