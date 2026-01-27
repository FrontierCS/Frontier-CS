#include <bits/stdc++.h>
using namespace std;

struct BlueBase {
    int x, y;
    long long fuel; // g
    long long missile; // c
    // d, v ignored for blue
};

struct RedBase {
    int x, y;
    long long def; // remaining defense
    long long value;
    bool destroyed = false;
};

struct Fighter {
    int id;
    int x, y;
    int G, C; // capacities
    int fuel = 0;
    int missile = 0;
    int homeBaseIdx = -1;

    // Planning/state
    enum Mode { AT_BASE, TO_TARGET, ATTACK, TO_BASE, IDLE } mode = AT_BASE;

    int targetId = -1;
    int stagingX = -1, stagingY = -1;
    int attackDir = -1;

    vector<int> path; // directions from base to staging
    int pathIndex = 0;
    vector<int> pathBack; // directions from staging back to base
    int pathBackIndex = 0;
};

struct BFSResult {
    int n, m;
    vector<int> dist;      // size n*m
    vector<int> parent;    // previous cell index
    vector<int> cameDir;   // direction used from parent to this cell
    int startIdx;
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

    auto inside = [&](int x, int y){ return x>=0 && x<n && y>=0 && y<m; };

    int Bn;
    cin >> Bn;
    vector<BlueBase> blue(Bn);
    unordered_map<long long, int> bluePosToIdx; // key = ((long long)x<<32)|y
    for (int i = 0; i < Bn; ++i) {
        int x, y;
        cin >> x >> y;
        long long g, c, d, v;
        cin >> g >> c >> d >> v;
        blue[i] = {x, y, g, c};
        long long key = ( (long long)x << 32 ) ^ (unsigned long long)y;
        bluePosToIdx[key] = i;
    }

    int Rn;
    cin >> Rn;
    vector<RedBase> red(Rn);
    unordered_map<long long, int> redPosToIdx;
    for (int i = 0; i < Rn; ++i) {
        int x, y;
        cin >> x >> y;
        long long g, c, d, v;
        cin >> g >> c >> d >> v;
        red[i] = {x, y, d, v, false};
        long long key = ( (long long)x << 32 ) ^ (unsigned long long)y;
        redPosToIdx[key] = i;
    }

    int k;
    cin >> k;
    vector<Fighter> fighters(k);
    for (int i = 0; i < k; ++i) {
        int x, y, G, C;
        cin >> x >> y >> G >> C;
        fighters[i].id = i;
        fighters[i].x = x; fighters[i].y = y;
        fighters[i].G = G; fighters[i].C = C;
        long long key = ( (long long)x << 32 ) ^ (unsigned long long)y;
        if (bluePosToIdx.count(key)) fighters[i].homeBaseIdx = bluePosToIdx[key];
        else fighters[i].homeBaseIdx = -1;
    }

    // Directions
    int dx[4] = {-1, 1, 0, 0};
    int dy[4] = {0, 0, -1, 1};
    auto invDir = [&](int d){ if (d==0) return 1; if (d==1) return 0; if (d==2) return 3; return 2; };

    // Precompute BFS from each unique home base used by fighters
    unordered_map<int, BFSResult> bfsByBase; // baseIdx -> BFS
    auto idxOf = [&](int x, int y){ return x*m + y; };
    auto coordOf = [&](int idx){ return pair<int,int>(idx/m, idx%m); };

    set<int> neededBases;
    for (auto &f: fighters) if (f.homeBaseIdx >= 0) neededBases.insert(f.homeBaseIdx);

    for (int bidx : neededBases) {
        BFSResult res;
        res.n = n; res.m = m;
        res.dist.assign(n*m, -1);
        res.parent.assign(n*m, -1);
        res.cameDir.assign(n*m, -1);
        int sx = blue[bidx].x, sy = blue[bidx].y;
        int sidx = idxOf(sx, sy);
        res.startIdx = sidx;
        deque<int> dq;
        dq.push_back(sidx);
        res.dist[sidx] = 0;
        while (!dq.empty()) {
            int u = dq.front(); dq.pop_front();
            int ux = u / m, uy = u % m;
            for (int d = 0; d < 4; ++d) {
                int vx = ux + dx[d], vy = uy + dy[d];
                if (!inside(vx, vy)) continue;
                if (grid[vx][vy] == '#') continue; // cannot enter red base cells
                int v = idxOf(vx, vy);
                if (res.dist[v] != -1) continue;
                res.dist[v] = res.dist[u] + 1;
                res.parent[v] = u;
                res.cameDir[v] = d;
                dq.push_back(v);
            }
        }
        bfsByBase[bidx] = move(res);
    }

