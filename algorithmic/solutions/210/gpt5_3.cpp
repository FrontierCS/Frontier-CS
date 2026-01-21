#include <bits/stdc++.h>
using namespace std;

struct BlueBase {
    int x, y;
    long long g, c;
    int d;
    long long v;
};

struct RedBase {
    int x, y;
    long long g, c;
    int d;
    long long v;
};

struct Fighter {
    int x, y;
    int G, C;
};

struct Candidate {
    int f, r;
    long long v;
    int L;
    int neighborId;
    int attackDir;
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
    
    int BN;
    cin >> BN;
    vector<BlueBase> blue(BN);
    for (int i = 0; i < BN; ++i) {
        cin >> blue[i].x >> blue[i].y;
        cin >> blue[i].g >> blue[i].c >> blue[i].d >> blue[i].v;
    }
    int RN;
    cin >> RN;
    vector<RedBase> red(RN);
    for (int i = 0; i < RN; ++i) {
        cin >> red[i].x >> red[i].y;
        cin >> red[i].g >> red[i].c >> red[i].d >> red[i].v;
    }
    int K;
    cin >> K;
    vector<Fighter> fighters(K);
    for (int i = 0; i < K; ++i) {
        cin >> fighters[i].x >> fighters[i].y >> fighters[i].G >> fighters[i].C;
    }
    
    const int INF = 1e9;
    auto inb = [&](int x, int y){ return x >= 0 && x < n && y >= 0 && y < m; };
    int dx[4] = {-1, 1, 0, 0};
    int dy[4] = {0, 0, -1, 1};
    
    // Map position to blue base index
    vector<vector<int>> posToBlue(n, vector<int>(m, -1));
    for (int i = 0; i < BN; ++i) {
        posToBlue[blue[i].x][blue[i].y] = i;
    }
    
    // BFS distances per fighter
    auto idx = [&](int x, int y){ return x * m + y; };
    vector<vector<int>> dists(K, vector<int>(n * m, INF));
    for (int fi = 0; fi < K; ++fi) {
        vector<int>& dist = dists[fi];
        deque<int> q;
        int sx = fighters[fi].x, sy = fighters[fi].y;
        int sid = idx(sx, sy);
        dist[sid] = 0;
        q.push_back(sid);
        while (!q.empty()) {
            int id = q.front(); q.pop_front();
            int x = id / m, y = id % m;
            for (int dir = 0; dir < 4; ++dir) {
                int nx = x + dx[dir], ny = y + dy[dir];
                if (!inb(nx, ny)) continue;
                if (grid[nx][ny] == '#') continue; // cannot enter red bases
                int nid = idx(nx, ny);
                if (dist[nid] == INF) {
                    dist[nid] = dist[id] + 1;
                    q.push_back(nid);
                }
            }
        }
    }
    
    // Build candidates
    vector<Candidate> cands;
    for (int fi = 0; fi < K; ++fi) {
        for (int ri = 0; ri < RN; ++ri) {
            if (red[ri].d <= 0) continue; // trivial or already destroyed-like, skip
            if (fighters[fi].C < red[ri].d) continue; // we restrict to single-fighter kill
            int rx = red[ri].x, ry = red[ri].y;
            int bestL = INF, bestN = -1, bestDir = -1;
            for (int dir = 0; dir < 4; ++dir) {
                int nx = rx + dx[dir], ny = ry + dy[dir];
                if (!inb(nx, ny)) continue;
                if (grid[nx][ny] == '#') continue; // cannot stand on another red base
                int nid = idx(nx, ny);
                int L = dists[fi][nid];
                if (L < bestL) {
                    bestL = L;
                    bestN = nid;
                    // attack direction is from neighbor to red base
                    // If red is at (rx,ry) and neighbor at (nx,ny), direction is where (nx + delta == rx, ny + delta == ry)
                    int nnx = bestN / m, nny = bestN % m;
                    int dd = -1;
                    if (rx == nnx - 1 && ry == nny) dd = 0;
                    else if (rx == nnx + 1 && ry == nny) dd = 1;
                    else if (rx == nnx && ry == nny - 1) dd = 2;
                    else if (rx == nnx && ry == nny + 1) dd = 3;
                    bestDir = dd;
                }
            }
            if (bestL >= INF) continue;
            if (bestL > fighters[fi].G) continue; // fuel tank capacity
            Candidate c;
            c.f = fi;
            c.r = ri;
            c.v = red[ri].v;
            c.L = bestL;
            c.neighborId = bestN;
            c.attackDir = bestDir;
            cands.push_back(c);
        }
    }
    
    sort(cands.begin(), cands.end(), [&](const Candidate& a, const Candidate& b){
        if (a.v != b.v) return a.v > b.v; // higher value first
        if (a.L != b.L) return a.L < b.L; // shorter distance first
        if (a.r != b.r) return a.r < b.r;
        return a.f < b.f;
    });
    
    vector<long long> gRem(BN), cRem(BN);
    for (int i = 0; i < BN; ++i) {
        gRem[i] = blue[i].g;
        cRem[i] = blue[i].c;
    }
    vector<int> assignedRed(K, -1);
    vector<char> redUsed(RN, 0);
    vector<int> assignedNeighbor(K, -1);
    vector<int> assignedDir(K, -1);
    vector<int> assignedL(K, 0);
    
