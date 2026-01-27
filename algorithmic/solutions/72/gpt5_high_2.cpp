#include <bits/stdc++.h>
using namespace std;

struct Move {
    uint8_t id;
    char dir;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    const int H = 6, W = 6;
    vector<vector<int>> board(H, vector<int>(W));
    int n = 0;
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            int x;
            if (!(cin >> x)) return 0;
            board[r][c] = x;
            n = max(n, x);
        }
    }
    if (n == 0) {
        cout << 0 << " " << 0 << "\n";
        return 0;
    }
    vector<vector<pair<int,int>>> pos(n+1);
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            int id = board[r][c];
            if (id > 0) pos[id].push_back({r,c});
        }
    }
    vector<bool> horiz(n+1, false);
    vector<int> len(n+1, 0);
    vector<int> fix(n+1, 0); // fixed row if horiz, fixed col if vertical
    vector<int> var0(n+1, 0); // initial variable coordinate (col for horiz, row for vert)
    for (int id = 1; id <= n; ++id) {
        auto &v = pos[id];
        if (v.empty()) continue;
        len[id] = (int)v.size();
        if ((int)v.size() >= 2 && v[0].first == v[1].first) {
            horiz[id] = true;
            int r = v[0].first;
            int minc = 10, maxc = -1;
            for (auto &p : v) { minc = min(minc, p.second); maxc = max(maxc, p.second); }
            fix[id] = r;
            var0[id] = minc;
        } else {
            horiz[id] = false;
            int c = v[0].second;
            int minr = 10, maxr = -1;
            for (auto &p : v) { minr = min(minr, p.first); maxr = max(maxr, p.first); }
            fix[id] = c;
            var0[id] = minr;
        }
    }
    // Precompute shifts
    vector<int> shift(n+1, 0);
    for (int i = 1; i <= n; ++i) shift[i] = 3*(i-1);
    
    auto pack = [&](const vector<int>& var)->uint64_t{
        uint64_t key = 0;
        for (int i = 1; i <= n; ++i) {
            key |= (uint64_t(var[i]) << shift[i]);
        }
        return key;
    };
    
    auto buildBoard = [&](uint64_t key, array<uint8_t,36>& occ, array<uint8_t,11>& var){
        occ.fill(0);
        for (int i = 1; i <= n; ++i) {
            uint8_t v = (key >> shift[i]) & 7u;
            var[i] = v;
            if (horiz[i]) {
                int r = fix[i];
                int c = v;
                for (int d = 0; d < len[i]; ++d) {
                    occ[r*6 + (c+d)] = (uint8_t)i;
                }
            } else {
                int c = fix[i];
                int r = v;
                for (int d = 0; d < len[i]; ++d) {
                    occ[(r+d)*6 + c] = (uint8_t)i;
                }
            }
        }
    };
    
    // Initial key
    vector<int> varInit(n+1, 0);
    for (int i = 1; i <= n; ++i) varInit[i] = var0[i];
    uint64_t startKey = pack(varInit);
    
    // BFS from initial to explore reachable states, record parents and moves
    unordered_map<uint64_t,int> idOf;
    idOf.reserve(1<<20);
    vector<uint64_t> keys;
    vector<int> parent;
    vector<Move> how;
    vector<int> distInit;
    vector<int> goalIndices; // states where red car at var=4
    deque<int> q;
    
    idOf[startKey] = 0;
    keys.push_back(startKey);
    parent.push_back(-1);
    how.push_back({0,'X'});
    distInit.push_back(0);
    q.push_back(0);
    // Check if start is goal (red at var=4)
    {
        int v1 = (startKey >> shift[1]) & 7;
        if (horiz[1] && v1 == 4) goalIndices.push_back(0);
    }
    
    // Full BFS (we'll allow it fully; typical sizes are manageable)
    while (!q.empty()) {
        int cur = q.front(); q.pop_front();
        uint64_t key = keys[cur];
        array<uint8_t,36> occ;
        array<uint8_t,11> var;
        buildBoard(key, occ, var);
        for (int i = 1; i <= n; ++i) {
            int sh = shift[i];
            int L = len[i];
            if (horiz[i]) {
                int r = fix[i];
                int c = var[i];
                // left
                if (c > 0) {
                    int nc = c - 1;
                    if (occ[r*6 + nc] == 0) {
                        uint64_t nk = key - (1ULL << sh);
                        auto it = idOf.find(nk);
                        if (it == idOf.end()) {
                            int idx = (int)keys.size();
                            idOf.emplace(nk, idx);
                            keys.push_back(nk);
                            parent.push_back(cur);
                            how.push_back({(uint8_t)i, 'L'});
                            distInit.push_back(distInit[cur] + 1);
                            q.push_back(idx);
                            if (horiz[1]) {
                                int v1 = (nk >> shift[1]) & 7u;
                                if (v1 == 4) goalIndices.push_back(idx);
                            }
                        }
                    }
                }
                // right
                if (c + L <= 5) {
                    int nc = c + L;
                    if (occ[r*6 + nc] == 0) {
                        uint64_t nk = key + (1ULL << sh);
                        auto it = idOf.find(nk);
                        if (it == idOf.end()) {
                            int idx = (int)keys.size();
                            idOf.emplace(nk, idx);
                            keys.push_back(nk);
                            parent.push_back(cur);
                            how.push_back({(uint8_t)i, 'R'});
                            distInit.push_back(distInit[cur] + 1);
                            q.push_back(idx);
                            if (horiz[1]) {
                                int v1 = (nk >> shift[1]) & 7u;
                                if (v1 == 4) goalIndices.push_back(idx);
                            }
                        }
                    }
                }
            } else {
                int c = fix[i];
                int r = var[i];
                // up
                if (r > 0) {
                    int nr = r - 1;
                    if (occ[nr*6 + c] == 0) {
                        uint64_t nk = key - (1ULL << sh);
                        auto it = idOf.find(nk);
                        if (it == idOf.end()) {
                            int idx = (int)keys.size();
                            idOf.emplace(nk, idx);
                            keys.push_back(nk);
                            parent.push_back(cur);
                            how.push_back({(uint8_t)i, 'U'});
                            distInit.push_back(distInit[cur] + 1);
                            q.push_back(idx);
                            if (horiz[1]) {
                                int v1 = (nk >> shift[1]) & 7u;
                                if (v1 == 4) goalIndices.push_back(idx);
                            }
                        }
                    }
                }
                // down
                if (r + L <= 5) {
                    int nr = r + L;
                    if (occ[nr*6 + c] == 0) {
                        uint64_t nk = key + (1ULL << sh);
                        auto it = idOf.find(nk);
                        if (it == idOf.end()) {
                            int idx = (int)keys.size();
                            idOf.emplace(nk, idx);
                            keys.push_back(nk);
                            parent.push_back(cur);
                            how.push_back({(uint8_t)i, 'D'});
                            distInit.push_back(distInit[cur] + 1);
                            q.push_back(idx);
                            if (horiz[1]) {
                                int v1 = (nk >> shift[1]) & 7u;
                                if (v1 == 4) goalIndices.push_back(idx);
                            }
                        }
                    }
                }
            }
        }
    }
    
    // If no goal states found (extremely unlikely for solvable puzzle), fallback: no scramble, compute minimal steps from initial to exit as minimal to reach var1=4 plus 2
    if (goalIndices.empty()) {
        // BFS from initial to first goal (already done); find minimal among visited
        int bestDistToGoal = INT_MAX;
        for (size_t i = 0; i < keys.size(); ++i) {
            int v1 = (keys[i] >> shift[1]) & 7u;
            if (horiz[1] && v1 == 4) {
                bestDistToGoal = min(bestDistToGoal, distInit[i]);
            }
        }
        if (bestDistToGoal == INT_MAX) {
            // Just output 0 0 as safe fallback
            cout << 0 << " " << 0 << "\n";
            return 0;
        } else {
            int solveSteps = bestDistToGoal + 2;
            cout << solveSteps << " " << 0 << "\n";
            return 0;
        }
    }
    
    // BFS from goal states over the discovered component to compute minimal steps to goal (var1=4) within board
    int S = (int)keys.size();
    vector<int> distGoal(S, -1);
    deque<int> q2;
    for (int gi : goalIndices) {
        if (distGoal[gi] == 0) continue;
        distGoal[gi] = 0;
        q2.push_back(gi);
    }
    while (!q2.empty()) {
        int cur = q2.front(); q2.pop_front();
        uint64_t key = keys[cur];
        array<uint8_t,36> occ;
        array<uint8_t,11> var;
        buildBoard(key, occ, var);
        for (int i = 1; i <= n; ++i) {
            int sh = shift[i];
            int L = len[i];
            if (horiz[i]) {
                int r = fix[i];
                int c = var[i];
                // left
                if (c > 0) {
                    int nc = c - 1;
                    if (occ[r*6 + nc] == 0) {
                        uint64_t nk = key - (1ULL << sh);
                        auto it = idOf.find(nk);
                        if (it != idOf.end()) {
                            int ni = it->second;
                            if (distGoal[ni] == -1) {
                                distGoal[ni] = distGoal[cur] + 1;
                                q2.push_back(ni);
                            }
                        }
                    }
                }
                // right
                if (c + L <= 5) {
                    int nc = c + L;
                    if (occ[r*6 + nc] == 0) {
                        uint64_t nk = key + (1ULL << sh);
                        auto it = idOf.find(nk);
                        if (it != idOf.end()) {
                            int ni = it->second;
                            if (distGoal[ni] == -1) {
                                distGoal[ni] = distGoal[cur] + 1;
                                q2.push_back(ni);
                            }
                        }
                    }
                }
            } else {
                int c = fix[i];
                int r = var[i];
                // up
                if (r > 0) {
                    int nr = r - 1;
                    if (occ[nr*6 + c] == 0) {
                        uint64_t nk = key - (1ULL << sh);
                        auto it = idOf.find(nk);
                        if (it != idOf.end()) {
                            int ni = it->second;
                            if (distGoal[ni] == -1) {
                                distGoal[ni] = distGoal[cur] + 1;
                                q2.push_back(ni);
                            }
                        }
                    }
                }
                // down
                if (r + L <= 5) {
                    int nr = r + L;
                    if (occ[nr*6 + c] == 0) {
                        uint64_t nk = key + (1ULL << sh);
                        auto it = idOf.find(nk);
                        if (it != idOf.end()) {
                            int ni = it->second;
                            if (distGoal[ni] == -1) {
                                distGoal[ni] = distGoal[cur] + 1;
                                q2.push_back(ni);
                            }
                        }
                    }
                }
            }
        }
    }
    
    // Choose target state: maximize minimal steps to fully exit = distGoal + 2
    int maxSolve = -1;
    for (int i = 0; i < S; ++i) {
        if (distGoal[i] >= 0) {
            int val = distGoal[i] + 2;
            if (val > maxSolve) maxSolve = val;
        }
    }
    if (maxSolve < 0) {
        // Should not happen; fallback to 0 moves
        cout << 0 << " " << 0 << "\n";
        return 0;
    }
    // Limit scramble steps for practicality
    int scrambleLimit = 500;
    int target = -1;
    // Prefer exact maxSolve with minimal distInit, but if too long, accept slightly less
    for (int delta = 0; delta <= 2 && target == -1; ++delta) {
        int bestDist = INT_MAX;
        for (int i = 0; i < S; ++i) {
            if (distGoal[i] >= 0) {
                int val = distGoal[i] + 2;
                if (val >= maxSolve - delta) {
                    int di = distInit[i];
                    if (di < bestDist && di <= scrambleLimit) {
                        bestDist = di;
                        target = i;
                    }
                }
            }
        }
    }
    if (target == -1) {
        // No within limit, pick minimal distInit among maxSolve states
        int bestDist = INT_MAX;
        for (int i = 0; i < S; ++i) {
            if (distGoal[i] >= 0 && distGoal[i] + 2 == maxSolve) {
                if (distInit[i] < bestDist) {
                    bestDist = distInit[i];
                    target = i;
                }
            }
        }
        if (target == -1) {
            // pick any best
            for (int i = 0; i < S; ++i) {
                if (distGoal[i] >= 0) { target = i; break; }
            }
        }
    }
    
    int solveSteps = distGoal[target] + 2;
    int scrambleSteps = distInit[target];
    
    // Reconstruct path from initial to target
    vector<Move> path;
    int cur = target;
    while (parent[cur] != -1) {
        path.push_back(how[cur]);
        cur = parent[cur];
    }
    reverse(path.begin(), path.end());
    
    cout << solveSteps << " " << scrambleSteps << "\n";
    for (auto &mv : path) {
        cout << (int)mv.id << " " << mv.dir << "\n";
    }
    return 0;
}