    auto reconstructPath = [&](const BFSResult &res, int tx, int ty){
        vector<int> dirs;
        int t = idxOf(tx, ty);
        if (res.dist[t] < 0) return dirs; // empty indicates unreachable
        int s = res.startIdx;
        vector<int> rev;
        int cur = t;
        while (cur != s) {
            int d = res.cameDir[cur];
            rev.push_back(d);
            cur = res.parent[cur];
        }
        dirs.assign(rev.rbegin(), rev.rend());
        return dirs;
    };

    auto choose_target = [&](const Fighter &f) {
        struct Choice { bool ok=false; int id=-1; int sx=0,sy=0; int dist=0; int attackDir=-1; long long val=0; };
        Choice best;
        if (f.homeBaseIdx < 0) return best;
        const BFSResult &res = bfsByBase[f.homeBaseIdx];
        for (int i = 0; i < (int)red.size(); ++i) {
            if (red[i].destroyed || red[i].def <= 0) continue;
            int rx = red[i].x, ry = red[i].y;
            int bestLocalDist = INT_MAX;
            int bestSX = -1, bestSY = -1, bestDir = -1;
            for (int d = 0; d < 4; ++d) {
                int sx = rx + dx[d]*-1; // staging is opposite direction from red to fighter
                int sy = ry + dy[d]*-1;
                if (!inside(sx, sy)) continue;
                if (grid[sx][sy] == '#') continue; // cannot stand on red base cell
                int idx = idxOf(sx, sy);
                int dist = res.dist[idx];
                if (dist < 0) continue;
                if (dist < bestLocalDist) {
                    bestLocalDist = dist;
                    bestSX = sx; bestSY = sy;
                    bestDir = d; // direction from fighter to red
                }
            }
            if (bestLocalDist == INT_MAX) continue;
            if (2 * bestLocalDist > f.G) continue; // must be able to go and return on one tank
            // prioritize smallest distance, then highest value
            if (!best.ok || bestLocalDist < best.dist || (bestLocalDist == best.dist && red[i].value > best.val)) {
                best.ok = true;
                best.id = i;
                best.sx = bestSX;
                best.sy = bestSY;
                best.dist = bestLocalDist;
                best.attackDir = bestDir;
                best.val = red[i].value;
            }
        }
        return best;
    };

    auto move_apply = [&](Fighter &f, int dir){
        f.x += dx[dir];
        f.y += dy[dir];
    };

