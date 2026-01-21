#include <bits/stdc++.h>
using namespace std;

struct BlueBase {
    int x, y;
    long long g, c;
    long long d, v; // not used (d,v for blue base likely irrelevant)
};

struct RedBase {
    int x, y;
    int d;
    long long v;
};

struct Fighter {
    int x, y, G, C;
    int baseIdx; // index of the blue base at starting position
};

struct Plan {
    bool active = false;
    int targetRed = -1;
    vector<int> moves; // sequence of move directions
    int fuelLoad = 0;
    int missileLoad = 0;
    int attackDir = -1;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if(!(cin >> n >> m)) {
        return 0;
    }
    vector<string> grid(n);
    for (int i = 0; i < n; ++i) cin >> grid[i];

    auto inside = [&](int x, int y){ return x>=0 && x<n && y>=0 && y<m; };
    auto idx = [&](int x, int y){ return x*m + y; };

    int NB; cin >> NB;
    vector<BlueBase> blueBases(NB);
    for (int i = 0; i < NB; ++i) {
        cin >> blueBases[i].x >> blueBases[i].y;
        cin >> blueBases[i].g >> blueBases[i].c >> blueBases[i].d >> blueBases[i].v;
    }

    int NR; cin >> NR;
    vector<RedBase> redBases(NR);
    for (int i = 0; i < NR; ++i) {
        int x,y; long long g,c; int d; long long v;
        cin >> x >> y;
        cin >> g >> c >> d >> v;
        redBases[i] = {x, y, d, v};
    }

    int K; cin >> K;
    vector<Fighter> fighters(K);
    for (int i = 0; i < K; ++i) {
        cin >> fighters[i].x >> fighters[i].y >> fighters[i].G >> fighters[i].C;
        fighters[i].baseIdx = -1;
    }

    // Map blue base positions to indices
    int NM = n*m;
    vector<int> blueIndexByCell(NM, -1);
    for (int i = 0; i < NB; ++i) {
        blueIndexByCell[idx(blueBases[i].x, blueBases[i].y)] = i;
    }
    for (int i = 0; i < K; ++i) {
        int bid = blueIndexByCell[idx(fighters[i].x, fighters[i].y)];
        fighters[i].baseIdx = bid;
    }

    // Directions: 0 up, 1 down, 2 left, 3 right
    const int dx[4] = {-1, 1, 0, 0};
    const int dy[4] = {0, 0, -1, 1};
    auto opp = [&](int d){ return d^1; };

    // BFS per fighter
    const int INF = 1e9;
    vector<vector<int>> distAll(K, vector<int>(NM, INF));
    vector<vector<int>> parAll(K, vector<int>(NM, -1));
    vector<vector<char>> dirFromParAll(K, vector<char>(NM, -1));

    auto passable = [&](int x, int y) {
        if (!inside(x,y)) return false;
        if (grid[x][y] == '#') return false; // red base cells are not passable
        return true;
    };

    for (int fi = 0; fi < K; ++fi) {
        deque<int> dq;
        int sx = fighters[fi].x, sy = fighters[fi].y;
        int s = idx(sx, sy);
        distAll[fi][s] = 0;
        parAll[fi][s] = -1;
        dirFromParAll[fi][s] = -1;
        dq.push_back(s);
        while(!dq.empty()) {
            int cur = dq.front(); dq.pop_front();
            int cx = cur / m, cy = cur % m;
            for (int d = 0; d < 4; ++d) {
                int nx = cx + dx[d], ny = cy + dy[d];
                if (!passable(nx, ny)) continue;
                int ni = idx(nx, ny);
                if (distAll[fi][ni] > distAll[fi][cur] + 1) {
                    distAll[fi][ni] = distAll[fi][cur] + 1;
                    parAll[fi][ni] = cur;
                    dirFromParAll[fi][ni] = (char)d; // direction from parent to this cell
                    dq.push_back(ni);
                }
            }
        }
    }

    // For each fighter and red base, compute best adjacency dist, arrival cell, and attack dir
    vector<vector<int>> bestDistFR(K, vector<int>(NR, INF));
    vector<vector<int>> arrivalCellFR(K, vector<int>(NR, -1));
    vector<vector<int>> attackDirFR(K, vector<int>(NR, -1));

