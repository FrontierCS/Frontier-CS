#include <bits/stdc++.h>
using namespace std;

struct BlueBase {
    int x, y;
    long long g, c;
    long long d_unused, v_unused;
};
struct RedBase {
    int x, y;
    long long g_unused, c_unused;
    long long d, v;
    bool claimed = false;
};
struct Fighter {
    int id;
    int x, y;
    int G, C;
    int baseId;
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

    int NB;
    cin >> NB;
    vector<BlueBase> blue(NB);
    for (int i = 0; i < NB; ++i) {
        cin >> blue[i].x >> blue[i].y;
    }
    for (int i = 0; i < NB; ++i) {
        cin >> blue[i].g >> blue[i].c >> blue[i].d_unused >> blue[i].v_unused;
    }

    int NR;
    cin >> NR;
    vector<RedBase> red(NR);
    for (int i = 0; i < NR; ++i) {
        cin >> red[i].x >> red[i].y;
    }
    for (int i = 0; i < NR; ++i) {
        cin >> red[i].g_unused >> red[i].c_unused >> red[i].d >> red[i].v;
    }

    int k;
    cin >> k;
    vector<Fighter> fighters(k);
    for (int i = 0; i < k; ++i) {
        fighters[i].id = i;
        cin >> fighters[i].x >> fighters[i].y >> fighters[i].G >> fighters[i].C;
    }

    // Map blue base coordinates to index
    unordered_map<long long, int> coord2blue;
    coord2blue.reserve(NB * 2 + 1);
    auto keyfn = [&](int x, int y)->long long { return (static_cast<long long>(x) << 20) ^ y; };
    for (int i = 0; i < NB; ++i) coord2blue[keyfn(blue[i].x, blue[i].y)] = i;

    // Assign baseId to fighters (they start on a blue base)
    for (int i = 0; i < k; ++i) {
        long long key = keyfn(fighters[i].x, fighters[i].y);
        auto it = coord2blue.find(key);
        if (it != coord2blue.end()) {
            fighters[i].baseId = it->second;
        } else {
            // fallback: find closest blue base (shouldn't happen)
            int best = 0, bestd = INT_MAX;
            for (int j = 0; j < NB; ++j) {
                int d = abs(fighters[i].x - blue[j].x) + abs(fighters[i].y - blue[j].y);
                if (d < bestd) { bestd = d; best = j; }
            }
            fighters[i].baseId = best;
        }
    }

    // Remaining supplies per blue base
    vector<long long> g_rem(NB), c_rem(NB);
    for (int i = 0; i < NB; ++i) {
        g_rem[i] = blue[i].g;
        c_rem[i] = blue[i].c;
    }

    // Directions: 0 up, 1 down, 2 left, 3 right
    const int dx[4] = {-1, 1, 0, 0};
    const int dy[4] = {0, 0, -1, 1};

    int N = n, M = m;
    auto idx = [&](int x, int y){ return x * M + y; };

    // Base time offsets to avoid simultaneous refuel conflicts at same base
    vector<int> base_next_frame(NB, 0);

    // Commands per frame
    vector<vector<string>> frameCmds;
    int maxFrame = -1;

    auto ensureFrame = [&](int t){
        if (t < 0) return;
        if ((int)frameCmds.size() <= t) frameCmds.resize(t + 1);
        if (t > maxFrame) maxFrame = t;
    };
    auto addCmd = [&](int t, const string &cmd){
        ensureFrame(t);
        frameCmds[t].push_back(cmd);
    };