    int maxFrames = 15000;
    for (int frame = 0; frame < maxFrames; ++frame) {
        vector<string> lines;

        for (auto &f : fighters) {
            vector<string> cmds;
            if (f.mode == Fighter::TO_TARGET) {
                if (f.pathIndex < (int)f.path.size()) {
                    if (f.fuel > 0) {
                        int dir = f.path[f.pathIndex];
                        cmds.push_back("move " + to_string(f.id) + " " + to_string(dir));
                        f.fuel -= 1;
                        move_apply(f, dir);
                        f.pathIndex++;
                        if (f.pathIndex == (int)f.path.size()) {
                            f.mode = Fighter::ATTACK;
                        }
                    } else {
                        f.mode = Fighter::IDLE;
                    }
                } else {
                    f.mode = Fighter::ATTACK;
                }
            } else if (f.mode == Fighter::ATTACK) {
                if (f.targetId >= 0 && !red[f.targetId].destroyed && red[f.targetId].def > 0 && f.missile > 0) {
                    long long cnt = min<long long>(f.missile, red[f.targetId].def);
                    cmds.push_back("attack " + to_string(f.id) + " " + to_string(f.attackDir) + " " + to_string(cnt));
                    f.missile -= (int)cnt;
                    red[f.targetId].def -= cnt;
                    if (red[f.targetId].def <= 0) {
                        red[f.targetId].destroyed = true;
                        f.targetId = -1;
                    }
                }
                // return to base regardless
                f.mode = Fighter::TO_BASE;
                f.pathBackIndex = 0;
            } else if (f.mode == Fighter::TO_BASE) {
                if (f.pathBackIndex < (int)f.pathBack.size()) {
                    if (f.fuel > 0) {
                        int dir = f.pathBack[f.pathBackIndex];
                        cmds.push_back("move " + to_string(f.id) + " " + to_string(dir));
                        f.fuel -= 1;
                        move_apply(f, dir);
                        f.pathBackIndex++;
                        if (f.pathBackIndex == (int)f.pathBack.size()) {
                            f.mode = Fighter::AT_BASE;
                        }
                    } else {
                        f.mode = Fighter::IDLE;
                    }
                } else {
                    f.mode = Fighter::AT_BASE;
                }
            } else if (f.mode == Fighter::AT_BASE) {
                // Refill at base if possible
                int bidx = f.homeBaseIdx;
                if (bidx >= 0) {
                    BlueBase &bb = blue[bidx];
                    bool didReload = false;
                    int needFuel = f.G - f.fuel;
                    if (needFuel > 0 && bb.fuel > 0) {
                        int take = (int)min<long long>(needFuel, bb.fuel);
                        if (take > 0) {
                            cmds.push_back("fuel " + to_string(f.id) + " " + to_string(take));
                            f.fuel += take;
                            bb.fuel -= take;
                            didReload = true;
                        }
                    }
                    int needMiss = f.C - f.missile;
                    if (needMiss > 0 && bb.missile > 0) {
                        int take = (int)min<long long>(needMiss, bb.missile);
                        if (take > 0) {
                            cmds.push_back("missile " + to_string(f.id) + " " + to_string(take));
                            f.missile += take;
                            bb.missile -= take;
                            didReload = true;
                        }
                    }

                    // If we already have a target and staging is base cell, we can attack immediately
                    if (f.targetId >= 0 && !red[f.targetId].destroyed && red[f.targetId].def > 0) {
                        if (f.stagingX == f.x && f.stagingY == f.y) {
                            if (f.missile > 0) {
                                long long cnt = min<long long>(f.missile, red[f.targetId].def);
                                cmds.push_back("attack " + to_string(f.id) + " " + to_string(f.attackDir) + " " + to_string(cnt));
                                f.missile -= (int)cnt;
                                red[f.targetId].def -= cnt;
                                if (red[f.targetId].def <= 0) {
                                    red[f.targetId].destroyed = true;
                                    f.targetId = -1;
                                }
                            }
                            // stay at base
                        } else {
                            // Prepare to move to target if possible
                            if (f.fuel >= 2 * (int)f.path.size() && f.missile > 0) {
                                f.mode = Fighter::TO_TARGET;
                                if (!didReload && !f.path.empty()) {
                                    // start moving this frame
                                    int dir = f.path[0];
                                    cmds.push_back("move " + to_string(f.id) + " " + to_string(dir));
                                    f.fuel -= 1;
                                    move_apply(f, dir);
                                    f.pathIndex = 1;
                                    if (f.pathIndex == (int)f.path.size()) f.mode = Fighter::ATTACK;
                                } else {
                                    f.pathIndex = 0;
                                }
                            }
                        }
                    } else {
                        // choose a new target
                        auto choice = choose_target(f);
                        if (choice.ok) {
                            // setup path and staging
                            const BFSResult &res = bfsByBase[f.homeBaseIdx];
                            vector<int> p = reconstructPath(res, choice.sx, choice.sy);
                            f.targetId = choice.id;
                            f.stagingX = choice.sx;
                            f.stagingY = choice.sy;
                            f.attackDir = choice.attackDir;
                            f.path = move(p);
                            f.pathIndex = 0;
                            // pathBack is reverse with inverted dirs
                            f.pathBack.clear();
                            for (int i = (int)f.path.size() - 1; i >= 0; --i) f.pathBack.push_back(invDir(f.path[i]));
                            f.pathBackIndex = 0;

                            // If staging is base cell, we can attack immediately
                            if (f.stagingX == f.x && f.stagingY == f.y) {
                                if (f.missile > 0) {
                                    long long cnt = min<long long>(f.missile, red[f.targetId].def);
                                    cmds.push_back("attack " + to_string(f.id) + " " + to_string(f.attackDir) + " " + to_string(cnt));
                                    f.missile -= (int)cnt;
                                    red[f.targetId].def -= cnt;
                                    if (red[f.targetId].def <= 0) {
                                        red[f.targetId].destroyed = true;
                                        f.targetId = -1;
                                    }
                                }
                            } else {
                                // if enough fuel and at least 1 missile, start moving
                                if (f.fuel >= 2 * (int)f.path.size() && f.missile > 0) {
                                    f.mode = Fighter::TO_TARGET;
                                    // if we didn't reload this frame, we can start moving immediately
                                    if (!cmds.empty() && (cmds.back().rfind("missile",0)==0 || cmds.back().rfind("fuel",0)==0)) {
                                        // we did reload - don't move this frame
                                    } else {
                                        if (!f.path.empty()) {
                                            int dir = f.path[0];
                                            cmds.push_back("move " + to_string(f.id) + " " + to_string(dir));
                                            f.fuel -= 1;
                                            move_apply(f, dir);
                                            f.pathIndex = 1;
                                            if (f.pathIndex == (int)f.path.size()) f.mode = Fighter::ATTACK;
                                        }
                                    }
                                }
                            }
                        } else {
                            // no target available; do nothing
                        }
                    }
                } else {
                    // No home base found; can't refuel/reload - idle
                    f.mode = Fighter::IDLE;
                }
            } else {
                // IDLE: do nothing
            }

            for (auto &s : cmds) lines.push_back(s);
        }

        for (auto &s : lines) {
            cout << s << "\n";
        }
        cout << "OK\n";

        if (lines.empty()) break; // no actions this frame; end early
    }

    return 0;
}