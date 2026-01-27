#include <bits/stdc++.h>
using namespace std;

static constexpr int MAXC = 512;

struct Timer {
    chrono::steady_clock::time_point st;
    Timer() : st(chrono::steady_clock::now()) {}
    double elapsed() const {
        return chrono::duration<double>(chrono::steady_clock::now() - st).count();
    }
};

static int maxColor(const vector<int>& col) {
    int mx = 0;
    for (int c : col) mx = max(mx, c);
    return mx;
}

static void compressColors(vector<int>& col, int& K) {
    vector<int> mp(K + 1, 0);
    int nxt = 0;
    for (int &c : col) {
        if (c <= 0) continue;
        if (mp[c] == 0) mp[c] = ++nxt;
        c = mp[c];
    }
    K = nxt;
}

static void recolorWithinK(const vector<vector<int>>& adj, const vector<int>& deg, vector<int>& col, int& K) {
    int N = (int)col.size();
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    stable_sort(order.begin(), order.end(), [&](int a, int b){
        return deg[a] > deg[b];
    });

    vector<char> used;
    for (int it = 0; it < 12; it++) {
        bool any = false;
        used.assign(K + 1, 0);
        for (int v : order) {
            fill(used.begin(), used.end(), 0);
            for (int u : adj[v]) {
                int cu = col[u];
                if (cu >= 1 && cu <= K) used[cu] = 1;
            }
            int best = 1;
            while (best <= K && used[best]) best++;
            if (best <= K && best < col[v]) {
                col[v] = best;
                any = true;
            }
        }
        int newK = maxColor(col);
        if (newK < K) {
            K = newK;
            any = true;
        }
        if (!any) break;
    }
    compressColors(col, K);
}

static bool dsaturColoring(
    int N,
    const vector<vector<int>>& adj,
    const vector<int>& deg,
    int limitColors, // 0 => unlimited
    mt19937& rng,
    vector<int>& outCol,
    int& outK,
    bool randomizeColors
) {
    outCol.assign(N, 0);
    vector<bitset<MAXC>> forb(N);
    vector<int> sat(N, 0);

    int colored = 0;
    int currentK = 0;

    auto pickVertex = [&]() -> int {
        int bestSat = -1, bestDeg = -1;
        int chosen = -1;
        int cnt = 0;
        for (int i = 0; i < N; i++) if (outCol[i] == 0) {
            int s = sat[i];
            int d = deg[i];
            if (s > bestSat || (s == bestSat && d > bestDeg)) {
                bestSat = s; bestDeg = d;
                chosen = i;
                cnt = 1;
            } else if (s == bestSat && d == bestDeg) {
                cnt++;
                uniform_int_distribution<int> dist(1, cnt);
                if (dist(rng) == 1) chosen = i;
            }
        }
        return chosen;
    };

    auto chooseColor = [&](int v) -> int {
        int upper = (limitColors > 0 ? limitColors : currentK);
        vector<int> avail;
        avail.reserve(16);

        for (int c = 1; c <= upper; c++) {
            if (!forb[v].test(c)) avail.push_back(c);
        }
        if (!avail.empty()) {
            if (!randomizeColors || avail.size() == 1) return avail[0];
            // Prefer small colors, but sometimes diversify
            uniform_real_distribution<double> pr(0.0, 1.0);
            if (pr(rng) < 0.80) return avail[0];
            uniform_int_distribution<int> dist(0, (int)avail.size() - 1);
            return avail[dist(rng)];
        }

        if (limitColors > 0) return -1;
        return currentK + 1;
    };

    while (colored < N) {
        int v = pickVertex();
        if (v < 0) break;

        int c = chooseColor(v);
        if (c < 0) return false;

        outCol[v] = c;
        colored++;

        if (limitColors == 0) currentK = max(currentK, c);

        for (int u : adj[v]) {
            if (outCol[u] != 0) continue;
            if (!forb[u].test(c)) {
                forb[u].set(c);
                sat[u]++;
            }
        }
    }

    outK = (limitColors > 0 ? maxColor(outCol) : currentK);
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;

    vector<vector<int>> adj(N);
    adj.reserve(N);

    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    for (int i = 0; i < N; i++) {
        auto &a = adj[i];
        sort(a.begin(), a.end());
        a.erase(unique(a.begin(), a.end()), a.end());
    }

    vector<int> deg(N);
    for (int i = 0; i < N; i++) deg[i] = (int)adj[i].size();

    Timer timer;
    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    vector<int> bestCol;
    int bestK = N + 1;

    auto tryUpdateBest = [&](vector<int>& col, int K) {
        if (K < bestK) {
            bestK = K;
            bestCol = col;
        }
    };

    // Baseline deterministic attempt
    {
        vector<int> col;
        int K = 0;
        dsaturColoring(N, adj, deg, 0, rng, col, K, false);
        recolorWithinK(adj, deg, col, K);
        tryUpdateBest(col, K);
    }

    // Random restarts (unlimited)
    while (timer.elapsed() < 0.75) {
        vector<int> col;
        int K = 0;
        bool ok = dsaturColoring(N, adj, deg, 0, rng, col, K, true);
        if (!ok) continue;
        recolorWithinK(adj, deg, col, K);
        tryUpdateBest(col, K);
    }

    // Try to reduce number of colors with bounded DSATUR
    while (timer.elapsed() < 1.95 && bestK > 1) {
        int target = bestK - 1;
        bool improved = false;

        int attempts = 0;
        int maxAttempts = 20;
        if (N <= 200) maxAttempts = 35;

        for (; attempts < maxAttempts && timer.elapsed() < 1.95; attempts++) {
            vector<int> col;
            int K = 0;
            bool ok = dsaturColoring(N, adj, deg, target, rng, col, K, true);
            if (!ok) continue;
            recolorWithinK(adj, deg, col, K);
            if (K <= target && K < bestK) {
                tryUpdateBest(col, K);
                improved = true;
                break;
            }
        }
        if (!improved) break;
    }

    // Safety fallback (should never be empty)
    if (bestCol.empty()) {
        bestCol.resize(N);
        iota(bestCol.begin(), bestCol.end(), 1);
    }

    for (int i = 0; i < N; i++) {
        cout << bestCol[i] << "\n";
    }
    return 0;
}