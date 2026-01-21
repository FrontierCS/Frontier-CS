#include <bits/stdc++.h>
using namespace std;

static const int DX[4] = {-1, 1, 0, 0};
static const int DY[4] = {0, 0, -1, 1};

static inline int invDir(int d) {
    if (d == 0) return 1;
    if (d == 1) return 0;
    if (d == 2) return 3;
    return 2;
}

struct BlueBase {
    int x, y;
    long long fuel, missile;
};

struct RedBase {
    int x, y;
    long long def, val;
};

struct Fighter {
    int id;
    int sx, sy;
    int baseIdx;
    int G, C;
    int startIdx;
    int time = 0;
    vector<int> dist;
    vector<int> prev;
    vector<int> prevDir;
    vector<int> bestDist; // per red
    vector<int> bestGoal; // per red (cell idx)
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> grid(n);
    for (int i = 0; i < n; i++) cin >> grid[i];

    auto idxOf = [&](int x, int y) { return x * m + y; };
    auto inb = [&](int x, int y) { return 0 <= x && x < n && 0 <= y && y < m; };

    int NB;
    cin >> NB;
    vector<BlueBase> blue(NB);
    unordered_map<long long, int> blueAt;
    blueAt.reserve(NB * 2 + 10);
    for (int i = 0; i < NB; i++) {
        int x, y;
        long long g, c, d, v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
        blue[i] = {x, y, g, c};
        long long key = 1LL * x * m + y;
        if (!blueAt.count(key)) blueAt[key] = i;
    }

    int NR;
    cin >> NR;
    vector<RedBase> red(NR);
    vector<char> isRedCell(n * m, 0);
    for (int i = 0; i < NR; i++) {
        int x, y;
        long long g, c, d, v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
        red[i] = {x, y, d, v};
        if (inb(x, y)) isRedCell[idxOf(x, y)] = 1;
    }

    int k;
    cin >> k;
    vector<Fighter> fighters(k);
    for (int i = 0; i < k; i++) {
        int x, y, G, C;
        cin >> x >> y >> G >> C;
        long long key = 1LL * x * m + y;
        int bidx = blueAt.count(key) ? blueAt[key] : -1;
        fighters[i] = Fighter{i, x, y, bidx, G, C, idxOf(x, y)};
    }

    // Precompute BFS tree for each fighter from its start base.
    for (auto &f : fighters) {
        int S = n * m;
        f.dist.assign(S, INT_MAX);
        f.prev.assign(S, -1);
        f.prevDir.assign(S, -1);

        deque<int> q;
        f.dist[f.startIdx] = 0;
        q.push_back(f.startIdx);

        while (!q.empty()) {
            int cur = q.front();
            q.pop_front();
            int cx = cur / m, cy = cur % m;
            int cd = f.dist[cur];
            for (int dir = 0; dir < 4; dir++) {
                int nx = cx + DX[dir], ny = cy + DY[dir];
                if (!inb(nx, ny)) continue;
                int ni = idxOf(nx, ny);
                if (isRedCell[ni]) continue; // never enter red base cells
                if (f.dist[ni] != INT_MAX) continue;
                f.dist[ni] = cd + 1;
                f.prev[ni] = cur;
                f.prevDir[ni] = dir;
                q.push_back(ni);
            }
        }

        f.bestDist.assign(NR, INT_MAX);
        f.bestGoal.assign(NR, -1);
        for (int r = 0; r < NR; r++) {
            int rx = red[r].x, ry = red[r].y;
            int bestD = INT_MAX, bestG = -1;
            for (int dir = 0; dir < 4; dir++) {
                int ax = rx + DX[dir], ay = ry + DY[dir];
                if (!inb(ax, ay)) continue;
                int ai = idxOf(ax, ay);
                if (isRedCell[ai]) continue;
                int d = f.dist[ai];
                if (d < bestD) {
                    bestD = d;
                    bestG = ai;
                }
            }
            f.bestDist[r] = bestD;
            f.bestGoal[r] = bestG;
        }
    }

    const int FRAME_LIMIT = 15000;
    vector<vector<string>> out; // out[frame] = commands
    vector<char> alive(NR, 1);

    auto ensureOutSize = [&](int sz) {
        if ((int)out.size() < sz) out.resize(sz);
    };

    auto reconstructPath = [&](const Fighter &f, int goalIdx) -> vector<int> {
        vector<int> dirs;
        int cur = goalIdx;
        if (cur < 0) return dirs;
        while (cur != f.startIdx) {
            int pd = f.prevDir[cur];
            int pr = f.prev[cur];
            if (pr < 0 || pd < 0) {
                dirs.clear();
                return dirs;
            }
            dirs.push_back(pd);
            cur = pr;
        }
        reverse(dirs.begin(), dirs.end());
        return dirs;
    };

