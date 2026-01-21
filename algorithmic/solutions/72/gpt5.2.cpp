#include <bits/stdc++.h>
using namespace std;

struct Vehicle {
    bool horiz;     // true: horizontal, false: vertical
    int len;        // 2 or 3
    int fixed;      // row if horiz, col if vertical
    int range;      // number of possible positions for variable coordinate
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int board[6][6];
    int n = 0;
    for (int r = 0; r < 6; r++) {
        for (int c = 0; c < 6; c++) {
            if (!(cin >> board[r][c])) return 0;
            n = max(n, board[r][c]);
        }
    }

    const int MAXV = 10;
    vector<int> minR(n + 1, 6), maxR(n + 1, -1), minC(n + 1, 6), maxC(n + 1, -1);
    for (int r = 0; r < 6; r++) {
        for (int c = 0; c < 6; c++) {
            int id = board[r][c];
            if (id <= 0) continue;
            minR[id] = min(minR[id], r);
            maxR[id] = max(maxR[id], r);
            minC[id] = min(minC[id], c);
            maxC[id] = max(maxC[id], c);
        }
    }

    vector<Vehicle> veh(n);
    vector<int> initPos(n, 0);

    for (int id = 1; id <= n; id++) {
        int h = maxR[id] - minR[id] + 1;
        int w = maxC[id] - minC[id] + 1;
        bool horiz = (w > 1);
        int len = max(h, w);
        int fixed = horiz ? minR[id] : minC[id];
        int var0 = horiz ? minC[id] : minR[id];

        Vehicle v;
        v.horiz = horiz;
        v.len = len;
        v.fixed = fixed;
        if (id == 1) v.range = 7; // red car can go out to the right: col 0..6
        else v.range = 6 - len + 1;

        veh[id - 1] = v;
        initPos[id - 1] = var0;
    }

    // Mixed-radix multipliers
    vector<int> rangev(n), mult(n, 1);
    for (int i = 0; i < n; i++) rangev[i] = veh[i].range;
    for (int i = 1; i < n; i++) mult[i] = mult[i - 1] * rangev[i - 1];

    long long totalStatesLL = 1;
    for (int i = 0; i < n; i++) totalStatesLL *= rangev[i];
    int totalStates = (int)totalStatesLL;

    int startKey = 0;
    for (int i = 0; i < n; i++) startKey += initPos[i] * mult[i];

    // Precompute occupancy masks for each vehicle and each possible position
    vector<vector<uint64_t>> masks(n);
    for (int i = 0; i < n; i++) {
        masks[i].assign(rangev[i], 0ULL);
        const auto &v = veh[i];
        for (int p = 0; p < rangev[i]; p++) {
            uint64_t m = 0;
            if (v.horiz) {
                int r = v.fixed;
                for (int k = 0; k < v.len; k++) {
                    int c = p + k;
                    if (0 <= c && c < 6) m |= (1ULL << (r * 6 + c));
                }
            } else {
                int c = v.fixed;
                for (int k = 0; k < v.len; k++) {
                    int r = p + k;
                    if (0 <= r && r < 6) m |= (1ULL << (r * 6 + c));
                }
            }
            masks[i][p] = m;
        }
    }

    vector<int> distInit(totalStates, -1);
    vector<int> parent(totalStates, -1);
    vector<uint8_t> prevVeh(totalStates, 0);
    vector<uint8_t> prevDir(totalStates, 0);

    auto decodePosOcc = [&](int key, int posOut[MAXV], uint64_t &occOut) {
        int tmp = key;
        uint64_t occ = 0;
        for (int i = 0; i < n; i++) {
            int p = tmp % rangev[i];
            tmp /= rangev[i];
            posOut[i] = p;
            occ |= masks[i][p];
        }
        occOut = occ;
    };

