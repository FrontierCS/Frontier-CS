#include <bits/stdc++.h>
using namespace std;

struct BlueBase {
    int x, y;
    long long fuel, missiles;
    int d_unused, v_unused;
};

struct RedBase {
    int x, y;
    long long d, v;
};

struct Fighter {
    int id;
    int x, y;
    int G, C;
    int baseIdx;
};

struct BFSData {
    vector<int> dist;
    vector<int> par;
    vector<char> pdir;
    int startIdx;
};

struct Option {
    bool ok = false;
    int L = INT_MAX;
    int attackDir = -1;
    int adjIdx = -1;
    int redIdx = -1;
};

struct Plan {
    bool active = false;
    vector<int> path;
    int attackDir = -1;
    int missilesToFire = 0;
    int fuelToTake = 0; // equals path length
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<string> grid(n);
    for (int i = 0; i < n; i++) cin >> grid[i];

    int numBlue;
    cin >> numBlue;
    vector<BlueBase> blue(numBlue);
    vector<vector<int>> blueIdx(n, vector<int>(m, -1));
    for (int i = 0; i < numBlue; i++) {
        int x, y;
        cin >> x >> y;
        long long g, c;
        int d, v;
        cin >> g >> c >> d >> v;
        blue[i] = {x, y, g, c, d, v};
        blueIdx[x][y] = i;
    }

    int numRed;
    cin >> numRed;
    vector<RedBase> red(numRed);
    for (int i = 0; i < numRed; i++) {
        int x, y;
        long long g, c, d, v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
        red[i] = {x, y, d, v};
    }

    int k;
    cin >> k;
    vector<Fighter> fighters(k);
    for (int i = 0; i < k; i++) {
        int x, y, G, C;
        cin >> x >> y >> G >> C;
        fighters[i] = {i, x, y, G, C, -1};
        if (x >= 0 && x < n && y >= 0 && y < m) {
            fighters[i].baseIdx = (blueIdx[x][y] >= 0 ? blueIdx[x][y] : -1);
        }
    }

    auto inside = [&](int x, int y) -> bool {
        return (x >= 0 && x < n && y >= 0 && y < m);
    };
    auto idx = [&](int x, int y) -> int {
        return x * m + y;
    };
    const int INF = 1e9;
    int dx[4] = {-1, 1, 0, 0};
    int dy[4] = {0, 0, -1, 1};

    // BFS for each fighter
    vector<BFSData> bfsAll(k);
    for (int fi = 0; fi < k; fi++) {
        BFSData data;
        data.dist.assign(n * m, INF);
        data.par.assign(n * m, -1);
        data.pdir.assign(n * m, -1);
        int sx = fighters[fi].x, sy = fighters[fi].y;
        int sidx = idx(sx, sy);
        data.startIdx = sidx;
        deque<int> q;
        data.dist[sidx] = 0;
        q.push_back(sidx);
        while (!q.empty()) {
            int u = q.front(); q.pop_front();
            int ux = u / m, uy = u % m;
            for (int d = 0; d < 4; d++) {
                int vx = ux + dx[d];
                int vy = uy + dy[d];
                if (!inside(vx, vy)) continue;
                if (grid[vx][vy] == '#') continue; // cannot enter red base cell
                int v = idx(vx, vy);
                if (data.dist[v] > data.dist[u] + 1) {
                    data.dist[v] = data.dist[u] + 1;
                    data.par[v] = u;
                    data.pdir[v] = (char)d; // move direction from parent to v
                    q.push_back(v);
                }
            }
        }
        bfsAll[fi] = move(data);
    }