    auto attackDirFromCellToRed = [&](int cellIdx, int rid) -> int {
        int cx = cellIdx / m, cy = cellIdx % m;
        int rx = red[rid].x, ry = red[rid].y;
        if (rx == cx - 1 && ry == cy) return 0;
        if (rx == cx + 1 && ry == cy) return 1;
        if (rx == cx && ry == cy - 1) return 2;
        if (rx == cx && ry == cy + 1) return 3;
        return -1;
    };

    auto betterRatio = [&](long long v1, int dur1, long long v2, int dur2) -> bool {
        // v1/dur1 > v2/dur2 ?
        __int128 lhs = (__int128)v1 * dur2;
        __int128 rhs = (__int128)v2 * dur1;
        return lhs > rhs;
    };

    while (true) {
        int bestF = -1, bestR = -1;
        long long bestV = 0;
        int bestDur = 1;
        int bestDist = 0;

        for (auto &f : fighters) {
            if (f.baseIdx < 0) continue;
            for (int r = 0; r < NR; r++) {
                if (!alive[r]) continue;
                int d = f.bestDist[r];
                int goal = f.bestGoal[r];
                if (goal < 0 || d == INT_MAX) continue;

                if (2LL * d > f.G) continue;
                if (red[r].def > f.C) continue;

                int dur = 2 * d + 2;
                if (f.time + dur > FRAME_LIMIT) continue;

                BlueBase &b = blue[f.baseIdx];
                if (b.fuel < 2LL * d) continue;
                if (b.missile < red[r].def) continue;

                if (bestF == -1 ||
                    betterRatio(red[r].val, dur, bestV, bestDur) ||
                    (!betterRatio(bestV, bestDur, red[r].val, dur) && (
                        red[r].val > bestV ||
                        (red[r].val == bestV && (dur < bestDur ||
                         (dur == bestDur && f.time < fighters[bestF].time)))
                    ))
                ) {
                    bestF = f.id;
                    bestR = r;
                    bestV = red[r].val;
                    bestDur = dur;
                    bestDist = d;
                }
            }
        }

        if (bestF == -1) break;

        Fighter &f = fighters[bestF];
        int r = bestR;
        int d = bestDist;
        int goal = f.bestGoal[r];
        int startTime = f.time;
        int dur = 2 * d + 2;
        if (startTime + dur > FRAME_LIMIT) {
            alive[r] = 0;
            continue;
        }

        vector<int> path = reconstructPath(f, goal);
        if ((int)path.size() != d) {
            alive[r] = 0;
            continue;
        }

        int atkDir = attackDirFromCellToRed(goal, r);
        if (atkDir < 0) {
            alive[r] = 0;
            continue;
        }

        // Reserve supplies at the base.
        BlueBase &b = blue[f.baseIdx];
        long long needFuel = 2LL * d;
        long long needMiss = red[r].def;

        if (b.fuel < needFuel || b.missile < needMiss) {
            alive[r] = 0;
            continue;
        }
        b.fuel -= needFuel;
        b.missile -= needMiss;

        ensureOutSize(startTime + dur);

        // Frame startTime: fuel + missile
        if (needFuel > 0) out[startTime].push_back("fuel " + to_string(f.id) + " " + to_string(needFuel));
        if (needMiss > 0) out[startTime].push_back("missile " + to_string(f.id) + " " + to_string(needMiss));

        // Move out
        for (int i = 0; i < d; i++) {
            int frame = startTime + 1 + i;
            out[frame].push_back("move " + to_string(f.id) + " " + to_string(path[i]));
        }

        // Attack
        int attackFrame = startTime + 1 + d;
        out[attackFrame].push_back("attack " + to_string(f.id) + " " + to_string(atkDir) + " " + to_string(needMiss));

        // Move back
        for (int i = 0; i < d; i++) {
            int frame = attackFrame + 1 + i;
            int dir = invDir(path[d - 1 - i]);
            out[frame].push_back("move " + to_string(f.id) + " " + to_string(dir));
        }

        alive[r] = 0;
        f.time += dur;
    }

    int maxFramesUsed = 0;
    for (auto &f : fighters) maxFramesUsed = max(maxFramesUsed, f.time);
    maxFramesUsed = min(maxFramesUsed, FRAME_LIMIT);
    if ((int)out.size() < maxFramesUsed) out.resize(maxFramesUsed);

    for (int t = 0; t < maxFramesUsed; t++) {
        for (auto &cmd : out[t]) cout << cmd << "\n";
        cout << "OK\n";
    }

    return 0;
}