#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<vector<int>> H(N, vector<int>(N));
    for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) cin >> H[i][j];

    vector<pair<int,int>> path;
    path.reserve(N*N);
    for (int i = 0; i < N; ++i) {
        if (i % 2 == 0) {
            for (int j = 0; j < N; ++j) path.emplace_back(i, j);
        } else {
            for (int j = N-1; j >= 0; --j) path.emplace_back(i, j);
        }
    }

    auto moveChar = [](pair<int,int> a, pair<int,int> b) -> char {
        if (a.first == b.first) {
            if (a.second + 1 == b.second) return 'R';
            if (a.second - 1 == b.second) return 'L';
        } else if (a.second == b.second) {
            if (a.first + 1 == b.first) return 'D';
            if (a.first - 1 == b.first) return 'U';
        }
        return 'X';
    };

    vector<string> ops;
    long long load = 0;
    int M = N*N;

    // Pass 1: serpentine forward, load positives, unload to negatives as much as possible
    for (int idx = 0; idx < M; ++idx) {
        auto [r, c] = path[idx];
        int h = H[r][c];
        if (h > 0) {
            ops.push_back("+" + to_string(h));
            load += h;
            H[r][c] = 0;
        } else if (h < 0 && load > 0) {
            long long d = min<long long>(-h, load);
            if (d > 0) {
                ops.push_back("-" + to_string(d));
                load -= d;
                H[r][c] += (int)d;
            }
        }
        if (idx + 1 < M) {
            char mv = moveChar(path[idx], path[idx+1]);
            ops.push_back(string(1, mv));
        }
    }

    // Pass 2: reverse serpentine, finish remaining negatives
    for (int idx = M - 1; idx >= 0; --idx) {
        auto [r, c] = path[idx];
        int h = H[r][c];
        if (h < 0) {
            int d = -h;
            if (d > 0) {
                ops.push_back("-" + to_string(d));
                load -= d;
                H[r][c] = 0;
            }
        }
        if (idx - 1 >= 0) {
            char mv = moveChar(path[idx], path[idx-1]);
            ops.push_back(string(1, mv));
        }
    }

    for (auto &s : ops) cout << s << '\n';
    return 0;
}