    auto getAdjOptionForRed = [&](const BFSData &bfs, const RedBase &rb, int redIdxVal) -> Option {
        Option opt;
        int bestL = INF;
        int bestDir = -1;
        int bestAdj = -1;
        for (int d = 0; d < 4; d++) {
            int ax = rb.x - dx[d];
            int ay = rb.y - dy[d];
            if (!inside(ax, ay)) continue;
            if (grid[ax][ay] == '#') continue; // cannot stand on red base cell
            int aidx = idx(ax, ay);
            int L = bfs.dist[aidx];
            if (L < bestL) {
                bestL = L;
                bestDir = d;
                bestAdj = aidx;
            }
        }
        if (bestL < INF) {
            opt.ok = true;
            opt.L = bestL;
            opt.attackDir = bestDir;
            opt.adjIdx = bestAdj;
            opt.redIdx = redIdxVal;
        }
        return opt;
    };

    auto getBestGlobalOption = [&](const BFSData &bfs, const vector<RedBase> &reds, const vector<char> &exclude) -> Option {
        Option best;
        long long bestValueTie = -1;
        for (int ri = 0; ri < (int)reds.size(); ri++) {
            if (!reds.size()) break;
            if (!exclude.empty() && exclude[ri]) continue;
            Option op = getAdjOptionForRed(bfs, reds[ri], ri);
            if (!op.ok) continue;
            if (!best.ok || op.L < best.L || (op.L == best.L && reds[ri].v > bestValueTie)) {
                best = op;
                bestValueTie = reds[ri].v;
            }
        }
        return best;
    };

    // Copy remaining supplies
    vector<long long> remFuel(numBlue), remMiss(numBlue);
    for (int i = 0; i < numBlue; i++) {
        remFuel[i] = blue[i].fuel;
        remMiss[i] = blue[i].missiles;
    }

    vector<Plan> plans(k); // initially inactive

    // Choose red base with minimal defense
    int bMinD = -1;
    if (numRed > 0) {
        long long bestD = LLONG_MAX;
        long long bestV = -1;
        for (int i = 0; i < numRed; i++) {
            if (red[i].d < bestD || (red[i].d == bestD && red[i].v > bestV)) {
                bestD = red[i].d;
                bestV = red[i].v;
                bMinD = i;
            }
        }
    }

    vector<char> excluded(numRed, 0);

    // Try to assign fighters to destroy the easiest base bMinD
    if (bMinD != -1) {
        struct Cand { int fId; int L; int adjIdx; int attackDir; };
        vector<Cand> candidates;
        for (int f = 0; f < k; f++) {
            if (fighters[f].baseIdx < 0) continue;
            Option op = getAdjOptionForRed(bfsAll[f], red[bMinD], bMinD);
            if (!op.ok) continue;
            if (op.L > fighters[f].G) continue; // cannot carry enough fuel even if base has
            candidates.push_back({f, op.L, op.adjIdx, op.attackDir});
        }
        sort(candidates.begin(), candidates.end(), [&](const Cand &a, const Cand &b) {
            if (a.L != b.L) return a.L < b.L;
            return a.fId < b.fId;
        });

        long long need = red[bMinD].d;
        long long sumMiss = 0;
        struct Assigned {
            int fId;
            int fuel;
            int missiles;
            int baseIdx;
            int adjIdx;
            int attackDir;
        };
        vector<Assigned> assigned;
        for (auto &c : candidates) {
            if (sumMiss >= need) break;
            int f = c.fId;
            int b0 = fighters[f].baseIdx;
            long long availFuel = min((long long)fighters[f].G, remFuel[b0]);
            if (availFuel < c.L) continue;
            long long availMiss = min((long long)fighters[f].C, remMiss[b0]);
            if (availMiss <= 0) continue;
            long long take = min(availMiss, need - sumMiss);
            if (take <= 0) continue;
            remFuel[b0] -= c.L;
            remMiss[b0] -= take;
            assigned.push_back({f, c.L, (int)take, b0, c.adjIdx, c.attackDir});
            sumMiss += take;
        }
        if (sumMiss >= need) {
            // commit plans
            for (auto &a : assigned) {
                Plan p;
                p.active = true;
                p.missilesToFire = a.missiles;
                p.fuelToTake = a.fuel;
                p.attackDir = a.attackDir;
                // reconstruct path
                vector<int> rev;
                int cur = a.adjIdx;
                const BFSData &bfs = bfsAll[a.fId];
                while (cur != bfs.startIdx && cur != -1) {
                    rev.push_back((int)bfs.pdir[cur]);
                    cur = bfs.par[cur];
                }
                reverse(rev.begin(), rev.end());
                p.path = move(rev);
                plans[a.fId] = move(p);
            }
            excluded[bMinD] = 1; // avoid targeting it again
        } else {
            // revert resource reservations
            for (auto &a : assigned) {
                remFuel[a.baseIdx] += a.fuel;
                remMiss[a.baseIdx] += a.missiles;
            }
        }
    }

