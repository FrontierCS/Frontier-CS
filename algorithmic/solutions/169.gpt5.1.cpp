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
    const int INF = 1e9;

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (C[i][j] != 'x') continue;

            bool upSafe = true, downSafe = true, leftSafe = true, rightSafe = true;

            for (int r = i - 1; r >= 0; --r) {
                if (C[r][j] == 'o') { upSafe = false; break; }
            }
            for (int r = i + 1; r < N; ++r) {
                if (C[r][j] == 'o') { downSafe = false; break; }
            }
            for (int c = j - 1; c >= 0; --c) {
                if (C[i][c] == 'o') { leftSafe = false; break; }
            }
            for (int c = j + 1; c < N; ++c) {
                if (C[i][c] == 'o') { rightSafe = false; break; }
            }

            int bestCost = INF;
            char bestDir = '?';
            int steps = 0;

            if (upSafe) {
                int s = i + 1;
                int cost = 2 * s;
                if (cost < bestCost) {
                    bestCost = cost;
                    bestDir = 'U';
                    steps = s;
                }
            }
            if (downSafe) {
                int s = N - i;
                int cost = 2 * s;
                if (cost < bestCost) {
                    bestCost = cost;
                    bestDir = 'D';
                    steps = s;
                }
            }
            if (leftSafe) {
                int s = j + 1;
                int cost = 2 * s;
                if (cost < bestCost) {
                    bestCost = cost;
                    bestDir = 'L';
                    steps = s;
                }
            }
            if (rightSafe) {
                int s = N - j;
                int cost = 2 * s;
                if (cost < bestCost) {
                    bestCost = cost;
                    bestDir = 'R';
                    steps = s;
                }
            }

            if (bestDir == 'U') {
                for (int k = 0; k < steps; ++k) ops.emplace_back('U', j);
                for (int k = 0; k < steps; ++k) ops.emplace_back('D', j);
            } else if (bestDir == 'D') {
                for (int k = 0; k < steps; ++k) ops.emplace_back('D', j);
                for (int k = 0; k < steps; ++k) ops.emplace_back('U', j);
            } else if (bestDir == 'L') {
                for (int k = 0; k < steps; ++k) ops.emplace_back('L', i);
                for (int k = 0; k < steps; ++k) ops.emplace_back('R', i);
            } else if (bestDir == 'R') {
                for (int k = 0; k < steps; ++k) ops.emplace_back('R', i);
                for (int k = 0; k < steps; ++k) ops.emplace_back('L', i);
            }
        }
    }

    if ((int)ops.size() > 4 * N * N) {
        ops.resize(4 * N * N);
    }

    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }

    return 0;
}