#include <bits/stdc++.h>
using namespace std;

static const int MAXB = 512;

struct ColoringResult {
    vector<int> col;
    int K;
};

static inline int computeK(const vector<int>& col) {
    int K = 0;
    for (int c : col) K = max(K, c);
    return K;
}

static bool validateColoring(const vector<vector<int>>& g, const vector<int>& col) {
    int n = (int)g.size();
    for (int v = 0; v < n; v++) {
        int cv = col[v];
        for (int u : g[v]) {
            if (u > v && col[u] == cv) return false;
        }
    }
    return true;
}

static ColoringResult dsaturColoring(const vector<vector<int>>& g, const vector<int>& deg,
                                    mt19937& rng, bool randomTie, bool randomFeasible) {
    int n = (int)g.size();
    vector<int> col(n, 0);
    vector<int> sat(n, 0);
    vector<bitset<MAXB>> used(n);

    int K = 0;

    for (int it = 0; it < n; it++) {
        int bestSat = -1, bestDeg = -1;
        int v = -1;

        if (!randomTie) {
            for (int i = 0; i < n; i++) if (col[i] == 0) {
                if (sat[i] > bestSat || (sat[i] == bestSat && deg[i] > bestDeg) ||
                    (sat[i] == bestSat && deg[i] == bestDeg && i < v)) {
                    bestSat = sat[i];
                    bestDeg = deg[i];
                    v = i;
                }
            }
        } else {
            vector<int> cand;
            for (int i = 0; i < n; i++) if (col[i] == 0) {
                if (sat[i] > bestSat || (sat[i] == bestSat && deg[i] > bestDeg)) {
                    bestSat = sat[i];
                    bestDeg = deg[i];
                    cand.clear();
                    cand.push_back(i);
                } else if (sat[i] == bestSat && deg[i] == bestDeg) {
                    cand.push_back(i);
                }
            }
            uniform_int_distribution<int> dist(0, (int)cand.size() - 1);
            v = cand[dist(rng)];
        }

        int chosen = 0;
        if (!randomFeasible) {
            for (int c = 1; c <= n; c++) {
                if (!used[v].test(c)) { chosen = c; break; }
            }
        } else {
            vector<int> feas;
            int limit = min(n, max(3, K + 1));
            for (int c = 1; c <= limit; c++) {
                if (!used[v].test(c)) {
                    feas.push_back(c);
                    if ((int)feas.size() >= 6) break;
                }
            }
            if (feas.empty()) {
                for (int c = 1; c <= n; c++) if (!used[v].test(c)) { feas.push_back(c); break; }
            }
            if (feas.empty()) chosen = n;
            else {
                // Bias to smaller colors
                uniform_int_distribution<int> dist(0, (int)feas.size() - 1);
                int pick = dist(rng);
                if ((rng() % 100) < 75) pick = 0;
                chosen = feas[pick];
            }
        }

        col[v] = chosen;
        K = max(K, chosen);

        for (int u : g[v]) {
            if (col[u] == 0 && !used[u].test(chosen)) {
                used[u].set(chosen);
                sat[u]++;
            }
        }
    }

    return {col, K};
}

static ColoringResult greedyColoringOrder(const vector<vector<int>>& g, const vector<int>& order) {
    int n = (int)g.size();
    vector<int> col(n, 0);
    static int seen[MAXB];
    int timer = 1;
    int K = 0;

    for (int v : order) {
        ++timer;
        for (int u : g[v]) {
            int cu = col[u];
            if (cu) seen[cu] = timer;
        }
        int c = 1;
        while (c < MAXB && seen[c] == timer) ++c;
        if (c >= MAXB) c = MAXB - 1;
        col[v] = c;
        K = max(K, c);
    }
    return {col, K};
}

static vector<int> makeOrderDegreeNoise(const vector<int>& deg, mt19937& rng) {
    int n = (int)deg.size();
    vector<pair<int,int>> a;
    a.reserve(n);
    for (int i = 0; i < n; i++) {
        int key = deg[i] * 2048 + (int)(rng() & 2047);
        a.push_back({-key, i});
    }
    sort(a.begin(), a.end());
    vector<int> order;
    order.reserve(n);
    for (auto &p : a) order.push_back(p.second);
    return order;
}

static vector<int> makeOrderRandom(int n, mt19937& rng) {
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    shuffle(order.begin(), order.end(), rng);
    return order;
}

