#include <bits/stdc++.h>
using namespace std;

struct BlueBase {
    int x, y;
    long long g, c, d, v;
};

struct RedBase {
    int x, y;
    long long g, c, d, v;
    bool assigned = false;
};

struct Fighter {
    int x, y, G, C;
    int baseIdx = -1;
    int targetIdx = -1;
    int fLoad = 0;
    int mLoad = 0;
    vector<int> path; // sequence of directions 0..3
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

    auto inside = [&](int x, int y) {
        return x >= 0 && x < n && y >= 0 && y < m;
    };

    int NB;
    cin >> NB;
    vector<BlueBase> blue(NB);
    unordered_map<long long, int> blueIndex;
    for (int i = 0; i < NB; ++i) {
        int x, y;
        cin >> x >> y;
        long long g, c, d, v;
        cin >> g >> c >> d >> v;
        blue[i] = {x, y, g, c, d, v};
        long long key = 1LL * x * (m + 5) + y;
        blueIndex[key] = i;
    }

    int NR;
    cin >> NR;
    vector<RedBase> red(NR);
    unordered_map<long long, int> redIndex;
    for (int i = 0; i < NR; ++i) {
        int x, y;
        cin >> x >> y;
        long long g, c, d, v;
        cin >> g >> c >> d >> v;
        red[i] = {x, y, g, c, d, v, false};
        long long key = 1LL * x * (m + 5) + y;
        redIndex[key] = i;
    }

    int K;
    cin >> K;
    vector<Fighter> fighters(K);
    for (int i = 0; i < K; ++i) {
        int x, y, G, Cc;
        cin >> x >> y >> G >> Cc;
        fighters[i] = {x, y, G, Cc, -1, -1, 0, 0, {}, -1};
        long long key = 1LL * x * (m + 5) + y;
        if (blueIndex.count(key)) fighters[i].baseIdx = blueIndex[key];
    }

    const int dx[4] = {-1, 1, 0, 0};
    const int dy[4] = {0, 0, -1, 1};

    auto bfs_all = [&](int sx, int sy, vector<vector<int>>& dist, vector<vector<short>>& prevDir) {
        dist.assign(n, vector<int>(m, -1));
        prevDir.assign(n, vector<short>(m, -1));
        deque<pair<int,int>> q;
        dist[sx][sy] = 0;
        q.push_back({sx, sy});
        while (!q.empty()) {
            auto [x, y] = q.front(); q.pop_front();
            for (int dir = 0; dir < 4; ++dir) {
                int nx = x + dx[dir], ny = y + dy[dir];
                if (!inside(nx, ny)) continue;
                if (grid[nx][ny] == '#') continue; // cannot step into red base cell
                if (dist[nx][ny] != -1) continue;
                dist[nx][ny] = dist[x][y] + 1;
                prevDir[nx][ny] = dir; // reached (nx,ny) from (x,y) via dir
                q.push_back({nx, ny});
            }
        }
    };

    auto reconstruct_path = [&](int sx, int sy, int tx, int ty, const vector<vector<short>>& prevDir) {
        vector<int> rev;
        int x = tx, y = ty;
        while (!(x == sx && y == sy)) {
            short dir = prevDir[x][y];
            if (dir == -1) { rev.clear(); break; }
            rev.push_back(dir);
            x -= dx[dir];
            y -= dy[dir];
        }
        reverse(rev.begin(), rev.end());
        return rev;
    };

