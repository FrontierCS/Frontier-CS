#include <bits/stdc++.h>
using namespace std;

struct BlueBase {
    int x, y;
    long long fuelSupply;
    long long missileSupply;
    long long d, v; // unused for blue
};
struct RedBase {
    int x, y;
    long long g, c; // unused for red
    long long d; // defense remaining
    long long v; // value
    bool alive;
};
struct Fighter {
    int id;
    int x, y;
    int G, C;
    long long fuel = 0;
    long long missiles = 0;
    vector<pair<int,int>> path; // sequence of cells to move to
    int mode = 0; // 0 Idle, 1 ToTarget, 2 Attack, 3 ToBase
    int targetRed = -1;
    int attackDir = -1;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<string> grid(n);
    for (int i = 0; i < n; ++i) cin >> grid[i];

    auto inb = [&](int x, int y){ return x>=0 && x<n && y>=0 && y<m; };

    int NB;
    cin >> NB;
    vector<BlueBase> blueBases(NB);
    vector<vector<int>> blueIndex(n, vector<int>(m, -1));
    for (int i = 0; i < NB; ++i) {
        int x,y; cin >> x >> y;
        long long g,c,d,v; cin >> g >> c >> d >> v;
        blueBases[i] = {x,y,g,c,d,v};
        if (inb(x,y)) blueIndex[x][y] = i;
    }

    int NR;
    cin >> NR;
    vector<RedBase> redBases(NR);
    vector<vector<int>> redIndex(n, vector<int>(m, -1));
    for (int i = 0; i < NR; ++i) {
        int x,y; cin >> x >> y;
        long long g,c,d,v; cin >> g >> c >> d >> v;
        redBases[i] = {x,y,g,c,d,v,true};
        if (inb(x,y)) redIndex[x][y] = i;
    }

    int K;
    cin >> K;
    vector<Fighter> fighters(K);
    for (int i = 0; i < K; ++i) {
        int x,y,G,C; cin >> x >> y >> G >> C;
        fighters[i].id = i;
        fighters[i].x = x; fighters[i].y = y;
        fighters[i].G = G; fighters[i].C = C;
    }

    const int dx[4] = {-1,1,0,0};
    const int dy[4] = {0,0,-1,1};

    auto isPassable = [&](int x, int y) -> bool {
        if (!inb(x,y)) return false;
        if (grid[x][y] == '#') {
            int ri = redIndex[x][y];
            if (ri >= 0) {
                if (!redBases[ri].alive) return true;
                return false;
            }
            return false;
        }
        return true;
    };

    auto bfs_from = [&](int sx, int sy, vector<int>& dist, vector<int>& parent) {
        int N = n*m;
        dist.assign(N, -1);
        parent.assign(N, -1);
        deque<int> dq;
        int sidx = sx*m + sy;
        dist[sidx] = 0;
        dq.push_back(sidx);
        while (!dq.empty()) {
            int u = dq.front(); dq.pop_front();
            int ux = u / m, uy = u % m;
            for (int dir=0; dir<4; ++dir) {
                int vx = ux + dx[dir], vy = uy + dy[dir];
                if (!inb(vx,vy)) continue;
                if (!isPassable(vx,vy)) continue;
                int vidx = vx*m + vy;
                if (dist[vidx] == -1) {
                    dist[vidx] = dist[u] + 1;
                    parent[vidx] = u;
                    dq.push_back(vidx);
                }
            }
        }
    };

    auto reconstruct_path = [&](int tx, int ty, const vector<int>& parent, int sx, int sy) -> vector<pair<int,int>> {
        vector<pair<int,int>> rev;
        int t = tx*m + ty;
        int s = sx*m + sy;
        if (t == s) return {};
        if (parent[t] == -1) return {};
        while (t != s) {
            int x = t / m, y = t % m;
            rev.emplace_back(x,y);
            t = parent[t];
            if (t == -1) { rev.clear(); break; }
        }
        reverse(rev.begin(), rev.end());
        return rev;
    };

    auto dir_from_to = [&](int ax, int ay, int bx, int by) -> int {
        if (bx == ax-1 && by == ay) return 0;
        if (bx == ax+1 && by == ay) return 1;
        if (bx == ax && by == ay-1) return 2;
        if (bx == ax && by == ay+1) return 3;
        return -1;
    };

