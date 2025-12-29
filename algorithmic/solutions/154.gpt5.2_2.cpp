#include <bits/stdc++.h>
using namespace std;

struct Pos {
    int x, y;
};

static constexpr int H = 30, W = 30;

static inline bool inb(int x, int y) { return 1 <= x && x <= H && 1 <= y && y <= W; }

struct Partition {
    bool vertical;   // true: block column K; false: block row K
    int K;           // 2..29
    bool targetNeg;  // vertical: left (y<K), horizontal: top (x<K)
    int gate;        // varying coordinate: row if vertical, col if horizontal
};

static inline bool onTarget(const Partition& P, const Pos& p) {
    if (P.vertical) return P.targetNeg ? (p.y < P.K) : (p.y > P.K);
    return P.targetNeg ? (p.x < P.K) : (p.x > P.K);
}

static inline bool isGateCell(const Partition& P, const Pos& p) {
    if (P.vertical) return p.x == P.gate && p.y == P.K;
    return p.x == P.K && p.y == P.gate;
}

static inline Pos barrierCell(const Partition& P, int t) {
    if (P.vertical) return Pos{t, P.K};
    return Pos{P.K, t};
}

static inline int deltaToTarget(const Partition& P) {
    (void)P;
    return P.targetNeg ? -1 : +1;
}

static inline Pos buildGoalPos(const Partition& P, int t) {
    int d = deltaToTarget(P);
    if (P.vertical) return Pos{t, P.K + d};
    return Pos{P.K + d, t};
}

static inline char moveCharVertical(int dx) { return (dx < 0) ? 'U' : 'D'; }
static inline char moveCharHorizontal(int dy) { return (dy < 0) ? 'L' : 'R'; }

static inline char evacStep(const Partition& P, const Pos& p) {
    int d = deltaToTarget(P); // direction from barrier/gate toward target side (also from opp-adj into gate)
    if (isGateCell(P, p)) {
        if (P.vertical) return (d == -1) ? 'L' : 'R';
        return (d == -1) ? 'U' : 'D';
    }

    if (P.vertical) {
        int oppAdjCol = P.K - d;
        int gateRow = P.gate;
        if (p.x != gateRow) return moveCharVertical(gateRow - p.x);
        if (p.y != oppAdjCol) {
            int ny = p.y + ((oppAdjCol < p.y) ? -1 : +1);
            // keep within opposite side columns
            if ((d == -1 && ny <= P.K) || (d == +1 && ny >= P.K)) return '.';
            return moveCharHorizontal(oppAdjCol - p.y);
        }
        // enter gate
        return (d == -1) ? 'L' : 'R';
    } else {
        int oppAdjRow = P.K - d;
        int gateCol = P.gate;
        if (p.y != gateCol) return moveCharHorizontal(gateCol - p.y);
        if (p.x != oppAdjRow) {
            int nx = p.x + ((oppAdjRow < p.x) ? -1 : +1);
            if ((d == -1 && nx <= P.K) || (d == +1 && nx >= P.K)) return '.';
            return moveCharVertical(oppAdjRow - p.x);
        }
        // enter gate
        return (d == -1) ? 'U' : 'D';
    }
}

static inline char buildDirChar(const Partition& P) {
    int d = deltaToTarget(P);
    if (P.vertical) return (d == -1) ? 'r' : 'l';  // from target side into barrier
    return (d == -1) ? 'd' : 'u';
}

