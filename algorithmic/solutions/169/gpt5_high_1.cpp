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

    auto add_ops = [&](char a, int p, int cnt){
        for (int k = 0; k < cnt; ++k) ops.emplace_back(a, p);
    };

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (C[i][j] != 'x') continue;

            bool up = true, down = true, left = true, right = true;
            for (int r = 0; r < i; ++r) if (C[r][j] == 'o') { up = false; break; }
            for (int r = i+1; r < N; ++r) if (C[r][j] == 'o') { down = false; break; }
            for (int c = 0; c < j; ++c) if (C[i][c] == 'o') { left = false; break; }
            for (int c = j+1; c < N; ++c) if (C[i][c] == 'o') { right = false; break; }

            int bestD = INT_MAX;
            char dir = 'U';
            int param = j;
            int d;

            if (up) {
                d = i + 1;
                if (d < bestD) { bestD = d; dir = 'U'; param = j; }
            }
            if (down) {
                d = N - i;
                if (d < bestD) { bestD = d; dir = 'D'; param = j; }
            }
            if (left) {
                d = j + 1;
                if (d < bestD) { bestD = d; dir = 'L'; param = i; }
            }
            if (right) {
                d = N - j;
                if (d < bestD) { bestD = d; dir = 'R'; param = i; }
            }

            // Apply the chosen sequence
            if (dir == 'U') {
                add_ops('U', param, bestD);
                add_ops('D', param, bestD);
            } else if (dir == 'D') {
                add_ops('D', param, bestD);
                add_ops('U', param, bestD);
            } else if (dir == 'L') {
                add_ops('L', param, bestD);
                add_ops('R', param, bestD);
            } else { // 'R'
                add_ops('R', param, bestD);
                add_ops('L', param, bestD);
            }
        }
    }

    // Ensure we don't exceed limit
    size_t limit = 4ULL * N * N;
    if (ops.size() > limit) ops.resize(limit);

    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }

    return 0;
}