#include <bits/stdc++.h>
using namespace std;

static const int MAX_FRAMES = 15000;

struct BlueBase {
    int x, y;
    long long fuelSup = 0;
    long long missSup = 0;
};

struct RedBase {
    int x, y;
    long long rem = 0;
    long long val = 0;
    bool destroyed = false;
    int reservedBy = -1;
};

struct Fighter {
    enum Mode { IDLE, TO_TARGET, ATTACK, TO_BASE, RELOCATE };

    int id = -1;
    int x = 0, y = 0;
    int G = 0, C = 0;
    int fuel = 0, miss = 0;

    int homeBase = -1;          // blue base index to return to (for current trip)
    Mode mode = IDLE;

    int target = -1;            // red base index
    int destIdx = -1;           // destination cell index for TO_TARGET/RELOCATE
    int tripDist = 0;           // distance base->dest for current target trip

    vector<int> path;           // dirs to follow
    int pathPos = 0;

    vector<int> trail;          // dirs actually taken from base to target, for reverse return
    int relocateBase = -1;      // destination base index for relocation
};

struct BFSWorkspace {
    int nm = 0, m = 0;
    vector<int> dist, parent, q;
    vector<signed char> pdir;

    void init(int n_, int m_) {
        m = m_;
        nm = n_ * m_;
        dist.assign(nm, -1);
        parent.assign(nm, -1);
        pdir.assign(nm, -1);
        q.reserve(nm);
    }
};

