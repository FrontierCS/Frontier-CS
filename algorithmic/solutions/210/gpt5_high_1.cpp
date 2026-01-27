#include <bits/stdc++.h>
using namespace std;

struct BlueBase {
    int x, y;
    long long g_rem, c_rem;
};

struct RedBase {
    int x, y;
    long long d_rem;
    long long v;
    bool destroyed = false;
};

struct Fighter {
    int id;
    int x, y;
    int G, C;
    long long fuel = 0, missiles = 0;
    int homeBase = -1;
};

struct PathResult {
    bool ok = false;
    vector<int> dirs;
    int vx = -1, vy = -1;
    int attackDir = -1;
};

const int INF = 1e9;
const int MAX_FRAMES = 15000;
int n, m;
vector<string> grid;
vector<BlueBase> blueBases;
vector<RedBase> redBases;
vector<Fighter> fighters;
int dx[4] = {-1, 1, 0, 0};
int dy[4] = {0, 0, -1, 1};

bool inside(int x, int y) {
    return x >= 0 && x < n && y >= 0 && y < m;
}

int idx(int x, int y) {
    return x * m + y;
}

vector<int> bfsAllDist(int sx, int sy) {
    int N = n * m;
    vector<int> dist(N, INF);
    queue<pair<int,int>> q;
    dist[idx(sx, sy)] = 0;
    q.push({sx, sy});
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int dir = 0; dir < 4; ++dir) {
            int nx_ = x + dx[dir], ny_ = y + dy[dir];
            if (!inside(nx_, ny_)) continue;
            if (grid[nx_][ny_] == '#') continue; // can't enter red base cells
            int idn = idx(nx_, ny_);
            if (dist[idn] == INF) {
                dist[idn] = dist[idx(x, y)] + 1;
                q.push({nx_, ny_});
            }
        }
    }
    return dist;
}

PathResult bfsPathToVantage(int sx, int sy, const vector<pair<pair<int,int>, int>>& vantages) {
    int N = n * m;
    vector<int> dist(N, INF), prev(N, -1), prevDir(N, -1);
    vector<char> isTarget(N, 0);
    vector<int> attDir(N, -1);
    for (auto &va : vantages) {
        int vx = va.first.first, vy = va.first.second;
        int a = idx(vx, vy);
        isTarget[a] = 1;
        attDir[a] = va.second;
    }
    queue<int> q;
    int s = idx(sx, sy);
    dist[s] = 0;
    q.push(s);
    int target = -1;
    if (isTarget[s]) target = s;
    while (!q.empty() && target == -1) {
        int u = q.front(); q.pop();
        int ux = u / m, uy = u % m;
        for (int dir = 0; dir < 4; ++dir) {
            int vx = ux + dx[dir], vy = uy + dy[dir];
            if (!inside(vx, vy)) continue;
            if (grid[vx][vy] == '#') continue;
            int v = idx(vx, vy);
            if (dist[v] == INF) {
                dist[v] = dist[u] + 1;
                prev[v] = u;
                prevDir[v] = dir;
                if (isTarget[v]) {
                    target = v;
                    break;
                }
                q.push(v);
            }
        }
    }
    PathResult res;
    if (target == -1) return res;
    vector<int> dirs;
    int cur = target;
    while (cur != s) {
        dirs.push_back(prevDir[cur]);
        cur = prev[cur];
    }
    reverse(dirs.begin(), dirs.end());
    res.ok = true;
    res.dirs = dirs;
    res.vx = target / m;
    res.vy = target % m;
    res.attackDir = attDir[target];
    return res;
}

