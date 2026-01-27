#include <bits/stdc++.h>
using namespace std;

static constexpr int MAXN = 500;
static constexpr int MAXC = 512;

struct Solver {
    int N, M;
    vector<vector<int>> adj;
    vector<int> deg;

    mt19937 rng;

    Solver() : rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count()) {}

    vector<int> dsatur(int &K, bool randomized) {
        vector<int> color(N, 0);
        vector<int> satDeg(N, 0);
        vector<bitset<MAXC>> satMask(N);

        vector<int> mark(N + 2, 0);
        int stamp = 0;

        int maxColor = 0;

        for (int it = 0; it < N; it++) {
            int bestSat = -1, bestDeg = -1;
            int v = -1;

            if (randomized) {
                vector<int> cand;
                cand.reserve(N);
                for (int i = 0; i < N; i++) if (color[i] == 0) {
                    int s = satDeg[i], d = deg[i];
                    if (s > bestSat || (s == bestSat && d > bestDeg)) {
                        bestSat = s; bestDeg = d;
                        cand.clear();
                        cand.push_back(i);
                    } else if (s == bestSat && d == bestDeg) {
                        cand.push_back(i);
                    }
                }
                v = cand[uniform_int_distribution<int>(0, (int)cand.size() - 1)(rng)];
            } else {
                for (int i = 0; i < N; i++) if (color[i] == 0) {
                    int s = satDeg[i], d = deg[i];
                    if (s > bestSat || (s == bestSat && d > bestDeg)) {
                        bestSat = s; bestDeg = d; v = i;
                    }
                }
            }

            ++stamp;
            for (int u : adj[v]) {
                int cu = color[u];
                if (cu) mark[cu] = stamp;
            }
            int chosen = 0;
            for (int c = 1; c <= maxColor; c++) {
                if (mark[c] != stamp) { chosen = c; break; }
            }
            if (!chosen) chosen = maxColor + 1;
            color[v] = chosen;
            if (chosen > maxColor) maxColor = chosen;

            for (int u : adj[v]) if (color[u] == 0) {
                if (!satMask[u].test(chosen)) {
                    satMask[u].set(chosen);
                    satDeg[u]++;
                }
            }
        }
        K = maxColor;
        return color;
    }

    void compressColors(vector<int> &col, int &K) {
        vector<int> used(K + 1, 0);
        for (int x : col) if (x >= 1 && x <= K) used[x] = 1;
        vector<int> mp(K + 1, 0);
        int nk = 0;
        for (int c = 1; c <= K; c++) if (used[c]) mp[c] = ++nk;
        for (int &x : col) x = mp[x];
        K = nk;
    }

    void greedyImprove(vector<int> &col, int &K) {
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        stable_sort(order.begin(), order.end(), [&](int a, int b) {
            return deg[a] > deg[b];
        });

        vector<int> mark(N + 2, 0);
        int stamp = 0;

        for (int v : order) {
            ++stamp;
            for (int u : adj[v]) {
                int cu = col[u];
                if (cu) mark[cu] = stamp;
            }
            int cur = col[v];
            for (int c = 1; c < cur; c++) {
                if (mark[c] != stamp) { col[v] = c; break; }
            }
        }
        compressColors(col, K);
    }

    bool recolorOrOneSwap(int v, int target, int limit, vector<int> &col) {
        static array<int, MAXN + 5> cnt;
        static array<int, MAXN + 5> lastN;
        cnt.fill(0);
        lastN.fill(-1);

        for (int u : adj[v]) {
            int cu = col[u];
            if (cu >= 1 && cu <= limit) {
                cnt[cu]++;
                lastN[cu] = u;
            }
        }

        for (int c = 1; c <= limit; c++) {
            if (cnt[c] == 0) {
                col[v] = c;
                return true;
            }
        }

        static array<int, MAXN + 5> mark;
        static int stamp = 0;

        for (int a = 1; a <= limit; a++) {
            if (cnt[a] != 1) continue;
            int u = lastN[a];

            ++stamp;
            for (int w : adj[u]) {
                int cw = (w == v ? a : col[w]);
                if (cw >= 1 && cw <= limit) mark[cw] = stamp;
            }
            for (int b = 1; b <= limit; b++) {
                if (b == a) continue;
                if (mark[b] != stamp) {
                    col[u] = b;
                    col[v] = a;
                    return true;
                }
            }
        }

        return false;
    }

    bool eliminateMaxColor(vector<int> &col, int &K, int attempts) {
        if (K <= 1) return false;
        int target = K;
        int limit = K - 1;

        vector<int> nodes;
        nodes.reserve(N);
        for (int i = 0; i < N; i++) if (col[i] == target) nodes.push_back(i);
        if (nodes.empty()) { K--; return true; }

        vector<int> backup = col;

        for (int att = 0; att < attempts; att++) {
            col = backup;
            shuffle(nodes.begin(), nodes.end(), rng);
            stable_sort(nodes.begin(), nodes.end(), [&](int a, int b) {
                return deg[a] < deg[b];
            });

            bool ok = true;
            for (int v : nodes) {
                if (col[v] != target) continue;
                if (!recolorOrOneSwap(v, target, limit, col)) {
                    ok = false;
                    break;
                }
            }
            if (!ok) continue;

            bool any = false;
            for (int x : col) if (x == target) { any = true; break; }
            if (!any) {
                K--;
                compressColors(col, K);
                return true;
            }
        }

        col = backup;
        return false;
    }

    void randomFeasibleRecolor(vector<int> &col, int K, int steps) {
        if (K <= 1) return;
        vector<int> mark(N + 2, 0);
        int stamp = 0;

        for (int s = 0; s < steps; s++) {
            int v = uniform_int_distribution<int>(0, N - 1)(rng);
            ++stamp;
            for (int u : adj[v]) mark[col[u]] = stamp;
            vector<int> feas;
            feas.reserve(K);
            for (int c = 1; c <= K; c++) if (mark[c] != stamp) feas.push_back(c);
            if (feas.empty()) continue;
            int chosen = feas[uniform_int_distribution<int>(0, (int)feas.size() - 1)(rng)];
            col[v] = chosen;
        }
    }

    bool validColoring(const vector<int> &col) {
        for (int v = 0; v < N; v++) {
            if (col[v] <= 0) return false;
            for (int u : adj[v]) if (u > v) {
                if (col[u] == col[v]) return false;
            }
        }
        return true;
    }

    int maxColorUsed(const vector<int> &col) {
        int K = 0;
        for (int x : col) K = max(K, x);
        return K;
    }

    void solve() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        cin >> N >> M;
        adj.assign(N, {});
        deg.assign(N, 0);

        vector<bitset<MAXN>> mat(N);
        for (int i = 0; i < M; i++) {
            int u, v;
            cin >> u >> v;
            --u; --v;
            if (u == v) continue;
            if (!mat[u].test(v)) {
                mat[u].set(v);
                mat[v].set(u);
                adj[u].push_back(v);
                adj[v].push_back(u);
            }
        }
        for (int i = 0; i < N; i++) deg[i] = (int)adj[i].size();

        auto t0 = chrono::steady_clock::now();
        auto elapsed = [&]() -> double {
            return chrono::duration<double>(chrono::steady_clock::now() - t0).count();
        };

        const double TL = 1.95;
        const double PH1 = 0.85;

        vector<int> bestCol;
        int bestK = INT_MAX;

        {
            int K0 = 0;
            auto col0 = dsatur(K0, false);
            greedyImprove(col0, K0);
            bestCol = col0;
            bestK = K0;
        }

        int runs = 0;
        while (elapsed() < PH1 && runs < 300) {
            int K = 0;
            auto col = dsatur(K, true);
            // quick refinement
            for (int i = 0; i < 2; i++) greedyImprove(col, K);
            eliminateMaxColor(col, K, 12);

            if (K < bestK && validColoring(col)) {
                bestK = K;
                bestCol = col;
            }
            runs++;
        }

        int noImprove = 0;
        while (elapsed() < TL) {
            int prevK = bestK;

            greedyImprove(bestCol, bestK);
            while (elapsed() < TL && eliminateMaxColor(bestCol, bestK, 25)) {
                greedyImprove(bestCol, bestK);
            }

            if (bestK < prevK) {
                noImprove = 0;
            } else {
                noImprove++;
                if (noImprove >= 3) {
                    randomFeasibleRecolor(bestCol, bestK, max(5, N / 8));
                    greedyImprove(bestCol, bestK);
                    noImprove = 0;
                }
            }
        }

        if (!validColoring(bestCol)) {
            int K = 0;
            bestCol = dsatur(K, false);
            bestK = K;
            greedyImprove(bestCol, bestK);
            if (!validColoring(bestCol)) {
                bestCol.assign(N, 0);
                for (int i = 0; i < N; i++) bestCol[i] = i + 1;
                bestK = N;
            }
        }

        for (int i = 0; i < N; i++) {
            cout << bestCol[i] << "\n";
        }
    }
};

int main() {
    Solver s;
    s.solve();
    return 0;
}