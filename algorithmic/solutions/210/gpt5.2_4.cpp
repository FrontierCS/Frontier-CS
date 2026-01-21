#include <bits/stdc++.h>
using namespace std;

struct BlueBase {
    int x, y;
    long long fuelSupply = 0;
    long long missileSupply = 0;
};

struct RedBase {
    int x, y;
    long long defenseRemaining = 0;
    long long value = 0;
};

struct Fighter {
    int id;
    int x, y;
    int homeBaseIdx;
    int G, C;
    long long fuel = 0;
    long long missiles = 0;

    enum Mode { IDLE, TO_TARGET, ATTACKING, RETURNING, STRANDED } mode = IDLE;

    int targetRed = -1;

    vector<int> path;
    int pathPos = 0;

    vector<int> returnPath;
    int returnPos = 0;

    int attackX = -1, attackY = -1;
};

struct BFSData {
    int n = 0, m = 0;
    int startIdx = -1;
    vector<int> dist;
    vector<int> parent;
    vector<int> parentDir;
};

struct HomeInfo {
    bool computed = false;
    BFSData bfs;
    vector<int> bestDist; // to best adjacent cell of each red base
    vector<int> bestAdj;  // cell idx of best adjacent cell
};

static const int INF = 1e9;
static const int dx[4] = {-1, 1, 0, 0};
static const int dy[4] = {0, 0, -1, 1};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> grid(n);
    for (int i = 0; i < n; i++) cin >> grid[i];

    int Nb;
    cin >> Nb;
    vector<BlueBase> blueBases(Nb);
    unordered_map<int, int> bluePosToIdx;
    bluePosToIdx.reserve((size_t)Nb * 2 + 8);
    for (int i = 0; i < Nb; i++) {
        int x, y;
        cin >> x >> y;
        long long g, c, d, v;
        cin >> g >> c >> d >> v;
        blueBases[i].x = x;
        blueBases[i].y = y;
        blueBases[i].fuelSupply = g;
        blueBases[i].missileSupply = c;
        bluePosToIdx[x * m + y] = i;
    }

    int Nr;
    cin >> Nr;
    vector<RedBase> redBases(Nr);
    for (int i = 0; i < Nr; i++) {
        int x, y;
        cin >> x >> y;
        long long g, c, d, v;
        cin >> g >> c >> d >> v;
        redBases[i].x = x;
        redBases[i].y = y;
        redBases[i].defenseRemaining = d;
        redBases[i].value = v;
    }

    int k;
    cin >> k;
    vector<Fighter> fighters(k);
    vector<int> usedHomeBases;
    usedHomeBases.reserve(k);

    vector<char> homeUsed(Nb, 0);
    for (int i = 0; i < k; i++) {
        int x, y, G, C;
        cin >> x >> y >> G >> C;
        fighters[i].id = i;
        fighters[i].x = x;
        fighters[i].y = y;
        fighters[i].G = G;
        fighters[i].C = C;
        auto it = bluePosToIdx.find(x * m + y);
        int bidx = (it == bluePosToIdx.end() ? 0 : it->second);
        fighters[i].homeBaseIdx = bidx;
        if (bidx >= 0 && bidx < Nb && !homeUsed[bidx]) {
            homeUsed[bidx] = 1;
            usedHomeBases.push_back(bidx);
        }
    }

    // Precompute BFS and best adjacent cells for each used home base.
    vector<HomeInfo> homeInfos(Nb);

    auto computeBFS = [&](int bidx) {
        HomeInfo &hi = homeInfos[bidx];
        if (hi.computed) return;

        hi.computed = true;
        BFSData bfs;
        bfs.n = n;
        bfs.m = m;
        bfs.startIdx = blueBases[bidx].x * m + blueBases[bidx].y;
        bfs.dist.assign(n * m, INF);
        bfs.parent.assign(n * m, -1);
        bfs.parentDir.assign(n * m, -1);

        deque<int> q;
        bfs.dist[bfs.startIdx] = 0;
        q.push_back(bfs.startIdx);

        auto inside = [&](int x, int y) { return 0 <= x && x < n && 0 <= y && y < m; };

        while (!q.empty()) {
            int v = q.front();
            q.pop_front();
            int x = v / m, y = v % m;
            int dv = bfs.dist[v];
            for (int dir = 0; dir < 4; dir++) {
                int nx = x + dx[dir], ny = y + dy[dir];
                if (!inside(nx, ny)) continue;
                if (grid[nx][ny] == '#') continue; // treat all red bases as blocked
                int ni = nx * m + ny;
                if (bfs.dist[ni] != INF) continue;
                bfs.dist[ni] = dv + 1;
                bfs.parent[ni] = v;
                bfs.parentDir[ni] = dir;
                q.push_back(ni);
            }
        }

        hi.bfs = std::move(bfs);
        hi.bestDist.assign(Nr, INF);
        hi.bestAdj.assign(Nr, -1);

        for (int r = 0; r < Nr; r++) {
            int rx = redBases[r].x, ry = redBases[r].y;
            int bestD = INF;
            int bestCell = -1;
            for (int dir = 0; dir < 4; dir++) {
                int ax = rx + dx[dir], ay = ry + dy[dir];
                if (ax < 0 || ax >= n || ay < 0 || ay >= m) continue;
                if (grid[ax][ay] == '#') continue;
                int ai = ax * m + ay;
                int d = hi.bfs.dist[ai];
                if (d < bestD) {
                    bestD = d;
                    bestCell = ai;
                }
            }
            hi.bestDist[r] = bestD;
            hi.bestAdj[r] = bestCell;
        }
    };

    for (int bidx : usedHomeBases) computeBFS(bidx);

    vector<int> reservedBy(Nr, -1);

    auto oppositeDir = [&](int d) -> int {
        if (d == 0) return 1;
        if (d == 1) return 0;
        if (d == 2) return 3;
        return 2;
    };

    auto pickTarget = [&](const Fighter &f) -> int {
        const HomeInfo &hi = homeInfos[f.homeBaseIdx];
        const BlueBase &bb = blueBases[f.homeBaseIdx];

        long long bestScore = LLONG_MIN;
        int best = -1;

        for (int r = 0; r < Nr; r++) {
            if (redBases[r].defenseRemaining <= 0) continue;
            if (reservedBy[r] != -1) continue;

            int dist = hi.bestDist[r];
            if (dist >= INF) continue;

            long long maxFuelLoad = min(bb.fuelSupply, (long long)f.G - f.fuel);
            long long maxMissLoad = min(bb.missileSupply, (long long)f.C - f.missiles);

            long long fuelAfterMax = f.fuel + maxFuelLoad;
            long long missAfterMax = f.missiles + maxMissLoad;

            if (fuelAfterMax < dist) continue;
            if (missAfterMax <= 0) continue;

            long long score = redBases[r].value * 1000000LL / (dist + 1);
            // Slightly prefer closer targets if scores tie.
            score = score * 1000LL - dist;

            if (score > bestScore) {
                bestScore = score;
                best = r;
            }
        }
        return best;
    };

    auto releaseReservation = [&](Fighter &f) {
        if (f.targetRed != -1 && reservedBy[f.targetRed] == f.id) reservedBy[f.targetRed] = -1;
        f.targetRed = -1;
    };

    auto buildPathFromHomeTo = [&](int homeBaseIdx, int attackIdx, vector<int> &outPath) -> bool {
        const HomeInfo &hi = homeInfos[homeBaseIdx];
        const BFSData &bfs = hi.bfs;
        if (attackIdx < 0) return false;
        if (bfs.dist[attackIdx] >= INF) return false;
        outPath.clear();
        int cur = attackIdx;
        while (cur != bfs.startIdx) {
            int dir = bfs.parentDir[cur];
            int p = bfs.parent[cur];
            if (dir < 0 || p < 0) return false;
            outPath.push_back(dir);
            cur = p;
        }
        reverse(outPath.begin(), outPath.end());
        return true;
    };

    auto emit = [&](int &cmdCount, const string &s) {
        cout << s << '\n';
        cmdCount++;
    };

    for (int frame = 0; frame < 15000; frame++) {
        int cmdCount = 0;
        bool anyActiveAfter = false;

        for (auto &f : fighters) {
            BlueBase &bb = blueBases[f.homeBaseIdx];
            HomeInfo &hi = homeInfos[f.homeBaseIdx];
            if (!hi.computed) computeBFS(f.homeBaseIdx);

            const int hx = bb.x, hy = bb.y;

            // Normalize state on arrival.
            if (f.mode == Fighter::RETURNING && f.x == hx && f.y == hy) {
                f.mode = Fighter::IDLE;
            }
            if (f.mode == Fighter::TO_TARGET && f.pathPos >= (int)f.path.size()) {
                // Should already be at attack cell if moves succeeded.
                if (f.x == f.attackX && f.y == f.attackY) f.mode = Fighter::ATTACKING;
            }

            bool actionIssued = false;

            // If stranded but on home base, allow recovery.
            if (f.mode == Fighter::STRANDED && f.x == hx && f.y == hy) {
                f.mode = Fighter::IDLE;
            }

            if (f.mode == Fighter::IDLE) {
                if (f.x != hx || f.y != hy) {
                    releaseReservation(f);
                    f.mode = Fighter::STRANDED;
                } else {
                    // Clear invalid/finished target.
                    if (f.targetRed != -1) {
                        if (redBases[f.targetRed].defenseRemaining <= 0) {
                            releaseReservation(f);
                        } else if (reservedBy[f.targetRed] != f.id) {
                            f.targetRed = -1;
                        }
                    }

                    // Acquire target if none.
                    if (f.targetRed == -1) {
                        int t = pickTarget(f);
                        if (t != -1) {
                            reservedBy[t] = f.id;
                            f.targetRed = t;
                        }
                    }

                    // Plan a trip if target exists.
                    if (f.targetRed != -1) {
                        int t = f.targetRed;
                        if (redBases[t].defenseRemaining <= 0) {
                            releaseReservation(f);
                        } else {
                            int dist = hi.bestDist[t];
                            int attackIdx = hi.bestAdj[t];
                            if (dist >= INF || attackIdx < 0) {
                                releaseReservation(f);
                            } else {
                                vector<int> path;
                                if (!buildPathFromHomeTo(f.homeBaseIdx, attackIdx, path)) {
                                    releaseReservation(f);
                                } else {
                                    f.path = std::move(path);
                                    f.pathPos = 0;
                                    f.returnPath.clear();
                                    f.returnPath.reserve(f.path.size());
                                    for (int i = (int)f.path.size() - 1; i >= 0; i--) {
                                        f.returnPath.push_back(oppositeDir(f.path[i]));
                                    }
                                    f.returnPos = 0;

                                    f.attackX = attackIdx / m;
                                    f.attackY = attackIdx % m;

                                    long long distLL = (long long)f.path.size();

                                    long long maxFuelLoad = min(bb.fuelSupply, (long long)f.G - f.fuel);
                                    long long maxMissLoad = min(bb.missileSupply, (long long)f.C - f.missiles);

                                    // Feasibility checks (must be able to reach attack position and have >=1 missile).
                                    if (f.fuel + maxFuelLoad < distLL || f.missiles + maxMissLoad <= 0) {
                                        releaseReservation(f);
                                    } else {
                                        // Fueling strategy.
                                        long long desiredFuel = min<long long>(f.G, (2LL * distLL <= f.G ? 2LL * distLL : distLL));
                                        long long fuelLoad = 0;
                                        if (f.fuel < desiredFuel) {
                                            fuelLoad = min<long long>(maxFuelLoad, desiredFuel - f.fuel);
                                        }
                                        if (f.fuel + fuelLoad < distLL) {
                                            fuelLoad = maxFuelLoad; // load as much as possible to ensure reach
                                        }
                                        if (fuelLoad > 0) {
                                            emit(cmdCount, "fuel " + to_string(f.id) + " " + to_string(fuelLoad));
                                            f.fuel += fuelLoad;
                                            bb.fuelSupply -= fuelLoad;
                                        }

                                        // Missile loading strategy.
                                        long long remainingDef = redBases[t].defenseRemaining;
                                        if (remainingDef < 0) remainingDef = 0;
                                        long long desiredMiss = min<long long>(f.C, remainingDef);
                                        long long missLoad = 0;
                                        maxMissLoad = min(bb.missileSupply, (long long)f.C - f.missiles);
                                        if (f.missiles < desiredMiss) {
                                            missLoad = min<long long>(maxMissLoad, desiredMiss - f.missiles);
                                        }
                                        if (f.missiles + missLoad <= 0) {
                                            missLoad = maxMissLoad; // load anything available
                                        }
                                        if (missLoad > 0) {
                                            emit(cmdCount, "missile " + to_string(f.id) + " " + to_string(missLoad));
                                            f.missiles += missLoad;
                                            bb.missileSupply -= missLoad;
                                        }

                                        f.mode = (distLL == 0 ? Fighter::ATTACKING : Fighter::TO_TARGET);
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Issue at most one action: move or attack.
            if (!actionIssued) {
                if (f.mode == Fighter::TO_TARGET) {
                    if (f.pathPos < (int)f.path.size()) {
                        if (f.fuel > 0) {
                            int dir = f.path[f.pathPos];
                            int nx = f.x + dx[dir], ny = f.y + dy[dir];
                            // Move should be valid due to BFS, but keep safe.
                            if (0 <= nx && nx < n && 0 <= ny && ny < m && grid[nx][ny] != '#') {
                                emit(cmdCount, "move " + to_string(f.id) + " " + to_string(dir));
                                f.x = nx;
                                f.y = ny;
                                f.fuel -= 1;
                                f.pathPos++;
                                // Do not attack in the same frame even if reached.
                                if (f.pathPos >= (int)f.path.size() && f.x == f.attackX && f.y == f.attackY) {
                                    f.mode = Fighter::ATTACKING;
                                }
                            } else {
                                // Path invalid; give up.
                                releaseReservation(f);
                                f.mode = Fighter::STRANDED;
                            }
                            actionIssued = true;
                        } else {
                            // Out of fuel; give up.
                            releaseReservation(f);
                            f.mode = Fighter::STRANDED;
                        }
                    } else {
                        if (f.x == f.attackX && f.y == f.attackY) f.mode = Fighter::ATTACKING;
                        else {
                            // Inconsistent; give up.
                            releaseReservation(f);
                            f.mode = Fighter::STRANDED;
                        }
                    }
                }

                if (!actionIssued && f.mode == Fighter::ATTACKING) {
                    int t = f.targetRed;
                    if (t == -1 || redBases[t].defenseRemaining <= 0) {
                        if (f.x == hx && f.y == hy) f.mode = Fighter::IDLE;
                        else f.mode = Fighter::RETURNING;
                    } else {
                        int rx = redBases[t].x, ry = redBases[t].y;
                        int adir = -1;
                        for (int d = 0; d < 4; d++) {
                            if (f.x + dx[d] == rx && f.y + dy[d] == ry) {
                                adir = d;
                                break;
                            }
                        }
                        if (adir == -1) {
                            // Not adjacent; cannot attack. Give up.
                            releaseReservation(f);
                            f.mode = Fighter::STRANDED;
                        } else if (f.missiles > 0) {
                            long long need = redBases[t].defenseRemaining;
                            long long cnt = min<long long>(f.missiles, need);
                            if (cnt > 0) {
                                emit(cmdCount, "attack " + to_string(f.id) + " " + to_string(adir) + " " + to_string(cnt));
                                f.missiles -= cnt;
                                redBases[t].defenseRemaining -= cnt;
                                if (redBases[t].defenseRemaining <= 0) {
                                    redBases[t].defenseRemaining = 0;
                                    if (reservedBy[t] == f.id) reservedBy[t] = -1;
                                    f.targetRed = -1;
                                    if (f.x == hx && f.y == hy) f.mode = Fighter::IDLE;
                                    else {
                                        f.mode = Fighter::RETURNING;
                                        f.returnPos = 0;
                                    }
                                } else if (f.missiles == 0) {
                                    if (f.x == hx && f.y == hy) f.mode = Fighter::IDLE;
                                    else {
                                        f.mode = Fighter::RETURNING;
                                        f.returnPos = 0;
                                    }
                                }
                            } else {
                                // Shouldn't happen; start returning.
                                if (f.x == hx && f.y == hy) f.mode = Fighter::IDLE;
                                else {
                                    f.mode = Fighter::RETURNING;
                                    f.returnPos = 0;
                                }
                            }
                            actionIssued = true;
                        } else {
                            // No missiles: start returning, and move immediately if possible.
                            if (f.x == hx && f.y == hy) {
                                f.mode = Fighter::IDLE;
                            } else {
                                f.mode = Fighter::RETURNING;
                                f.returnPos = 0;
                                if (f.returnPos < (int)f.returnPath.size() && f.fuel > 0) {
                                    int dir = f.returnPath[f.returnPos];
                                    int nx = f.x + dx[dir], ny = f.y + dy[dir];
                                    if (0 <= nx && nx < n && 0 <= ny && ny < m && grid[nx][ny] != '#') {
                                        emit(cmdCount, "move " + to_string(f.id) + " " + to_string(dir));
                                        f.x = nx;
                                        f.y = ny;
                                        f.fuel -= 1;
                                        f.returnPos++;
                                        if (f.x == hx && f.y == hy) f.mode = Fighter::IDLE;
                                        actionIssued = true;
                                    } else {
                                        // Can't move; give up and release reservation.
                                        releaseReservation(f);
                                        f.mode = Fighter::STRANDED;
                                    }
                                } else if (f.fuel == 0) {
                                    // Stranded; release.
                                    releaseReservation(f);
                                    f.mode = Fighter::STRANDED;
                                }
                            }
                        }
                    }
                }

                if (!actionIssued && f.mode == Fighter::RETURNING) {
                    if (f.x == hx && f.y == hy) {
                        f.mode = Fighter::IDLE;
                    } else if (f.returnPos < (int)f.returnPath.size()) {
                        if (f.fuel > 0) {
                            int dir = f.returnPath[f.returnPos];
                            int nx = f.x + dx[dir], ny = f.y + dy[dir];
                            if (0 <= nx && nx < n && 0 <= ny && ny < m && grid[nx][ny] != '#') {
                                emit(cmdCount, "move " + to_string(f.id) + " " + to_string(dir));
                                f.x = nx;
                                f.y = ny;
                                f.fuel -= 1;
                                f.returnPos++;
                                if (f.x == hx && f.y == hy) f.mode = Fighter::IDLE;
                            } else {
                                // Invalid; stranded.
                                releaseReservation(f);
                                f.mode = Fighter::STRANDED;
                            }
                            actionIssued = true;
                        } else {
                            releaseReservation(f);
                            f.mode = Fighter::STRANDED;
                        }
                    } else {
                        // Should be at home but isn't; stranded.
                        releaseReservation(f);
                        f.mode = Fighter::STRANDED;
                    }
                }
            }

            if (f.mode == Fighter::TO_TARGET || f.mode == Fighter::ATTACKING || f.mode == Fighter::RETURNING) {
                anyActiveAfter = true;
            }
        }

        cout << "OK\n";

        if (cmdCount == 0 && !anyActiveAfter) {
            // No commands and no active missions; end early.
            break;
        }
    }

    return 0;
}