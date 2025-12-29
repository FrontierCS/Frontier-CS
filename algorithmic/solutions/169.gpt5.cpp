#include <bits/stdc++.h>
using namespace std;

struct Cand {
    char dir;   // 'U','D','L','R'
    int idx;    // column for U/D, row for L/R
    int k;      // number of shifts in first half
    int cost;   // 2*k
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<string> C(N);
    for (int i = 0; i < N; ++i) cin >> C[i];

    vector<vector<bool>> isFuku(N, vector<bool>(N, false));
    vector<vector<bool>> isOni(N, vector<bool>(N, false));
    int oniCount = 0;
    for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) {
        if (C[i][j] == 'o') isFuku[i][j] = true;
        if (C[i][j] == 'x') { isOni[i][j] = true; oniCount++; }
    }

    // Map each Oni to an ID and store its minCost individually
    vector<vector<int>> oniID(N, vector<int>(N, -1));
    vector<pair<int,int>> oniPos;
    int id = 0;
    for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) {
        if (isOni[i][j]) {
            oniID[i][j] = id++;
            oniPos.push_back({i,j});
        }
    }
    int M = id;

    auto safeUp = [&](int i, int j)->bool{
        for (int r = 0; r < i; ++r) if (isFuku[r][j]) return false;
        return true;
    };
    auto safeDown = [&](int i, int j)->bool{
        for (int r = i+1; r < N; ++r) if (isFuku[r][j]) return false;
        return true;
    };
    auto safeLeft = [&](int i, int j)->bool{
        for (int c = 0; c < j; ++c) if (isFuku[i][c]) return false;
        return true;
    };
    auto safeRight = [&](int i, int j)->bool{
        for (int c = j+1; c < N; ++c) if (isFuku[i][c]) return false;
        return true;
    };

    // Precompute min individual cost per Oni (based on original board)
    vector<int> minCost(M, INT_MAX);
    for (int t = 0; t < M; ++t) {
        int i = oniPos[t].first, j = oniPos[t].second;
        if (safeUp(i,j)) minCost[t] = min(minCost[t], 2*(i+1));
        if (safeDown(i,j)) minCost[t] = min(minCost[t], 2*(N - i));
        if (safeLeft(i,j)) minCost[t] = min(minCost[t], 2*(j+1));
        if (safeRight(i,j)) minCost[t] = min(minCost[t], 2*(N - j));
        // Safety: minCost must be set due to guarantee
        if (minCost[t] == INT_MAX) {
            // Fallback shouldn't happen, but set a default large value
            minCost[t] = 2*N;
        }
    }

    // Build candidate list
    vector<Cand> cands;
    cands.reserve(M * 4);
    for (int t = 0; t < M; ++t) {
        int i = oniPos[t].first, j = oniPos[t].second;
        if (safeUp(i,j))     cands.push_back({'U', j, i+1, 2*(i+1)});
        if (safeDown(i,j))   cands.push_back({'D', j, N - i, 2*(N - i)});
        if (safeLeft(i,j))   cands.push_back({'L', i, j+1, 2*(j+1)});
        if (safeRight(i,j))  cands.push_back({'R', i, N - j, 2*(N - j)});
    }

    vector<vector<bool>> oniRem = isOni;
    int remaining = oniCount;

    auto reverseDir = [](char d)->char{
        if (d=='U') return 'D';
        if (d=='D') return 'U';
        if (d=='L') return 'R';
        return 'L';
    };

    vector<pair<char,int>> ops;

    auto compute_gain_and_budget = [&](const Cand &c)->pair<int,int>{
        int gain = 0;
        int budget = 0;
        if (c.dir == 'U') {
            int j = c.idx;
            for (int r = 0; r <= c.k - 1; ++r) {
                if (oniRem[r][j]) {
                    gain++;
                    int tid = oniID[r][j];
                    budget += minCost[tid];
                }
            }
        } else if (c.dir == 'D') {
            int j = c.idx;
            int i = N - c.k;
            for (int r = i; r < N; ++r) {
                if (oniRem[r][j]) {
                    gain++;
                    int tid = oniID[r][j];
                    budget += minCost[tid];
                }
            }
        } else if (c.dir == 'L') {
            int i = c.idx;
            for (int col = 0; col <= c.k - 1; ++col) {
                if (oniRem[i][col]) {
                    gain++;
                    int tid = oniID[i][col];
                    budget += minCost[tid];
                }
            }
        } else { // 'R'
            int i = c.idx;
            int j = N - c.k;
            for (int col = j; col < N; ++col) {
                if (oniRem[i][col]) {
                    gain++;
                    int tid = oniID[i][col];
                    budget += minCost[tid];
                }
            }
        }
        return {gain, budget};
    };

    while (remaining > 0) {
        // Select best candidate with gain > 0 and cost <= budget (sum of minCosts of covered Onis)
        int bestIdx = -1;
        int bestGain = 0;
        int bestCost = 1;
        // compare ratio gain/cost by cross multiplication
        for (int ci = 0; ci < (int)cands.size(); ++ci) {
            auto &c = cands[ci];
            auto [g, bud] = compute_gain_and_budget(c);
            if (g == 0) continue;
            if (c.cost > bud) continue; // keep total cost <= base min sum
            if (bestIdx == -1) {
                bestIdx = ci; bestGain = g; bestCost = c.cost;
            } else {
                // Compare g/cost vs bestGain/bestCost
                long long lhs = 1LL * g * bestCost;
                long long rhs = 1LL * bestGain * c.cost;
                if (lhs > rhs) {
                    bestIdx = ci; bestGain = g; bestCost = c.cost;
                } else if (lhs == rhs) {
                    // tie-breaker: higher gain, then lower cost
                    if (g > bestGain || (g == bestGain && c.cost < bestCost)) {
                        bestIdx = ci; bestGain = g; bestCost = c.cost;
                    }
                }
            }
        }

        // If none found (shouldn't happen), fall back to any remaining Oni with its minimal direction
        if (bestIdx == -1) {
            // find an Oni still remaining
            int fi = -1, fj = -1, fid = -1;
            for (int i = 0; i < N && fid==-1; ++i) {
                for (int j = 0; j < N; ++j) {
                    if (oniRem[i][j]) { fi = i; fj = j; fid = oniID[i][j]; break; }
                }
            }
            if (fid == -1) break; // no oni left
            int bestLocalCost = INT_MAX;
            Cand bestLocalCand{'U', 0, 1, 2};
            if (safeUp(fi,fj)) {
                int k = fi+1, cost = 2*k;
                if (cost < bestLocalCost) bestLocalCost = cost, bestLocalCand = {'U', fj, k, cost};
            }
            if (safeDown(fi,fj)) {
                int k = N - fi, cost = 2*k;
                if (cost < bestLocalCost) bestLocalCost = cost, bestLocalCand = {'D', fj, k, cost};
            }
            if (safeLeft(fi,fj)) {
                int k = fj+1, cost = 2*k;
                if (cost < bestLocalCost) bestLocalCost = cost, bestLocalCand = {'L', fi, k, cost};
            }
            if (safeRight(fi,fj)) {
                int k = N - fj, cost = 2*k;
                if (cost < bestLocalCost) bestLocalCost = cost, bestLocalCand = {'R', fi, k, cost};
            }
            // Apply fallback candidate
            Cand c = bestLocalCand;
            for (int t = 0; t < c.k; ++t) ops.push_back({c.dir, c.idx});
            char rd = reverseDir(c.dir);
            for (int t = 0; t < c.k; ++t) ops.push_back({rd, c.idx});
            // mark removal
            if (c.dir == 'U') {
                int j = c.idx;
                for (int r = 0; r <= c.k - 1; ++r) {
                    if (oniRem[r][j]) { oniRem[r][j] = false; remaining--; }
                }
            } else if (c.dir == 'D') {
                int j = c.idx;
                int i = N - c.k;
                for (int r = i; r < N; ++r) {
                    if (oniRem[r][j]) { oniRem[r][j] = false; remaining--; }
                }
            } else if (c.dir == 'L') {
                int i = c.idx;
                for (int col = 0; col <= c.k - 1; ++col) {
                    if (oniRem[i][col]) { oniRem[i][col] = false; remaining--; }
                }
            } else { // 'R'
                int i = c.idx;
                int j = N - c.k;
                for (int col = j; col < N; ++col) {
                    if (oniRem[i][col]) { oniRem[i][col] = false; remaining--; }
                }
            }
            continue;
        }

        // Apply best candidate
        Cand c = cands[bestIdx];
        for (int t = 0; t < c.k; ++t) ops.push_back({c.dir, c.idx});
        char rd = reverseDir(c.dir);
        for (int t = 0; t < c.k; ++t) ops.push_back({rd, c.idx});
        // mark removal
        if (c.dir == 'U') {
            int j = c.idx;
            for (int r = 0; r <= c.k - 1; ++r) {
                if (oniRem[r][j]) { oniRem[r][j] = false; remaining--; }
            }
        } else if (c.dir == 'D') {
            int j = c.idx;
            int i = N - c.k;
            for (int r = i; r < N; ++r) {
                if (oniRem[r][j]) { oniRem[r][j] = false; remaining--; }
            }
        } else if (c.dir == 'L') {
            int i = c.idx;
            for (int col = 0; col <= c.k - 1; ++col) {
                if (oniRem[i][col]) { oniRem[i][col] = false; remaining--; }
            }
        } else { // 'R'
            int i = c.idx;
            int j = N - c.k;
            for (int col = j; col < N; ++col) {
                if (oniRem[i][col]) { oniRem[i][col] = false; remaining--; }
            }
        }
    }

    // Output operations
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}