#include <bits/stdc++.h>
using namespace std;

struct BlueBase {
    int x, y;
    long long g, c;
    long long d, v; // unused for blue
};

struct RedBase {
    int x, y;
    long long d, v;
    bool assigned = false;
};

struct FighterPlan {
    bool hasPlan = false;
    int id;
    int homeBase = -1;
    int fuelUsed = 0;
    long long missilesUsed = 0;
    vector<int> path; // directions 0..3
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

    int bn;
    cin >> bn;
    vector<BlueBase> blue(bn);
    for (int i = 0; i < bn; ++i) {
        cin >> blue[i].x >> blue[i].y;
        cin >> blue[i].g >> blue[i].c >> blue[i].d >> blue[i].v;
    }
    int rn;
    cin >> rn;
    vector<RedBase> red(rn);
    for (int i = 0; i < rn; ++i) {
        int x, y;
        long long g, c, d, v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
        red[i].x = x; red[i].y = y; red[i].d = d; red[i].v = v;
    }
    int k;
    cin >> k;
    struct Fighter { int id, x, y, G, C; int homeBase; };
    vector<Fighter> fighters(k);
    for (int i = 0; i < k; ++i) {
        int x, y, G, C;
        cin >> x >> y >> G >> C;
        fighters[i] = {i, x, y, G, C, -1};
    }

    // Map blue base positions to index
    map<pair<int,int>, int> blueIndex;
    for (int i = 0; i < bn; ++i) {
        blueIndex[{blue[i].x, blue[i].y}] = i;
    }
    for (auto &f: fighters) {
        auto it = blueIndex.find({f.x, f.y});
        if (it != blueIndex.end()) f.homeBase = it->second;
        else f.homeBase = -1;
    }

    vector<vector<bool>> passable(n, vector<bool>(m, true));
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            if (grid[i][j] == '#') passable[i][j] = false;

    const int dx[4] = {-1, 1, 0, 0};
    const int dy[4] = {0, 0, -1, 1};

    auto bfs = [&](int sx, int sy, vector<int> &dist, vector<int> &par, vector<int> &pdir) {
        int N = n*m;
        dist.assign(N, -1);
        par.assign(N, -1);
        pdir.assign(N, -1);
        deque<int> q;
        int sidx = sx*m + sy;
        dist[sidx] = 0;
        q.push_back(sidx);
        while(!q.empty()){
            int u = q.front(); q.pop_front();
            int ux = u / m, uy = u % m;
            for (int dir = 0; dir < 4; ++dir) {
                int vx = ux + dx[dir], vy = uy + dy[dir];
                if (vx < 0 || vx >= n || vy < 0 || vy >= m) continue;
                if (!passable[vx][vy]) continue;
                int vidx = vx*m + vy;
                if (dist[vidx] != -1) continue;
                dist[vidx] = dist[u] + 1;
                par[vidx] = u;
                pdir[vidx] = dir; // moved from u to vidx via dir
                q.push_back(vidx);
            }
        }
    };

    vector<FighterPlan> plans(k);
    for (int i = 0; i < k; ++i) {
        plans[i].id = i;
        plans[i].homeBase = fighters[i].homeBase;
    }

