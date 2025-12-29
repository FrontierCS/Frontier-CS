#include <bits/stdc++.h>
using namespace std;

struct Move {
    int ni, nj;
    char dir;
    int tid;
};

static const int H = 50;
static const int W = 50;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int si, sj;
    if (!(cin >> si >> sj)) return 0;
    static int t[H][W];
    static int p[H][W];
    int maxTid = -1;
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            cin >> t[i][j];
            if (t[i][j] > maxTid) maxTid = t[i][j];
        }
    }
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            cin >> p[i][j];
        }
    }
    int M = maxTid + 1;

    auto idx = [&](int i, int j){ return i*W + j; };
    auto inb = [&](int i, int j){ return 0 <= i && i < H && 0 <= j && j < W; };

    vector<array<Move,4>> neigh(H*W);
    vector<int> neigh_sz(H*W, 0);

    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char dc[4] = {'U','D','L','R'};

    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            int id = idx(i,j);
            int k = 0;
            for (int d = 0; d < 4; d++) {
                int ni = i + di[d];
                int nj = j + dj[d];
                if (!inb(ni,nj)) continue;
                if (t[ni][nj] == t[i][j]) continue; // cannot move within same tile
                neigh[id][k++] = Move{ni, nj, dc[d], t[ni][nj]};
            }
            neigh_sz[id] = k;
        }
    }

    // Random engine
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t(si) << 17) ^ (uint64_t(sj) << 29);
    std::mt19937_64 rng(seed);
    auto rnd01 = [&](){ return std::uniform_real_distribution<double>(0.0,1.0)(rng); };
    auto rndInt = [&](int l, int r){ return std::uniform_int_distribution<int>(l,r)(rng); };

    // Time limit
    auto startTime = chrono::high_resolution_clock::now();
    const double TIME_LIMIT = 1.95; // seconds
    auto elapsed = [&](){
        auto now = chrono::high_resolution_clock::now();
        return chrono::duration<double>(now - startTime).count();
    };

    // Helper to compute out-degree from a cell, with optional exclusion set
    auto outdeg_from = [&](int ci, int cj, const vector<unsigned char>& visited, int exclude1, int exclude2){
        int id = idx(ci,cj);
        int sz = neigh_sz[id];
        int cnt = 0;
        for (int k = 0; k < sz; k++) {
            const Move &m = neigh[id][k];
            if (visited[m.tid]) continue;
            if (m.tid == exclude1 || m.tid == exclude2) continue;
            cnt++;
        }
        return cnt;
    };

    // Multiple tries with random parameters
    string bestPath;
    long long bestScore = -1;

    // Decide number of tries dynamically
    int maxTries = 1000000000; // effectively unlimited, bound by time
    for (int iter = 0; iter < maxTries; iter++) {
        if (elapsed() > TIME_LIMIT) break;

        // random heuristic parameters
        double a = 8.0 + rnd01() * 16.0;   // weight for outdeg at next cell
        double b = 0.25 + rnd01() * 0.6;   // weight for 2-step lookahead value
        double c = 2.0 + rnd01() * 6.0;    // weight for outdeg at second step
        double noise = 1e-6;               // small noise for tie-breaking

        vector<unsigned char> visited(M, 0);
        int ci = si, cj = sj;
        visited[t[ci][cj]] = 1;
        long long score = p[ci][cj];
        string path; path.reserve(2500);

        // Greedy walk
        while (true) {
            int id = idx(ci,cj);
            int sz = neigh_sz[id];
            // collect candidates (unvisited tile moves)
            struct Cand { int ni,nj; char dir; int tid; double val; int out1; };
            int candCount = 0;
            double bestVal = -1e100;
            int bestIdx = -1;
            vector<Cand> cands;
            cands.reserve(4);
            for (int k = 0; k < sz; k++) {
                const Move &m = neigh[id][k];
                if (visited[m.tid]) continue;
                cands.push_back({m.ni, m.nj, m.dir, m.tid, 0.0, 0});
            }
            if (cands.empty()) break;

            // Evaluate candidates
            for (int cidx = 0; cidx < (int)cands.size(); cidx++) {
                auto &cand = cands[cidx];
                int ni = cand.ni, nj = cand.nj, tidB = cand.tid;
                int gain1 = p[ni][nj];

                // out-degree from next cell (after stepping)
                int out1 = outdeg_from(ni, nj, visited, -1, -1);
                cand.out1 = out1;

                // best second step evaluation
                double best2 = 0.0;
                if (out1 > 0) {
                    int id2 = idx(ni, nj);
                    int sz2 = neigh_sz[id2];
                    for (int k2 = 0; k2 < sz2; k2++) {
                        const Move &m2 = neigh[id2][k2];
                        if (visited[m2.tid]) continue;       // already visited
                        // Note: cannot go back to current tile since it's visited
                        int ngi = m2.ni, ngj = m2.nj;
                        int gain2 = p[ngi][ngj];
                        // out-degree after second step, excluding going back to B
                        int out2 = outdeg_from(ngi, ngj, visited, tidB, -1);
                        double v2 = gain2 + c * out2;
                        if (v2 > best2) best2 = v2;
                    }
                }

                double val = (double)gain1 + a * out1 + b * best2 + noise * (rnd01() - 0.5);
                cand.val = val;
                if (val > bestVal) {
                    bestVal = val;
                    bestIdx = cidx;
                }
            }

            if (bestIdx == -1) break;
            auto &pick = cands[bestIdx];
            // step
            path.push_back(pick.dir);
            visited[pick.tid] = 1;
            ci = pick.ni; cj = pick.nj;
            score += p[ci][cj];
        }

        if (score > bestScore) {
            bestScore = score;
            bestPath = path;
        }
    }

    cout << bestPath << "\n";
    return 0;
}