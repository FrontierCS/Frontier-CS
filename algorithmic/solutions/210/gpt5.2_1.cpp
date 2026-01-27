#include <bits/stdc++.h>
using namespace std;

struct BlueBase {
    int x, y;
    long long fuel, missile;
};

struct RedBase {
    int x, y;
    int def, val;
    int rem;
    bool dead = false;
};

struct Fighter {
    int x, y;
    int G, C;
    int fuel = 0, missile = 0;
    int baseIdx = -1;
};

static const int MAX_FRAMES = 15000;
static const int INF = 1e9;
static const int dx[4] = {-1, 1, 0, 0};
static const int dy[4] = {0, 0, -1, 1};
static const int opp[4] = {1, 0, 3, 2};

struct Candidate {
    int redIdx = -1;
    int ax = -1, ay = -1;
    int attackDir = -1;
    int dist = INF;
    long long framesNeed = (1LL << 60);
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> grid(n);
    for (int i = 0; i < n; i++) cin >> grid[i];

    int nb;
    cin >> nb;
    vector<BlueBase> blue(nb);
    unordered_map<int, int> blueAt;
    blueAt.reserve(nb * 2 + 10);
    for (int i = 0; i < nb; i++) {
        int x, y;
        cin >> x >> y;
        long long g, c;
        long long d, v;
        cin >> g >> c >> d >> v;
        blue[i] = {x, y, g, c};
        blueAt[x * m + y] = i;
    }

    int nr;
    cin >> nr;
    vector<RedBase> red(nr);
    vector<char> blocked(n * m, 0);
    for (int i = 0; i < nr; i++) {
        int x, y;
        cin >> x >> y;
        long long g, c;
        int d, v;
        cin >> g >> c >> d >> v;
        red[i] = {x, y, d, v, d, false};
        if (0 <= x && x < n && 0 <= y && y < m) blocked[x * m + y] = 1;
    }

    int k;
    cin >> k;
    vector<Fighter> fighters(k);
    for (int i = 0; i < k; i++) {
        int x, y, G, C;
        cin >> x >> y >> G >> C;
        fighters[i] = {x, y, G, C, 0, 0, -1};
        auto it = blueAt.find(x * m + y);
        if (it != blueAt.end()) fighters[i].baseIdx = it->second;
    }

    // Choose one fighter to control
    int fid = 0;
    long long bestMetric = -1;
    for (int i = 0; i < k; i++) {
        int bi = fighters[i].baseIdx;
        if (bi < 0) continue;
        long long metric = 0;
        metric += min<long long>(blue[bi].missile, 1LL * fighters[i].C * 10);
        metric += min<long long>(blue[bi].fuel, 1LL * fighters[i].G * 10) / 10;
        metric += fighters[i].C / 10;
        if (metric > bestMetric) {
            bestMetric = metric;
            fid = i;
        }
    }

    Fighter &F = fighters[fid];
    if (F.baseIdx < 0) {
        // No recognizable base; output nothing.
        return 0;
    }

    int curBase = F.baseIdx;

    vector<int> dist(n * m);
    vector<int8_t> parentDir(n * m);

    auto bfsFrom = [&](int sx, int sy) {
        fill(dist.begin(), dist.end(), INF);
        fill(parentDir.begin(), parentDir.end(), (int8_t)-1);
        deque<int> q;
        int sidx = sx * m + sy;
        dist[sidx] = 0;
        q.push_back(sidx);
        while (!q.empty()) {
            int idx = q.front();
            q.pop_front();
            int x = idx / m, y = idx % m;
            int nd = dist[idx] + 1;
            for (int d = 0; d < 4; d++) {
                int nx = x + dx[d], ny = y + dy[d];
                if ((unsigned)nx >= (unsigned)n || (unsigned)ny >= (unsigned)m) continue;
                int nidx = nx * m + ny;
                if (blocked[nidx]) continue;
                if (dist[nidx] > nd) {
                    dist[nidx] = nd;
                    parentDir[nidx] = (int8_t)d;
                    q.push_back(nidx);
                }
            }
        }
    };