    // For remaining fighters, plan nearest target individually
    for (int f = 0; f < k; f++) {
        if (plans[f].active) continue;
        int b0 = fighters[f].baseIdx;
        if (b0 < 0) continue;
        Option op = getBestGlobalOption(bfsAll[f], red, excluded);
        if (!op.ok) continue;
        int L = op.L;
        if (L > fighters[f].G) continue; // capacity insufficient
        long long availFuel = min((long long)fighters[f].G, remFuel[b0]);
        if (availFuel < L) continue; // cannot reach
        long long availMiss = min((long long)fighters[f].C, remMiss[b0]);
        if (availMiss <= 0) continue;
        long long take = min(availMiss, red[op.redIdx].d);
        if (take <= 0) continue;

        // allocate
        remFuel[b0] -= L;
        remMiss[b0] -= take;

        Plan p;
        p.active = true;
        p.missilesToFire = (int)take;
        p.fuelToTake = L;
        p.attackDir = op.attackDir;
        // reconstruct path
        vector<int> rev;
        int cur = op.adjIdx;
        const BFSData &bfs = bfsAll[f];
        while (cur != bfs.startIdx && cur != -1) {
            rev.push_back((int)bfs.pdir[cur]);
            cur = bfs.par[cur];
        }
        reverse(rev.begin(), rev.end());
        p.path = move(rev);
        plans[f] = move(p);
    }

    // Build frames: frame 0 -> fuel/missile only, moves start at frame 1, attack at frame pathLen+1
    int maxLen = 0;
    for (int f = 0; f < k; f++) {
        if (!plans[f].active) continue;
        int L = (int)plans[f].path.size();
        maxLen = max(maxLen, L);
    }
    int totalFrames = maxLen + 2; // 0: refuel/reload; 1..L: moves; L+1: attack

    vector<vector<string>> frames(totalFrames);
    // Frame 0: issue fuel/missile
    for (int f = 0; f < k; f++) {
        if (!plans[f].active) continue;
        if (plans[f].fuelToTake > 0) {
            frames[0].push_back("fuel " + to_string(fighters[f].id) + " " + to_string(plans[f].fuelToTake));
        }
        if (plans[f].missilesToFire > 0) {
            frames[0].push_back("missile " + to_string(fighters[f].id) + " " + to_string(plans[f].missilesToFire));
        }
    }
    // Moves
    for (int f = 0; f < k; f++) {
        if (!plans[f].active) continue;
        for (int step = 0; step < (int)plans[f].path.size(); step++) {
            int frameIdx = step + 1; // moves start at frame 1
            int dir = plans[f].path[step];
            frames[frameIdx].push_back("move " + to_string(fighters[f].id) + " " + to_string(dir));
        }
    }
    // Attacks
    for (int f = 0; f < k; f++) {
        if (!plans[f].active) continue;
        if (plans[f].missilesToFire > 0) {
            int frameIdx = (int)plans[f].path.size() + 1; // attack after arrival
            frames[frameIdx].push_back("attack " + to_string(fighters[f].id) + " " + to_string(plans[f].attackDir) + " " + to_string(plans[f].missilesToFire));
        }
    }

    // Output frames
    for (int t = 0; t < totalFrames; t++) {
        for (auto &cmd : frames[t]) {
            cout << cmd << "\n";
        }
        cout << "OK\n";
    }

    return 0;
}