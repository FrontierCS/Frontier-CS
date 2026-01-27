#include <bits/stdc++.h>
using namespace std;

struct MaxCutSolver {
    int n, m;
    vector<vector<int>> adj;
    vector<pair<int,int>> edges;
    vector<int> deg;
    int maxDeg = 0;
    mt19937 rng;

    MaxCutSolver(int n, int m) : n(n), m(m), adj(n), deg(n, 0) {
        uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
        rng.seed(seed ^ (uint64_t)(new int));
    }

    void add_edge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
        deg[u]++; deg[v]++;
        maxDeg = max(maxDeg, max(deg[u], deg[v]));
    }

    long long cut_value(const vector<int>& s) const {
        long long c = 0;
        for (auto &e : edges) {
            if (s[e.first] != s[e.second]) c++;
        }
        return c;
    }

    vector<int> initial_greedy() {
        vector<int> s(n, -1);
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        for (int v : order) {
            int cnt0 = 0, cnt1 = 0;
            for (int u : adj[v]) {
                if (s[u] == 0) cnt0++;
                else if (s[u] == 1) cnt1++;
            }
            // If set s[v] = 0, crossing edges = cnt1; if set to 1, crossing = cnt0
            if (cnt1 > cnt0) s[v] = 0;
            else if (cnt0 > cnt1) s[v] = 1;
            else s[v] = (rng() & 1);
        }
        return s;
    }

    // Single pass of FM-like algorithm (no balance constraint). Returns true if improved.
    bool fm_pass(vector<int>& s) {
        const int bucketTotal = 2 * maxDeg + 1;
        const int offset = maxDeg;

        vector<int> degOpp(n, 0);
        for (auto &e : edges) {
            int u = e.first, v = e.second;
            if (s[u] != s[v]) {
                degOpp[u]++; degOpp[v]++;
            }
        }
        vector<int> gain(n);
        for (int i = 0; i < n; ++i) gain[i] = deg[i] - 2 * degOpp[i];

        vector<int> b_head(bucketTotal, -1);
        vector<int> b_next(n, -1), b_prev(n, -1), b_index(n, -1);
        vector<char> locked(n, 0);

        auto addToBucket = [&](int v) {
            int idx = gain[v] + offset;
            // Ensure idx in range
            if (idx < 0) idx = 0;
            if (idx >= bucketTotal) idx = bucketTotal - 1;
            b_prev[v] = -1;
            b_next[v] = b_head[idx];
            if (b_next[v] != -1) b_prev[b_next[v]] = v;
            b_head[idx] = v;
            b_index[v] = idx;
        };
        auto removeFromBucket = [&](int v) {
            int idx = b_index[v];
            if (idx == -1) return;
            int pv = b_prev[v];
            int nv = b_next[v];
            if (pv != -1) b_next[pv] = nv;
            else b_head[idx] = nv;
            if (nv != -1) b_prev[nv] = pv;
            b_prev[v] = b_next[v] = -1;
            b_index[v] = -1;
        };

        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        for (int v : order) addToBucket(v);

        int curMax = bucketTotal - 1;
        while (curMax >= 0 && b_head[curMax] == -1) curMax--;

        vector<int> seqV; seqV.reserve(n);
        vector<int> seqG; seqG.reserve(n);

        for (int step = 0; step < n; ++step) {
            while (curMax >= 0 && b_head[curMax] == -1) curMax--;
            if (curMax < 0) break;

            int v = b_head[curMax];
            removeFromBucket(v);
            locked[v] = 1;

            int g = gain[v];
            seqV.push_back(v);
            seqG.push_back(g);

            int sv_before = s[v];
            for (int w : adj[v]) {
                if (!locked[w]) {
                    removeFromBucket(w);
                    if (s[w] == sv_before) {
                        degOpp[w] += 1;
                        gain[w] -= 2;
                    } else {
                        degOpp[w] -= 1;
                        gain[w] += 2;
                    }
                    addToBucket(w);
                    int idxNew = b_index[w];
                    if (idxNew > curMax) curMax = idxNew;
                }
            }
            s[v] ^= 1;
        }

        long long cum = 0, bestSum = 0;
        int bestK = -1;
        for (int i = 0; i < (int)seqG.size(); ++i) {
            cum += seqG[i];
            if (cum > bestSum) {
                bestSum = cum;
                bestK = i;
            }
        }

        if (bestK == -1) {
            for (int i = (int)seqV.size() - 1; i >= 0; --i) s[seqV[i]] ^= 1;
            return false;
        } else {
            for (int i = (int)seqV.size() - 1; i > bestK; --i) s[seqV[i]] ^= 1;
            return true;
        }
    }

    vector<int> solve_with_time(double time_limit_seconds) {
        vector<int> bestS(n, 0);
        long long bestC = -1;

        auto start = chrono::high_resolution_clock::now();
        auto elapsed = [&]() {
            auto now = chrono::high_resolution_clock::now();
            chrono::duration<double> diff = now - start;
            return diff.count();
        };

        // First try greedy initial
        vector<int> s = initial_greedy();
        while (elapsed() < time_limit_seconds * 0.98) {
            bool improved = fm_pass(s);
            if (!improved) break;
        }
        long long cut = cut_value(s);
        if (cut > bestC) {
            bestC = cut;
            bestS = s;
        }

        // Random restarts
        uniform_int_distribution<int> bit(0, 1);
        while (elapsed() < time_limit_seconds * 0.98) {
            vector<int> sr(n);
            for (int i = 0; i < n; ++i) sr[i] = bit(rng);
            while (elapsed() < time_limit_seconds * 0.98) {
                bool improved = fm_pass(sr);
                if (!improved) break;
            }
            long long c = cut_value(sr);
            if (c > bestC) {
                bestC = c;
                bestS = sr;
            }
        }
        return bestS;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    MaxCutSolver solver(n, m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        solver.add_edge(u, v);
    }

    vector<int> ans;
    if (m == 0) {
        ans.assign(n, 0);
    } else {
        // Use a conservative time budget; if judge has a fixed limit, this should be safe.
        double time_limit_seconds = 1.8;
        ans = solver.solve_with_time(time_limit_seconds);
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << '\n';
    return 0;
}