#include <bits/stdc++.h>
using namespace std;

static const int N = 50;

struct TrialParams {
    int wv, wd, wl;
    int noise;
    bool filter_dead;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int si, sj;
    cin >> si >> sj;

    vector<vector<int>> t(N, vector<int>(N));
    int mx = -1;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cin >> t[i][j];
            mx = max(mx, t[i][j]);
        }
    }
    int M = mx + 1;

    vector<vector<int>> p(N, vector<int>(N));
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) cin >> p[i][j];

    const int di[4] = {-1, 1, 0, 0};
    const int dj[4] = {0, 0, -1, 1};
    const char dc[4] = {'U', 'D', 'L', 'R'};

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    auto run_trial = [&](const TrialParams& prm) -> pair<int, string> {
        vector<unsigned char> vis(M, 0);
        int ci = si, cj = sj;
        int ct = t[ci][cj];
        vis[ct] = 1;
        int score = p[ci][cj];
        string path;
        path.reserve(2600);

        auto deg_from = [&](int i, int j, int assumed_tile_id) -> int {
            int d = 0;
            for (int k = 0; k < 4; k++) {
                int ni = i + di[k], nj = j + dj[k];
                if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
                int nt = t[ni][nj];
                if (nt == assumed_tile_id) continue;
                if (vis[nt]) continue;
                d++;
            }
            return d;
        };

        for (int step = 0; step < 2600; step++) {
            struct Cand {
                int k, ni, nj, nt;
                int val;
                int deg1;
                int look2;
            };
            Cand cands[4];
            int csz = 0;
            for (int k = 0; k < 4; k++) {
                int ni = ci + di[k], nj = cj + dj[k];
                if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
                int nt = t[ni][nj];
                if (nt == ct) continue;
                if (vis[nt]) continue;

                int deg1 = deg_from(ni, nj, nt);

                int look2 = 0;
                for (int kk = 0; kk < 4; kk++) {
                    int xi = ni + di[kk], xj = nj + dj[kk];
                    if (xi < 0 || xi >= N || xj < 0 || xj >= N) continue;
                    int tt2 = t[xi][xj];
                    if (tt2 == nt) continue;
                    if (vis[tt2]) continue; // vis includes current tile already; and we treat nt as visited by excluding tt2==nt
                    look2 = max(look2, p[xi][xj]);
                }

                cands[csz++] = Cand{k, ni, nj, nt, p[ni][nj], deg1, look2};
            }
            if (csz == 0) break;

            bool has_non_dead = false;
            for (int i = 0; i < csz; i++) if (cands[i].deg1 > 0) { has_non_dead = true; break; }

            int best_idx = -1;
            long long best_h = LLONG_MIN;

            uniform_int_distribution<int> dist_noise(0, max(0, prm.noise));
            for (int idx = 0; idx < csz; idx++) {
                const auto &c = cands[idx];
                if (prm.filter_dead && has_non_dead && c.deg1 == 0) continue;

                long long h = 0;
                h += 1LL * prm.wv * c.val;
                h += 1LL * prm.wd * c.deg1;
                h += 1LL * prm.wl * c.look2;
                if (prm.noise > 0) h += dist_noise(rng);
                // Mild penalty to deg==0 even when not filtering, to push it toward the end.
                if (c.deg1 == 0) h -= 2000;

                if (h > best_h) {
                    best_h = h;
                    best_idx = idx;
                }
            }
            if (best_idx < 0) {
                // Only dead-ends existed and filtered them all; choose the best dead-end.
                best_idx = 0;
                for (int idx = 1; idx < csz; idx++) {
                    if (cands[idx].val > cands[best_idx].val) best_idx = idx;
                }
            }

            auto &c = cands[best_idx];
            path.push_back(dc[c.k]);
            ci = c.ni; cj = c.nj;
            ct = c.nt;
            vis[ct] = 1;
            score += c.val;
        }

        return {score, path};
    };

    int best_score = -1;
    string best_path;

    // Baseline deterministic-ish
    {
        TrialParams prm;
        prm.wv = 10;
        prm.wd = 500;
        prm.wl = 6;
        prm.noise = 0;
        prm.filter_dead = true;
        auto [sc, pa] = run_trial(prm);
        best_score = sc;
        best_path = pa;
    }

    auto start = chrono::steady_clock::now();
    const double TL = 1.85;

    uniform_int_distribution<int> wv_dist(6, 18);
    uniform_int_distribution<int> wd_dist(250, 850);
    uniform_int_distribution<int> wl_dist(0, 16);
    uniform_int_distribution<int> noise_dist(0, 600);
    uniform_int_distribution<int> bern(0, 99);

    while (true) {
        double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start).count();
        if (elapsed > TL) break;

        TrialParams prm;
        prm.wv = wv_dist(rng);
        prm.wd = wd_dist(rng);
        prm.wl = wl_dist(rng);
        prm.noise = noise_dist(rng);
        prm.filter_dead = (bern(rng) < 85);

        auto [sc, pa] = run_trial(prm);
        if (sc > best_score) {
            best_score = sc;
            best_path = std::move(pa);
        }
    }

    cout << best_path << "\n";
    return 0;
}