    for (int fi = 0; fi < K; ++fi) {
        for (int ri = 0; ri < NR; ++ri) {
            int rx = redBases[ri].x, ry = redBases[ri].y;
            int bestD = INF, bestCell = -1, bestAtk = -1;
            for (int d = 0; d < 4; ++d) {
                int ax = rx + dx[d], ay = ry + dy[d];
                if (!inside(ax, ay)) continue;
                if (grid[ax][ay] == '#') continue; // can't stand on a red base
                int ai = idx(ax, ay);
                int dist = distAll[fi][ai];
                if (dist < bestD) {
                    bestD = dist;
                    bestCell = ai;
                    bestAtk = opp(d); // from adjacency to red is opposite of red->adj direction
                }
            }
            bestDistFR[fi][ri] = bestD;
            arrivalCellFR[fi][ri] = bestCell;
            attackDirFR[fi][ri] = bestAtk;
        }
    }

    auto reconstructPath = [&](int fi, int endCell) -> vector<int> {
        vector<int> pathDirs;
        int s = idx(fighters[fi].x, fighters[fi].y);
        if (endCell == -1) return pathDirs;
        if (distAll[fi][endCell] >= INF) return pathDirs;
        int cur = endCell;
        while (cur != s) {
            int d = dirFromParAll[fi][cur];
            if (d < 0) break; // safety
            pathDirs.push_back(d);
            cur = parAll[fi][cur];
        }
        reverse(pathDirs.begin(), pathDirs.end());
        return pathDirs;
    };

    vector<Plan> plans(K);
    vector<long long> remG(NB), remC(NB);
    for (int i = 0; i < NB; ++i) { remG[i] = blueBases[i].g; remC[i] = blueBases[i].c; }
    vector<char> redAssigned(NR, 0);

    // Unique assignment: each fighter to a distinct red base if possible (with C >= d and supplies sufficient)
    for (int fi = 0; fi < K; ++fi) {
        int bidx = fighters[fi].baseIdx;
        if (bidx < 0) continue;
        int bestR = -1;
        double bestScore = -1e100;
        for (int ri = 0; ri < NR; ++ri) {
            if (redAssigned[ri]) continue;
            int dist = bestDistFR[fi][ri];
            if (dist >= INF) continue;
            if (dist > fighters[fi].G) continue;
            int needMiss = redBases[ri].d;
            if (needMiss > fighters[fi].C) continue;
            if (remG[bidx] < dist) continue;
            if (remC[bidx] < needMiss) continue;
            double score = (double)redBases[ri].v / (double)(dist + 1);
            if (score > bestScore) {
                bestScore = score;
                bestR = ri;
            }
        }
        if (bestR != -1) {
            int dist = bestDistFR[fi][bestR];
            vector<int> path = reconstructPath(fi, arrivalCellFR[fi][bestR]);
            int atkDir = attackDirFR[fi][bestR];
            int needMiss = redBases[bestR].d;

            plans[fi].active = true;
            plans[fi].targetRed = bestR;
            plans[fi].moves = std::move(path);
            plans[fi].fuelLoad = dist;
            plans[fi].missileLoad = needMiss;
            plans[fi].attackDir = atkDir;

            remG[bidx] -= dist;
            remC[bidx] -= needMiss;
            redAssigned[bestR] = 1;
        }
    }

