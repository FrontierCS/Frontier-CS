#include <bits/stdc++.h>
using namespace std;

struct Vehicle {
    bool isH;
    int len;
    int fix; // row if H, col if V
};

struct MoveInfo {
    int id;
    char dir;
};

static const int NROWS = 6;
static const int NCOLS = 6;
static const int SHIFT = 4;
static const unsigned long long MASK = (1ULL << SHIFT) - 1;

int n; // number of vehicles
vector<Vehicle> veh;
vector<int> minPos_, maxPos_;

unsigned long long encode(const vector<int>& pos) {
    unsigned long long key = 0;
    for (int i = 1; i <= n; ++i) {
        key |= (unsigned long long)(pos[i] & MASK) << ((i - 1) * SHIFT);
    }
    return key;
}
void decode(unsigned long long key, int pos[]) {
    for (int i = 1; i <= n; ++i) {
        pos[i] = (int)(key & MASK);
        key >>= SHIFT;
    }
}

inline char invertDir(char c) {
    if (c == 'L') return 'R';
    if (c == 'R') return 'L';
    if (c == 'U') return 'D';
    if (c == 'D') return 'U';
    return c;
}

void buildGrid(const int pos[], unsigned char grid[NROWS][NCOLS]) {
    for (int r = 0; r < NROWS; ++r) for (int c = 0; c < NCOLS; ++c) grid[r][c] = 0;
    for (int i = 1; i <= n; ++i) {
        if (veh[i].isH) {
            int r = veh[i].fix;
            int left = pos[i];
            for (int c = left; c < left + veh[i].len; ++c) {
                if (0 <= c && c < NCOLS) grid[r][c] = (unsigned char)i;
            }
        } else {
            int c = veh[i].fix;
            int top = pos[i];
            for (int r = top; r < top + veh[i].len; ++r) {
                if (0 <= r && r < NROWS) grid[r][c] = (unsigned char)i;
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int board[6][6];
    int maxId = 0;
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            if (!(cin >> board[r][c])) return 0;
            maxId = max(maxId, board[r][c]);
        }
    }
    n = maxId;
    if (n == 0) {
        cout << "0 0\n";
        return 0;
    }
    // Determine vehicle properties
    vector<int> rmin(n + 1, 10), rmax(n + 1, -1), cmin(n + 1, 10), cmax(n + 1, -1);
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            int id = board[r][c];
            if (id == 0) continue;
            rmin[id] = min(rmin[id], r);
            rmax[id] = max(rmax[id], r);
            cmin[id] = min(cmin[id], c);
            cmax[id] = max(cmax[id], c);
        }
    }
    veh.assign(n + 1, Vehicle{});
    vector<int> initPos(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        if (rmin[i] == rmax[i]) {
            veh[i].isH = true;
            veh[i].len = cmax[i] - cmin[i] + 1;
            veh[i].fix = rmin[i];
            initPos[i] = cmin[i];
        } else {
            veh[i].isH = false;
            veh[i].len = rmax[i] - rmin[i] + 1;
            veh[i].fix = cmin[i];
            initPos[i] = rmin[i];
        }
    }
    // Constraints (min/max positions)
    minPos_.assign(n + 1, 0);
    maxPos_.assign(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        if (veh[i].isH) {
            if (i == 1) { // red car can move out to the right to left=6
                maxPos_[i] = 6;
            } else {
                maxPos_[i] = 6 - veh[i].len;
            }
        } else {
            maxPos_[i] = 6 - veh[i].len;
        }
    }

    unsigned long long initKey = encode(initPos);

    // BFS1: From initial, visit all states; record distInit; collect goals (pos1 == 6)
    unordered_map<unsigned long long, int> distInit;
    distInit.reserve(1 << 20);
    queue<unsigned long long> q1;
    distInit.emplace(initKey, 0);
    q1.push(initKey);

    vector<unsigned long long> goalStates;
    int posArrSize = n + 1;
    int *pos = new int[posArrSize];
    unsigned char grid[6][6];

    while (!q1.empty()) {
        unsigned long long cur = q1.front(); q1.pop();
        int dcur = distInit[cur];
        decode(cur, pos);
        if (pos[1] == 6) {
            goalStates.push_back(cur);
        }
        buildGrid(pos, grid);

        for (int i = 1; i <= n; ++i) {
            if (veh[i].isH) {
                int r = veh[i].fix;
                int left = pos[i];
                // move left
                if (left > minPos_[i]) {
                    int newLeft = left - 1;
                    if (newLeft >= 0) {
                        if (grid[r][newLeft] == 0) {
                            int old = pos[i];
                            pos[i] = newLeft;
                            unsigned long long nxt = encode(vector<int>(pos, pos + posArrSize));
                            if (!distInit.count(nxt)) {
                                distInit.emplace(nxt, dcur + 1);
                                q1.push(nxt);
                            }
                            pos[i] = old;
                        }
                    }
                }
                // move right
                if (left < maxPos_[i]) {
                    int ahead = left + veh[i].len;
                    bool can = false;
                    if (ahead < NCOLS) {
                        can = (grid[r][ahead] == 0);
                    } else {
                        // outside board
                        if (i == 1) can = true;
                    }
                    if (can) {
                        int old = pos[i];
                        pos[i] = left + 1;
                        unsigned long long nxt = encode(vector<int>(pos, pos + posArrSize));
                        if (!distInit.count(nxt)) {
                            distInit.emplace(nxt, dcur + 1);
                            q1.push(nxt);
                        }
                        pos[i] = old;
                    }
                }
            } else {
                int c = veh[i].fix;
                int top = pos[i];
                // move up
                if (top > minPos_[i]) {
                    int newTop = top - 1;
                    if (newTop >= 0) {
                        if (grid[newTop][c] == 0) {
                            int old = pos[i];
                            pos[i] = newTop;
                            unsigned long long nxt = encode(vector<int>(pos, pos + posArrSize));
                            if (!distInit.count(nxt)) {
                                distInit.emplace(nxt, dcur + 1);
                                q1.push(nxt);
                            }
                            pos[i] = old;
                        }
                    }
                }
                // move down
                if (top < maxPos_[i]) {
                    int below = top + veh[i].len;
                    if (below < NROWS && grid[below][c] == 0) {
                        int old = pos[i];
                        pos[i] = top + 1;
                        unsigned long long nxt = encode(vector<int>(pos, pos + posArrSize));
                        if (!distInit.count(nxt)) {
                            distInit.emplace(nxt, dcur + 1);
                            q1.push(nxt);
                        }
                        pos[i] = old;
                    }
                }
            }
        }
    }

    if (goalStates.empty()) {
        // Should not happen as per problem statement, but handle gracefully
        cout << "0 0\n";
        delete[] pos;
        return 0;
    }

    // BFS2: Multi-source from goalStates to compute distGoal
    unordered_map<unsigned long long, int> distGoal;
    distGoal.reserve(distInit.size() * 2 + 1);
    queue<unsigned long long> q2;
    for (auto g : goalStates) {
        if (!distGoal.count(g)) {
            distGoal.emplace(g, 0);
            q2.push(g);
        }
    }

    while (!q2.empty()) {
        unsigned long long cur = q2.front(); q2.pop();
        int dcur = distGoal[cur];
        decode(cur, pos);
        buildGrid(pos, grid);

        for (int i = 1; i <= n; ++i) {
            if (veh[i].isH) {
                int r = veh[i].fix;
                int left = pos[i];
                // left
                if (left > minPos_[i]) {
                    int newLeft = left - 1;
                    if (newLeft >= 0 && grid[r][newLeft] == 0) {
                        int old = pos[i];
                        pos[i] = newLeft;
                        unsigned long long nxt = encode(vector<int>(pos, pos + posArrSize));
                        if (!distGoal.count(nxt)) {
                            distGoal.emplace(nxt, dcur + 1);
                            q2.push(nxt);
                        }
                        pos[i] = old;
                    }
                }
                // right
                if (left < maxPos_[i]) {
                    int ahead = left + veh[i].len;
                    bool can = false;
                    if (ahead < NCOLS) {
                        can = (grid[r][ahead] == 0);
                    } else {
                        if (i == 1) can = true;
                    }
                    if (can) {
                        int old = pos[i];
                        pos[i] = left + 1;
                        unsigned long long nxt = encode(vector<int>(pos, pos + posArrSize));
                        if (!distGoal.count(nxt)) {
                            distGoal.emplace(nxt, dcur + 1);
                            q2.push(nxt);
                        }
                        pos[i] = old;
                    }
                }
            } else {
                int c = veh[i].fix;
                int top = pos[i];
                // up
                if (top > minPos_[i]) {
                    int newTop = top - 1;
                    if (newTop >= 0 && grid[newTop][c] == 0) {
                        int old = pos[i];
                        pos[i] = newTop;
                        unsigned long long nxt = encode(vector<int>(pos, pos + posArrSize));
                        if (!distGoal.count(nxt)) {
                            distGoal.emplace(nxt, dcur + 1);
                            q2.push(nxt);
                        }
                        pos[i] = old;
                    }
                }
                // down
                if (top < maxPos_[i]) {
                    int below = top + veh[i].len;
                    if (below < NROWS && grid[below][c] == 0) {
                        int old = pos[i];
                        pos[i] = top + 1;
                        unsigned long long nxt = encode(vector<int>(pos, pos + posArrSize));
                        if (!distGoal.count(nxt)) {
                            distGoal.emplace(nxt, dcur + 1);
                            q2.push(nxt);
                        }
                        pos[i] = old;
                    }
                }
            }
        }
    }

    // Choose best state (reachable from initial) maximizing distGoal
    int bestDist = -1;
    unsigned long long bestKey = initKey;
    for (const auto& kv : distInit) {
        auto it = distGoal.find(kv.first);
        if (it != distGoal.end()) {
            int d = it->second;
            if (d > bestDist) {
                bestDist = d;
                bestKey = kv.first;
            }
        }
    }

    // Reconstruct path from init to best using distInit gradient
    vector<MoveInfo> revMoves;
    unsigned long long cur = bestKey;
    while (cur != initKey) {
        int dcur = distInit[cur];
        decode(cur, pos);
        buildGrid(pos, grid);
        bool found = false;
        // From cur, try all neighbors; if neighbor has distInit = dcur - 1, step to it
        for (int i = 1; i <= n && !found; ++i) {
            if (veh[i].isH) {
                int r = veh[i].fix;
                int left = pos[i];
                // move left from cur to nxt
                if (left > minPos_[i]) {
                    int newLeft = left - 1;
                    if (newLeft >= 0 && grid[r][newLeft] == 0) {
                        int old = pos[i];
                        pos[i] = newLeft;
                        unsigned long long nxt = encode(vector<int>(pos, pos + posArrSize));
                        auto it = distInit.find(nxt);
                        if (it != distInit.end() && it->second == dcur - 1) {
                            // We moved L from cur to nxt, so forward move is R
                            revMoves.push_back({i, invertDir('L')});
                            cur = nxt;
                            found = true;
                        }
                        pos[i] = old;
                    }
                }
                if (found) break;
                // move right from cur to nxt
                if (left < maxPos_[i]) {
                    int ahead = left + veh[i].len;
                    bool can = false;
                    if (ahead < NCOLS) can = (grid[r][ahead] == 0);
                    else if (i == 1) can = true;
                    if (can) {
                        int old = pos[i];
                        pos[i] = left + 1;
                        unsigned long long nxt = encode(vector<int>(pos, pos + posArrSize));
                        auto it = distInit.find(nxt);
                        if (it != distInit.end() && it->second == dcur - 1) {
                            // We moved R from cur to nxt, so forward move is L
                            revMoves.push_back({i, invertDir('R')});
                            cur = nxt;
                            found = true;
                        }
                        pos[i] = old;
                    }
                }
            } else {
                int c = veh[i].fix;
                int top = pos[i];
                // move up
                if (top > minPos_[i]) {
                    int newTop = top - 1;
                    if (newTop >= 0 && grid[newTop][c] == 0) {
                        int old = pos[i];
                        pos[i] = newTop;
                        unsigned long long nxt = encode(vector<int>(pos, pos + posArrSize));
                        auto it = distInit.find(nxt);
                        if (it != distInit.end() && it->second == dcur - 1) {
                            revMoves.push_back({i, invertDir('U')});
                            cur = nxt;
                            found = true;
                        }
                        pos[i] = old;
                    }
                }
                if (found) break;
                // move down
                if (top < maxPos_[i]) {
                    int below = top + veh[i].len;
                    if (below < NROWS && grid[below][c] == 0) {
                        int old = pos[i];
                        pos[i] = top + 1;
                        unsigned long long nxt = encode(vector<int>(pos, pos + posArrSize));
                        auto it = distInit.find(nxt);
                        if (it != distInit.end() && it->second == dcur - 1) {
                            revMoves.push_back({i, invertDir('D')});
                            cur = nxt;
                            found = true;
                        }
                        pos[i] = old;
                    }
                }
            }
        }
        if (!found) {
            // Fallback: should not happen
            break;
        }
    }
    reverse(revMoves.begin(), revMoves.end());

    int stepsToSolve = bestDist;
    int stepsToForm = (int)revMoves.size();

    cout << stepsToSolve << " " << stepsToForm << "\n";
    for (auto &m : revMoves) {
        cout << m.id << " " << m.dir << "\n";
    }

    delete[] pos;
    return 0;
}