static inline int oppDir(int d) { return d ^ 1; }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> grid(n);
    for (int i = 0; i < n; i++) cin >> grid[i];

    int Nb;
    cin >> Nb;
    vector<BlueBase> blue(Nb);
    for (int i = 0; i < Nb; i++) {
        int x, y;
        long long g, c, d, v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
        blue[i].x = x; blue[i].y = y;
        blue[i].fuelSup = g;
        blue[i].missSup = c;
    }

    int Nr;
    cin >> Nr;
    vector<RedBase> red(Nr);
    for (int i = 0; i < Nr; i++) {
        int x, y;
        long long g, c, d, v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
        red[i].x = x; red[i].y = y;
        red[i].rem = d;
        red[i].val = v;
    }

    int k;
    cin >> k;
    vector<Fighter> fighters(k);

    auto idx = [&](int x, int y) { return x * m + y; };
    int nm = n * m;

    vector<int> baseAt(nm, -1);
    for (int i = 0; i < Nb; i++) baseAt[idx(blue[i].x, blue[i].y)] = i;

    vector<int> redAt(nm, -1);
    for (int i = 0; i < Nr; i++) redAt[idx(red[i].x, red[i].y)] = i;

    for (int i = 0; i < k; i++) {
        int x, y, G, C;
        cin >> x >> y >> G >> C;
        fighters[i].id = i;
        fighters[i].x = x; fighters[i].y = y;
        fighters[i].G = G; fighters[i].C = C;
        fighters[i].fuel = 0; fighters[i].miss = 0;
        fighters[i].homeBase = baseAt[idx(x, y)];
        fighters[i].mode = Fighter::IDLE;
    }

    auto isBlockedIdx = [&](int id) -> bool {
        int rid = redAt[id];
        return (rid != -1 && !red[rid].destroyed);
    };

    auto isBlockedXY = [&](int x, int y) -> bool {
        if (x < 0 || x >= n || y < 0 || y >= m) return true;
        return isBlockedIdx(idx(x, y));
    };

    BFSWorkspace bfsWS;
    bfsWS.init(n, m);

    static const int dx[4] = {-1, 1, 0, 0};
    static const int dy[4] = {0, 0, -1, 1};

    auto bfsAllFrom = [&](int sx, int sy) {
        fill(bfsWS.dist.begin(), bfsWS.dist.end(), -1);
        fill(bfsWS.parent.begin(), bfsWS.parent.end(), -1);
        fill(bfsWS.pdir.begin(), bfsWS.pdir.end(), -1);
        bfsWS.q.clear();

        int s = idx(sx, sy);
        bfsWS.dist[s] = 0;
        bfsWS.q.push_back(s);
        size_t head = 0;
        while (head < bfsWS.q.size()) {
            int u = bfsWS.q[head++];
            int ux = u / m, uy = u % m;
            int du = bfsWS.dist[u];
            for (int dir = 0; dir < 4; dir++) {
                int vx = ux + dx[dir], vy = uy + dy[dir];
                if (vx < 0 || vx >= n || vy < 0 || vy >= m) continue;
                int v = idx(vx, vy);
                if (bfsWS.dist[v] != -1) continue;
                if (isBlockedIdx(v)) continue;
                bfsWS.dist[v] = du + 1;
                bfsWS.parent[v] = u;
                bfsWS.pdir[v] = (signed char)dir;
                bfsWS.q.push_back(v);
            }
        }
    };

    auto buildPathFromParents = [&](int s, int t) -> vector<int> {
        vector<int> dirs;
        if (s == t) return dirs;
        int cur = t;
        while (cur != s) {
            int p = bfsWS.parent[cur];
            if (p == -1) { dirs.clear(); return dirs; }
            int dir = (int)bfsWS.pdir[cur];
            if (dir < 0) { dirs.clear(); return dirs; }
            dirs.push_back(dir);
            cur = p;
        }
        reverse(dirs.begin(), dirs.end());
        return dirs;
    };

    auto computePath = [&](int sx, int sy, int tx, int ty) -> vector<int> {
        if (sx == tx && sy == ty) return {};
        bfsAllFrom(sx, sy);
        int s = idx(sx, sy);
        int t = idx(tx, ty);
        if (bfsWS.dist[t] == -1) return {};
        return buildPathFromParents(s, t);
    };

    auto computeRelocateFromBase = [&](int baseIdx, int fighterG, int &bestBase, vector<int> &path) -> bool {
        bestBase = -1;
        path.clear();
        bfsAllFrom(blue[baseIdx].x, blue[baseIdx].y);
        int s = idx(blue[baseIdx].x, blue[baseIdx].y);

        int bestDist = INT_MAX;
        for (int bi = 0; bi < (int)blue.size(); bi++) {
            if (bi == baseIdx) continue;
            if (blue[bi].missSup <= 0) continue;
            int t = idx(blue[bi].x, blue[bi].y);
            int d = bfsWS.dist[t];
            if (d < 0) continue;
            if (d > fighterG) continue;
            if (d < bestDist) {
                bestDist = d;
                bestBase = bi;
            }
        }
        if (bestBase == -1) return false;
        int t = idx(blue[bestBase].x, blue[bestBase].y);
        path = buildPathFromParents(s, t);
        return true;
    };

    auto selectTargetFromBase = [&](int baseIdx, Fighter &f, int &outTarget, int &outDestIdx, int &outDist, vector<int> &outPath) -> bool {
        outTarget = -1;
        outDestIdx = -1;
        outDist = -1;
        outPath.clear();

        bfsAllFrom(blue[baseIdx].x, blue[baseIdx].y);
        int s = idx(blue[baseIdx].x, blue[baseIdx].y);

        long double bestScore = -1.0L;
        int bestT = -1;
        int bestDest = -1;
        int bestDist = INT_MAX;

        for (int i = 0; i < Nr; i++) {
            if (red[i].destroyed) continue;
            if (red[i].reservedBy != -1) continue;

            int rx = red[i].x, ry = red[i].y;
            int localBestDest = -1;
            int localBestDist = INT_MAX;

            for (int dir = 0; dir < 4; dir++) {
                int nx = rx + dx[dir], ny = ry + dy[dir];
                if (nx < 0 || nx >= n || ny < 0 || ny >= m) continue;
                int nid = idx(nx, ny);
                if (isBlockedIdx(nid)) continue;
                int d = bfsWS.dist[nid];
                if (d < 0) continue;
                if (d < localBestDist) {
                    localBestDist = d;
                    localBestDest = nid;
                }
            }
            if (localBestDest == -1) continue;
            if (2LL * localBestDist > f.G) continue;

            long double score = (long double)red[i].val / (long double)(localBestDist + 1);
            if (score > bestScore ||
                (fabsl(score - bestScore) < 1e-18L && (localBestDist < bestDist ||
                 (localBestDist == bestDist && red[i].val > red[bestT].val)))) {
                bestScore = score;
                bestT = i;
                bestDest = localBestDest;
                bestDist = localBestDist;
            }
        }

        if (bestT == -1) return false;
        outTarget = bestT;
        outDestIdx = bestDest;
        outDist = bestDist;
        outPath = buildPathFromParents(s, bestDest);
        return true;
    };

    auto isOnBlueBase = [&](int x, int y) -> int {
        if (x < 0 || x >= n || y < 0 || y >= m) return -1;
        return baseAt[idx(x, y)];
    };

    auto doRefuelAtBase = [&](vector<string> &cmds, Fighter &f, int baseIdx, int desiredFuel, int desiredMiss) -> bool {
        if (baseIdx < 0) return false;
        bool did = false;

        desiredFuel = max(0, min(f.G, desiredFuel));
        desiredMiss = max(0, min(f.C, desiredMiss));

        if (f.fuel < desiredFuel && blue[baseIdx].fuelSup > 0) {
            int need = desiredFuel - f.fuel;
            int take = (int)min<long long>(need, blue[baseIdx].fuelSup);
            if (take > 0) {
                blue[baseIdx].fuelSup -= take;
                f.fuel += take;
                cmds.push_back("fuel " + to_string(f.id) + " " + to_string(take));
                did = true;
            }
        }
        if (f.miss < desiredMiss && blue[baseIdx].missSup > 0) {
            int need = desiredMiss - f.miss;
            int take = (int)min<long long>(need, blue[baseIdx].missSup);
            if (take > 0) {
                blue[baseIdx].missSup -= take;
                f.miss += take;
                cmds.push_back("missile " + to_string(f.id) + " " + to_string(take));
                did = true;
            }
        }
        return did;
    };

    auto moveOne = [&](vector<string> &cmds, Fighter &f, int dir) -> bool {
        if (f.fuel <= 0) return false;
        int nx = f.x + dx[dir];
        int ny = f.y + dy[dir];
        if (nx < 0 || nx >= n || ny < 0 || ny >= m) return false;
        int nid = idx(nx, ny);
        if (isBlockedIdx(nid)) return false;

        cmds.push_back("move " + to_string(f.id) + " " + to_string(dir));
        f.x = nx; f.y = ny;
        f.fuel -= 1;
        return true;
    };

    auto attackIfPossible = [&](vector<string> &cmds, Fighter &f) -> bool {
        if (f.target < 0 || f.target >= Nr) return false;
        RedBase &rb = red[f.target];
        if (rb.destroyed) return false;
        int dxr = rb.x - f.x;
        int dyr = rb.y - f.y;
        int dir = -1;
        if (dxr == -1 && dyr == 0) dir = 0;
        else if (dxr == 1 && dyr == 0) dir = 1;
        else if (dxr == 0 && dyr == -1) dir = 2;
        else if (dxr == 0 && dyr == 1) dir = 3;
        else return false;

        if (f.miss <= 0) return false;
        long long need = rb.rem;
        if (need <= 0) return false;
        int cnt = (int)min<long long>(f.miss, need);
        if (cnt <= 0) return false;

        cmds.push_back("attack " + to_string(f.id) + " " + to_string(dir) + " " + to_string(cnt));
        f.miss -= cnt;
        rb.rem -= cnt;
        if (rb.rem <= 0) {
            rb.destroyed = true;
            rb.reservedBy = -1;
        }
        return true;
    };

    auto abandonTarget = [&](Fighter &f) {
        if (f.target >= 0 && f.target < Nr && red[f.target].reservedBy == f.id) {
            red[f.target].reservedBy = -1;
        }
        f.target = -1;
        f.destIdx = -1;
        f.tripDist = 0;
        f.path.clear();
        f.pathPos = 0;
        f.trail.clear();
        f.mode = Fighter::IDLE;
    };

    auto allDestroyed = [&]() -> bool {
        for (int i = 0; i < Nr; i++) if (!red[i].destroyed) return false;
        return true;
    };

    int stagnation = 0;

    for (int frame = 0; frame < MAX_FRAMES; frame++) {
        vector<string> cmds;
        bool anyCommand = false;

        for (auto &f : fighters) {
            int curIdx = idx(f.x, f.y);
            int baseHere = baseAt[curIdx];

            auto ensureAtBaseOrReturn = [&]() {
                if (baseHere == -1) {
                    // If somehow off-base while IDLE, go back to home base (BFS).
                    if (f.homeBase >= 0 && f.homeBase < Nb) {
                        vector<int> p = computePath(f.x, f.y, blue[f.homeBase].x, blue[f.homeBase].y);
                        if (!p.empty()) {
                            f.mode = Fighter::TO_BASE;
                            f.path = std::move(p);
                            f.pathPos = 0;
                        }
                    }
                } else {
                    f.homeBase = baseHere;
                }
            };

            if (f.mode == Fighter::ATTACK) {
                if (f.target < 0 || f.target >= Nr || red[f.target].destroyed) {
                    if (f.target >= 0 && f.target < Nr && red[f.target].reservedBy == f.id) red[f.target].reservedBy = -1;
                    f.target = -1;
                    f.mode = Fighter::TO_BASE;
                    // Return using reversed trail.
                    vector<int> ret;
                    ret.reserve(f.trail.size());
                    for (int i = (int)f.trail.size() - 1; i >= 0; i--) ret.push_back(oppDir(f.trail[i]));
                    f.path = std::move(ret);
                    f.pathPos = 0;
                    continue;
                }

                if (f.miss <= 0) {
                    f.mode = Fighter::TO_BASE;
                    vector<int> ret;
                    ret.reserve(f.trail.size());
                    for (int i = (int)f.trail.size() - 1; i >= 0; i--) ret.push_back(oppDir(f.trail[i]));
                    f.path = std::move(ret);
                    f.pathPos = 0;
                    continue;
                }

                if (attackIfPossible(cmds, f)) {
                    anyCommand = true;
                    // If destroyed or out of missiles, start returning next frame.
                    if (f.target >= 0 && f.target < Nr && red[f.target].destroyed) {
                        f.target = -1;
                        f.mode = Fighter::TO_BASE;
                        vector<int> ret;
                        ret.reserve(f.trail.size());
                        for (int i = (int)f.trail.size() - 1; i >= 0; i--) ret.push_back(oppDir(f.trail[i]));
                        f.path = std::move(ret);
                        f.pathPos = 0;
                    } else if (f.miss <= 0) {
                        f.mode = Fighter::TO_BASE;
                        vector<int> ret;
                        ret.reserve(f.trail.size());
                        for (int i = (int)f.trail.size() - 1; i >= 0; i--) ret.push_back(oppDir(f.trail[i]));
                        f.path = std::move(ret);
                        f.pathPos = 0;
                    }
                } else {
                    // Not adjacent; try to go to target destination again (compute BFS from current).
                    if (f.target >= 0 && f.target < Nr && !red[f.target].destroyed) {
                        // Pick best adjacent cell from current position and go there.
                        // Simplify: go to previous destIdx if still valid.
                        if (f.destIdx != -1) {
                            int tx = f.destIdx / m, ty = f.destIdx % m;
                            vector<int> p = computePath(f.x, f.y, tx, ty);
                            if (!p.empty() || (f.x == tx && f.y == ty)) {
                                f.mode = Fighter::TO_TARGET;
                                f.path = std::move(p);
                                f.pathPos = 0;
                            } else {
                                abandonTarget(f);
                            }
                        } else {
                            abandonTarget(f);
                        }
                    } else {
                        abandonTarget(f);
                    }
                }
                continue;
            }

            if (f.mode == Fighter::TO_TARGET) {
                if (f.target >= 0 && f.target < Nr && red[f.target].destroyed) {
                    // Target gone.
                    if (red[f.target].reservedBy == f.id) red[f.target].reservedBy = -1;
                    f.target = -1;
                    f.mode = Fighter::TO_BASE;
                    vector<int> ret;
                    ret.reserve(f.trail.size());
                    for (int i = (int)f.trail.size() - 1; i >= 0; i--) ret.push_back(oppDir(f.trail[i]));
                    f.path = std::move(ret);
                    f.pathPos = 0;
                    continue;
                }

                if (f.destIdx != -1 && curIdx == f.destIdx) {
                    f.mode = Fighter::ATTACK;
                    // Attack in this frame (no movement)
                    if (f.miss > 0 && attackIfPossible(cmds, f)) {
                        anyCommand = true;
                        if (f.target >= 0 && f.target < Nr && red[f.target].destroyed) {
                            f.target = -1;
                            f.mode = Fighter::TO_BASE;
                            vector<int> ret;
                            ret.reserve(f.trail.size());
                            for (int i = (int)f.trail.size() - 1; i >= 0; i--) ret.push_back(oppDir(f.trail[i]));
                            f.path = std::move(ret);
                            f.pathPos = 0;
                        } else if (f.miss <= 0) {
                            f.mode = Fighter::TO_BASE;
                            vector<int> ret;
                            ret.reserve(f.trail.size());
                            for (int i = (int)f.trail.size() - 1; i >= 0; i--) ret.push_back(oppDir(f.trail[i]));
                            f.path = std::move(ret);
                            f.pathPos = 0;
                        }
                    }
                    continue;
                }

                if (f.pathPos >= (int)f.path.size()) {
                    // Reached by path, but destIdx mismatch; treat as arrived if close.
                    if (f.destIdx != -1 && curIdx == f.destIdx) {
                        f.mode = Fighter::ATTACK;
                    } else if (f.destIdx != -1) {
                        int tx = f.destIdx / m, ty = f.destIdx % m;
                        vector<int> p = computePath(f.x, f.y, tx, ty);
                        if (!p.empty() || (f.x == tx && f.y == ty)) {
                            f.path = std::move(p);
                            f.pathPos = 0;
                        } else {
                            abandonTarget(f);
                        }
                    } else {
                        abandonTarget(f);
                    }
                    continue;
                }

                int dir = f.path[f.pathPos];
                if (moveOne(cmds, f, dir)) {
                    anyCommand = true;
                    f.pathPos++;
                    f.trail.push_back(dir);
                } else {
                    // Try recompute path to destination.
                    if (f.destIdx != -1) {
                        int tx = f.destIdx / m, ty = f.destIdx % m;
                        vector<int> p = computePath(f.x, f.y, tx, ty);
                        if (!p.empty() || (f.x == tx && f.y == ty)) {
                            f.path = std::move(p);
                            f.pathPos = 0;
                            // no command this frame
                        } else {
                            abandonTarget(f);
                        }
                    } else {
                        abandonTarget(f);
                    }
                }
                continue;
            }

            if (f.mode == Fighter::TO_BASE) {
                // If we are on some base cell, consider arrived if it's homeBase.
                if (baseHere != -1 && f.homeBase == baseHere) {
                    f.mode = Fighter::IDLE;
                    f.path.clear(); f.pathPos = 0;
                    f.trail.clear();
                    continue;
                }
                // If no path, compute BFS to home base.
                if (f.pathPos >= (int)f.path.size()) {
                    if (f.homeBase >= 0 && f.homeBase < Nb) {
                        vector<int> p = computePath(f.x, f.y, blue[f.homeBase].x, blue[f.homeBase].y);
                        f.path = std::move(p);
                        f.pathPos = 0;
                        if (f.path.empty() && (f.x == blue[f.homeBase].x && f.y == blue[f.homeBase].y)) {
                            f.mode = Fighter::IDLE;
                            continue;
                        }
                    } else {
                        f.mode = Fighter::IDLE;
                        continue;
                    }
                }
                if (f.pathPos < (int)f.path.size()) {
                    int dir = f.path[f.pathPos];
                    if (moveOne(cmds, f, dir)) {
                        anyCommand = true;
                        f.pathPos++;
                    } else {
                        // Recompute
                        if (f.homeBase >= 0 && f.homeBase < Nb) {
                            vector<int> p = computePath(f.x, f.y, blue[f.homeBase].x, blue[f.homeBase].y);
                            f.path = std::move(p);
                            f.pathPos = 0;
                        }
                    }
                }
                continue;
            }

            if (f.mode == Fighter::RELOCATE) {
                if (baseHere != -1 && baseHere == f.relocateBase) {
                    f.homeBase = baseHere;
                    f.mode = Fighter::IDLE;
                    f.path.clear(); f.pathPos = 0;
                    f.relocateBase = -1;
                    continue;
                }
                if (f.pathPos >= (int)f.path.size()) {
                    // Recompute to relocate base
                    if (f.relocateBase >= 0 && f.relocateBase < Nb) {
                        vector<int> p = computePath(f.x, f.y, blue[f.relocateBase].x, blue[f.relocateBase].y);
                        f.path = std::move(p);
                        f.pathPos = 0;
                    } else {
                        f.mode = Fighter::IDLE;
                        continue;
                    }
                }
                if (f.pathPos < (int)f.path.size()) {
                    int dir = f.path[f.pathPos];
                    if (moveOne(cmds, f, dir)) {
                        anyCommand = true;
                        f.pathPos++;
                    } else {
                        // Recompute
                        if (f.relocateBase >= 0 && f.relocateBase < Nb) {
                            vector<int> p = computePath(f.x, f.y, blue[f.relocateBase].x, blue[f.relocateBase].y);
                            f.path = std::move(p);
                            f.pathPos = 0;
                        }
                    }
                }
                continue;
            }

            // IDLE
            ensureAtBaseOrReturn();
            curIdx = idx(f.x, f.y);
            baseHere = baseAt[curIdx];

            if (baseHere == -1) {
                // Not on base, try to go home.
                if (f.homeBase >= 0 && f.homeBase < Nb) {
                    vector<int> p = computePath(f.x, f.y, blue[f.homeBase].x, blue[f.homeBase].y);
                    if (!p.empty()) {
                        f.mode = Fighter::TO_BASE;
                        f.path = std::move(p);
                        f.pathPos = 0;
                    }
                }
                continue;
            }

            // At base: plan next.
            if (allDestroyed()) continue;

            // Try select a target from this base.
            int t = -1, dest = -1, dist = -1;
            vector<int> pathToDest;
            bool foundTarget = selectTargetFromBase(baseHere, f, t, dest, dist, pathToDest);

            if (!foundTarget) {
                // If no target from here, consider relocating to a base with missiles remaining.
                int bestB;
                vector<int> relocatePath;
                if (computeRelocateFromBase(baseHere, f.G, bestB, relocatePath)) {
                    // Need enough fuel to reach relocation base. If no fuel, refuel fuel only.
                    int desiredFuel = (int)relocatePath.size();
                    bool refueled = doRefuelAtBase(cmds, f, baseHere, desiredFuel, 0);
                    if (refueled) {
                        anyCommand = true;
                        continue; // refuel frame only
                    }
                    if (f.fuel < desiredFuel) continue;
                    f.mode = Fighter::RELOCATE;
                    f.relocateBase = bestB;
                    f.path = std::move(relocatePath);
                    f.pathPos = 0;
                    if (!f.path.empty()) {
                        int dir = f.path[f.pathPos];
                        if (moveOne(cmds, f, dir)) {
                            anyCommand = true;
                            f.pathPos++;
                        }
                    }
                }
                continue;
            }

            // Reserve and set target
            red[t].reservedBy = f.id;
            f.target = t;
            f.destIdx = dest;
            f.tripDist = dist;
            f.trail.clear();
            f.path = std::move(pathToDest);
            f.pathPos = 0;
            f.mode = (curIdx == f.destIdx) ? Fighter::ATTACK : Fighter::TO_TARGET;

            // Refuel/reload for this trip (one frame).
            int desiredFuel = min(f.G, 2 * dist);
            int desiredMiss = min(f.C, (int)min<long long>(red[t].rem, (long long)f.C));
            if (desiredMiss <= 0) desiredMiss = 1; // at least try to load something
            bool didRefuel = doRefuelAtBase(cmds, f, baseHere, desiredFuel, desiredMiss);
            if (didRefuel) {
                anyCommand = true;
                continue;
            }

            // If still can't make safe trip, abandon.
            if (f.fuel < desiredFuel) { // desiredFuel = 2*dist
                abandonTarget(f);
                continue;
            }
            if (f.miss <= 0) {
                abandonTarget(f);
                continue;
            }

            // Execute one action (move/attack) if possible.
            if (f.mode == Fighter::ATTACK) {
                if (attackIfPossible(cmds, f)) {
                    anyCommand = true;
                    if (f.target >= 0 && f.target < Nr && red[f.target].destroyed) {
                        f.target = -1;
                        f.mode = Fighter::TO_BASE;
                        f.path.clear(); f.pathPos = 0;
                        // Already at base (dist==0), so nothing.
                    } else if (f.miss <= 0) {
                        f.mode = Fighter::TO_BASE;
                        f.path.clear(); f.pathPos = 0;
                    }
                } else {
                    // Not adjacent; switch to TO_TARGET and attempt move if path exists.
                    f.mode = Fighter::TO_TARGET;
                    if (!f.path.empty()) {
                        int dir = f.path[f.pathPos];
                        if (moveOne(cmds, f, dir)) {
                            anyCommand = true;
                            f.pathPos++;
                            f.trail.push_back(dir);
                        }
                    }
                }
            } else if (f.mode == Fighter::TO_TARGET) {
                if (!f.path.empty() && f.pathPos < (int)f.path.size()) {
                    int dir = f.path[f.pathPos];
                    if (moveOne(cmds, f, dir)) {
                        anyCommand = true;
                        f.pathPos++;
                        f.trail.push_back(dir);
                    }
                } else {
                    // Should be at dest
                    if (curIdx == f.destIdx) f.mode = Fighter::ATTACK;
                }
            }
        }

        for (auto &s : cmds) cout << s << "\n";
        cout << "OK\n";

        if (!anyCommand) stagnation++;
        else stagnation = 0;

        if (allDestroyed()) break;
        if (frame == 0) continue; // ensure at least one frame is output
        if (stagnation >= 200) break;
    }

    return 0;
}