    for (const auto& cand : cands) {
        int f = cand.f, r = cand.r;
        if (assignedRed[f] != -1) continue;
        if (redUsed[r]) continue;
        int sx = fighters[f].x, sy = fighters[f].y;
        int bidx = -1;
        if (sx >= 0 && sx < n && sy >= 0 && sy < m) {
            bidx = posToBlue[sx][sy];
        }
        if (bidx < 0) continue; // not on a blue base (shouldn't happen)
        int L = cand.L;
        int needFuel = L;
        int needMiss = red[r].d;
        if (needFuel <= fighters[f].G && needMiss <= fighters[f].C &&
            gRem[bidx] >= needFuel && cRem[bidx] >= needMiss) {
            assignedRed[f] = r;
            redUsed[r] = 1;
            assignedNeighbor[f] = cand.neighborId;
            assignedDir[f] = cand.attackDir;
            assignedL[f] = L;
            gRem[bidx] -= needFuel;
            cRem[bidx] -= needMiss;
        }
    }
    
    struct Plan {
        bool assigned = false;
        int redIdx = -1;
        int L = 0;
        vector<int> steps; // directions per move
        int attackDir = -1;
        int missiles = 0;
    };
    vector<Plan> plans(K);
    
    // BFS to reconstruct path for each assigned fighter
    for (int fi = 0; fi < K; ++fi) {
        if (assignedRed[fi] == -1) continue;
        int targetId = assignedNeighbor[fi];
        if (targetId < 0) continue;
        int tx = targetId / m, ty = targetId % m;
        // BFS with parents
        vector<int> dist(n * m, INF), parent(n * m, -1);
        deque<int> q;
        int sx = fighters[fi].x, sy = fighters[fi].y;
        int sid = idx(sx, sy);
        dist[sid] = 0;
        q.push_back(sid);
        while (!q.empty()) {
            int id = q.front(); q.pop_front();
            if (id == targetId) break;
            int x = id / m, y = id % m;
            for (int dir = 0; dir < 4; ++dir) {
                int nx = x + dx[dir], ny = y + dy[dir];
                if (!inb(nx, ny)) continue;
                if (grid[nx][ny] == '#') continue;
                int nid = idx(nx, ny);
                if (dist[nid] == INF) {
                    dist[nid] = dist[id] + 1;
                    parent[nid] = id;
                    q.push_back(nid);
                }
            }
        }
        // reconstruct
        vector<int> revCells;
        int cur = targetId;
        if (dist[cur] >= INF) {
            // If unable to reconstruct (shouldn't happen), skip this plan
            assignedRed[fi] = -1;
            continue;
        }
        while (cur != sid) {
            revCells.push_back(cur);
            cur = parent[cur];
            if (cur == -1) break; // safety
        }
        reverse(revCells.begin(), revCells.end());
        vector<int> steps;
        int px = sx, py = sy;
        for (int idc : revCells) {
            int cx = idc / m, cy = idc % m;
            int dir = -1;
            if (cx == px - 1 && cy == py) dir = 0;
            else if (cx == px + 1 && cy == py) dir = 1;
            else if (cx == px && cy == py - 1) dir = 2;
            else if (cx == px && cy == py + 1) dir = 3;
            else dir = -1;
            if (dir == -1) {
                steps.clear();
                break;
            }
            steps.push_back(dir);
            px = cx; py = cy;
        }
        if ((int)steps.size() != assignedL[fi]) {
            // Something went wrong; skip
            assignedRed[fi] = -1;
            continue;
        }
        plans[fi].assigned = true;
        plans[fi].redIdx = assignedRed[fi];
        plans[fi].L = assignedL[fi];
        plans[fi].steps = steps;
        plans[fi].attackDir = assignedDir[fi];
        plans[fi].missiles = red[assignedRed[fi]].d;
    }
    
    int maxL = 0;
    for (int fi = 0; fi < K; ++fi) if (plans[fi].assigned) maxL = max(maxL, plans[fi].L);
    int T = 0;
    if (maxL == 0) {
        bool any = false;
        for (int fi = 0; fi < K; ++fi) if (plans[fi].assigned) any = true;
        if (any) T = 2; // frame 0 fuel+missile, frame 1 attack
        else T = 1; // just an empty frame
    } else {
        T = 2 + maxL; // 0: prepare, 1..L: move, L+1: attack
    }
    if (T > 15000) T = 15000; // safety cap
    
    vector<vector<string>> frames(T);
    
    // Frame 0: fueling and missiles
    if (T >= 1) {
        for (int fi = 0; fi < K; ++fi) {
            if (!plans[fi].assigned) continue;
            int fuelAmt = plans[fi].L;
            int missAmt = plans[fi].missiles;
            if (fuelAmt > 0) {
                frames[0].push_back(string("fuel ") + to_string(fi) + " " + to_string(fuelAmt));
            } else {
                // still may push zero fuel? Skip
            }
            if (missAmt > 0) {
                frames[0].push_back(string("missile ") + to_string(fi) + " " + to_string(missAmt));
            } else {
                // skip zero missiles
            }
        }
    }
    // Movement frames
    for (int fi = 0; fi < K; ++fi) {
        if (!plans[fi].assigned) continue;
        const auto& steps = plans[fi].steps;
        for (int s = 0; s < (int)steps.size(); ++s) {
            int frameIdx = 1 + s;
            if (frameIdx >= T) break;
            frames[frameIdx].push_back(string("move ") + to_string(fi) + " " + to_string(steps[s]));
        }
    }
    // Attack frames
    for (int fi = 0; fi < K; ++fi) {
        if (!plans[fi].assigned) continue;
        int frameIdx = 1 + plans[fi].L;
        if (frameIdx >= T) continue;
        int dir = plans[fi].attackDir;
        int miss = plans[fi].missiles;
        if (dir >= 0 && miss > 0) {
            frames[frameIdx].push_back(string("attack ") + to_string(fi) + " " + to_string(dir) + " " + to_string(miss));
        }
    }
    
    for (int t = 0; t < T; ++t) {
        for (const auto& cmd : frames[t]) {
            cout << cmd << "\n";
        }
        cout << "OK\n";
    }
    return 0;
}