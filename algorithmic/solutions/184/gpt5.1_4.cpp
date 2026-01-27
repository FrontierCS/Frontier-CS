#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1000;
bitset<MAXN> adj[MAXN];

struct XorShift64 {
    uint64_t x;
    XorShift64(uint64_t seed = 88172645463325252ull) { x = seed; }
    uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    uint32_t next32() { return (uint32_t)next(); }
    int nextInt(int n) { return (int)(next32() % n); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    long long M;
    if (!(cin >> N >> M)) return 0;

    for (int i = 0; i < N; ++i) adj[i].reset();

    for (long long i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u < 0 || u >= N || v < 0 || v >= N || u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }

    vector<vector<int>> g(N);
    vector<int> degree(N, 0);
    for (int v = 0; v < N; ++v) {
        for (int u = 0; u < N; ++u) {
            if (adj[v].test(u)) {
                g[v].push_back(u);
            }
        }
        degree[v] = (int)g[v].size();
    }

    auto seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    XorShift64 rng((uint64_t)seed);

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.8; // seconds

    vector<int> bestSel(N, 0);
    int bestK = 0;

    auto build_from_order = [&](const vector<int> &order) {
        vector<char> banned(N, 0), inS(N, 0);
        int k = 0;
        for (int v : order) {
            if (!banned[v]) {
                inS[v] = 1;
                ++k;
                banned[v] = 1;
                for (int u : g[v]) banned[u] = 1;
            }
        }
        if (k > bestK) {
            bestK = k;
            for (int i = 0; i < N; ++i) bestSel[i] = inS[i];
        }
    };

    // Initial run: degree ascending
    vector<int> perm(N);
    for (int i = 0; i < N; ++i) perm[i] = i;
    sort(perm.begin(), perm.end(), [&](int a, int b) {
        if (degree[a] != degree[b]) return degree[a] < degree[b];
        return a < b;
    });
    build_from_order(perm);

    int iterations = 0;
    while (true) {
        ++iterations;
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > TIME_LIMIT) break;

        if (iterations % 2 == 1) {
            // Degree-biased with random tie-breaks
            vector<uint32_t> noise(N);
            for (int i = 0; i < N; ++i) noise[i] = rng.next32();
            perm.resize(N);
            for (int i = 0; i < N; ++i) perm[i] = i;
            sort(perm.begin(), perm.end(), [&](int a, int b) {
                if (degree[a] != degree[b]) return degree[a] < degree[b];
                if (noise[a] != noise[b]) return noise[a] < noise[b];
                return a < b;
            });
            build_from_order(perm);
        } else {
            // Pure random order
            perm.resize(N);
            for (int i = 0; i < N; ++i) perm[i] = i;
            for (int i = N - 1; i > 0; --i) {
                int j = rng.nextInt(i + 1);
                swap(perm[i], perm[j]);
            }
            build_from_order(perm);
        }

        // Occasionally run dynamic min-degree greedy
        if (iterations % 20 == 0) {
            now = chrono::steady_clock::now();
            elapsed = chrono::duration<double>(now - start).count();
            if (elapsed > TIME_LIMIT) break;

            vector<char> inS(N, 0);
            bitset<MAXN> R;
            R.reset();
            for (int i = 0; i < N; ++i) R.set(i);
            int curDeg[MAXN];
            vector<int> cand;
            while (R.any()) {
                int best_deg = INT_MAX;
                for (int i = 0; i < N; ++i) {
                    if (R.test(i)) {
                        int d = (int)(adj[i] & R).count();
                        curDeg[i] = d;
                        if (d < best_deg) best_deg = d;
                    }
                }
                cand.clear();
                for (int i = 0; i < N; ++i) {
                    if (R.test(i) && curDeg[i] == best_deg) cand.push_back(i);
                }
                int v = cand[rng.nextInt((int)cand.size())];
                inS[v] = 1;
                R.reset(v);
                bitset<MAXN> toRemove = adj[v] & R;
                R &= ~toRemove;
            }
            int k = 0;
            for (int i = 0; i < N; ++i) if (inS[i]) ++k;
            if (k > bestK) {
                bestK = k;
                for (int i = 0; i < N; ++i) bestSel[i] = inS[i];
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << bestSel[i] << "\n";
    }

    return 0;
}