    auto forNeighbors = [&](int curKey, const int pos[MAXV], uint64_t occ, auto &&visit) {
        for (int i = 0; i < n; i++) {
            const auto &v = veh[i];
            int p = pos[i];
            if (v.horiz) {
                int r = v.fixed;
                // Left
                if (p > 0) {
                    int enterC = p - 1;
                    uint64_t bit = (1ULL << (r * 6 + enterC));
                    if ((occ & bit) == 0) visit(curKey - mult[i], i, 2); // L
                }
                // Right
                if (i == 0) {
                    // red can go to p==6
                    if (p < 6) {
                        int enterC = p + v.len;
                        if (enterC >= 6) {
                            visit(curKey + mult[i], i, 3); // R
                        } else {
                            uint64_t bit = (1ULL << (r * 6 + enterC));
                            if ((occ & bit) == 0) visit(curKey + mult[i], i, 3); // R
                        }
                    }
                } else {
                    if (p + v.len < 6) {
                        int enterC = p + v.len;
                        uint64_t bit = (1ULL << (r * 6 + enterC));
                        if ((occ & bit) == 0) visit(curKey + mult[i], i, 3); // R
                    }
                }
            } else {
                int c = v.fixed;
                // Up
                if (p > 0) {
                    int enterR = p - 1;
                    uint64_t bit = (1ULL << (enterR * 6 + c));
                    if ((occ & bit) == 0) visit(curKey - mult[i], i, 0); // U
                }
                // Down
                if (p + v.len < 6) {
                    int enterR = p + v.len;
                    uint64_t bit = (1ULL << (enterR * 6 + c));
                    if ((occ & bit) == 0) visit(curKey + mult[i], i, 1); // D
                }
            }
        }
    };

    // BFS from initial to enumerate connected component and record shortest paths (for forming moves)
    vector<int> q;
    q.reserve(1 << 20);
    distInit[startKey] = 0;
    q.push_back(startKey);
    size_t head = 0;

    int pos[MAXV];
    uint64_t occ = 0;

    while (head < q.size()) {
        int cur = q[head++];
        int d = distInit[cur];

        decodePosOcc(cur, pos, occ);

        forNeighbors(cur, pos, occ, [&](int nxt, int vidx, int dirIdx) {
            if (distInit[nxt] != -1) return;
            distInit[nxt] = d + 1;
            parent[nxt] = cur;
            prevVeh[nxt] = (uint8_t)(vidx + 1);
            prevDir[nxt] = (uint8_t)dirIdx;
            q.push_back(nxt);
        });
    }

    // Multi-source BFS from all goal states (red position == 6) within reachable component
    vector<int> distGoal(totalStates, -1);
    vector<int> q2;
    q2.reserve(1 << 20);
    const int redRange = rangev[0];

    for (int key = 0; key < totalStates; key++) {
        if (distInit[key] == -1) continue;
        if ((key % redRange) == 6) { // red out
            distGoal[key] = 0;
            q2.push_back(key);
        }
    }

    head = 0;
    while (head < q2.size()) {
        int cur = q2[head++];
        int d = distGoal[cur];

        decodePosOcc(cur, pos, occ);

        forNeighbors(cur, pos, occ, [&](int nxt, int /*vidx*/, int /*dirIdx*/) {
            if (distInit[nxt] == -1) return;      // must be reachable from initial
            if (distGoal[nxt] != -1) return;
            distGoal[nxt] = d + 1;
            q2.push_back(nxt);
        });
    }

    // Choose reachable state maximizing distGoal (hardest solvable puzzle)
    int bestKey = startKey;
    int bestSolve = distGoal[startKey];
    for (int key = 0; key < totalStates; key++) {
        if (distInit[key] == -1) continue;
        int dg = distGoal[key];
        if (dg > bestSolve) {
            bestSolve = dg;
            bestKey = key;
        }
    }

    // Reconstruct forming moves from startKey to bestKey
    vector<pair<int, char>> moves;
    int cur = bestKey;
    const char dirs[4] = {'U', 'D', 'L', 'R'};
    while (cur != startKey) {
        moves.push_back({(int)prevVeh[cur], dirs[prevDir[cur]]});
        cur = parent[cur];
    }
    reverse(moves.begin(), moves.end());

    cout << bestSolve << ' ' << moves.size() << "\n";
    for (auto &mv : moves) {
        cout << mv.first << ' ' << mv.second << "\n";
    }

    return 0;
}