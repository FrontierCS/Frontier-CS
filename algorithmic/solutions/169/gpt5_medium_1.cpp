#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<string> G(N);
    for (int i = 0; i < N; ++i) cin >> G[i];

    vector<pair<char,int>> ops;

    auto shiftColUp = [&](int j){
        ops.emplace_back('U', j);
        for (int i = 0; i < N-1; ++i) G[i][j] = G[i+1][j];
        G[N-1][j] = '.';
    };
    auto shiftColDown = [&](int j){
        ops.emplace_back('D', j);
        for (int i = N-1; i >= 1; --i) G[i][j] = G[i-1][j];
        G[0][j] = '.';
    };
    auto shiftRowLeft = [&](int i){
        ops.emplace_back('L', i);
        for (int j = 0; j < N-1; ++j) G[i][j] = G[i][j+1];
        G[i][N-1] = '.';
    };
    auto shiftRowRight = [&](int i){
        ops.emplace_back('R', i);
        for (int j = N-1; j >= 1; --j) G[i][j] = G[i][j-1];
        G[i][0] = '.';
    };

    size_t limit = 4u * N * N;
    bool stop = false;

    for (int i = 0; i < N && !stop; ++i) {
        for (int j = 0; j < N && !stop; ++j) {
            if (G[i][j] != 'x') continue;

            bool upOK = true;
            for (int r = 0; r < i; ++r) if (G[r][j] == 'o') { upOK = false; break; }
            bool downOK = true;
            for (int r = i+1; r < N; ++r) if (G[r][j] == 'o') { downOK = false; break; }
            bool leftOK = true;
            for (int c = 0; c < j; ++c) if (G[i][c] == 'o') { leftOK = false; break; }
            bool rightOK = true;
            for (int c = j+1; c < N; ++c) if (G[i][c] == 'o') { rightOK = false; break; }

            int bestCost = INT_MAX;
            char bestDir = '?';
            int k = 0;

            if (upOK) {
                int cost = 2 * (i + 1);
                if (cost < bestCost) { bestCost = cost; bestDir = 'U'; k = i + 1; }
            }
            if (downOK) {
                int cost = 2 * (N - i);
                if (cost < bestCost) { bestCost = cost; bestDir = 'D'; k = N - i; }
            }
            if (leftOK) {
                int cost = 2 * (j + 1);
                if (cost < bestCost) { bestCost = cost; bestDir = 'L'; k = j + 1; }
            }
            if (rightOK) {
                int cost = 2 * (N - j);
                if (cost < bestCost) { bestCost = cost; bestDir = 'R'; k = N - j; }
            }

            if (bestDir == '?') continue; // Should not happen due to problem guarantee

            if (ops.size() + (size_t)bestCost > limit) { stop = true; break; }

            if (bestDir == 'U') {
                for (int t = 0; t < k; ++t) shiftColUp(j);
                for (int t = 0; t < k; ++t) shiftColDown(j);
            } else if (bestDir == 'D') {
                for (int t = 0; t < k; ++t) shiftColDown(j);
                for (int t = 0; t < k; ++t) shiftColUp(j);
            } else if (bestDir == 'L') {
                for (int t = 0; t < k; ++t) shiftRowLeft(i);
                for (int t = 0; t < k; ++t) shiftRowRight(i);
            } else if (bestDir == 'R') {
                for (int t = 0; t < k; ++t) shiftRowRight(i);
                for (int t = 0; t < k; ++t) shiftRowLeft(i);
            }
        }
    }

    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}