static vector<int> makeOrderSmallestLast(const vector<vector<int>>& g, const vector<int>& deg, mt19937& rng, bool randomTie) {
    int n = (int)g.size();
    vector<int> d = deg;
    vector<char> removed(n, 0);
    vector<int> rev;
    rev.reserve(n);

    for (int it = 0; it < n; it++) {
        int best = INT_MAX;
        int v = -1;
        if (!randomTie) {
            for (int i = 0; i < n; i++) if (!removed[i]) {
                if (d[i] < best || (d[i] == best && i < v)) {
                    best = d[i];
                    v = i;
                }
            }
        } else {
            vector<int> cand;
            for (int i = 0; i < n; i++) if (!removed[i]) {
                if (d[i] < best) {
                    best = d[i];
                    cand.clear();
                    cand.push_back(i);
                } else if (d[i] == best) cand.push_back(i);
            }
            uniform_int_distribution<int> dist(0, (int)cand.size() - 1);
            v = cand[dist(rng)];
        }

        removed[v] = 1;
        rev.push_back(v);
        for (int u : g[v]) if (!removed[u]) d[u]--;
    }

    reverse(rev.begin(), rev.end());
    return rev;
}

static bool canAssign(const vector<vector<int>>& g, const vector<int>& col, int v, int c) {
    for (int u : g[v]) if (col[u] == c) return false;
    return true;
}

static void tryReduceColors(const vector<vector<int>>& g, const vector<int>& deg, vector<int>& col, mt19937& rng) {
    int n = (int)g.size();
    int K = computeK(col);

    while (K > 1) {
        vector<int> verts;
        verts.reserve(n);
        for (int i = 0; i < n; i++) if (col[i] == K) verts.push_back(i);

        if (verts.empty()) { K--; continue; }

        bool success = false;
        const int ATTEMPTS = 40;

        for (int attempt = 0; attempt < ATTEMPTS && !success; attempt++) {
            vector<int> tmp = col;
            vector<int> order = verts;

            if (attempt == 0) {
                sort(order.begin(), order.end(), [&](int a, int b){
                    if (deg[a] != deg[b]) return deg[a] > deg[b];
                    return a < b;
                });
            } else {
                shuffle(order.begin(), order.end(), rng);
                // Slight bias: sort in blocks by degree
                stable_sort(order.begin(), order.end(), [&](int a, int b){
                    if (deg[a] != deg[b]) return deg[a] > deg[b];
                    return a < b;
                });
                // Re-shuffle small prefix to diversify
                int pref = min<int>(order.size(), 10);
                shuffle(order.begin(), order.begin() + pref, rng);
            }

            bool ok = true;
            for (int v : order) {
                int chosen = 0;

                // Try smallest feasible
                for (int c = 1; c <= K - 1; c++) {
                    if (canAssign(g, tmp, v, c)) { chosen = c; break; }
                }

                if (!chosen) { ok = false; break; }
                tmp[v] = chosen;
            }

            if (ok) {
                col.swap(tmp);
                success = true;
            }
        }

        if (!success) break;
        K--;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<bitset<MAXB>> adj(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }

    vector<vector<int>> compG(N);
    for (int i = 0; i < N; i++) compG[i].reserve(N);

    for (int i = 0; i < N; i++) {
        for (int j = i + 1; j < N; j++) {
            if (!adj[i].test(j)) {
                compG[i].push_back(j);
                compG[j].push_back(i);
            }
        }
    }

    vector<int> deg(N);
    for (int i = 0; i < N; i++) deg[i] = (int)compG[i].size();

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    vector<int> bestCol(N);
    iota(bestCol.begin(), bestCol.end(), 1);
    int bestK = N;

    auto consider = [&](vector<int> col) {
        if (!validateColoring(compG, col)) return;
        tryReduceColors(compG, deg, col, rng);
        int K = computeK(col);
        if (K < bestK) {
            bestK = K;
            bestCol = std::move(col);
        }
    };

    // Deterministic DSATUR
    {
        auto res = dsaturColoring(compG, deg, rng, false, false);
        consider(std::move(res.col));
    }

    // Randomized DSATUR
    for (int t = 0; t < 18; t++) {
        bool randomFeasible = (t % 3 == 0);
        auto res = dsaturColoring(compG, deg, rng, true, randomFeasible);
        consider(std::move(res.col));
    }

    // Greedy by degree with noise
    for (int t = 0; t < 16; t++) {
        auto order = makeOrderDegreeNoise(deg, rng);
        auto res = greedyColoringOrder(compG, order);
        consider(std::move(res.col));
    }

    // Smallest-last orderings
    for (int t = 0; t < 10; t++) {
        auto order = makeOrderSmallestLast(compG, deg, rng, true);
        auto res = greedyColoringOrder(compG, order);
        consider(std::move(res.col));
    }

    // Pure random orderings
    for (int t = 0; t < 10; t++) {
        auto order = makeOrderRandom(N, rng);
        auto res = greedyColoringOrder(compG, order);
        consider(std::move(res.col));
    }

    if (!validateColoring(compG, bestCol)) {
        bestCol.resize(N);
        for (int i = 0; i < N; i++) bestCol[i] = i + 1;
    }

    for (int i = 0; i < N; i++) {
        cout << bestCol[i] << "\n";
    }
    return 0;
}