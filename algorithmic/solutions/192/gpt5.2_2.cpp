#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct Solver {
    int n, m;
    vector<pair<int,int>> edges;
    vector<vector<int>> adj;
    mt19937 rng;

    Solver(int n_, int m_) : n(n_), m(m_) {
        adj.assign(n, {});
        uint64_t seed = splitmix64((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
        rng.seed((uint32_t)(seed ^ (seed >> 32)));
    }

    vector<int> randomInit() {
        vector<int> s(n);
        uniform_int_distribution<int> dist(0, 1);
        for (int i = 0; i < n; i++) s[i] = dist(rng);
        return s;
    }

    vector<int> greedyInit() {
        vector<int> s(n, -1);
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);

        uniform_int_distribution<int> dist(0, 1);
        for (int v : order) {
            int c0 = 0, c1 = 0;
            for (int u : adj[v]) {
                if (s[u] == 0) c0++;
                else if (s[u] == 1) c1++;
            }
            // If v=0 => cut edges to assigned 1 => c1
            // If v=1 => cut edges to assigned 0 => c0
            if (c1 > c0) s[v] = 0;
            else if (c0 > c1) s[v] = 1;
            else s[v] = dist(rng);
        }
        return s;
    }

    int computeCut(const vector<int>& s) const {
        int cut = 0;
        for (auto [a,b] : edges) if (s[a] != s[b]) cut++;
        return cut;
    }

    int computeCutAndGains(const vector<int>& s, vector<int>& gain) const {
        int cut = 0;
        for (auto [a,b] : edges) if (s[a] != s[b]) cut++;

        gain.assign(n, 0);
        for (int v = 0; v < n; v++) {
            int opp = 0;
            for (int u : adj[v]) if (s[u] != s[v]) opp++;
            int deg = (int)adj[v].size();
            gain[v] = deg - 2 * opp; // same - opp
        }
        return cut;
    }

    inline void flipVertex(int v, vector<int>& s, vector<int>& gain, int& cut) {
        s[v] ^= 1;
        cut += gain[v];

        gain[v] = -gain[v];
        for (int u : adj[v]) {
            if (s[u] == s[v]) gain[u] += 2;
            else gain[u] -= 2;
        }
    }

    int localImprove(vector<int>& s) const {
        vector<int> gain;
        int cut = computeCutAndGains(s, gain);

        while (true) {
            int bestGain = 0;
            vector<int> cand;
            cand.reserve(8);

            for (int v = 0; v < n; v++) {
                int g = gain[v];
                if (g > bestGain) {
                    bestGain = g;
                    cand.clear();
                    cand.push_back(v);
                } else if (g == bestGain && g > 0) {
                    cand.push_back(v);
                }
            }

            if (bestGain <= 0) break;

            int v;
            if (cand.size() == 1) v = cand[0];
            else {
                uniform_int_distribution<int> dist(0, (int)cand.size() - 1);
                v = cand[dist(rng)];
            }

            // flip
            s[v] ^= 1;
            cut += gain[v];

            gain[v] = -gain[v];
            for (int u : adj[v]) {
                if (s[u] == s[v]) gain[u] += 2;
                else gain[u] -= 2;
            }
        }
        return cut;
    }

    vector<int> solve(double timeLimitSec = 1.85) {
        if (m == 0) return vector<int>(n, 0);

        auto t0 = chrono::steady_clock::now();
        auto elapsed = [&]() -> double {
            return chrono::duration<double>(chrono::steady_clock::now() - t0).count();
        };

        vector<int> bestS = greedyInit();
        int bestCut = localImprove(bestS);

        uniform_int_distribution<int> coin(0, 1);
        uniform_int_distribution<int> kickDist(1, 12);

        // restarts + iterated local search
        while (elapsed() < timeLimitSec) {
            vector<int> s;
            if (coin(rng) == 0) s = greedyInit();
            else s = randomInit();

            int cut = localImprove(s);
            if (cut > bestCut) {
                bestCut = cut;
                bestS.swap(s);
            }

            // Try a few kicks from the current best to escape local optimum
            for (int rep = 0; rep < 3 && elapsed() < timeLimitSec; rep++) {
                s = bestS;
                int k = kickDist(rng);
                uniform_int_distribution<int> vd(0, n - 1);
                for (int i = 0; i < k; i++) s[vd(rng)] ^= 1;

                cut = localImprove(s);
                if (cut > bestCut) {
                    bestCut = cut;
                    bestS.swap(s);
                }
            }
        }

        return bestS;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    Solver solver(n, m);
    solver.edges.reserve(m);

    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        solver.edges.push_back({u, v});
        solver.adj[u].push_back(v);
        solver.adj[v].push_back(u);
    }

    vector<int> ans = solver.solve();

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << '\n';
    return 0;
}