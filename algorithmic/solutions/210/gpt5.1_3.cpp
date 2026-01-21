#include <bits/stdc++.h>
using namespace std;

struct BlueBase {
    int x, y;
    long long g, c, d, v;
};

struct RedBase {
    int x, y;
    long long g, c, d, v;
};

struct Fighter {
    int x, y;
    int G, C;
};

const int INF = 1e9;
const int MAX_PATH = 14000;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }

    vector<string> grid(n);
    for (int i = 0; i < n; ++i) {
        cin >> grid[i];
    }

    int nb;
    cin >> nb;
    vector<BlueBase> blue(nb);
    for (int i = 0; i < nb; ++i) {
        cin >> blue[i].x >> blue[i].y;
        cin >> blue[i].g >> blue[i].c >> blue[i].d >> blue[i].v;
    }

    int nr;
    cin >> nr;
    vector<RedBase> red(nr);
    for (int i = 0; i < nr; ++i) {
        cin >> red[i].x >> red[i].y;
        cin >> red[i].g >> red[i].c >> red[i].d >> red[i].v;
    }

    int k;
    cin >> k;
    vector<Fighter> fighters(k);
    for (int i = 0; i < k; ++i) {
        cin >> fighters[i].x >> fighters[i].y >> fighters[i].G >> fighters[i].C;
    }

    int cells = n * m;

    // Map cell to blue base index (home base)
    vector<int> cellToBlueBase(cells, -1);
    for (int i = 0; i < nb; ++i) {
        int idx = blue[i].x * m + blue[i].y;
        cellToBlueBase[idx] = i;
    }

    vector<int> fighterHomeBase(k, -1);
    for (int i = 0; i < k; ++i) {
        int idx = fighters[i].x * m + fighters[i].y;
        if (idx >= 0 && idx < cells)
            fighterHomeBase[i] = cellToBlueBase[idx];
    }

    const int dx[4] = {-1, 1, 0, 0};
    const int dy[4] = {0, 0, -1, 1};
    const int opp[4] = {1, 0, 3, 2};

    // Distances from each fighter to each red base (adjacent cell)
    vector<vector<int>> baseDist(k, vector<int>(nr, INF));
    vector<vector<int>> baseDestIdx(k, vector<int>(nr, -1));
    vector<vector<int>> baseAtkDir(k, vector<int>(nr, -1));

    if (nr > 0) {
        // BFS for each fighter to compute distances to all cells
        for (int f = 0; f < k; ++f) {
            int sx = fighters[f].x;
            int sy = fighters[f].y;
            int sIdx = sx * m + sy;

            vector<int> dist(cells, -1);
            queue<int> q;
            dist[sIdx] = 0;
            q.push(sIdx);

            while (!q.empty()) {
                int idx = q.front(); q.pop();
                int x = idx / m;
                int y = idx % m;
                for (int dir = 0; dir < 4; ++dir) {
                    int nx = x + dx[dir];
                    int ny = y + dy[dir];
                    if (nx < 0 || nx >= n || ny < 0 || ny >= m) continue;
                    if (grid[nx][ny] == '#') continue; // cannot enter red base
                    int nidx = nx * m + ny;
                    if (dist[nidx] == -1) {
                        dist[nidx] = dist[idx] + 1;
                        q.push(nidx);
                    }
                }
            }

            // For each red base, find best adjacent cell
            for (int r = 0; r < nr; ++r) {
                int bx = red[r].x;
                int by = red[r].y;
                int bestD = INF;
                int bestCell = -1;
                int bestDir = -1;
                for (int d = 0; d < 4; ++d) {
                    int nx = bx + dx[d];
                    int ny = by + dy[d];
                    if (nx < 0 || nx >= n || ny < 0 || ny >= m) continue;
                    if (grid[nx][ny] == '#') continue;
                    int nidx = nx * m + ny;
                    if (dist[nidx] == -1) continue;
                    int dtemp = dist[nidx];
                    if (dtemp < bestD) {
                        bestD = dtemp;
                        bestCell = nidx;
                        bestDir = opp[d]; // from neighbor to base
                    }
                }
                if (bestD < INF) {
                    baseDist[f][r] = bestD;
                    baseDestIdx[f][r] = bestCell;
                    baseAtkDir[f][r] = bestDir;
                }
            }
        }
    }

    // Assignment of fighters to red bases
    vector<int> assignedBaseForF(k, -1);
    vector<bool> baseAssigned(nr, false);

    vector<long long> remainingFuel(nb), remainingMissile(nb);
    for (int i = 0; i < nb; ++i) {
        remainingFuel[i] = blue[i].g;
        remainingMissile[i] = blue[i].c;
    }

    if (nr > 0) {
        vector<int> redOrder(nr);
        iota(redOrder.begin(), redOrder.end(), 0);
        sort(redOrder.begin(), redOrder.end(), [&](int a, int b) {
            if (red[a].v != red[b].v) return red[a].v > red[b].v;
            return red[a].d < red[b].d;
        });

        for (int idx = 0; idx < nr; ++idx) {
            int r = redOrder[idx];
            if (baseAssigned[r]) continue;

            int bestF = -1;
            int bestD = INF;

            for (int f = 0; f < k; ++f) {
                if (assignedBaseForF[f] != -1) continue;
                int hb = fighterHomeBase[f];
                if (hb < 0) continue; // no valid home base

                int d = baseDist[f][r];
                if (d == INF) continue;
                if (d > fighters[f].G) continue;
                if (d > MAX_PATH) continue;

                long long neededFuel = d;
                long long neededMiss = red[r].d;

                if (neededMiss > fighters[f].C) continue;
                if (remainingFuel[hb] < neededFuel) continue;
                if (remainingMissile[hb] < neededMiss) continue;

                if (bestF == -1 || d < bestD) {
                    bestF = f;
                    bestD = d;
                }
            }

            if (bestF != -1) {
                assignedBaseForF[bestF] = r;
                baseAssigned[r] = true;
                int hb = fighterHomeBase[bestF];
                if (hb >= 0) {
                    remainingFuel[hb] -= baseDist[bestF][r];
                    remainingMissile[hb] -= red[r].d;
                }
            }
        }
    }

    bool anyAssigned = false;
    for (int f = 0; f < k; ++f) {
        if (assignedBaseForF[f] != -1) {
            anyAssigned = true;
            break;
        }
    }

    if (!anyAssigned) {
        // Do nothing, just one empty frame
        cout << "OK\n";
        return 0;
    }

    // For each assigned fighter, compute actual path (sequence of moves)
    vector<vector<int>> fighterPathDirs(k);
    int maxLen = 0;

    for (int f = 0; f < k; ++f) {
        int r = assignedBaseForF[f];
        if (r == -1) continue;

        int sx = fighters[f].x;
        int sy = fighters[f].y;
        int sIdx = sx * m + sy;
        int destIdx = baseDestIdx[f][r];

        if (destIdx == -1) continue; // should not happen

        if (sIdx == destIdx) {
            // Already at destination; empty path
            fighterPathDirs[f].clear();
            // maxLen unchanged
            continue;
        }

        vector<int> dist(cells, -1), par(cells, -1), pdir(cells, -1);
        queue<int> q;
        dist[sIdx] = 0;
        q.push(sIdx);
        bool found = false;
        while (!q.empty()) {
            int idx = q.front(); q.pop();
            if (idx == destIdx) {
                found = true;
                break;
            }
            int x = idx / m;
            int y = idx % m;
            for (int dir = 0; dir < 4; ++dir) {
                int nx = x + dx[dir];
                int ny = y + dy[dir];
                if (nx < 0 || nx >= n || ny < 0 || ny >= m) continue;
                if (grid[nx][ny] == '#') continue;
                int nidx = nx * m + ny;
                if (dist[nidx] == -1) {
                    dist[nidx] = dist[idx] + 1;
                    par[nidx] = idx;
                    pdir[nidx] = dir;
                    q.push(nidx);
                }
            }
        }

        vector<int> path;
        if (found && dist[destIdx] != -1) {
            int cur = destIdx;
            while (cur != sIdx) {
                int d = pdir[cur];
                path.push_back(d);
                cur = par[cur];
            }
            reverse(path.begin(), path.end());
        } else {
            // Should not happen; fallback: no path
            path.clear();
        }
        fighterPathDirs[f] = path;
        if ((int)path.size() > maxLen) maxLen = (int)path.size();
    }

    if (maxLen > MAX_PATH) {
        // Safety fallback, though shouldn't happen due to earlier constraint
        cout << "OK\n";
        return 0;
    }

    // Frame 0: refuel and load missiles
    for (int f = 0; f < k; ++f) {
        int r = assignedBaseForF[f];
        if (r == -1) continue;
        int hb = fighterHomeBase[f];
        if (hb < 0) continue;

        int neededFuel = baseDist[f][r];
        long long neededMiss = red[r].d;

        if (neededFuel > 0)
            cout << "fuel " << f << " " << neededFuel << "\n";
        if (neededMiss > 0)
            cout << "missile " << f << " " << neededMiss << "\n";
    }
    cout << "OK\n";

    // Frames 1..maxLen: movement along paths
    for (int step = 0; step < maxLen; ++step) {
        for (int f = 0; f < k; ++f) {
            if (assignedBaseForF[f] == -1) continue;
            if (step < (int)fighterPathDirs[f].size()) {
                int dir = fighterPathDirs[f][step];
                cout << "move " << f << " " << dir << "\n";
            }
        }
        cout << "OK\n";
    }

    // Final frame: attacks
    for (int f = 0; f < k; ++f) {
        int r = assignedBaseForF[f];
        if (r == -1) continue;
        int dir = baseAtkDir[f][r];
        long long cnt = red[r].d;
        if (dir >= 0 && cnt > 0) {
            cout << "attack " << f << " " << dir << " " << cnt << "\n";
        }
    }
    cout << "OK\n";

    return 0;
}