    auto reconstructPath = [&](int tx, int ty, int sx, int sy, const vector<int8_t> &par) -> vector<int> {
        int sidx = sx * m + sy;
        int idx = tx * m + ty;
        if (idx < 0 || idx >= n * m) return {};
        if (dist[idx] >= INF) return {};
        vector<int> path;
        while (idx != sidx) {
            int8_t d = par[idx];
            if (d < 0) return {};
            path.push_back((int)d);
            int x = idx / m, y = idx % m;
            int px = x - dx[d], py = y - dy[d];
            idx = px * m + py;
        }
        reverse(path.begin(), path.end());
        return path;
    };

    auto selectBestTargetAtCurrent = [&](int framesUsed) -> Candidate {
        Candidate best;
        int bx = blue[curBase].x, by = blue[curBase].y;
        (void)bx; (void)by;
        for (int i = 0; i < nr; i++) {
            if (red[i].dead) continue;
            int rx = red[i].x, ry = red[i].y;
            int bestD = INF, bestAx = -1, bestAy = -1, bestDir = -1;
            for (int d = 0; d < 4; d++) {
                int ax = rx - dx[d];
                int ay = ry - dy[d];
                if ((unsigned)ax >= (unsigned)n || (unsigned)ay >= (unsigned)m) continue;
                int aidx = ax * m + ay;
                if (blocked[aidx]) continue;
                int dd = dist[aidx];
                if (dd < bestD) {
                    bestD = dd;
                    bestAx = ax;
                    bestAy = ay;
                    bestDir = d;
                }
            }
            if (bestD >= INF) continue;

            if (2LL * bestD > F.G) continue;

            int rem = red[i].rem;
            if (rem <= 0) continue;

            long long trips = (rem + F.C - 1) / F.C;
            long long fuelNeed = trips * 2LL * bestD;
            long long framesNeed = trips * (2LL * bestD + 2LL);

            if (blue[curBase].missile < rem) continue;
            if (blue[curBase].fuel < fuelNeed) continue;
            if (framesUsed + framesNeed > MAX_FRAMES) continue;

            if (best.redIdx == -1) {
                best = {i, bestAx, bestAy, bestDir, bestD, framesNeed};
            } else {
                // Compare by value/framesNeed ratio
                __int128 lhs = (__int128)red[i].val * best.framesNeed;
                __int128 rhs = (__int128)red[best.redIdx].val * framesNeed;
                if (lhs > rhs ||
                    (lhs == rhs && (red[i].val > red[best.redIdx].val ||
                                    (red[i].val == red[best.redIdx].val && framesNeed < best.framesNeed)))) {
                    best = {i, bestAx, bestAy, bestDir, bestD, framesNeed};
                }
            }
        }
        return best;
    };

    string out;
    out.reserve(1 << 20);
    int framesUsed = 0;
    bool stop = false;

    auto emitFrame = [&](const vector<string> &cmds) {
        if (stop) return;
        if (framesUsed >= MAX_FRAMES) { stop = true; return; }
        for (auto &s : cmds) {
            out += s;
            out += '\n';
        }
        out += "OK\n";
        framesUsed++;
    };

    auto doFuelMissileFrame = [&](int fuelAmt, int missileAmt) {
        vector<string> cmds;
        if (fuelAmt > 0) cmds.push_back("fuel " + to_string(fid) + " " + to_string(fuelAmt));
        if (missileAmt > 0) cmds.push_back("missile " + to_string(fid) + " " + to_string(missileAmt));
        emitFrame(cmds);
    };

    auto doMoveFrame = [&](int dir) {
        emitFrame({ "move " + to_string(fid) + " " + to_string(dir) });
        F.x += dx[dir];
        F.y += dy[dir];
        if (F.fuel > 0) F.fuel--;
    };

    auto doAttackFrame = [&](int dir, int count) {
        emitFrame({ "attack " + to_string(fid) + " " + to_string(dir) + " " + to_string(count) });
        F.missile = max(0, F.missile - count);
    };

