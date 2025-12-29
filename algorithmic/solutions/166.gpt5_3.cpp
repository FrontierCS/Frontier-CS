#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<vector<int>> h(N, vector<int>(N));
    for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) cin >> h[i][j];

    vector<pair<int,int>> path;
    path.reserve(N*N);
    for (int i = 0; i < N; ++i) {
        if (i % 2 == 0) {
            for (int j = 0; j < N; ++j) path.emplace_back(i, j);
        } else {
            for (int j = N-1; j >= 0; --j) path.emplace_back(i, j);
        }
    }

    auto moveChar = [&](pair<int,int> a, pair<int,int> b)->char{
        if (b.first == a.first + 1) return 'D';
        if (b.first == a.first - 1) return 'U';
        if (b.second == a.second + 1) return 'R';
        if (b.second == a.second - 1) return 'L';
        return '?';
    };

    vector<string> ops;
    ops.reserve(5000);

    long long load = 0;

    auto proc = [&](int r, int c) {
        int val = h[r][c];
        if (val > 0) {
            ops.emplace_back("+" + to_string(val));
            load += val;
            h[r][c] = 0;
        } else if (val < 0 && load > 0) {
            long long d = min<long long>(-val, load);
            if (d > 0) {
                ops.emplace_back("-" + to_string(d));
                load -= d;
                h[r][c] += (int)d;
            }
        }
    };

    // Forward pass
    if (!path.empty()) {
        proc(path[0].first, path[0].second);
        for (size_t i = 1; i < path.size(); ++i) {
            char mv = moveChar(path[i-1], path[i]);
            ops.emplace_back(string(1, mv));
            proc(path[i].first, path[i].second);
        }
    }

    // Reverse pass
    if (!path.empty()) {
        // Try to unload at the last cell again if needed to reduce load before moving back
        proc(path.back().first, path.back().second);
        for (int i = (int)path.size() - 2; i >= 0; --i) {
            char mv = moveChar(path[i+1], path[i]);
            ops.emplace_back(string(1, mv));
            proc(path[i].first, path[i].second);
        }
    }

    // Output operations
    for (auto &s : ops) cout << s << '\n';
    return 0;
}