static inline Pos applyMove(const Pos& p, char act) {
    Pos q = p;
    if (act == 'U' || act == 'u') q.x--;
    else if (act == 'D' || act == 'd') q.x++;
    else if (act == 'L' || act == 'l') q.y--;
    else if (act == 'R' || act == 'r') q.y++;
    return q;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<Pos> pets(N);
    vector<int> ptype(N);
    for (int i = 0; i < N; i++) {
        cin >> pets[i].x >> pets[i].y >> ptype[i];
    }
    int M;
    cin >> M;
    vector<Pos> humans(M);
    for (int i = 0; i < M; i++) cin >> humans[i].x >> humans[i].y;

    // Choose partition line and side by crude expected objective from initial positions.
    auto evalConfig = [&](bool vertical, int K, bool targetNeg) -> double {
        double petInLine = 0.0, petTarget = 0.0;
        for (auto &p : pets) {
            int coord = vertical ? p.y : p.x;
            if (coord == K) petInLine += 1.0;
            else if (targetNeg ? (coord < K) : (coord > K)) petTarget += 1.0;
        }
        petTarget += 0.5 * petInLine;

        double area = vertical ? (targetNeg ? 30.0 * (K - 1) : 30.0 * (30 - K))
                               : (targetNeg ? 30.0 * (K - 1) : 30.0 * (30 - K));
        if (area <= 0.0) return -1e100;
        return log(area / 900.0) - petTarget * log(2.0);
    };

    Partition P{};
    double best = -1e100;
    for (bool vertical : {true, false}) {
        for (int K = 2; K <= 29; K++) {
            for (bool targetNeg : {true, false}) {
                double sc = evalConfig(vertical, K, targetNeg);
                if (sc > best) {
                    best = sc;
                    P.vertical = vertical;
                    P.K = K;
                    P.targetNeg = targetNeg;
                }
            }
        }
    }

    // Choose gate coordinate (row if vertical, col if horizontal) to avoid initial pet crowding and reduce human travel.
    auto petNeighborhoodCount = [&](int gateCoord) -> int {
        Pos gc = P.vertical ? Pos{gateCoord, P.K} : Pos{P.K, gateCoord};
        int cnt = 0;
        static const int dx[5] = {0, -1, 1, 0, 0};
        static const int dy[5] = {0, 0, 0, -1, 1};
        for (int i = 0; i < N; i++) {
            for (int k = 0; k < 5; k++) {
                int nx = gc.x + dx[k], ny = gc.y + dy[k];
                if (inb(nx, ny) && pets[i].x == nx && pets[i].y == ny) {
                    cnt++;
                    break;
                }
            }
        }
        return cnt;
    };
    auto humanAxisDist = [&](int gateCoord) -> int {
        int sum = 0;
        for (auto &h : humans) {
            sum += P.vertical ? abs(h.x - gateCoord) : abs(h.y - gateCoord);
        }
        return sum;
    };
    int bestGate = 15;
    long long bestGateScore = (1LL<<60);
    for (int g = 1; g <= 30; g++) {
        int pc = petNeighborhoodCount(g);
        int hd = humanAxisDist(g);
        long long score = 50LL * pc + hd;
        if (score < bestGateScore) {
            bestGateScore = score;
            bestGate = g;
        }
    }
    P.gate = bestGate;

    vector<vector<bool>> blocked(H + 1, vector<bool>(W + 1, false));

    auto rebuildCounts = [&](vector<vector<int>>& petCnt, vector<vector<int>>& humanCnt) {
        for (int i = 1; i <= H; i++) {
            fill(petCnt[i].begin(), petCnt[i].end(), 0);
            fill(humanCnt[i].begin(), humanCnt[i].end(), 0);
        }
        for (auto &p : pets) petCnt[p.x][p.y]++;
        for (auto &h : humans) humanCnt[h.x][h.y]++;
    };

    auto canBuildCell = [&](const Pos& c, const vector<vector<int>>& petCnt, const vector<vector<int>>& humanCnt) -> bool {
        if (!inb(c.x, c.y)) return false;
        if (humanCnt[c.x][c.y] > 0) return false;
        if (petCnt[c.x][c.y] > 0) return false;
        static const int dx[4] = {-1, 1, 0, 0};
        static const int dy[4] = {0, 0, -1, 1};
        for (int k = 0; k < 4; k++) {
            int nx = c.x + dx[k], ny = c.y + dy[k];
            if (inb(nx, ny) && petCnt[nx][ny] > 0) return false;
        }
        return true;
    };

    auto passable = [&](int x, int y) -> bool {
        if (!inb(x, y)) return false;
        return !blocked[x][y];
    };

    auto oneStepToward = [&](const Pos& from, const Pos& to) -> char {
        if (P.vertical) {
            if (from.y != to.y) return (to.y < from.y) ? 'L' : 'R';
            if (from.x != to.x) return (to.x < from.x) ? 'U' : 'D';
        } else {
            if (from.x != to.x) return (to.x < from.x) ? 'U' : 'D';
            if (from.y != to.y) return (to.y < from.y) ? 'L' : 'R';
        }
        return '.';
    };

    vector<vector<int>> petCnt(H + 1, vector<int>(W + 1, 0));
    vector<vector<int>> humanCnt(H + 1, vector<int>(W + 1, 0));

    for (int turn = 0; turn < 300; turn++) {
        rebuildCounts(petCnt, humanCnt);

        bool allOnT = true;
        for (auto &h : humans) {
            if (!onTarget(P, h)) { allOnT = false; break; }
        }
        bool wantCloseGate = allOnT;

        // Determine remaining barrier cells to build
        vector<int> need;
        need.reserve(30);
        for (int t = 1; t <= 30; t++) {
            if (!wantCloseGate && t == P.gate) continue;
            Pos b = barrierCell(P, t);
            if (!blocked[b.x][b.y]) need.push_back(t);
        }
        bool barrierDone = need.empty();

        vector<char> act(M, '.');
        vector<Pos> willBlock;
        willBlock.reserve(M);

        // Evacuate those not on target side
        for (int i = 0; i < M; i++) {
            if (onTarget(P, humans[i])) continue;
            char mv = evacStep(P, humans[i]);
            if (mv == '.') { act[i] = '.'; continue; }
            Pos to = applyMove(humans[i], mv);
            if (!passable(to.x, to.y)) { act[i] = '.'; continue; }
            act[i] = mv;
        }

        if (!barrierDone) {
            // Builders: those on target side and not already assigned move
            vector<int> builders;
            builders.reserve(M);
            for (int i = 0; i < M; i++) {
                if (act[i] != '.') continue;
                if (!onTarget(P, humans[i])) continue;
                builders.push_back(i);
            }

            // Buildability for each t
            array<bool, 31> canNow{};
            for (int t : need) {
                Pos b = barrierCell(P, t);
                canNow[t] = canBuildCell(b, petCnt, humanCnt);
            }

            // Candidate list: prefer buildable
            vector<int> cand = need;
            stable_sort(cand.begin(), cand.end(), [&](int a, int b) {
                if (canNow[a] != canNow[b]) return canNow[a] > canNow[b];
                return a < b;
            });

            // Assign distinct targets greedily
            vector<int> assignedT(M, -1);
            vector<char> plannedBuild(M, '.');
            vector<bool> used(31, false);

            for (int idx : builders) {
                long long bestCost = (1LL<<60);
                int bestT = -1;
                for (int t : cand) {
                    if (used[t]) continue;
                    Pos goal = buildGoalPos(P, t);
                    long long dist = llabs(humans[idx].x - goal.x) + llabs(humans[idx].y - goal.y);
                    long long cost = dist + (canNow[t] ? 0 : 1000);
                    if (cost < bestCost) {
                        bestCost = cost;
                        bestT = t;
                    }
                }
                if (bestT != -1) {
                    used[bestT] = true;
                    assignedT[idx] = bestT;
                }
            }

            // Pass 1: decide build actions for those already at goal and buildable now
            char bchar = buildDirChar(P);
            for (int idx : builders) {
                int t = assignedT[idx];
                if (t == -1) continue;
                Pos goal = buildGoalPos(P, t);
                if (humans[idx].x == goal.x && humans[idx].y == goal.y && canNow[t]) {
                    Pos b = barrierCell(P, t);
                    // ensure our build direction indeed targets barrier cell
                    Pos tgt = applyMove(humans[idx], bchar);
                    if (tgt.x == b.x && tgt.y == b.y && inb(tgt.x, tgt.y) && canBuildCell(b, petCnt, humanCnt)) {
                        plannedBuild[idx] = bchar;
                        willBlock.push_back(b);
                    }
                }
            }

            // Make a set of cells that will be blocked this turn
            vector<vector<bool>> toBeBlocked(H + 1, vector<bool>(W + 1, false));
            for (auto &b : willBlock) if (inb(b.x, b.y)) toBeBlocked[b.x][b.y] = true;

            // Pass 2: decide movement for other builders
            for (int idx : builders) {
                if (plannedBuild[idx] != '.') continue;
                int t = assignedT[idx];
                if (t == -1) continue;
                Pos goal = buildGoalPos(P, t);

                if (humans[idx].x == goal.x && humans[idx].y == goal.y) {
                    act[idx] = '.'; // wait
                    continue;
                }

                char mv = oneStepToward(humans[idx], goal);
                if (mv == '.') { act[idx] = '.'; continue; }
                Pos to = applyMove(humans[idx], mv);
                if (!passable(to.x, to.y)) { act[idx] = '.'; continue; }
                if (toBeBlocked[to.x][to.y]) { act[idx] = '.'; continue; }
                act[idx] = mv;
            }

            // Apply build actions
            for (int i = 0; i < M; i++) if (plannedBuild[i] != '.') act[i] = plannedBuild[i];
        }

        string out;
        out.reserve(M);
        for (int i = 0; i < M; i++) out.push_back(act[i]);
        cout << out << '\n' << flush;

        // Read pet move strings (interactive)
        vector<string> mv(N);
        for (int i = 0; i < N; i++) {
            if (!(cin >> mv[i])) return 0;
        }

        // Apply wall builds
        for (int i = 0; i < M; i++) {
            char a = act[i];
            if (a == 'u' || a == 'd' || a == 'l' || a == 'r') {
                Pos t = applyMove(humans[i], a);
                if (inb(t.x, t.y)) blocked[t.x][t.y] = true;
            }
        }

        // Apply human moves
        for (int i = 0; i < M; i++) {
            char a = act[i];
            if (a == 'U' || a == 'D' || a == 'L' || a == 'R') {
                Pos t = applyMove(humans[i], a);
                if (inb(t.x, t.y) && !blocked[t.x][t.y]) humans[i] = t;
            }
        }

        // Apply pet moves based on judge input
        for (int i = 0; i < N; i++) {
            const string &s = mv[i];
            if (s == ".") continue;
            for (char c : s) {
                Pos np = pets[i];
                if (c == 'U') np.x--;
                else if (c == 'D') np.x++;
                else if (c == 'L') np.y--;
                else if (c == 'R') np.y++;
                if (inb(np.x, np.y) && !blocked[np.x][np.y]) pets[i] = np;
            }
        }
    }

    return 0;
}