    // Multi-assignment helper: assign a group of fighters to one red base (sum missiles >= d)
    auto tryMultiAssign = [&](const vector<int>& availFighters) -> bool {
        int chosenR = -1;
        vector<int> chosenF;
        vector<int> chosenFuel, chosenMiss, chosenAtkDir, chosenArrival;
        long long bestV = -1;
        long long bestSumDist = (1LL<<60);
        vector<long long> tempG, tempC;
        for (int ri = 0; ri < NR; ++ri) {
            if (redAssigned[ri]) continue;
            // simulate greedy selection
            vector<long long> tg = remG, tc = remC;
            int left = redBases[ri].d;
            struct Cand { int f; int dist; int bidx; int maxMiss; };
            vector<Cand> cands;
            for (int fi : availFighters) {
                int bidx = fighters[fi].baseIdx;
                if (bidx < 0) continue;
                int dist = bestDistFR[fi][ri];
                if (dist >= INF) continue;
                if (dist > fighters[fi].G) continue;
                if (tg[bidx] < dist) continue;
                int maxMiss = (int)min<long long>(fighters[fi].C, tc[bidx]);
                if (maxMiss <= 0) continue;
                cands.push_back({fi, dist, bidx, maxMiss});
            }
            if (cands.empty()) continue;
            // sort by maxMiss desc, then dist asc
            sort(cands.begin(), cands.end(), [](const Cand& a, const Cand& b){
                if (a.maxMiss != b.maxMiss) return a.maxMiss > b.maxMiss;
                return a.dist < b.dist;
            });
            vector<int> selF, selFuel, selMiss, selAtkDir, selArrival;
            long long sumDist = 0;
            for (auto &c : cands) {
                if (left <= 0) break;
                if (tg[c.bidx] < c.dist) continue;
                int possible = (int)min<long long>({(long long)fighters[c.f].C, tc[c.bidx], (long long)left});
                if (possible <= 0) continue;
                tg[c.bidx] -= c.dist;
                tc[c.bidx] -= possible;
                left -= possible;
                selF.push_back(c.f);
                selFuel.push_back(c.dist);
                selMiss.push_back(possible);
                sumDist += c.dist;
                selArrival.push_back(arrivalCellFR[c.f][ri]);
                selAtkDir.push_back(attackDirFR[c.f][ri]);
            }
            if (left <= 0) {
                // feasible
                long long val = redBases[ri].v;
                if (val > bestV || (val == bestV && sumDist < bestSumDist)) {
                    bestV = val;
                    bestSumDist = sumDist;
                    chosenR = ri;
                    chosenF = selF; chosenFuel = selFuel; chosenMiss = selMiss; chosenAtkDir = selAtkDir; chosenArrival = selArrival;
                    tempG = tg; tempC = tc;
                }
            }
        }
        if (chosenR == -1) return false;
        // apply selection
        for (size_t i = 0; i < chosenF.size(); ++i) {
            int fi = chosenF[i];
            plans[fi].active = true;
            plans[fi].targetRed = chosenR;
            plans[fi].moves = reconstructPath(fi, chosenArrival[i]);
            plans[fi].fuelLoad = chosenFuel[i];
            plans[fi].missileLoad = chosenMiss[i];
            plans[fi].attackDir = chosenAtkDir[i];
        }
        remG = tempG;
        remC = tempC;
        redAssigned[chosenR] = 1;
        return true;
    };

    // After unique assignment, try to assign remaining fighters via multi-assignment, possibly multiple times
    {
        vector<int> unassigned;
        for (int fi = 0; fi < K; ++fi) if (!plans[fi].active) unassigned.push_back(fi);
        // Attempt repeated multi-assign while possible
        while (true) {
            // filter still unassigned
            vector<int> curr;
            for (int fi : unassigned) if (!plans[fi].active) curr.push_back(fi);
            if (curr.empty()) break;
            if (!tryMultiAssign(curr)) break;
            // continue loop to try another red base
        }
    }

    // Prepare output frames
    int maxLen = 0;
    for (int fi = 0; fi < K; ++fi) if (plans[fi].active) {
        maxLen = max<int>(maxLen, (int)plans[fi].moves.size());
    }

    bool anyActive = false;
    for (int fi = 0; fi < K; ++fi) if (plans[fi].active) { anyActive = true; break; }

    if (!anyActive) {
        // No plan; output a single empty frame
        cout << "OK\n";
        return 0;
    }

    // Frame 0: fueling and missiles
    for (int fi = 0; fi < K; ++fi) if (plans[fi].active) {
        if (plans[fi].fuelLoad > 0) cout << "fuel " << fi << " " << plans[fi].fuelLoad << "\n";
        if (plans[fi].missileLoad > 0) cout << "missile " << fi << " " << plans[fi].missileLoad << "\n";
    }
    cout << "OK\n";

    // Movement frames
    for (int step = 0; step < maxLen; ++step) {
        for (int fi = 0; fi < K; ++fi) if (plans[fi].active) {
            if (step < (int)plans[fi].moves.size()) {
                cout << "move " << fi << " " << plans[fi].moves[step] << "\n";
            }
        }
        cout << "OK\n";
    }

    // Attack frame
    for (int fi = 0; fi < K; ++fi) if (plans[fi].active) {
        if (plans[fi].missileLoad > 0 && plans[fi].attackDir >= 0) {
            cout << "attack " << fi << " " << plans[fi].attackDir << " " << plans[fi].missileLoad << "\n";
        }
    }
    cout << "OK\n";

    return 0;
}