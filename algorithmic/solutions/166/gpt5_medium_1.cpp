#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<vector<int>> h(N, vector<int>(N));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) cin >> h[i][j];
    }

    vector<pair<int,int>> path;
    path.reserve(N*N);
    for (int i = 0; i < N; ++i) {
        if (i % 2 == 0) {
            for (int j = 0; j < N; ++j) path.emplace_back(i, j);
        } else {
            for (int j = N - 1; j >= 0; --j) path.emplace_back(i, j);
        }
    }

    vector<string> ops;
    long long load = 0;
    int M = N * N;

    auto moveChar = [](pair<int,int> a, pair<int,int> b) -> char {
        if (b.first == a.first + 1 && b.second == a.second) return 'D';
        if (b.first == a.first - 1 && b.second == a.second) return 'U';
        if (b.first == a.first && b.second == a.second + 1) return 'R';
        if (b.first == a.first && b.second == a.second - 1) return 'L';
        return ' '; // should not happen
    };

    // First pass: load from positive cells
    for (int idx = 0; idx < M; ++idx) {
        auto [r, c] = path[idx];
        if (h[r][c] > 0) {
            ops.push_back("+" + to_string(h[r][c]));
            load += h[r][c];
            h[r][c] = 0;
        }
        if (idx + 1 < M) {
            char mv = moveChar(path[idx], path[idx + 1]);
            ops.push_back(string(1, mv));
        }
    }

    // Second pass: unload to negative cells (reverse path)
    for (int idx = M - 1; idx >= 0; --idx) {
        auto [r, c] = path[idx];
        if (h[r][c] < 0) {
            int d = -h[r][c];
            ops.push_back("-" + to_string(d));
            load -= d;
            h[r][c] = 0;
        }
        if (idx - 1 >= 0) {
            char mv = moveChar(path[idx], path[idx - 1]);
            ops.push_back(string(1, mv));
        }
    }

    for (auto &s : ops) {
        cout << s << '\n';
    }
    return 0;
}