    // Assign targets
    for (int i = 0; i < k; ++i) {
        auto &f = fighters[i];
        if (f.homeBase < 0) continue; // invalid start
        // BFS from fighter position
        vector<int> dist, par, pdir;
        bfs(f.x, f.y, dist, par, pdir);

        int bestRed = -1;
        int bestL = -1;
        int bestAdjX = -1, bestAdjY = -1;
        int bestAttackDir = -1;
        double bestScore = -1.0;

        for (int r = 0; r < rn; ++r) {
            if (red[r].assigned) continue;
            if (red[r].d > f.C) continue; // can't carry enough missiles
            // find best adjacent cell
            int rx = red[r].x, ry = red[r].y;
            int localBestL = INT_MAX;
            int adjx = -1, adjy = -1, attackDir = -1;
            for (int dir = 0; dir < 4; ++dir) {
                int ax = rx + dx[dir]*(-1); // adjacent cell from which to attack in 'dir'? Let's compute properly below
                // Actually we want fighter at (rx - dx[dir], ry - dy[dir]) to attack towards dir.
                int fx = rx - dx[dir];
                int fy = ry - dy[dir];
                if (fx < 0 || fx >= n || fy < 0 || fy >= m) continue;
                if (!passable[fx][fy]) continue;
                int idx = fx*m + fy;
                if (dist[idx] == -1) continue;
                if (dist[idx] < localBestL) {
                    localBestL = dist[idx];
                    adjx = fx; adjy = fy;
                    attackDir = dir;
                }
            }
            if (localBestL == INT_MAX) continue; // unreachable
            if (localBestL > f.G) continue; // cannot carry enough fuel capacity
            // Check base supplies available
            auto &b = blue[f.homeBase];
            if (b.g < localBestL) continue;
            if (b.c < red[r].d) continue;

            // score
            double sc = (double)red[r].v / (double)(localBestL + 1);
            // Prefer higher sc, tie-breaker: higher value, then shorter L
            if (sc > bestScore + 1e-12 ||
                (abs(sc - bestScore) <= 1e-12 && (red[r].v > (bestRed==-1? -1 : red[bestRed].v))) ||
                (abs(sc - bestScore) <= 1e-12 && red[r].v == (bestRed==-1? -1 : red[bestRed].v) && localBestL < bestL)) {
                bestScore = sc;
                bestRed = r;
                bestL = localBestL;
                bestAdjX = adjx;
                bestAdjY = adjy;
                bestAttackDir = -1;
                // attackDir mapping computed as direction from adj cell to red:
                int dxr = red[r].x - adjx;
                int dyr = red[r].y - adjy;
                if (dxr == -1 && dyr == 0) bestAttackDir = 0;
                else if (dxr == 1 && dyr == 0) bestAttackDir = 1;
                else if (dxr == 0 && dyr == -1) bestAttackDir = 2;
                else if (dxr == 0 && dyr == 1) bestAttackDir = 3;
            }
        }

        if (bestRed == -1) continue; // no feasible assignment

        // Reconstruct path to (bestAdjX, bestAdjY)
        vector<int> dists, parents, pdirs;
        bfs(f.x, f.y, dists, parents, pdirs);
        int targetIdx = bestAdjX * m + bestAdjY;
        vector<int> path;
        int cur = targetIdx;
        int sidx = f.x * m + f.y;
        while (cur != sidx) {
            int dir = pdirs[cur];
            if (dir < 0) { path.clear(); break; }
            path.push_back(dir);
            cur = parents[cur];
        }
        reverse(path.begin(), path.end());
        if ((int)path.size() != bestL) {
            // Fallback: if mismatch, skip planning
            continue;
        }

        // Deduct supplies
        blue[f.homeBase].g -= bestL;
        blue[f.homeBase].c -= red[bestRed].d;
        red[bestRed].assigned = true;

        plans[i].hasPlan = true;
        plans[i].fuelUsed = bestL;
        plans[i].missilesUsed = red[bestRed].d;
        plans[i].path = path;
        plans[i].attackDir = bestAttackDir;
    }

    // Compute max path length among planned fighters
    int Lmax = 0;
    bool anyPlan = false;
    for (int i = 0; i < k; ++i) {
        if (plans[i].hasPlan) {
            anyPlan = true;
            Lmax = max(Lmax, (int)plans[i].path.size());
        }
    }

    // Frame 0: refuel and reload
    for (int i = 0; i < k; ++i) {
        if (!plans[i].hasPlan) continue;
        if (plans[i].fuelUsed > 0) {
            cout << "fuel " << plans[i].id << " " << plans[i].fuelUsed << "\n";
        }
        if (plans[i].missilesUsed > 0) {
            cout << "missile " << plans[i].id << " " << plans[i].missilesUsed << "\n";
        }
    }
    cout << "OK\n";

    // Movement frames
    for (int t = 0; t < Lmax; ++t) {
        for (int i = 0; i < k; ++i) {
            if (!plans[i].hasPlan) continue;
            if (t < (int)plans[i].path.size()) {
                int dir = plans[i].path[t];
                cout << "move " << plans[i].id << " " << dir << "\n";
            }
        }
        cout << "OK\n";
    }

    // Attack frame (single synchronized attack after all movements)
    if (anyPlan) {
        for (int i = 0; i < k; ++i) {
            if (!plans[i].hasPlan) continue;
            if (plans[i].missilesUsed > 0 && plans[i].attackDir >= 0) {
                cout << "attack " << plans[i].id << " " << plans[i].attackDir << " " << plans[i].missilesUsed << "\n";
            }
        }
        cout << "OK\n";
    }

    return 0;
}