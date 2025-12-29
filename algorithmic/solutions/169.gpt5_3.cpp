#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<string> C(N);
    for (int i = 0; i < N; ++i) cin >> C[i];

    // Prefix sums of 'o' per row and per column
    vector<vector<int>> rowPref(N, vector<int>(N+1, 0));
    vector<vector<int>> colPref(N, vector<int>(N+1, 0));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            rowPref[i][j+1] = rowPref[i][j] + (C[i][j]=='o');
        }
    }
    for (int j = 0; j < N; ++j) {
        for (int i = 0; i < N; ++i) {
            colPref[j][i+1] = colPref[j][i] + (C[i][j]=='o');
        }
    }

    auto allowedU = [&](int i, int j)->bool {
        return colPref[j][i] == 0;
    };
    auto allowedD = [&](int i, int j)->bool {
        return (colPref[j][N] - colPref[j][i+1]) == 0;
    };
    auto allowedL = [&](int i, int j)->bool {
        return rowPref[i][j] == 0;
    };
    auto allowedR = [&](int i, int j)->bool {
        return (rowPref[i][N] - rowPref[i][j+1]) == 0;
    };

    vector<vector<char>> hasX(N, vector<char>(N, 0));
    int totalX = 0;
    for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) {
        if (C[i][j] == 'x') { hasX[i][j] = 1; totalX++; }
    }

    vector<pair<char,int>> ops;
    const int maxOps = 4*N*N;

    while (totalX > 0) {
        // Find best move by maximizing gain/cost, tie-break by smaller cost then larger gain
        bool found = false;
        char bestDir = 'U';
        int bestI = -1, bestJ = -1;
        int bestCost = 1;
        int bestGain = -1;

        for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) {
            if (!hasX[i][j]) continue;
            // Up
            if (allowedU(i,j)) {
                int gain = 0;
                for (int r = 0; r <= i; ++r) if (hasX[r][j]) gain++;
                int cost = 2*(i+1);
                if (gain > 0) {
                    if (!found || (long long)gain*bestCost > (long long)bestGain*cost ||
                        ((long long)gain*bestCost == (long long)bestGain*cost && (cost < bestCost || (cost == bestCost && gain > bestGain)))) {
                        found = true; bestDir = 'U'; bestI = i; bestJ = j; bestCost = cost; bestGain = gain;
                    }
                }
            }
            // Down
            if (allowedD(i,j)) {
                int gain = 0;
                for (int r = i; r < N; ++r) if (hasX[r][j]) gain++;
                int cost = 2*(N - i);
                if (gain > 0) {
                    if (!found || (long long)gain*bestCost > (long long)bestGain*cost ||
                        ((long long)gain*bestCost == (long long)bestGain*cost && (cost < bestCost || (cost == bestCost && gain > bestGain)))) {
                        found = true; bestDir = 'D'; bestI = i; bestJ = j; bestCost = cost; bestGain = gain;
                    }
                }
            }
            // Left
            if (allowedL(i,j)) {
                int gain = 0;
                for (int c = 0; c <= j; ++c) if (hasX[i][c]) gain++;
                int cost = 2*(j + 1);
                if (gain > 0) {
                    if (!found || (long long)gain*bestCost > (long long)bestGain*cost ||
                        ((long long)gain*bestCost == (long long)bestGain*cost && (cost < bestCost || (cost == bestCost && gain > bestGain)))) {
                        found = true; bestDir = 'L'; bestI = i; bestJ = j; bestCost = cost; bestGain = gain;
                    }
                }
            }
            // Right
            if (allowedR(i,j)) {
                int gain = 0;
                for (int c = j; c < N; ++c) if (hasX[i][c]) gain++;
                int cost = 2*(N - j);
                if (gain > 0) {
                    if (!found || (long long)gain*bestCost > (long long)bestGain*cost ||
                        ((long long)gain*bestCost == (long long)bestGain*cost && (cost < bestCost || (cost == bestCost && gain > bestGain)))) {
                        found = true; bestDir = 'R'; bestI = i; bestJ = j; bestCost = cost; bestGain = gain;
                    }
                }
            }
        }

        if (!found) break; // Should not happen due to guarantees

        // Apply the best move
        if (bestDir == 'U') {
            int i = bestI, j = bestJ;
            int k = i + 1;
            // Add operations if within limit
            if ((int)ops.size() + 2*k > maxOps) break;
            for (int t = 0; t < k; ++t) ops.emplace_back('U', j);
            for (int t = 0; t < k; ++t) ops.emplace_back('D', j);
            for (int r = 0; r <= i; ++r) if (hasX[r][j]) { hasX[r][j] = 0; totalX--; }
        } else if (bestDir == 'D') {
            int i = bestI, j = bestJ;
            int k = N - i;
            if ((int)ops.size() + 2*k > maxOps) break;
            for (int t = 0; t < k; ++t) ops.emplace_back('D', j);
            for (int t = 0; t < k; ++t) ops.emplace_back('U', j);
            for (int r = i; r < N; ++r) if (hasX[r][j]) { hasX[r][j] = 0; totalX--; }
        } else if (bestDir == 'L') {
            int i = bestI, j = bestJ;
            int k = j + 1;
            if ((int)ops.size() + 2*k > maxOps) break;
            for (int t = 0; t < k; ++t) ops.emplace_back('L', i);
            for (int t = 0; t < k; ++t) ops.emplace_back('R', i);
            for (int c = 0; c <= j; ++c) if (hasX[i][c]) { hasX[i][c] = 0; totalX--; }
        } else { // 'R'
            int i = bestI, j = bestJ;
            int k = N - j;
            if ((int)ops.size() + 2*k > maxOps) break;
            for (int t = 0; t < k; ++t) ops.emplace_back('R', i);
            for (int t = 0; t < k; ++t) ops.emplace_back('L', i);
            for (int c = j; c < N; ++c) if (hasX[i][c]) { hasX[i][c] = 0; totalX--; }
        }
    }

    // Output operations
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}