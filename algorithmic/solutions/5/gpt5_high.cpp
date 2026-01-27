#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct RNG {
    uint64_t x;
    RNG() {
        uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
        x = splitmix64(seed);
    }
    uint64_t next() { return x = splitmix64(x); }
    template<class It>
    void shuffle(It first, It last) {
        size_t n = last - first;
        for (size_t i = n - 1; i > 0; --i) {
            size_t j = (size_t)(next() % (i + 1));
            swap(*(first + i), *(first + j));
        }
    }
};
RNG rng;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<int> a(10);
    for (int i = 0; i < 10; ++i) cin >> a[i];

    vector<vector<int>> out(n + 1), in(n + 1);
    out.reserve(n + 1);
    in.reserve(n + 1);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        out[u].push_back(v);
        in[v].push_back(u);
    }

    // Sort out adjacency lists for binary_search checks
    for (int u = 1; u <= n; ++u) {
        sort(out[u].begin(), out[u].end());
    }

    vector<int> degOut(n + 1), degIn(n + 1);
    for (int u = 1; u <= n; ++u) {
        degOut[u] = (int)out[u].size();
        degIn[u] = (int)in[u].size();
    }

    vector<int> order(n);
    for (int i = 0; i < n; ++i) order[i] = i + 1;
    vector<int> pos(n + 1, 0);
    vector<int> dp(n + 1), par(n + 1);

    auto runDPWithOrder = [&](const vector<int>& ord, vector<int>& pathOut) {
        for (int i = 0; i < n; ++i) pos[ord[i]] = i;
        for (int i = 1; i <= n; ++i) {
            dp[i] = 1;
            par[i] = 0;
        }
        for (int i = 0; i < n; ++i) {
            int v = ord[i];
            int dv = dp[v];
            const auto& nbrs = out[v];
            for (int w : nbrs) {
                if (pos[w] > i) {
                    if (dv + 1 > dp[w]) {
                        dp[w] = dv + 1;
                        par[w] = v;
                    }
                }
            }
        }
        int bestV = 1, bestLen = dp[1];
        for (int v = 2; v <= n; ++v) {
            if (dp[v] > bestLen) {
                bestLen = dp[v];
                bestV = v;
            }
        }
        pathOut.clear();
        pathOut.reserve(bestLen);
        int cur = bestV;
        while (cur != 0) {
            pathOut.push_back(cur);
            cur = par[cur];
        }
        reverse(pathOut.begin(), pathOut.end());
        return bestLen;
    };

    vector<int> bestPath, tmpPath;

    // Decide number of DP iterations based on input size
    long long budget = 15000000LL; // approx edges processed
    long long sizeSum = (long long)n + (long long)m;
    int T = (int)min(50LL, max(2LL, budget / max(1LL, sizeSum)) + 2LL);

    for (int iter = 0; iter < T; ++iter) {
        if (iter == 0) {
            sort(order.begin(), order.end(), [&](int x, int y) {
                int a = degOut[x] - degIn[x];
                int b = degOut[y] - degIn[y];
                if (a != b) return a > b;
                return x < y;
            });
        } else if (iter == 1) {
            sort(order.begin(), order.end(), [&](int x, int y) {
                if (degOut[x] != degOut[y]) return degOut[x] > degOut[y];
                return x < y;
            });
        } else {
            rng.shuffle(order.begin(), order.end());
        }
        int len = runDPWithOrder(order, tmpPath);
        if ((int)bestPath.size() < len) {
            bestPath = tmpPath;
            if ((int)bestPath.size() == n) break;
        }
    }

    if (bestPath.empty()) {
        // Fallback: pick any edge or vertex
        if (n >= 1) {
            // try to find any edge
            bool found = false;
            for (int u = 1; u <= n && !found; ++u) {
                for (int v : out[u]) {
                    bestPath = {u, v};
                    found = true;
                    break;
                }
            }
            if (!found) bestPath = {1};
        }
    }

    // Greedy extension at both ends
    auto extendEnds = [&](vector<int>& path) {
        vector<char> inPath(n + 1, 0);
        for (int v : path) inPath[v] = 1;
        deque<int> dq;
        for (int v : path) dq.push_back(v);
        while (true) {
            bool progressed = false;
            // forward as much as possible
            while (true) {
                int t = dq.back();
                bool found = false;
                const auto& nb = out[t];
                for (int w : nb) {
                    if (!inPath[w]) {
                        inPath[w] = 1;
                        dq.push_back(w);
                        found = true;
                        break;
                    }
                }
                if (!found) break;
                progressed = true;
                if ((int)dq.size() == n) break;
            }
            if ((int)dq.size() == n) break;
            // backward as much as possible
            while (true) {
                int h = dq.front();
                bool found = false;
                const auto& nb = in[h];
                for (int u : nb) {
                    if (!inPath[u]) {
                        inPath[u] = 1;
                        dq.push_front(u);
                        found = true;
                        break;
                    }
                }
                if (!found) break;
                progressed = true;
                if ((int)dq.size() == n) break;
            }
            if (!progressed) break;
            if ((int)dq.size() == n) break;
        }
        vector<int> res;
        res.reserve(dq.size());
        for (int v : dq) res.push_back(v);
        path.swap(res);
    };

    extendEnds(bestPath);

    // Insertion between consecutive vertices using queue
    auto hasEdge = [&](int u, int v) -> bool {
        const auto& vec = out[u];
        auto it = lower_bound(vec.begin(), vec.end(), v);
        return it != vec.end() && *it == v;
    };

    auto insertBridging = [&](vector<int>& path) {
        int k = (int)path.size();
        vector<int> next(n + 1, -1), prev(n + 1, -1);
        vector<char> inPath(n + 1, 0);
        if (k == 0) return;
        for (int i = 0; i < k; ++i) inPath[path[i]] = 1;
        for (int i = 0; i + 1 < k; ++i) {
            int u = path[i], v = path[i + 1];
            next[u] = v;
            prev[v] = u;
        }
        int head = path[0], tail = path.back();

        deque<int> q;
        vector<char> inQ(n + 1, 0);
        for (int i = 0; i + 1 < k; ++i) {
            int u = path[i];
            if (!inQ[u]) { q.push_back(u); inQ[u] = 1; }
        }

        while (!q.empty()) {
            int p = q.front(); q.pop_front(); inQ[p] = 0;
            int w = next[p];
            if (w == -1) continue;
            bool insertedAny = false;
            const auto& nbrs = out[p];
            for (int x : nbrs) {
                if (inPath[x]) continue;
                int curSucc = next[p];
                if (curSucc == -1) break;
                if (hasEdge(x, curSucc)) {
                    // insert x between p and curSucc
                    next[p] = x;
                    prev[x] = p;
                    next[x] = curSucc;
                    prev[curSucc] = x;
                    inPath[x] = 1;
                    insertedAny = true;

                    if (!inQ[x] && next[x] != -1) { q.push_back(x); inQ[x] = 1; }
                }
            }
            if (insertedAny && next[p] != -1 && !inQ[p]) { q.push_back(p); inQ[p] = 1; }
        }

        // Reconstruct path
        vector<int> res;
        res.reserve(n);
        int cur = head;
        while (cur != -1) {
            res.push_back(cur);
            cur = next[cur];
        }
        path.swap(res);
    };

    insertBridging(bestPath);
    if ((int)bestPath.size() < n) {
        extendEnds(bestPath);
        insertBridging(bestPath);
    }

    // Final refinement: run DP with order starting from current path then the rest randomized
    if ((int)bestPath.size() < n) {
        vector<char> used(n + 1, 0);
        for (int v : bestPath) used[v] = 1;
        vector<int> rest;
        rest.reserve(n - bestPath.size());
        for (int v = 1; v <= n; ++v) if (!used[v]) rest.push_back(v);
        if (!rest.empty()) rng.shuffle(rest.begin(), rest.end());
        vector<int> ordFinal;
        ordFinal.reserve(n);
        ordFinal.insert(ordFinal.end(), bestPath.begin(), bestPath.end());
        ordFinal.insert(ordFinal.end(), rest.begin(), rest.end());

        vector<int> trialPath;
        int len = runDPWithOrder(ordFinal, trialPath);
        if (len > (int)bestPath.size()) bestPath = trialPath;

        // and a reverse-ordered attempt
        reverse(ordFinal.begin(), ordFinal.end());
        len = runDPWithOrder(ordFinal, trialPath);
        if (len > (int)bestPath.size()) bestPath = trialPath;

        extendEnds(bestPath);
        insertBridging(bestPath);
        extendEnds(bestPath);
    }

    // Output
    cout << bestPath.size() << "\n";
    for (size_t i = 0; i < bestPath.size(); ++i) {
        if (i) cout << ' ';
        cout << bestPath[i];
    }
    cout << "\n";
    return 0;
}