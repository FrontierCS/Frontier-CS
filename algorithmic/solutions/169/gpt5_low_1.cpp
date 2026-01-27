#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<string> C(N);
    for (int i = 0; i < N; ++i) cin >> C[i];

    vector<pair<char,int>> ops;

    auto clear_up = [&](int i, int j) {
        for (int r = 0; r < i; ++r) if (C[r][j] == 'o') return false;
        return true;
    };
    auto clear_down = [&](int i, int j) {
        for (int r = i+1; r < N; ++r) if (C[r][j] == 'o') return false;
        return true;
    };
    auto clear_left = [&](int i, int j) {
        for (int c = 0; c < j; ++c) if (C[i][c] == 'o') return false;
        return true;
    };
    auto clear_right = [&](int i, int j) {
        for (int c = j+1; c < N; ++c) if (C[i][c] == 'o') return false;
        return true;
    };

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (C[i][j] != 'x') continue;
            int bestCost = INT_MAX;
            char dir1 = 0, dir2 = 0;
            int idx = -1, k = 0;

            // Up
            if (clear_up(i,j)) {
                int cost = 2*(i+1);
                if (cost < bestCost) {
                    bestCost = cost; dir1 = 'U'; dir2 = 'D'; idx = j; k = i+1;
                }
            }
            // Down
            if (clear_down(i,j)) {
                int kk = (N - i);
                int cost = 2*kk;
                if (cost < bestCost) {
                    bestCost = cost; dir1 = 'D'; dir2 = 'U'; idx = j; k = kk;
                }
            }
            // Left
            if (clear_left(i,j)) {
                int cost = 2*(j+1);
                if (cost < bestCost) {
                    bestCost = cost; dir1 = 'L'; dir2 = 'R'; idx = i; k = j+1;
                }
            }
            // Right
            if (clear_right(i,j)) {
                int kk = (N - j);
                int cost = 2*kk;
                if (cost < bestCost) {
                    bestCost = cost; dir1 = 'R'; dir2 = 'L'; idx = i; k = kk;
                }
            }

            // Append operations
            for (int t = 0; t < k; ++t) ops.emplace_back(dir1, idx);
            for (int t = 0; t < k; ++t) ops.emplace_back(dir2, idx);
        }
    }

    // Output
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}