#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<string> grid(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];

    // Precompute Fukunokami ('o') prefix sums (they never change)
    vector<vector<int>> prefOCol(N, vector<int>(N + 1, 0));
    vector<vector<int>> prefORow(N, vector<int>(N + 1, 0));
    for (int j = 0; j < N; ++j) {
        for (int i = 0; i < N; ++i) {
            prefOCol[j][i + 1] = prefOCol[j][i] + (grid[i][j] == 'o');
        }
    }
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            prefORow[i][j + 1] = prefORow[i][j] + (grid[i][j] == 'o');
        }
    }

    auto upAllowed = [&](int i, int j) -> bool {
        return prefOCol[j][i] == 0;
    };
    auto downAllowed = [&](int i, int j) -> bool {
        return prefOCol[j][N] - prefOCol[j][i + 1] == 0;
    };
    auto leftAllowed = [&](int i, int j) -> bool {
        return prefORow[i][j] == 0;
    };
    auto rightAllowed = [&](int i, int j) -> bool {
        return prefORow[i][N] - prefORow[i][j + 1] == 0;
    };

    struct Op { char d; int p; };
    vector<Op> ops;
    int maxOps = 4 * N * N;

    auto anyOni = [&]() -> bool {
        for (int i = 0; i < N; ++i)
            for (int j = 0; j < N; ++j)
                if (grid[i][j] == 'x') return true;
        return false;
    };

    while (anyOni()) {
        // Find best operation: maximize removed Oni per cost
        bool found = false;
        long long bestGain = -1;
        long long bestCost = 1;
        char bestDir = 'U';
        int bestIdx = 0;
        int bestSteps = 0;

        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (grid[i][j] != 'x') continue;

                // Up
                if (upAllowed(i, j)) {
                    int steps = i + 1;
                    int gain = 0;
                    for (int r = 0; r <= i; ++r) if (grid[r][j] == 'x') ++gain;
                    long long cost = 2LL * steps;
                    if (!found || gain * bestCost > bestGain * cost ||
                        (gain * bestCost == bestGain * cost && (gain > bestGain ||
                        (gain == bestGain && cost < bestCost)))) {
                        found = true;
                        bestGain = gain;
                        bestCost = cost;
                        bestDir = 'U';
                        bestIdx = j;
                        bestSteps = steps;
                    }
                }
                // Down
                if (downAllowed(i, j)) {
                    int steps = N - i;
                    int gain = 0;
                    for (int r = i; r < N; ++r) if (grid[r][j] == 'x') ++gain;
                    long long cost = 2LL * steps;
                    if (!found || gain * bestCost > bestGain * cost ||
                        (gain * bestCost == bestGain * cost && (gain > bestGain ||
                        (gain == bestGain && cost < bestCost)))) {
                        found = true;
                        bestGain = gain;
                        bestCost = cost;
                        bestDir = 'D';
                        bestIdx = j;
                        bestSteps = steps;
                    }
                }
                // Left
                if (leftAllowed(i, j)) {
                    int steps = j + 1;
                    int gain = 0;
                    for (int c = 0; c <= j; ++c) if (grid[i][c] == 'x') ++gain;
                    long long cost = 2LL * steps;
                    if (!found || gain * bestCost > bestGain * cost ||
                        (gain * bestCost == bestGain * cost && (gain > bestGain ||
                        (gain == bestGain && cost < bestCost)))) {
                        found = true;
                        bestGain = gain;
                        bestCost = cost;
                        bestDir = 'L';
                        bestIdx = i;
                        bestSteps = steps;
                    }
                }
                // Right
                if (rightAllowed(i, j)) {
                    int steps = N - j;
                    int gain = 0;
                    for (int c = j; c < N; ++c) if (grid[i][c] == 'x') ++gain;
                    long long cost = 2LL * steps;
                    if (!found || gain * bestCost > bestGain * cost ||
                        (gain * bestCost == bestGain * cost && (gain > bestGain ||
                        (gain == bestGain && cost < bestCost)))) {
                        found = true;
                        bestGain = gain;
                        bestCost = cost;
                        bestDir = 'R';
                        bestIdx = i;
                        bestSteps = steps;
                    }
                }
            }
        }

        if (!found) break; // should not happen

        // Apply operation to board and record ops
        if (bestDir == 'U') {
            int j = bestIdx;
            int steps = bestSteps;
            // remove all 'x' in column j, rows [0..steps-1]
            for (int r = 0; r <= steps - 1; ++r) {
                if (grid[r][j] == 'x') grid[r][j] = '.';
            }
            // record operations
            for (int t = 0; t < steps && (int)ops.size() < maxOps; ++t) ops.push_back({'U', j});
            for (int t = 0; t < steps && (int)ops.size() < maxOps; ++t) ops.push_back({'D', j});
        } else if (bestDir == 'D') {
            int j = bestIdx;
            int steps = bestSteps;
            for (int r = N - steps; r < N; ++r) {
                if (grid[r][j] == 'x') grid[r][j] = '.';
            }
            for (int t = 0; t < steps && (int)ops.size() < maxOps; ++t) ops.push_back({'D', j});
            for (int t = 0; t < steps && (int)ops.size() < maxOps; ++t) ops.push_back({'U', j});
        } else if (bestDir == 'L') {
            int i = bestIdx;
            int steps = bestSteps;
            for (int c = 0; c <= steps - 1; ++c) {
                if (grid[i][c] == 'x') grid[i][c] = '.';
            }
            for (int t = 0; t < steps && (int)ops.size() < maxOps; ++t) ops.push_back({'L', i});
            for (int t = 0; t < steps && (int)ops.size() < maxOps; ++t) ops.push_back({'R', i});
        } else if (bestDir == 'R') {
            int i = bestIdx;
            int steps = bestSteps;
            for (int c = N - steps; c < N; ++c) {
                if (grid[i][c] == 'x') grid[i][c] = '.';
            }
            for (int t = 0; t < steps && (int)ops.size() < maxOps; ++t) ops.push_back({'R', i});
            for (int t = 0; t < steps && (int)ops.size() < maxOps; ++t) ops.push_back({'L', i});
        }

        if ((int)ops.size() >= maxOps) break;
    }

    // Output operations
    int T = min((int)ops.size(), 4 * N * N);
    for (int t = 0; t < T; ++t) {
        cout << ops[t].d << ' ' << ops[t].p << '\n';
    }
    return 0;
}