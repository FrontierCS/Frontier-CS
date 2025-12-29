#include <bits/stdc++.h>
using namespace std;

static const int N = 50;
static const int NN = 2500;

struct SplitMix64 {
    uint64_t x;
    SplitMix64(uint64_t seed = 0) : x(seed) {}
    uint64_t nextU64() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint32_t nextU32() { return (uint32_t)nextU64(); }
    int nextInt(int lo, int hi) { // inclusive
        return lo + (int)(nextU64() % (uint64_t)(hi - lo + 1));
    }
    double nextDouble() { // [0,1)
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

struct Candidate {
    int ni, nj;
    char mv;
    double hv;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj;
    cin >> si >> sj;

    static int tid[N][N];
    static int pval[N][N];
    int mx = -1;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cin >> tid[i][j];
            mx = max(mx, tid[i][j]);
        }
    }
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cin >> pval[i][j];
        }
    }
    int M = mx + 1;

    static int neigh[NN][4];
    for (int idx = 0; idx < NN; idx++) for (int d = 0; d < 4; d++) neigh[idx][d] = -1;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            int idx = i * N + j;
            if (i > 0) neigh[idx][0] = (i - 1) * N + j;     // U
            if (i + 1 < N) neigh[idx][1] = (i + 1) * N + j; // D
            if (j > 0) neigh[idx][2] = i * N + (j - 1);     // L
            if (j + 1 < N) neigh[idx][3] = i * N + (j + 1); // R
        }
    }
    static const char dirc[4] = {'U', 'D', 'L', 'R'};

    SplitMix64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    vector<int> visStamp(M, 0);
    int stamp = 0;

    auto simulate = [&](double beta, double gamma, double eps) -> pair<long long, string> {
        stamp++;
        int st = stamp;

        int ci = si, cj = sj;
        int curIdx = ci * N + cj;

        long long score = pval[ci][cj];
        visStamp[tid[ci][cj]] = st;

        string path;
        path.reserve(2600);

        while (true) {
            Candidate cands[4];
            int cnt = 0;

            for (int d = 0; d < 4; d++) {
                int nidx = neigh[curIdx][d];
                if (nidx < 0) continue;
                int ni = nidx / N, nj = nidx % N;
                int nt = tid[ni][nj];
                if (visStamp[nt] == st) continue;

                int deg1 = 0;
                int bestNextP = 0;
                // compute deg and best next p after moving to (ni,nj): can move only to different, unvisited tiles
                for (int d2 = 0; d2 < 4; d2++) {
                    int n2 = neigh[nidx][d2];
                    if (n2 < 0) continue;
                    int xi = n2 / N, xj = n2 % N;
                    int tt = tid[xi][xj];
                    if (tt == nt) continue;
                    if (visStamp[tt] == st) continue;
                    deg1++;
                    bestNextP = max(bestNextP, pval[xi][xj]);
                }

                double hv = (double)pval[ni][nj] + beta * (double)deg1 + gamma * (double)bestNextP;

                cands[cnt++] = Candidate{ni, nj, dirc[d], hv};
            }

            if (cnt == 0) break;

            int chosen = 0;
            if (rng.nextDouble() < eps) {
                chosen = rng.nextInt(0, cnt - 1);
            } else {
                // sort (cnt<=4) by hv descending
                for (int a = 0; a < cnt; a++) {
                    for (int b = a + 1; b < cnt; b++) {
                        if (cands[b].hv > cands[a].hv) swap(cands[a], cands[b]);
                    }
                }
                int K = 1;
                if (cnt >= 2 && rng.nextInt(0, 99) < 40) K = 2;
                if (cnt >= 3 && rng.nextInt(0, 99) < 12) K = 3;
                if (cnt >= 4 && rng.nextInt(0, 99) < 4) K = 4;
                if (K > cnt) K = cnt;
                chosen = rng.nextInt(0, K - 1);
            }

            auto &ch = cands[chosen];
            path.push_back(ch.mv);
            ci = ch.ni; cj = ch.nj;
            curIdx = ci * N + cj;
            score += pval[ci][cj];
            visStamp[tid[ci][cj]] = st;
        }

        return {score, path};
    };

    auto startTime = chrono::steady_clock::now();
    auto timeLimit = chrono::milliseconds(1850);

    long long bestScore = -1;
    string bestPath;

    // Always try a few deterministic settings first
    {
        vector<tuple<double,double,double>> presets = {
            {7.0, 0.30, 0.05},
            {9.0, 0.15, 0.08},
            {5.0, 0.45, 0.12},
            {10.0, 0.10, 0.03},
            {6.0, 0.60, 0.15},
        };
        for (auto [b,g,e] : presets) {
            auto [sc, pa] = simulate(b,g,e);
            if (sc > bestScore) { bestScore = sc; bestPath = move(pa); }
        }
    }

    int it = 0;
    while (chrono::steady_clock::now() - startTime < timeLimit) {
        it++;
        double beta = (double)rng.nextInt(3, 14);
        double gamma = rng.nextDouble() * 0.8;
        double eps = rng.nextDouble() * 0.22;

        // slight annealing-ish adjustment
        if ((it & 15) == 0) { beta = 10.0; gamma = 0.15; eps = 0.06; }

        auto [sc, pa] = simulate(beta, gamma, eps);
        if (sc > bestScore) {
            bestScore = sc;
            bestPath = move(pa);
        }
    }

    cout << bestPath << "\n";
    return 0;
}