    auto relocateIfNeeded = [&]() -> bool {
        // BFS already computed from current base position.
        int curX = blue[curBase].x, curY = blue[curBase].y;
        int curIdx = curX * m + curY;

        vector<pair<long long,int>> reachable; // (missiles, baseIdx)
        reachable.reserve(nb);
        for (int i = 0; i < nb; i++) {
            if (i == curBase) continue;
            int bx = blue[i].x, by = blue[i].y;
            int bidx = bx * m + by;
            int d = dist[bidx];
            if (d >= INF) continue;
            if (d > F.G) continue;
            if (blue[curBase].fuel < d) continue;
            if (framesUsed + 1 + d >= MAX_FRAMES) continue;
            reachable.push_back({blue[i].missile, i});
        }
        if (reachable.empty()) return false;

        sort(reachable.begin(), reachable.end(), [&](auto &a, auto &b){
            if (a.first != b.first) return a.first > b.first;
            return a.second < b.second;
        });

        int limit = (int)min<size_t>(20, reachable.size());
        int bestBaseIdx = -1;
        __int128 bestScoreNum = -1; // val * denom
        long long bestScoreDen = 1;
        long long bestRelocDist = 0;

        // Evaluate candidates after relocation, for a few bases.
        vector<int> dist2(n * m);
        vector<int8_t> par2(n * m);

        for (int t = 0; t < limit; t++) {
            int bi = reachable[t].second;
            int bx = blue[bi].x, by = blue[bi].y;
            int bidx = bx * m + by;
            int relocDist = dist[bidx];
            int framesLeftAfterReloc = MAX_FRAMES - framesUsed - (1 + relocDist);
            if (framesLeftAfterReloc <= 0) continue;

            // BFS from candidate base
            fill(dist2.begin(), dist2.end(), INF);
            fill(par2.begin(), par2.end(), (int8_t)-1);
            deque<int> q;
            dist2[bidx] = 0;
            q.push_back(bidx);
            while (!q.empty()) {
                int idx = q.front(); q.pop_front();
                int x = idx / m, y = idx % m;
                int nd = dist2[idx] + 1;
                for (int d = 0; d < 4; d++) {
                    int nx = x + dx[d], ny = y + dy[d];
                    if ((unsigned)nx >= (unsigned)n || (unsigned)ny >= (unsigned)m) continue;
                    int nidx = nx * m + ny;
                    if (blocked[nidx]) continue;
                    if (dist2[nidx] > nd) {
                        dist2[nidx] = nd;
                        par2[nidx] = (int8_t)d;
                        q.push_back(nidx);
                    }
                }
            }

            // Find best target from this base under framesLeftAfterReloc
            Candidate cand;
            for (int i = 0; i < nr; i++) {
                if (red[i].dead) continue;
                int rx = red[i].x, ry = red[i].y;
                int bestD = INF;
                for (int d = 0; d < 4; d++) {
                    int ax = rx - dx[d];
                    int ay = ry - dy[d];
                    if ((unsigned)ax >= (unsigned)n || (unsigned)ay >= (unsigned)m) continue;
                    int aidx = ax * m + ay;
                    if (blocked[aidx]) continue;
                    bestD = min(bestD, dist2[aidx]);
                }
                if (bestD >= INF) continue;
                if (2LL * bestD > F.G) continue;
                int rem = red[i].rem;
                if (rem <= 0) continue;

                long long trips = (rem + F.C - 1) / F.C;
                long long fuelNeed = trips * 2LL * bestD;
                long long framesNeed = trips * (2LL * bestD + 2LL);

                if (blue[bi].missile < rem) continue;
                if (blue[bi].fuel < fuelNeed) continue;
                if (framesNeed > framesLeftAfterReloc) continue;

                if (cand.redIdx == -1) {
                    cand.redIdx = i;
                    cand.framesNeed = framesNeed;
                } else {
                    __int128 lhs = (__int128)red[i].val * cand.framesNeed;
                    __int128 rhs = (__int128)red[cand.redIdx].val * framesNeed;
                    if (lhs > rhs) {
                        cand.redIdx = i;
                        cand.framesNeed = framesNeed;
                    }
                }
            }
            if (cand.redIdx == -1) continue;

            long long totalFrames = 1 + relocDist + cand.framesNeed;
            // score rate = val/totalFrames
            __int128 num = (__int128)red[cand.redIdx].val * bestScoreDen;
            __int128 cur = (__int128)(bestScoreNum < 0 ? 0 : bestScoreNum);
            __int128 num2 = (__int128)(bestScoreNum < 0 ? 0 : red[bestBaseIdx].val) * totalFrames; // invalid if bestBaseIdx==-1, fixed below

            if (bestBaseIdx == -1) {
                bestBaseIdx = bi;
                bestRelocDist = relocDist;
                bestScoreNum = red[cand.redIdx].val;
                bestScoreDen = totalFrames;
            } else {
                // Compare redVal/totalFrames
                __int128 lhs = (__int128)red[cand.redIdx].val * bestScoreDen;
                __int128 rhs = (__int128)bestScoreNum * totalFrames;
                if (lhs > rhs) {
                    bestBaseIdx = bi;
                    bestRelocDist = relocDist;
                    bestScoreNum = red[cand.redIdx].val;
                    bestScoreDen = totalFrames;
                }
            }
        }

        if (bestBaseIdx == -1) return false;

        int targetX = blue[bestBaseIdx].x, targetY = blue[bestBaseIdx].y;
        vector<int> path = reconstructPath(targetX, targetY, curX, curY, parentDir);
        if ((int)path.size() != bestRelocDist) {
            // Fallback: if reconstruction fails, try any reachable base from list head
            int bi = reachable[0].second;
            targetX = blue[bi].x; targetY = blue[bi].y;
            bestRelocDist = dist[targetX * m + targetY];
            path = reconstructPath(targetX, targetY, curX, curY, parentDir);
            if (path.empty() && bestRelocDist != 0) return false;
            bestBaseIdx = bi;
        }

        // Fuel for relocation
        int needFuel = (int)bestRelocDist;
        int canTake = min<int>(needFuel, F.G - F.fuel);
        canTake = min<long long>(canTake, blue[curBase].fuel);
        if (canTake < needFuel) return false;

        blue[curBase].fuel -= canTake;
        F.fuel += canTake;
        doFuelMissileFrame(canTake, 0);
        if (stop) return true;

        // Move along path
        for (int d : path) {
            if (stop) break;
            doMoveFrame(d);
        }

        // Arrived at new base
        curBase = bestBaseIdx;
        F.baseIdx = curBase;
        F.fuel = 0;
        F.missile = 0;
        F.x = blue[curBase].x;
        F.y = blue[curBase].y;
        return true;
    };