int oppositeDir(int d) {
    if (d == 0) return 1;
    if (d == 1) return 0;
    if (d == 2) return 3;
    return 2;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n >> m)) {
        return 0;
    }
    grid.resize(n);
    for (int i = 0; i < n; ++i) cin >> grid[i];

    int Nb; cin >> Nb;
    blueBases.resize(Nb);
    for (int i = 0; i < Nb; ++i) {
        cin >> blueBases[i].x >> blueBases[i].y;
        long long g, c, d, v;
        cin >> g >> c >> d >> v;
        blueBases[i].g_rem = g;
        blueBases[i].c_rem = c;
    }

    int Nr; cin >> Nr;
    redBases.resize(Nr);
    for (int i = 0; i < Nr; ++i) {
        cin >> redBases[i].x >> redBases[i].y;
        long long g, c, d, v;
        cin >> g >> c >> d >> v;
        redBases[i].d_rem = d;
        redBases[i].v = v;
    }

    int k; cin >> k;
    fighters.resize(k);
    for (int i = 0; i < k; ++i) {
        fighters[i].id = i;
        cin >> fighters[i].x >> fighters[i].y >> fighters[i].G >> fighters[i].C;
        fighters[i].fuel = 0;
        fighters[i].missiles = 0;
        // map fighter start to a blue base index
        fighters[i].homeBase = -1;
        for (int b = 0; b < Nb; ++b) {
            if (blueBases[b].x == fighters[i].x && blueBases[b].y == fighters[i].y) {
                fighters[i].homeBase = b;
                break;
            }
        }
        if (fighters[i].homeBase == -1) {
            // if not matched, choose nearest blue base by Manhattan (fallback)
            int bestB = 0, bestD = INT_MAX;
            for (int b = 0; b < Nb; ++b) {
                int d = abs(blueBases[b].x - fighters[i].x) + abs(blueBases[b].y - fighters[i].y);
                if (d < bestD) bestD = d, bestB = b;
            }
            fighters[i].homeBase = bestB;
        }
    }

    // Precompute all distances from each fighter's home base to all cells
    vector<vector<int>> distPerF(k);
    for (int f = 0; f < k; ++f) {
        int bx = blueBases[fighters[f].homeBase].x;
        int by = blueBases[fighters[f].homeBase].y;
        distPerF[f] = bfsAllDist(bx, by);
    }

    auto getVantages = [&](int rx, int ry) {
        vector<pair<pair<int,int>, int>> vans;
        for (int dir = 0; dir < 4; ++dir) {
            int vx = rx + dx[dir]*(-1); // This is incorrect; fix below after thought
        }
        // Actually compute adjacent cells and attack direction from vantage to red
        vector<pair<pair<int,int>, int>> res;
        // adjacency: from vantage (vx,vy) to red (rx,ry)
        // If red is up from vantage: rx == vx - 1 => attack dir 0
        // If red is down from vantage: rx == vx + 1 => attack dir 1
        // If red is left from vantage: ry == vy - 1 => attack dir 2
        // If red is right from vantage: ry == vy + 1 => attack dir 3
        int vx, vy;
        vx = rx - 1; vy = ry;
        if (inside(vx, vy) && grid[vx][vy] != '#') res.push_back({{vx, vy}, 1}); // vantage below red -> attack down? Wait mapping:
        // From (vx,vy) to (rx,ry): if rx == vx - 1 => red is up => attack dir 0
        // For vx = rx - 1 => rx == vx + 1 => This was confusing. Let's recompute carefully.
        // We'll rebuild res properly ignoring above lines, then return.
        res.clear();
        // Up direction: vantage below red? Let's recompute precisely:
        // If vantage at (vx,vy) and red at (rx,ry):
        // rx == vx - 1 => red is up from vantage -> attack dir 0
        // rx == vx + 1 => red is down -> dir 1
        // ry == vy - 1 => red is left -> dir 2
        // ry == vy + 1 => red is right -> dir 3
        // So we should generate candidate vantage cells as the neighbors of red:
        // (rx-1,ry) with attack dir 1? Wait careful: If vantage is (rx-1,ry), then from vantage, red is at (vx+1, vy) -> red is down => dir 1.
        // Yes.

        // top cell (above red)
        vx = rx - 1; vy = ry;
        if (inside(vx, vy) && grid[vx][vy] != '#') res.push_back({{vx, vy}, 1}); // red is down from vantage
        // bottom cell (below red)
        vx = rx + 1; vy = ry;
        if (inside(vx, vy) && grid[vx][vy] != '#') res.push_back({{vx, vy}, 0}); // red is up from vantage
        // left cell
        vx = rx; vy = ry - 1;
        if (inside(vx, vy) && grid[vx][vy] != '#') res.push_back({{vx, vy}, 3}); // red is right from vantage
        // right cell
        vx = rx; vy = ry + 1;
        if (inside(vx, vy) && grid[vx][vy] != '#') res.push_back({{vx, vy}, 2}); // red is left from vantage

        return res;
    };

    auto minDistToVantage = [&](int f, int rid, int &bestVx, int &bestVy, int &bestAttackDir) {
        auto vans = getVantages(redBases[rid].x, redBases[rid].y);
        int best = INF;
        bestVx = bestVy = bestAttackDir = -1;
        for (auto &va : vans) {
            int vx = va.first.first, vy = va.first.second;
            int ad = va.second;
            int d = distPerF[f][idx(vx, vy)];
            if (d < best) {
                best = d;
                bestVx = vx; bestVy = vy; bestAttackDir = ad;
            }
        }
        return best;
    };

    int framesUsed = 0;

    auto printFrame = [&](const vector<string> &cmds) {
        for (auto &s : cmds) cout << s << "\n";
        cout << "OK\n";
        // flush is not required
    };

    // Main selection loop: greedy choose best-valued destroyable red base using any fighter/home base
    while (framesUsed < MAX_FRAMES) {
        long long bestValue = -1;
        int bestF = -1, bestR = -1;
        int bestLen = -1;
        // Save cusp vantage details to avoid recompute later
        int candVx = -1, candVy = -1, candAtkDir = -1;
        int candTrips = 0;
        long long candFuelNeed = 0;
        long long candFramesNeed = 0;
        for (int f = 0; f < k; ++f) {
            int hb = fighters[f].homeBase;
            if (hb < 0) continue;
            for (int r = 0; r < Nr; ++r) {
                if (redBases[r].destroyed) continue;
                if (redBases[r].d_rem <= 0) continue;
                int vx, vy, atkDir;
                int d1 = minDistToVantage(f, r, vx, vy, atkDir);
                if (d1 >= INF) continue;
                if (2LL * d1 > fighters[f].G) continue; // cannot do round trip
                long long trips = (redBases[r].d_rem + fighters[f].C - 1) / fighters[f].C;
                long long fuelNeed = 2LL * d1 * trips;
                if (blueBases[hb].g_rem < fuelNeed) continue; // not enough fuel at base
                if (blueBases[hb].c_rem < redBases[r].d_rem) continue; // require enough missiles at this base
                long long framesNeed = trips * (2LL * d1 + 2); // per trip: moves there and back + 1 attack + 1 fuel/missile frame
                if (framesUsed + framesNeed > MAX_FRAMES) continue;
                if (redBases[r].v > bestValue) {
                    bestValue = redBases[r].v;
                    bestF = f; bestR = r;
                    bestLen = d1;
                    candVx = vx; candVy = vy; candAtkDir = atkDir;
                    candTrips = (int)trips;
                    candFuelNeed = fuelNeed;
                    candFramesNeed = framesNeed;
                }
            }
        }
        if (bestF == -1) break;

        // Now execute missions for bestF on bestR
        Fighter &F = fighters[bestF];
        BlueBase &B = blueBases[F.homeBase];
        RedBase &R = redBases[bestR];

        // Recompute actual path using BFS to the set of vantages (to be safe and to get directions)
        auto vantages = getVantages(R.x, R.y);
        PathResult pr = bfsPathToVantage(blueBases[F.homeBase].x, blueBases[F.homeBase].y, vantages);
        if (!pr.ok) {
            // Should not happen, skip this target
            // Just break to avoid potential infinite loop
            break;
        }
        vector<int> pathDirs = pr.dirs;
        int attackDir = pr.attackDir;
        int pathLen = (int)pathDirs.size();

        // Perform the trips
        for (int t = 0; t < candTrips; ++t) {
            long long missilesToLoad = min<long long>(F.C - F.missiles, R.d_rem);
            long long needFuel = 2LL * pathLen - F.fuel;
            if (needFuel < 0) needFuel = 0;
            long long transferFuel = min<long long>(needFuel, B.g_rem);
            long long transferMissiles = min<long long>(missilesToLoad, B.c_rem);
            vector<string> cmds;
            if (transferFuel > 0) {
                cmds.push_back("fuel " + to_string(F.id) + " " + to_string(transferFuel));
                F.fuel += transferFuel;
                B.g_rem -= transferFuel;
            }
            if (transferMissiles > 0) {
                cmds.push_back("missile " + to_string(F.id) + " " + to_string(transferMissiles));
                F.missiles += transferMissiles;
                B.c_rem -= transferMissiles;
            }
            // Ensure we always output OK even if both were zero (shouldn't happen), but to be safe:
            printFrame(cmds);
            framesUsed++;

            // Move to vantage
            for (int dir : pathDirs) {
                // consume 1 fuel
                if (F.fuel > 0) F.fuel -= 1; // ensuring local simulation; checker will enforce
                vector<string> mcmd = { "move " + to_string(F.id) + " " + to_string(dir) };
                printFrame(mcmd);
                framesUsed++;
            }

            // Attack
            long long attackCnt = min<long long>(F.missiles, R.d_rem);
            if (attackCnt > 0) {
                vector<string> acmd = { "attack " + to_string(F.id) + " " + to_string(attackDir) + " " + to_string(attackCnt) };
                printFrame(acmd);
                framesUsed++;
                F.missiles -= attackCnt;
                R.d_rem -= attackCnt;
            } else {
                // Still need to spend a frame for OK to match our planning? Not necessary, but we skip.
            }

            // Move back to base
            for (int i = (int)pathDirs.size() - 1; i >= 0; --i) {
                int dir = oppositeDir(pathDirs[i]);
                if (F.fuel > 0) F.fuel -= 1;
                vector<string> mcmd = { "move " + to_string(F.id) + " " + to_string(dir) };
                printFrame(mcmd);
                framesUsed++;
            }
        }

        if (R.d_rem <= 0) {
            R.destroyed = true;
        }

        if (framesUsed >= MAX_FRAMES) break;
    }

    return 0;
}