    // Assign missions to fighters
    for (int i = 0; i < K; ++i) {
        Fighter &f = fighters[i];
        if (f.baseIdx < 0) continue;
        BlueBase &bb = blue[f.baseIdx];

        vector<vector<int>> dist;
        vector<vector<short>> prevDir;
        bfs_all(f.x, f.y, dist, prevDir);

        int bestRed = -1;
        int bestNx = -1, bestNy = -1;
        int bestDist = INT_MAX;
        long long bestVal = -1;
        int bestAttackDir = -1;

        for (int j = 0; j < NR; ++j) {
            if (red[j].assigned) continue;
            int rx = red[j].x, ry = red[j].y;
            // Need enough missiles and fuel availability from base
            if (red[j].d > f.C) continue;
            if (red[j].d > bb.c) continue;

            int localBestDist = INT_MAX;
            int localNx = -1, localNy = -1;
            int localAttackDir = -1;

            for (int dir = 0; dir < 4; ++dir) {
                int nx = rx + dx[dir], ny = ry + dy[dir];
                if (!inside(nx, ny)) continue;
                if (grid[nx][ny] == '#') continue; // cannot stand on another red base
                if (dist[nx][ny] == -1) continue;
                if (dist[nx][ny] < localBestDist) {
                    localBestDist = dist[nx][ny];
                    localNx = nx; localNy = ny;
                    // attack direction from (nx,ny) to (rx,ry)
                    if (rx == nx - 1 && ry == ny) localAttackDir = 0; // up
                    else if (rx == nx + 1 && ry == ny) localAttackDir = 1; // down
                    else if (ry == ny - 1 && rx == nx) localAttackDir = 2; // left
                    else if (ry == ny + 1 && rx == nx) localAttackDir = 3; // right
                }
            }
            if (localBestDist == INT_MAX) continue;
            if (localBestDist > f.G) continue;
            if (localBestDist > bb.g) continue;

            // choose by highest value, then by shorter distance
            if (red[j].v > bestVal || (red[j].v == bestVal && localBestDist < bestDist)) {
                bestVal = red[j].v;
                bestRed = j;
                bestNx = localNx;
                bestNy = localNy;
                bestDist = localBestDist;
                bestAttackDir = localAttackDir;
            }
        }

        if (bestRed != -1 && bestAttackDir != -1) {
            // Assign
            f.targetIdx = bestRed;
            f.fLoad = bestDist;
            f.mLoad = (int)red[bestRed].d;
            // Deduct supplies
            bb.g -= f.fLoad;
            bb.c -= f.mLoad;
            red[bestRed].assigned = true;

            // Reconstruct path
            vector<vector<int>> dist2;
            vector<vector<short>> prev2;
            bfs_all(f.x, f.y, dist2, prev2);
            f.path = reconstruct_path(f.x, f.y, bestNx, bestNy, prev2);
            f.attackDir = bestAttackDir;
        }
    }

    // Build frames: initial load, movement steps, attack
    vector<vector<string>> frames;

    // Initial load frame
    {
        vector<string> cmds;
        for (int i = 0; i < K; ++i) {
            const Fighter &f = fighters[i];
            if (f.targetIdx == -1) continue;
            if (f.fLoad > 0) {
                cmds.push_back(string("fuel ") + to_string(i) + " " + to_string(f.fLoad));
            }
            if (f.mLoad > 0) {
                cmds.push_back(string("missile ") + to_string(i) + " " + to_string(f.mLoad));
            }
        }
        frames.push_back(move(cmds));
    }

    int maxLen = 0;
    for (int i = 0; i < K; ++i) {
        if (fighters[i].targetIdx != -1) {
            maxLen = max<int>(maxLen, fighters[i].path.size());
        }
    }

    for (int step = 0; step < maxLen; ++step) {
        vector<string> cmds;
        for (int i = 0; i < K; ++i) {
            const Fighter &f = fighters[i];
            if (f.targetIdx == -1) continue;
            if (step < (int)f.path.size()) {
                int dir = f.path[step];
                cmds.push_back(string("move ") + to_string(i) + " " + to_string(dir));
            }
        }
        frames.push_back(move(cmds));
    }

    // Attack frame
    {
        vector<string> cmds;
        for (int i = 0; i < K; ++i) {
            const Fighter &f = fighters[i];
            if (f.targetIdx == -1) continue;
            if (f.mLoad > 0 && f.attackDir != -1) {
                cmds.push_back(string("attack ") + to_string(i) + " " + to_string(f.attackDir) + " " + to_string(f.mLoad));
            }
        }
        frames.push_back(move(cmds));
    }

    // Output frames
    for (auto &cmds : frames) {
        for (auto &s : cmds) cout << s << "\n";
        cout << "OK\n";
    }

    return 0;
}