    // Main planning loop
    int destroyedCount = 0;
    while (!stop && framesUsed < MAX_FRAMES) {
        // Ensure fighter is at current base cell (we keep it so)
        F.x = blue[curBase].x;
        F.y = blue[curBase].y;
        F.baseIdx = curBase;

        bfsFrom(F.x, F.y);
        Candidate cand = selectBestTargetAtCurrent(framesUsed);

        if (cand.redIdx == -1) {
            if (!relocateIfNeeded()) break;
            continue;
        }

        // Execute destruction plan (possibly multiple trips)
        int ridx = cand.redIdx;
        int ax = cand.ax, ay = cand.ay;
        int attackDir = cand.attackDir;
        int dgo = cand.dist;

        // reconstruct path from base to attack position
        vector<int> path = reconstructPath(ax, ay, F.x, F.y, parentDir);
        if (dgo != (int)path.size()) {
            // Something went wrong; try next iteration
            break;
        }

        while (!stop && !red[ridx].dead && red[ridx].rem > 0) {
            int needMiss = min(F.C, red[ridx].rem);
            long long needFuelLL = 2LL * dgo;
            if (needFuelLL > F.G) break;

            if (blue[curBase].missile < needMiss) break;
            if (blue[curBase].fuel < needFuelLL) break;
            if (framesUsed + (2LL * dgo + 2LL) > MAX_FRAMES) { stop = true; break; }

            // Load
            int fuelTake = (int)needFuelLL;
            int missileTake = needMiss;

            blue[curBase].fuel -= fuelTake;
            blue[curBase].missile -= missileTake;
            F.fuel += fuelTake;
            F.missile += missileTake;

            doFuelMissileFrame(fuelTake, missileTake);
            if (stop) break;

            // Move to attack cell
            for (int dir : path) {
                if (stop) break;
                doMoveFrame(dir);
            }
            if (stop) break;

            // Attack
            doAttackFrame(attackDir, needMiss);
            if (stop) break;

            red[ridx].rem -= needMiss;
            if (red[ridx].rem <= 0) {
                red[ridx].dead = true;
                destroyedCount++;
            }

            // Return
            for (int i = (int)path.size() - 1; i >= 0 && !stop; i--) {
                int rdir = opp[path[i]];
                doMoveFrame(rdir);
            }

            // Back on base, ensure states
            F.x = blue[curBase].x;
            F.y = blue[curBase].y;
            F.fuel = 0;
            F.missile = 0;

            if (destroyedCount >= 300) break;
        }
        if (destroyedCount >= 300) break;
    }

    cout << out;
    return 0;
}