    auto allRedDestroyed = [&](){
        for (auto &r: redBases) if (r.alive) return false;
        return true;
    };

    auto choose_target = [&](Fighter &f) -> bool {
        // must be on a blue base to check supplies
        if (!inb(f.x, f.y)) return false;
        int bi = blueIndex[f.x][f.y];
        if (bi < 0) return false;
        vector<int> dist, parent;
        bfs_from(f.x, f.y, dist, parent);
        long long bestDist = LLONG_MAX;
        long long bestV = -1;
        int bestRed = -1;
        int bestAdjX = -1, bestAdjY = -1, bestDir = -1;

        for (int ri = 0; ri < NR; ++ri) {
            if (!redBases[ri].alive) continue;
            int rx = redBases[ri].x, ry = redBases[ri].y;
            // find best neighbor
            long long minAdjDist = LLONG_MAX;
            int adjx=-1, adjy=-1, adir=-1;
            for (int d=0; d<4; ++d) {
                int nx = rx + dx[d], ny = ry + dy[d];
                if (!inb(nx,ny)) continue;
                if (!isPassable(nx,ny)) continue;
                int idx = nx*m + ny;
                if (dist[idx] >= 0) {
                    if ((long long)dist[idx] < minAdjDist) {
                        minAdjDist = dist[idx];
                        adjx = nx; adjy = ny; adir = d;
                    }
                }
            }
            if (minAdjDist == LLONG_MAX) continue;
            // constraints: within tank capacity
            if (minAdjDist > f.G) continue;
            long long needFuel = max(0LL, minAdjDist - f.fuel);
            if (blueBases[bi].fuelSupply < needFuel) continue; // cannot even fuel enough to reach
            if (blueBases[bi].missileSupply <= 0 && f.missiles <= 0) continue; // cannot attack
            // choose by minimal distance, then higher value
            if (minAdjDist < bestDist || (minAdjDist == bestDist && redBases[ri].v > bestV)) {
                bestDist = minAdjDist;
                bestV = redBases[ri].v;
                bestRed = ri;
                bestAdjX = adjx; bestAdjY = adjy; bestDir = adir;
            }
        }
        if (bestRed == -1) return false;
        // reconstruct path to bestAdj
        vector<int> dist2, parent2;
        bfs_from(f.x, f.y, dist2, parent2);
        vector<pair<int,int>> p = reconstruct_path(bestAdjX, bestAdjY, parent2, f.x, f.y);
        f.targetRed = bestRed;
        f.path = p;
        f.attackDir = bestDir;
        f.mode = (p.empty() ? 2 : 1); // if already adjacent, attack; else move to target
        return true;
    };

    auto path_to_nearest_blue = [&](Fighter &f) -> bool {
        vector<int> dist, parent;
        bfs_from(f.x, f.y, dist, parent);
        long long bestD = LLONG_MAX;
        int tx=-1, ty=-1;
        for (int i=0;i<NB;++i) {
            int bx = blueBases[i].x, by = blueBases[i].y;
            int idx = bx*m + by;
            if (dist[idx] >= 0) {
                if (dist[idx] < bestD) {
                    bestD = dist[idx];
                    tx = bx; ty = by;
                }
            }
        }
        if (tx == -1) return false;
        f.path = reconstruct_path(tx, ty, parent, f.x, f.y);
        f.mode = 3; // ToBase
        return true;
    };

    auto on_blue = [&](Fighter &f) -> bool {
        if (!inb(f.x,f.y)) return false;
        return blueIndex[f.x][f.y] != -1;
    };

