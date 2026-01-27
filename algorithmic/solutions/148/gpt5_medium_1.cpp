#include <bits/stdc++.h>
using namespace std;

struct Runner {
    static constexpr int H = 50;
    static constexpr int W = 50;
    int si, sj;
    int t[H][W];
    int p[H][W];
    int M;
    struct Nei { int ni, nj; char ch; };
    vector<Nei> adj[H][W]; // neighbors with different tile id
    mt19937 rng;

    Runner() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);
        unsigned seed = chrono::high_resolution_clock::now().time_since_epoch().count();
        rng.seed(seed);
    }

    void read_input() {
        cin >> si >> sj;
        int mx = -1;
        for (int i = 0; i < H; ++i) {
            for (int j = 0; j < W; ++j) {
                cin >> t[i][j];
                mx = max(mx, t[i][j]);
            }
        }
        for (int i = 0; i < H; ++i) {
            for (int j = 0; j < W; ++j) {
                cin >> p[i][j];
            }
        }
        M = mx + 1;
        // precompute adj with different tile id
        for (int i = 0; i < H; ++i) {
            for (int j = 0; j < W; ++j) {
                adj[i][j].clear();
                if (i > 0) {
                    if (t[i-1][j] != t[i][j]) adj[i][j].push_back({i-1, j, 'U'});
                }
                if (i+1 < H) {
                    if (t[i+1][j] != t[i][j]) adj[i][j].push_back({i+1, j, 'D'});
                }
                if (j > 0) {
                    if (t[i][j-1] != t[i][j]) adj[i][j].push_back({i, j-1, 'L'});
                }
                if (j+1 < W) {
                    if (t[i][j+1] != t[i][j]) adj[i][j].push_back({i, j+1, 'R'});
                }
            }
        }
    }

    struct Result {
        long long score;
        string path;
    };

    Result run_once(double w1, double wdeg1, double wdeg2, double zero_penalty, double noise_scale) {
        vector<char> used(M, 0);
        int ci = si, cj = sj;
        used[t[ci][cj]] = 1;
        long long score = p[ci][cj];
        string path;
        path.reserve(3000);

        auto randint = [&](int l, int r)->int{ uniform_int_distribution<int> d(l, r); return d(rng); };
        auto randreal = [&]()->double{ uniform_real_distribution<double> d(0.0, 1.0); return d(rng); };

        while (true) {
            // build candidates
            vector<Nei> cand;
            cand.reserve(4);
            for (auto &e : adj[ci][cj]) {
                if (!used[t[e.ni][e.nj]]) cand.push_back(e);
            }
            if (cand.empty()) break;

            // Evaluate candidates
            double bestVal = -1e100;
            int bestIdx = -1;
            bool existsNonZeroDeg = false;
            vector<int> deg1s(cand.size(), 0);

            // First pass to compute deg1 and existence of non-zero deg
            for (size_t idx = 0; idx < cand.size(); ++idx) {
                int ni = cand[idx].ni, nj = cand[idx].nj;
                int d1 = 0;
                for (auto &e2 : adj[ni][nj]) {
                    if (!used[t[e2.ni][e2.nj]]) d1++;
                }
                deg1s[idx] = d1;
                if (d1 > 0) existsNonZeroDeg = true;
            }

            for (size_t idx = 0; idx < cand.size(); ++idx) {
                int ni = cand[idx].ni, nj = cand[idx].nj;
                int tileV = t[ni][nj];
                int d1 = deg1s[idx];

                // two-step lookahead: best next move from (ni,nj)
                double best2 = 0.0;
                for (auto &e2 : adj[ni][nj]) {
                    int ci2 = e2.ni, cj2 = e2.nj;
                    int tileC = t[ci2][cj2];
                    if (used[tileC]) continue;
                    // cannot go back to tileV if we imagine stepping into (ni,nj) then to (ci2,cj2) - but from (ni,nj) we just came from current tile which is used already, so already excluded
                    // Now when evaluating deg2 from (ci2,cj2), we consider that tileV will be used then.
                    int d2 = 0;
                    for (auto &e3 : adj[ci2][cj2]) {
                        int tileN = t[e3.ni][e3.nj];
                        if (tileN == tileV) continue; // back to V not allowed
                        if (!used[tileN]) d2++;
                    }
                    double val2 = (double)p[ci2][cj2] + wdeg2 * (double)d2;
                    if (val2 > best2) best2 = val2;
                }

                double val = (double)p[ni][nj] + w1 * best2 + wdeg1 * (double)d1;
                if (d1 == 0 && existsNonZeroDeg) val -= zero_penalty;
                // small noise to diversify
                val += (randreal() - 0.5) * noise_scale;

                if (val > bestVal) {
                    bestVal = val;
                    bestIdx = (int)idx;
                }
            }

            auto chosen = cand[bestIdx];
            ci = chosen.ni; cj = chosen.nj;
            used[t[ci][cj]] = 1;
            score += p[ci][cj];
            path.push_back(chosen.ch);
        }

        return {score, path};
    }

    string solve() {
        // Time limit control
        auto start = chrono::high_resolution_clock::now();
        double TIME_LIMIT_MS = 1950.0; // ms

        Result best{(long long)p[si][sj], string()};

        int iter = 0;
        while (true) {
            auto now = chrono::high_resolution_clock::now();
            double elapsed = chrono::duration<double, std::milli>(now - start).count();
            if (elapsed > TIME_LIMIT_MS) break;

            // Randomize weights
            uniform_real_distribution<double> d01(0.0, 1.0);
            double w1 = 0.3 + 0.7 * d01(rng);        // lookahead weight
            double wdeg1 = 0.0 + 2.5 * d01(rng);     // degree at next step
            double wdeg2 = 0.0 + 2.0 * d01(rng);     // degree at two steps ahead
            double zero_penalty = 10.0 + 40.0 * d01(rng); // penalty for stepping into dead-end when alternatives exist
            double noise_scale = 0.2 + 0.8 * d01(rng);    // randomness

            Result cur = run_once(w1, wdeg1, wdeg2, zero_penalty, noise_scale);
            if (cur.score > best.score) best = cur;

            iter++;
            // Occasionally try a greedier setting
            if ((iter & 7) == 0) {
                Result cur2 = run_once(0.8, 1.5, 1.0, 25.0, 0.05);
                if (cur2.score > best.score) best = cur2;
            }
        }
        return best.path;
    }
};

int main() {
    Runner runner;
    runner.read_input();
    string ans = runner.solve();
    cout << ans << '\n';
    return 0;
}