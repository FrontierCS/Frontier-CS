#include <bits/stdc++.h>
using namespace std;

static const int H = 50;
static const int W = 50;

struct RNG {
    using u64 = unsigned long long;
    u64 state;
    RNG(u64 s = 0) {
        if (s == 0) {
            s = chrono::steady_clock::now().time_since_epoch().count();
        }
        state = s;
    }
    u64 next() {
        u64 z = (state += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    double drand() {
        return (next() >> 11) * (1.0 / 9007199254740992.0);
    }
    int randint(int a, int b) {
        return a + (int)(next() % (unsigned long long)(b - a + 1));
    }
};

int si, sj;
int tid[H][W];
int pval[H][W];
int dx[4] = {-1, 1, 0, 0};
int dy[4] = {0, 0, -1, 1};
char dc[4] = {'U', 'D', 'L', 'R'};

struct RunResult {
    string path;
    long long score;
};

struct Params {
    double w_deg1;
    double w_best2;
    double noise;
};

RunResult greedy_run(const Params& prm, RNG& rng, int M) {
    vector<unsigned char> visited(M, 0);
    int ci = si, cj = sj;
    visited[tid[ci][cj]] = 1;
    long long score = pval[ci][cj];
    string moves;
    moves.reserve(2500);

    while (true) {
        double best_eval = -1e100;
        int best_dir = -1;
        // Optionally shuffle direction order to add randomness
        int dirs[4] = {0,1,2,3};
        for (int k = 0; k < 4; ++k) {
            int r = k + (int)(rng.next() % (4 - k));
            swap(dirs[k], dirs[r]);
        }
        for (int idx = 0; idx < 4; ++idx) {
            int d = dirs[idx];
            int ni = ci + dx[d], nj = cj + dy[d];
            if (ni < 0 || ni >= H || nj < 0 || nj >= W) continue;
            int t1 = tid[ni][nj];
            if (visited[t1]) continue;

            // Evaluate this move
            int deg1 = 0;
            double best2 = 0.0;
            for (int d2 = 0; d2 < 4; ++d2) {
                int xi = ni + dx[d2], xj = nj + dy[d2];
                if (xi < 0 || xi >= H || xj < 0 || xj >= W) continue;
                int t2 = tid[xi][xj];
                if (t2 == t1) continue; // same tile as step 1 is not allowed
                if (visited[t2]) continue; // already visited
                deg1++;

                // second level
                int deg2 = 0;
                for (int d3 = 0; d3 < 4; ++d3) {
                    int yi = xi + dx[d3], yj = xj + dy[d3];
                    if (yi < 0 || yi >= H || yj < 0 || yj >= W) continue;
                    int t3 = tid[yi][yj];
                    if (t3 == t2) continue; // cannot move inside same tile at 2nd step
                    if (visited[t3]) continue; // visited
                    if (t3 == t1) continue; // after stepping to t2, t1 is also visited
                    deg2++;
                }
                double eval2 = (double)pval[xi][xj] + prm.w_deg1 * (double)deg2;
                if (eval2 > best2) best2 = eval2;
            }

            double eval = (double)pval[ni][nj] + prm.w_deg1 * (double)deg1 + prm.w_best2 * best2;
            if (prm.noise > 0.0) {
                eval += (rng.drand() * 2.0 - 1.0) * prm.noise;
            }
            if (eval > best_eval) {
                best_eval = eval;
                best_dir = d;
            }
        }

        if (best_dir == -1) break;
        int ni = ci + dx[best_dir], nj = cj + dy[best_dir];
        moves.push_back(dc[best_dir]);
        ci = ni; cj = nj;
        visited[tid[ci][cj]] = 1;
        score += pval[ci][cj];
    }
    return {moves, score};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> si >> sj)) {
        return 0;
    }
    int Mmax = -1;
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j < W; ++j) {
            cin >> tid[i][j];
            if (tid[i][j] > Mmax) Mmax = tid[i][j];
        }
    }
    int M = Mmax + 1;
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j < W; ++j) {
            cin >> pval[i][j];
        }
    }

    RNG rng;
    const auto start_time = chrono::steady_clock::now();
    const double TIME_LIMIT_MS = 1950.0;

    RunResult best;
    best.score = LLONG_MIN;

    // A quick deterministic baseline
    {
        Params prm;
        prm.w_deg1 = 4.0;
        prm.w_best2 = 0.8;
        prm.noise = 0.0;
        RunResult res = greedy_run(prm, rng, M);
        if (res.score > best.score) best = res;
    }

    // Randomized parameter search within time limit
    int iter = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double, milli>(now - start_time).count();
        if (elapsed > TIME_LIMIT_MS) break;
        Params prm;
        // Randomize weights slightly to explore different behaviors
        prm.w_deg1 = 2.0 + rng.drand() * 8.0;    // [2,10]
        prm.w_best2 = rng.drand() * 2.0;         // [0,2]
        prm.noise = 0.02;                        // small random noise to break ties

        RunResult res = greedy_run(prm, rng, M);
        if (res.score > best.score) best = res;
        iter++;
    }

    cout << best.path << '\n';
    return 0;
}