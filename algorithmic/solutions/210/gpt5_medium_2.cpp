#include <bits/stdc++.h>
using namespace std;

struct BlueBase {
    int x, y;
    long long g, c;
    long long d;
    long long v;
};
struct RedBase {
    int x, y;
    long long g, c;
    long long d;
    long long v;
};
struct FighterInput {
    int x, y, G, C;
};

struct FighterPlan {
    bool assigned = false;
    int targetRed = -1;
    vector<int> pathDirs; // directions 0..3
    int missilesToFire = 0;
    // runtime state
    int stage = 0; // 0 init/load, 1 moving, 2 attack, 3 done
    int pathIdx = 0;
    int curx = 0, cury = 0;
    int fuel = 0;
    int missiles = 0;
    int startBase = -1;
    int adjx = -1, adjy = -1;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        // No input, just output one frame
        cout << "OK\n";
        return 0;
    }
    vector<string> grid(n);
    for (int i = 0; i < n; ++i) cin >> grid[i];

    int NB;
    cin >> NB;
    vector<BlueBase> blue(NB);
    for (int i = 0; i < NB; ++i) {
        cin >> blue[i].x >> blue[i].y;
        cin >> blue[i].g >> blue[i].c >> blue[i].d >> blue[i].v;
    }
    int NR;
    cin >> NR;
    vector<RedBase> red(NR);
    for (int i = 0; i < NR; ++i) {
        cin >> red[i].x >> red[i].y;
        cin >> red[i].g >> red[i].c >> red[i].d >> red[i].v;
    }
    int K;
    cin >> K;
    vector<FighterInput> fighters(K);
    for (int i = 0; i < K; ++i) {
        cin >> fighters[i].x >> fighters[i].y >> fighters[i].G >> fighters[i].C;
    }

    // Map positions to blue/red base indices
    vector<vector<int>> blueIdx(n, vector<int>(m, -1));
    for (int i = 0; i < NB; ++i) {
        if (blue[i].x >= 0 && blue[i].x < n && blue[i].y >= 0 && blue[i].y < m)
            blueIdx[blue[i].x][blue[i].y] = i;
    }
    vector<vector<int>> redIdx(n, vector<int>(m, -1));
    for (int i = 0; i < NR; ++i) {
        if (red[i].x >= 0 && red[i].x < n && red[i].y >= 0 && red[i].y < m)
            redIdx[red[i].x][red[i].y] = i;
    }

    // For each fighter, find its starting base index
    vector<int> fighterBase(K, -1);
    for (int i = 0; i < K; ++i) {
        int bx = fighters[i].x, by = fighters[i].y;
        if (bx >= 0 && bx < n && by >= 0 && by < m) {
            fighterBase[i] = blueIdx[bx][by];
        }
    }

    // Precompute BFS from each fighter start to all cells (avoiding red '#')
    const int INF = 1e9;
    int totalCells = n * m;
    auto idx = [&](int x, int y){ return x * m + y; };
    auto inb = [&](int x, int y){ return x >= 0 && x < n && y >= 0 && y < m; };
    int dx[4] = {-1, 1, 0, 0};
    int dy[4] = {0, 0, -1, 1};

    vector<vector<int>> distF(K, vector<int>(totalCells, INF));
    vector<vector<int>> prevF(K, vector<int>(totalCells, -1));
    vector<vector<int>> prevDirF(K, vector<int>(totalCells, -1));

    for (int fi = 0; fi < K; ++fi) {
        // BFS
        deque<int> dq;
        int sx = fighters[fi].x, sy = fighters[fi].y;
        if (!(sx >= 0 && sx < n && sy >= 0 && sy < m)) continue;
        int sidx = idx(sx, sy);
        auto &dist = distF[fi];
        auto &prv = prevF[fi];
        auto &pdir = prevDirF[fi];
        fill(dist.begin(), dist.end(), INF);
        fill(prv.begin(), prv.end(), -1);
        fill(pdir.begin(), pdir.end(), -1);
        dist[sidx] = 0;
        dq.push_back(sidx);
        while (!dq.empty()) {
            int cur = dq.front(); dq.pop_front();
            int cx = cur / m, cy = cur % m;
            for (int d = 0; d < 4; ++d) {
                int nx_ = cx + dx[d], ny_ = cy + dy[d];
                if (!inb(nx_, ny_)) continue;
                if (grid[nx_][ny_] == '#') continue; // cannot pass through red base
                int ni = idx(nx_, ny_);
                if (dist[ni] == INF) {
                    dist[ni] = dist[cur] + 1;
                    prv[ni] = cur;
                    pdir[ni] = d; // direction from cur to ni
                    dq.push_back(ni);
                }
            }
        }
    }

    // Prepare assignment
    vector<long long> baseFuelLeft(NB), baseMissLeft(NB);
    for (int i = 0; i < NB; ++i) {
        baseFuelLeft[i] = blue[i].g;
        baseMissLeft[i] = blue[i].c;
    }
    vector<long long> redRemain(NR);
    for (int i = 0; i < NR; ++i) redRemain[i] = red[i].d;

    // Sort red bases by value descending
    vector<int> redOrder(NR);
    iota(redOrder.begin(), redOrder.end(), 0);
    sort(redOrder.begin(), redOrder.end(), [&](int a, int b){
        if (red[a].v != red[b].v) return red[a].v > red[b].v;
        return red[a].d < red[b].d;
    });

    vector<FighterPlan> plans(K);
    vector<char> usedF(K, 0);

    // Assignment algorithm with revert if cannot complete a target
    for (int ridxOrd : redOrder) {
        int rx = red[ridxOrd].x, ry = red[ridxOrd].y;
        // Build candidates
        struct Cand { int fi; int b; int dmin; int adjIdx; int adjx, adjy; int cap; };
        vector<Cand> cands;
        for (int fi = 0; fi < K; ++fi) {
            if (usedF[fi]) continue;
            int b = fighterBase[fi];
            if (b < 0) continue;
            // Determine best adjacency cell
            int bestD = INF;
            int bestAdj = -1;
            int bax = -1, bay = -1;
            for (int d = 0; d < 4; ++d) {
                int ax = rx + dx[d], ay = ry + dy[d];
                if (!inb(ax, ay)) continue;
                if (grid[ax][ay] == '#') continue; // cannot stand on red
                int aidx = idx(ax, ay);
                int dmin = distF[fi][aidx];
                if (dmin < bestD) {
                    bestD = dmin;
                    bestAdj = aidx;
                    bax = ax; bay = ay;
                }
            }
            if (bestD == INF) continue;
            if (bestD > fighters[fi].G) continue;
            if (baseFuelLeft[b] < bestD) continue;
            if (baseMissLeft[b] <= 0) continue;
            int cap = min(fighters[fi].C, (int)min<long long>(baseMissLeft[b], INT_MAX));
            if (cap <= 0) continue;
            cands.push_back({fi, b, bestD, bestAdj, bax, bay, cap});
        }
        if (cands.empty()) continue;

        // Snapshot supplies
        vector<long long> fuelSnap = baseFuelLeft;
        vector<long long> missSnap = baseMissLeft;

        // Compute total potential (rough), but we'll assign greedily
        // Sort candidates by distance asc, then capacity desc
        sort(cands.begin(), cands.end(), [&](const Cand& A, const Cand& B){
            if (A.dmin != B.dmin) return A.dmin < B.dmin;
            return A.cap > B.cap;
        });

        long long rem = redRemain[ridxOrd];
        vector<int> assignedFis;
        for (auto &cd : cands) {
            if (rem <= 0) break;
            if (usedF[cd.fi]) continue;
            if (baseFuelLeft[cd.b] < cd.dmin) continue;
            if (baseMissLeft[cd.b] <= 0) continue;
            int availMiss = (int)min<long long>((long long)fighters[cd.fi].C, baseMissLeft[cd.b]);
            if (availMiss <= 0) continue;
            int give = (int)min<long long>(availMiss, rem);
            if (give <= 0) continue;

            // Build path to cd.adjIdx
            vector<int> dirs;
            int sidx = idx(fighters[cd.fi].x, fighters[cd.fi].y);
            if (cd.adjIdx != sidx) {
                // reconstruct using prev arrays
                const auto &prv = prevF[cd.fi];
                const auto &pdir = prevDirF[cd.fi];
                int cur = cd.adjIdx;
                vector<int> rev;
                if (prv[cur] == -1 && cur != sidx) {
                    // unreachable due to some inconsistency
                    continue;
                }
                while (cur != sidx) {
                    int d = pdir[cur];
                    rev.push_back(d);
                    cur = prv[cur];
                }
                reverse(rev.begin(), rev.end());
                dirs = move(rev);
            } else {
                dirs.clear();
            }

            // Assign
            FighterPlan &fp = plans[cd.fi];
            fp.assigned = true;
            fp.targetRed = ridxOrd;
            fp.pathDirs = dirs;
            fp.missilesToFire = give;
            fp.curx = fighters[cd.fi].x;
            fp.cury = fighters[cd.fi].y;
            fp.stage = 0;
            fp.pathIdx = 0;
            fp.fuel = 0;
            fp.missiles = 0;
            fp.startBase = cd.b;
            fp.adjx = cd.adjx;
            fp.adjy = cd.adjy;

            usedF[cd.fi] = 1;
            baseFuelLeft[cd.b] -= cd.dmin;
            baseMissLeft[cd.b] -= give;
            rem -= give;
            assignedFis.push_back(cd.fi);
        }

        if (rem > 0) {
            // revert
            for (int fi : assignedFis) {
                usedF[fi] = 0;
                plans[fi] = FighterPlan();
            }
            baseFuelLeft = fuelSnap;
            baseMissLeft = missSnap;
        } else {
            // ok, keep assignments
            // redRemain remains unchanged; will be reduced during attacks
        }
    }

    // Check if any fighter assigned
    bool anyAssigned = false;
    for (int i = 0; i < K; ++i) if (plans[i].assigned) { anyAssigned = true; break; }
    if (!anyAssigned) {
        cout << "OK\n";
        return 0;
    }

    // Simulate frames, output commands
    auto dirToChar = [&](int d)->int { return d; }; // already 0..3
    auto moveDirToDelta = [&](int d, int &dxo, int &dyo){
        if (d == 0) { dxo = -1; dyo = 0; }
        else if (d == 1) { dxo = 1; dyo = 0; }
        else if (d == 2) { dxo = 0; dyo = -1; }
        else { dxo = 0; dyo = 1; }
    };
    auto attackDirFromTo = [&](int fx, int fy, int tx, int ty)->int {
        if (tx == fx - 1 && ty == fy) return 0;
        if (tx == fx + 1 && ty == fy) return 1;
        if (tx == fx && ty == fy - 1) return 2;
        if (tx == fx && ty == fy + 1) return 3;
        return 0;
    };

    int frame = 0;
    const int MAX_FRAMES = 15000;
    while (frame < MAX_FRAMES) {
        bool allDone = true;
        // Generate commands for this frame
        // We'll write directly to cout
        for (int i = 0; i < K; ++i) {
            if (!plans[i].assigned) continue;
            if (plans[i].stage == 3) continue;
            allDone = false;
            FighterPlan &fp = plans[i];
            if (fp.stage == 0) {
                // Load missiles and fuel at base
                if (fp.missilesToFire > 0) {
                    cout << "missile " << i << " " << fp.missilesToFire << "\n";
                    fp.missiles = fp.missilesToFire;
                }
                int fuelNeed = (int)fp.pathDirs.size();
                if (fuelNeed > 0) {
                    cout << "fuel " << i << " " << fuelNeed << "\n";
                    fp.fuel = fuelNeed;
                }
                // Move first step if any
                if (fp.pathIdx < (int)fp.pathDirs.size()) {
                    int d = fp.pathDirs[fp.pathIdx];
                    cout << "move " << i << " " << dirToChar(d) << "\n";
                    int mx, my; moveDirToDelta(d, mx, my);
                    fp.curx += mx; fp.cury += my;
                    fp.pathIdx++;
                    if (fp.fuel > 0) fp.fuel--;
                    // remain moving
                    if (fp.pathIdx >= (int)fp.pathDirs.size()) {
                        fp.stage = 2; // reached adjacency, next frame attack
                    } else {
                        fp.stage = 1;
                    }
                } else {
                    // already at adjacency, can attack immediately this frame
                    fp.stage = 2;
                    // fallthrough to attempt attack now
                    // But to avoid multiple actions in same loop, we will perform attack now
                    int rid = fp.targetRed;
                    if (rid >= 0) {
                        int ax = fp.curx, ay = fp.cury;
                        int tx = red[rid].x, ty = red[rid].y;
                        long long can = min<long long>(fp.missiles, redRemain[rid]);
                        if (can > 0) {
                            int adir = attackDirFromTo(ax, ay, tx, ty);
                            cout << "attack " << i << " " << adir << " " << (long long)can << "\n";
                            fp.missiles -= (int)can;
                            redRemain[rid] -= can;
                        }
                    }
                    fp.stage = 3; // done
                }
            } else if (fp.stage == 1) {
                // Moving along path
                if (fp.pathIdx < (int)fp.pathDirs.size()) {
                    int d = fp.pathDirs[fp.pathIdx];
                    cout << "move " << i << " " << dirToChar(d) << "\n";
                    int mx, my; moveDirToDelta(d, mx, my);
                    fp.curx += mx; fp.cury += my;
                    fp.pathIdx++;
                    if (fp.fuel > 0) fp.fuel--;
                    if (fp.pathIdx >= (int)fp.pathDirs.size()) {
                        fp.stage = 2;
                    }
                } else {
                    fp.stage = 2;
                }
            } else if (fp.stage == 2) {
                // Attack
                int rid = fp.targetRed;
                if (rid >= 0) {
                    int ax = fp.curx, ay = fp.cury;
                    int tx = red[rid].x, ty = red[rid].y;
                    long long can = min<long long>(fp.missiles, redRemain[rid]);
                    if (can > 0) {
                        int adir = attackDirFromTo(ax, ay, tx, ty);
                        cout << "attack " << i << " " << adir << " " << (long long)can << "\n";
                        fp.missiles -= (int)can;
                        redRemain[rid] -= can;
                    }
                }
                fp.stage = 3;
            }
        }
        cout << "OK\n";
        frame++;
        if (allDone) break;
    }
    return 0;
}