    // Plan for each fighter
    for (int i = 0; i < k; ++i) {
        Fighter &F = fighters[i];

        // BFS from fighter position avoiding red bases
        const int INF = 1e9;
        vector<int> dist(N * M, INF), par(N * M, -1);
        deque<int> q;
        int s = idx(F.x, F.y);
        dist[s] = 0;
        q.push_back(s);
        while (!q.empty()) {
            int u = q.front(); q.pop_front();
            int ux = u / M, uy = u % M;
            for (int dir = 0; dir < 4; ++dir) {
                int vx = ux + dx[dir], vy = uy + dy[dir];
                if (vx < 0 || vx >= N || vy < 0 || vy >= M) continue;
                if (grid[vx][vy] == '#') continue; // cannot enter red base cell
                int v = idx(vx, vy);
                if (dist[v] > dist[u] + 1) {
                    dist[v] = dist[u] + 1;
                    par[v] = u;
                    q.push_back(v);
                }
            }
        }

        // Choose a red base to attack: maximize v / (L+1), subject to constraints
        int bestRed = -1;
        int bestAdjX = -1, bestAdjY = -1, bestAttackDir = -1;
        int bestL = INF;
        double bestScore = -1.0;

        for (int j = 0; j < NR; ++j) {
            if (red[j].claimed) continue;
            // Need to find an adjacent cell to red[j]
            int rx = red[j].x, ry = red[j].y;
            int chosenDir = -1;
            int adjx = -1, adjy = -1;
            int L = INF;
            for (int dir = 0; dir < 4; ++dir) {
                int px = rx - dx[dir];
                int py = ry - dy[dir];
                if (px < 0 || px >= N || py < 0 || py >= M) continue;
                if (grid[px][py] == '#') continue; // cannot stand on red base
                int idp = idx(px, py);
                if (dist[idp] < L) {
                    L = dist[idp];
                    adjx = px; adjy = py;
                    chosenDir = dir;
                }
            }
            if (L >= INF) continue; // unreachable
            if (L > F.G) continue;  // cannot carry enough fuel
            int bId = F.baseId;
            if (g_rem[bId] < L) continue; // base lacks fuel
            if (F.C < red[j].d) continue; // capacity insufficient for required missiles
            if (c_rem[bId] < red[j].d) continue; // base lacks missiles

            double score = (double)red[j].v / (double)(L + 1);
            // Prefer higher score; tie-breaker smaller L, then larger v
            if (score > bestScore || (abs(score - bestScore) < 1e-12 && (L < bestL || (L == bestL && red[j].v > (bestRed == -1 ? -1 : red[bestRed].v))))) {
                bestScore = score;
                bestRed = j;
                bestAdjX = adjx;
                bestAdjY = adjy;
                bestAttackDir = chosenDir;
                bestL = L;
            }
        }

        if (bestRed == -1) {
            continue; // no plan
        }

        // Allocate supplies
        int bId = F.baseId;
        int L = bestL;
        long long missilesNeeded = red[bestRed].d;
        g_rem[bId] -= L;
        c_rem[bId] -= missilesNeeded;
        red[bestRed].claimed = true;

        // Reconstruct path from start to (bestAdjX, bestAdjY)
        vector<pair<int,int>> path;
        int tIdx = idx(bestAdjX, bestAdjY);
        if (dist[tIdx] >= INF) continue; // should not happen
        {
            int cur = tIdx;
            while (cur != s) {
                int cx = cur / M, cy = cur % M;
                path.emplace_back(cx, cy);
                cur = par[cur];
            }
            reverse(path.begin(), path.end()); // now from next after start to target
        }

        // Schedule commands
        int startFrame = base_next_frame[bId];
        base_next_frame[bId] = startFrame + 1; // next fighter at this base refuels at a later frame

        // At startFrame: refuel and load missiles
        {
            // Fuel exactly L
            if (L > 0) {
                string cmd = "fuel " + to_string(F.id) + " " + to_string(L);
                addCmd(startFrame, cmd);
            }
            if (missilesNeeded > 0) {
                string cmd = "missile " + to_string(F.id) + " " + to_string(missilesNeeded);
                addCmd(startFrame, cmd);
            }
        }

        // Moves: one per frame
        int curx = F.x, cury = F.y;
        int curFrame = startFrame + 1;
        for (auto &cell : path) {
            int nx = cell.first, ny = cell.second;
            int dir = -1;
            if (nx == curx - 1 && ny == cury) dir = 0;
            else if (nx == curx + 1 && ny == cury) dir = 1;
            else if (nx == curx && ny == cury - 1) dir = 2;
            else if (nx == curx && ny == cury + 1) dir = 3;
            else {
                // Should not happen
                // Skip invalid step
                curx = nx; cury = ny;
                continue;
            }
            string cmd = "move " + to_string(F.id) + " " + to_string(dir);
            addCmd(curFrame, cmd);
            curx = nx; cury = ny;
            curFrame++;
        }

        // Attack at arrival
        {
            string cmd = "attack " + to_string(F.id) + " " + to_string(bestAttackDir) + " " + to_string(missilesNeeded);
            addCmd(curFrame, cmd);
            // curFrame++;
        }
    }

    int totalFrames = maxFrame + 1;
    if (totalFrames <= 0) totalFrames = 1; // at least one frame
    for (int t = 0; t < totalFrames; ++t) {
        if (t < (int)frameCmds.size()) {
            for (const string &cmd : frameCmds[t]) {
                cout << cmd << "\n";
            }
        }
        cout << "OK\n";
    }

    return 0;
}