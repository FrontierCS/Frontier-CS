#include <bits/stdc++.h>
using namespace std;

struct BlueBase {
    int x, y;
    long long fuel, missiles;
};

struct RedBase {
    int x, y;
    long long defense, value;
};

struct Fighter {
    int x, y;
    int G, C;
    int baseIdx;
};

struct BFSData {
    int n, m;
    vector<int> dist;
    vector<int> parent;
    vector<unsigned char> pdir; // dir from parent to node
};

static const int DX[4] = {-1, 1, 0, 0};
static const int DY[4] = {0, 0, -1, 1};

static inline int idx(int x, int y, int m) { return x * m + y; }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<string> grid(n);
    for (int i = 0; i < n; i++) cin >> grid[i];

    int nb;
    cin >> nb;
    vector<BlueBase> blue(nb);
    vector<int> blueAt(n * m, -1);
    for (int i = 0; i < nb; i++) {
        int x, y;
        long long g, c, d, v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
        blue[i] = {x, y, g, c};
        if (0 <= x && x < n && 0 <= y && y < m) blueAt[idx(x, y, m)] = i;
    }

    int nr;
    cin >> nr;
    vector<RedBase> red(nr);
    for (int i = 0; i < nr; i++) {
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
        int bidx = -1;
        if (0 <= x && x < n && 0 <= y && y < m) bidx = blueAt[idx(x, y, m)];
        fighters[i] = {x, y, G, C, bidx};
    }

    // BFS for each fighter with all red base cells blocked (grid '#')
    vector<BFSData> bfs(k);
    for (int fi = 0; fi < k; fi++) {
        BFSData bd;
        bd.n = n; bd.m = m;
        int N = n * m;
        bd.dist.assign(N, -1);
        bd.parent.assign(N, -1);
        bd.pdir.assign(N, 255);

        int sx = fighters[fi].x, sy = fighters[fi].y;
        if (!(0 <= sx && sx < n && 0 <= sy && sy < m) || grid[sx][sy] == '#') {
            bfs[fi] = std::move(bd);
            continue;
        }

        deque<int> q;
        int s = idx(sx, sy, m);
        bd.dist[s] = 0;
        q.push_back(s);

        while (!q.empty()) {
            int cur = q.front(); q.pop_front();
            int cx = cur / m, cy = cur % m;
            int cd = bd.dist[cur];
            for (int dir = 0; dir < 4; dir++) {
                int nx = cx + DX[dir], ny = cy + DY[dir];
                if (nx < 0 || nx >= n || ny < 0 || ny >= m) continue;
                if (grid[nx][ny] == '#') continue;
                int ni = idx(nx, ny, m);
                if (bd.dist[ni] != -1) continue;
                bd.dist[ni] = cd + 1;
                bd.parent[ni] = cur;
                bd.pdir[ni] = (unsigned char)dir;
                q.push_back(ni);
            }
        }
        bfs[fi] = std::move(bd);
    }

    struct Cand {
        long long metric;
        int ridx;
        int mindist;
    };

    vector<Cand> candidates;
    candidates.reserve(nr);

    // Build candidates with a quick reachability estimate.
    for (int r = 0; r < nr; r++) {
        int rx = red[r].x, ry = red[r].y;
        bool hasAdj = false;
        int minDistAll = INT_MAX;

        for (int a = 0; a < 4; a++) {
            int ax = rx + DX[a], ay = ry + DY[a];
            if (ax < 0 || ax >= n || ay < 0 || ay >= m) continue;
            if (grid[ax][ay] == '#') continue;
            hasAdj = true;
        }
        if (!hasAdj) continue;

        for (int fi = 0; fi < k; fi++) {
            int best = INT_MAX;
            for (int a = 0; a < 4; a++) {
                int ax = rx + DX[a], ay = ry + DY[a];
                if (ax < 0 || ax >= n || ay < 0 || ay >= m) continue;
                if (grid[ax][ay] == '#') continue;
                int ai = idx(ax, ay, m);
                int d = bfs[fi].dist[ai];
                if (d >= 0) best = min(best, d);
            }
            minDistAll = min(minDistAll, best);
        }
        if (minDistAll == INT_MAX) continue;

        long long d = max(1LL, red[r].defense);
        long long metric = (red[r].value * 1000000LL) / d - 1000LL * (long long)minDistAll;
        candidates.push_back({metric, r, minDistAll});
    }

    sort(candidates.begin(), candidates.end(), [](const Cand& a, const Cand& b) {
        if (a.metric != b.metric) return a.metric > b.metric;
        return a.mindist < b.mindist;
    });

    bool found = false;
    int chosenR = -1;
    int chosenMask = 0;

    vector<int> chosenReqFuel(k, INT_MAX);
    vector<int> chosenAdjIdx(k, -1);
    vector<int> chosenAttackDir(k, -1);

    int evaluateLimit = min<int>((int)candidates.size(), 2000);

    for (int ci = 0; ci < evaluateLimit && !found; ci++) {
        int r = candidates[ci].ridx;
        int rx = red[r].x, ry = red[r].y;

        vector<int> reqFuel(k, INT_MAX);
        vector<int> adjIndex(k, -1);
        vector<int> attackDir(k, -1);

        // For each fighter, pick best adjacent cell
        for (int fi = 0; fi < k; fi++) {
            int bestD = INT_MAX;
            int bestAdj = -1;
            int bestAtkDir = -1;

            for (int a = 0; a < 4; a++) {
                int ax = rx + DX[a], ay = ry + DY[a];
                if (ax < 0 || ax >= n || ay < 0 || ay >= m) continue;
                if (grid[ax][ay] == '#') continue;
                int ai = idx(ax, ay, m);
                int d = bfs[fi].dist[ai];
                if (d < 0) continue;
                if (d < bestD) {
                    bestD = d;
                    bestAdj = ai;
                    // attack direction from adj to base
                    int fx = ax, fy = ay;
                    int ddx = rx - fx, ddy = ry - fy;
                    int ad = -1;
                    if (ddx == -1 && ddy == 0) ad = 0;       // base up
                    else if (ddx == 1 && ddy == 0) ad = 1;   // base down
                    else if (ddx == 0 && ddy == -1) ad = 2;  // base left
                    else if (ddx == 0 && ddy == 1) ad = 3;   // base right
                    bestAtkDir = ad;
                }
            }
            if (bestAdj != -1) {
                reqFuel[fi] = bestD;
                adjIndex[fi] = bestAdj;
                attackDir[fi] = bestAtkDir;
            }
        }

        int bestMask = -1;
        int bestMakespan = INT_MAX;
        long long bestSumFuel = (1LL << 60);

        int totalMasks = 1 << k;
        for (int mask = 1; mask < totalMasks; mask++) {
            vector<long long> usedFuel(nb, 0), capMiss(nb, 0);
            int makespan = 0;
            long long sumFuel = 0;
            bool ok = true;

            for (int fi = 0; fi < k; fi++) if (mask & (1 << fi)) {
                if (reqFuel[fi] == INT_MAX) { ok = false; break; }
                if (reqFuel[fi] > fighters[fi].G) { ok = false; break; }
                int b = fighters[fi].baseIdx;
                if (b < 0 || b >= nb) { ok = false; break; }
                usedFuel[b] += reqFuel[fi];
                capMiss[b] += fighters[fi].C;
                makespan = max(makespan, reqFuel[fi]);
                sumFuel += reqFuel[fi];
            }
            if (!ok) continue;

            for (int b = 0; b < nb; b++) {
                if (usedFuel[b] > blue[b].fuel) { ok = false; break; }
            }
            if (!ok) continue;

            long long totalMiss = 0;
            for (int b = 0; b < nb; b++) {
                totalMiss += min(blue[b].missiles, capMiss[b]);
            }
            if (totalMiss < red[r].defense) continue;

            int framesNeeded = 2 + makespan; // load + moves + attack
            if (framesNeeded > 15000) continue;

            if (makespan < bestMakespan || (makespan == bestMakespan && sumFuel < bestSumFuel)) {
                bestMakespan = makespan;
                bestSumFuel = sumFuel;
                bestMask = mask;
            }
        }

        if (bestMask != -1) {
            found = true;
            chosenR = r;
            chosenMask = bestMask;
            chosenReqFuel = std::move(reqFuel);
            chosenAdjIdx = std::move(adjIndex);
            chosenAttackDir = std::move(attackDir);
            break;
        }
    }

    if (!found) {
        cout << "OK\n";
        return 0;
    }

    // Allocate fuel and missiles
    vector<long long> remFuel(nb), remMiss(nb);
    for (int b = 0; b < nb; b++) {
        remFuel[b] = blue[b].fuel;
        remMiss[b] = blue[b].missiles;
    }

    vector<int> fuelAlloc(k, 0);
    vector<int> missileAlloc(k, 0);

    // Fuel: allocate exact required
    for (int fi = 0; fi < k; fi++) if (chosenMask & (1 << fi)) {
        int b = fighters[fi].baseIdx;
        int need = chosenReqFuel[fi];
        long long give = min<long long>(need, remFuel[b]);
        fuelAlloc[fi] = (int)give;
        remFuel[b] -= give;
    }

    // Missiles: allocate to cover defense
    long long remainingDefense = red[chosenR].defense;
    vector<vector<int>> fightersByBase(nb);
    for (int fi = 0; fi < k; fi++) if (chosenMask & (1 << fi)) {
        int b = fighters[fi].baseIdx;
        if (b >= 0 && b < nb) fightersByBase[b].push_back(fi);
    }
    for (int b = 0; b < nb && remainingDefense > 0; b++) {
        // any order ok
        for (int fi : fightersByBase[b]) {
            if (remainingDefense <= 0) break;
            long long give = min<long long>({(long long)fighters[fi].C, remMiss[b], remainingDefense});
            missileAlloc[fi] = (int)give;
            remMiss[b] -= give;
            remainingDefense -= give;
        }
    }

    // Reconstruct paths
    vector<vector<int>> paths(k);
    int makespan = 0;
    for (int fi = 0; fi < k; fi++) if (chosenMask & (1 << fi)) {
        int sx = fighters[fi].x, sy = fighters[fi].y;
        int sidx = idx(sx, sy, m);
        int tidx = chosenAdjIdx[fi];
        vector<int> dirs;
        if (tidx >= 0 && tidx < n * m) {
            int cur = tidx;
            while (cur != sidx) {
                unsigned char d = bfs[fi].pdir[cur];
                int p = bfs[fi].parent[cur];
                if (d == 255 || p == -1) { dirs.clear(); break; }
                dirs.push_back((int)d);
                cur = p;
            }
            reverse(dirs.begin(), dirs.end());
        }
        paths[fi] = std::move(dirs);
        makespan = max<int>(makespan, (int)paths[fi].size());
    }

    // Output frames
    // Frame 0: load
    for (int fi = 0; fi < k; fi++) if (chosenMask & (1 << fi)) {
        if (fuelAlloc[fi] > 0) cout << "fuel " << fi << " " << fuelAlloc[fi] << "\n";
        if (missileAlloc[fi] > 0) cout << "missile " << fi << " " << missileAlloc[fi] << "\n";
    }
    cout << "OK\n";

    // Movement frames
    for (int t = 0; t < makespan; t++) {
        for (int fi = 0; fi < k; fi++) if (chosenMask & (1 << fi)) {
            if (t < (int)paths[fi].size()) {
                cout << "move " << fi << " " << paths[fi][t] << "\n";
            }
        }
        cout << "OK\n";
    }

    // Attack frame
    for (int fi = 0; fi < k; fi++) if (chosenMask & (1 << fi)) {
        if (missileAlloc[fi] <= 0) continue;
        int ad = chosenAttackDir[fi];
        if (ad < 0) continue;
        cout << "attack " << fi << " " << ad << " " << missileAlloc[fi] << "\n";
    }
    cout << "OK\n";

    return 0;
}