    auto reload_at_base = [&](Fighter &f, long long needFuel, long long needMissiles, vector<string>& frame) -> bool {
        int bi = blueIndex[f.x][f.y];
        if (bi < 0) return false;
        bool did = false;
        long long addFuel = 0;
        if (f.fuel < needFuel) {
            addFuel = min({needFuel - f.fuel, blueBases[bi].fuelSupply, (long long)f.G - f.fuel});
            if (addFuel > 0) {
                frame.push_back("fuel " + to_string(f.id) + " " + to_string(addFuel));
                blueBases[bi].fuelSupply -= addFuel;
                f.fuel += addFuel;
                did = true;
            }
        }
        long long addMiss = 0;
        if (f.missiles < needMissiles) {
            addMiss = min({needMissiles - f.missiles, blueBases[bi].missileSupply, (long long)f.C - f.missiles});
            if (addMiss > 0) {
                frame.push_back("missile " + to_string(f.id) + " " + to_string(addMiss));
                blueBases[bi].missileSupply -= addMiss;
                f.missiles += addMiss;
                did = true;
            }
        }
        return did;
    };

    const int MAX_FRAMES = 15000;
    int frames = 0;
    int idleStreak = 0;

    while (frames < MAX_FRAMES) {
        vector<string> frame;
        bool anyAction = false;

        if (allRedDestroyed()) {
            break;
        }

        for (int i = 0; i < K; ++i) {
            Fighter &f = fighters[i];

            // Check if current target still alive
            if (f.targetRed != -1 && !redBases[f.targetRed].alive) {
                f.targetRed = -1;
                f.path.clear();
                if (f.mode == 1 || f.mode == 2) f.mode = 0; // reset to Idle
            }

            bool acted = false;

            if (f.mode == 1) { // ToTarget
                if (!f.path.empty()) {
                    if (f.fuel >= 1) {
                        auto nxt = f.path.front();
                        int dir = dir_from_to(f.x, f.y, nxt.first, nxt.second);
                        if (dir != -1) {
                            frame.push_back("move " + to_string(f.id) + " " + to_string(dir));
                            f.fuel -= 1;
                            f.x = nxt.first; f.y = nxt.second;
                            f.path.erase(f.path.begin());
                            acted = true;
                        } else {
                            // path broken, recompute
                            f.path.clear();
                        }
                    } else if (on_blue(f)) {
                        long long needFuel = (long long)f.path.size();
                        long long needMiss = max(1LL, min((long long)f.C, f.targetRed>=0 ? redBases[f.targetRed].d : (long long)1));
                        if (reload_at_base(f, needFuel, needMiss, frame)) {
                            acted = true;
                        }
                    } else {
                        // no fuel and not on base: stuck
                    }
                } else {
                    f.mode = 2; // arrived
                }
            }

            if (!acted && f.mode == 2) { // Attack
                if (f.targetRed == -1 || !redBases[f.targetRed].alive) {
                    f.mode = 0;
                } else {
                    int rx = redBases[f.targetRed].x, ry = redBases[f.targetRed].y;
                    int ddir = dir_from_to(f.x, f.y, rx, ry);
                    if (ddir == -1) {
                        // not adjacent anymore; recompute
                        f.mode = 0;
                    } else if (f.missiles > 0) {
                        long long cnt = min(f.missiles, redBases[f.targetRed].d);
                        if (cnt > 0) {
                            frame.push_back("attack " + to_string(f.id) + " " + to_string(ddir) + " " + to_string(cnt));
                            f.missiles -= cnt;
                            redBases[f.targetRed].d -= cnt;
                            if (redBases[f.targetRed].d <= 0) {
                                redBases[f.targetRed].alive = false;
                            }
                            acted = true;
                        }
                    } else {
                        // go to base to reload
                        if (!path_to_nearest_blue(f)) {
                            f.mode = 0;
                        }
                    }
                }
            }

            if (!acted && f.mode == 3) { // ToBase
                if (!f.path.empty()) {
                    if (f.fuel >= 1) {
                        auto nxt = f.path.front();
                        int dir = dir_from_to(f.x, f.y, nxt.first, nxt.second);
                        if (dir != -1) {
                            frame.push_back("move " + to_string(f.id) + " " + to_string(dir));
                            f.fuel -= 1;
                            f.x = nxt.first; f.y = nxt.second;
                            f.path.erase(f.path.begin());
                            acted = true;
                        } else {
                            f.path.clear();
                        }
                    } else if (on_blue(f)) {
                        f.mode = 0; // already on base
                    } else {
                        // stuck
                    }
                } else {
                    f.mode = 0; // reached base
                }
            }

            if (!acted && f.mode == 0) { // Idle
                if (on_blue(f)) {
                    // If no target, choose one
                    if (f.targetRed == -1) {
                        choose_target(f);
                    }
                    if (f.targetRed != -1) {
                        // Ensure enough fuel and missiles
                        long long needFuel = (long long)f.path.size();
                        long long needMiss = max(1LL, min((long long)f.C, redBases[f.targetRed].d));
                        bool did = false;
                        if (f.fuel < needFuel || f.missiles < needMiss) {
                            if (reload_at_base(f, needFuel, needMiss, frame)) {
                                acted = true;
                                did = true;
                            }
                        }
                        if (!did) {
                            // If adjacent (path empty) and have missiles, attack
                            if (f.path.empty()) {
                                if (redBases[f.targetRed].alive && f.missiles > 0) {
                                    int rx = redBases[f.targetRed].x, ry = redBases[f.targetRed].y;
                                    int ddir = dir_from_to(f.x, f.y, rx, ry);
                                    if (ddir != -1) {
                                        long long cnt = min(f.missiles, redBases[f.targetRed].d);
                                        if (cnt > 0) {
                                            frame.push_back("attack " + to_string(f.id) + " " + to_string(ddir) + " " + to_string(cnt));
                                            f.missiles -= cnt;
                                            redBases[f.targetRed].d -= cnt;
                                            if (redBases[f.targetRed].d <= 0) {
                                                redBases[f.targetRed].alive = false;
                                            }
                                            acted = true;
                                        }
                                    } else {
                                        // somehow not adjacent; recompute
                                        f.targetRed = -1;
                                    }
                                } else if (redBases[f.targetRed].alive && f.missiles == 0) {
                                    // try reload at least 1
                                    long long needMiss2 = max(1LL, min((long long)f.C, redBases[f.targetRed].d));
                                    if (reload_at_base(f, f.fuel, needMiss2, frame)) {
                                        acted = true;
                                    }
                                } else {
                                    // target destroyed or no missiles possible
                                    f.targetRed = -1;
                                }
                            } else {
                                // start moving if enough fuel
                                if (!f.path.empty() && f.fuel >= 1) {
                                    auto nxt = f.path.front();
                                    int dir = dir_from_to(f.x, f.y, nxt.first, nxt.second);
                                    if (dir != -1) {
                                        frame.push_back("move " + to_string(f.id) + " " + to_string(dir));
                                        f.fuel -= 1;
                                        f.x = nxt.first; f.y = nxt.second;
                                        f.path.erase(f.path.begin());
                                        f.mode = 1;
                                        acted = true;
                                    } else {
                                        f.path.clear();
                                        f.targetRed = -1;
                                    }
                                } else if (!f.path.empty() && f.fuel == 0) {
                                    // try refuel
                                    long long needFuel2 = (long long)f.path.size();
                                    if (reload_at_base(f, needFuel2, f.missiles, frame)) {
                                        acted = true;
                                    }
                                }
                            }
                        }
                    } else {
                        // No target available; optionally refuel to full or reload missiles (do nothing to avoid waste)
                        // We choose to do nothing
                    }
                } else {
                    // not on blue base, go to nearest base
                    if (f.path.empty() || f.mode != 3) {
                        path_to_nearest_blue(f);
                    }
                    if (!f.path.empty() && f.fuel >= 1) {
                        auto nxt = f.path.front();
                        int dir = dir_from_to(f.x, f.y, nxt.first, nxt.second);
                        if (dir != -1) {
                            frame.push_back("move " + to_string(f.id) + " " + to_string(dir));
                            f.fuel -= 1;
                            f.x = nxt.first; f.y = nxt.second;
                            f.path.erase(f.path.begin());
                            f.mode = 3;
                            acted = true;
                        } else {
                            f.path.clear();
                        }
                    } else {
                        // stuck if no fuel
                    }
                }
            }

            if (acted) anyAction = true;
        }

        for (auto &cmd : frame) {
            cout << cmd << "\n";
        }
        cout << "OK\n";
        frames++;

        if (!anyAction) {
            idleStreak++;
        } else {
            idleStreak = 0;
        }
        if (idleStreak >= 50 || allRedDestroyed()) {
            break;
        }
    }

    return 0;
}