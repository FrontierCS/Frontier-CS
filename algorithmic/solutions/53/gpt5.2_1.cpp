#include <bits/stdc++.h>
using namespace std;

struct RoundInfo {
    int n;
    vector<int> order; // 0-indexed values 1..n
    vector<int> pos;   // pos[v] in [0..n-1]
    vector<int> bit;   // bit[u] in {0,1}, u in [1..n]
};

struct HopcroftKarp {
    int nL, nR;
    const vector<vector<int>>* adj;
    int banU = -1, banV = -1;

    vector<int> dist, matchL, matchR;

    HopcroftKarp(int nL_, int nR_, const vector<vector<int>>* adj_) : nL(nL_), nR(nR_), adj(adj_) {
        dist.assign(nL + 1, 0);
        matchL.assign(nL + 1, 0);
        matchR.assign(nR + 1, 0);
    }

    bool bfs() {
        queue<int> q;
        const int INF = 1e9;
        for (int u = 1; u <= nL; u++) {
            if (matchL[u] == 0) {
                dist[u] = 0;
                q.push(u);
            } else dist[u] = INF;
        }
        bool found = false;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : (*adj)[u]) {
                if (u == banU && v == banV) continue;
                int u2 = matchR[v];
                if (u2 == 0) {
                    found = true;
                } else if (dist[u2] == INF) {
                    dist[u2] = dist[u] + 1;
                    q.push(u2);
                }
            }
        }
        return found;
    }

    bool dfs(int u) {
        const int INF = 1e9;
        for (int v : (*adj)[u]) {
            if (u == banU && v == banV) continue;
            int u2 = matchR[v];
            if (u2 == 0 || (dist[u2] == dist[u] + 1 && dfs(u2))) {
                matchL[u] = v;
                matchR[v] = u;
                return true;
            }
        }
        dist[u] = INF;
        return false;
    }

    int maxMatching() {
        fill(matchL.begin(), matchL.end(), 0);
        fill(matchR.begin(), matchR.end(), 0);
        int matching = 0;
        while (bfs()) {
            for (int u = 1; u <= nL; u++) {
                if (matchL[u] == 0 && dfs(u)) matching++;
            }
        }
        return matching;
    }
};

static inline int readInt() {
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    while (t--) {
        int n = readInt();

        int k = n / 2 + 1;
        if (k <= 1) k = 2;
        if (k >= n) k = n - 1;
        int L = n - k; // successors window size

        cout << k << "\n" << flush;

        int maxQueries = 10 * n;
        int queryCount = 0;

        vector<RoundInfo> rounds;

        auto do_query = [&](const vector<int>& q) -> int {
            cout << "?";
            for (int i = 0; i < n; i++) cout << " " << q[i];
            cout << "\n" << flush;
            queryCount++;
            return readInt();
        };

        auto buildCandidatesAdj = [&]() -> vector<vector<int>> {
            vector<vector<int>> adj(n + 1);
            for (int u = 1; u <= n; u++) {
                for (int v = 1; v <= n; v++) {
                    if (v == u) continue;
                    bool ok = true;
                    for (const auto& rd : rounds) {
                        int duv = (rd.pos[v] - rd.pos[u] + n) % n;
                        int pred = (duv != 0 && duv <= L) ? 1 : 0;
                        if (pred != rd.bit[u]) { ok = false; break; }
                    }
                    if (ok) adj[u].push_back(v);
                }
            }
            return adj;
        };

        auto solveIfUnique = [&]() -> optional<vector<int>> {
            if (rounds.empty()) return nullopt;

            vector<vector<int>> adj = buildCandidatesAdj();
            for (int u = 1; u <= n; u++) if (adj[u].empty()) return nullopt;

            HopcroftKarp hk(n, n, &adj);
            int msize = hk.maxMatching();
            if (msize != n) return nullopt;

            vector<int> p(n + 1);
            for (int u = 1; u <= n; u++) p[u] = hk.matchL[u];

            bool allSingle = true;
            for (int u = 1; u <= n; u++) if ((int)adj[u].size() != 1) { allSingle = false; break; }
            if (allSingle) return p;

            // uniqueness test: if removing any matched edge still allows perfect matching, not unique
            for (int u = 1; u <= n; u++) {
                int v = p[u];
                HopcroftKarp hk2(n, n, &adj);
                hk2.banU = u;
                hk2.banV = v;
                int m2 = hk2.maxMatching();
                if (m2 == n) return nullopt;
            }
            return p;
        };

        int attempts = 0;
        while (queryCount + n <= maxQueries && attempts < 10) {
            attempts++;

            vector<int> order(n);
            iota(order.begin(), order.end(), 1);

            if (attempts == 1) {
                // identity
            } else if (attempts == 2) {
                reverse(order.begin(), order.end());
            } else {
                shuffle(order.begin(), order.end(), rng);
            }

            vector<int> ans(n);
            for (int s = 0; s < n; s++) {
                vector<int> q(n);
                for (int i = 0; i < n; i++) q[i] = order[(s + i) % n];
                ans[s] = do_query(q);
            }

            int mn = *min_element(ans.begin(), ans.end());
            int mx = *max_element(ans.begin(), ans.end());

            if (mx == mn) {
                // ambiguous (all excluded edges same), discard this attempt
                continue;
            }
            if (mx - mn != 1) {
                // should not happen; discard
                continue;
            }

            RoundInfo rd;
            rd.n = n;
            rd.order = order;
            rd.pos.assign(n + 1, -1);
            for (int i = 0; i < n; i++) rd.pos[order[i]] = i;
            rd.bit.assign(n + 1, 0);

            int F = mx;
            for (int s = 0; s < n; s++) {
                int b = F - ans[s]; // 0 or 1
                if (b < 0 || b > 1) { b = 0; } // safety
                int excl = order[(s + (k - 1)) % n]; // q_k
                rd.bit[excl] = b;
            }

            rounds.push_back(std::move(rd));

            auto sol = solveIfUnique();
            if (sol.has_value()) {
                const auto& p = sol.value();
                cout << "!";
                for (int i = 1; i <= n; i++) cout << " " << p[i];
                cout << "\n" << flush;
                goto next_case;
            }
        }

        // Fallback: output any perfect matching from current constraints (if possible), else a simple derangement
        {
            vector<int> p(n + 1, 0);
            if (!rounds.empty()) {
                vector<vector<int>> adj = buildCandidatesAdj();
                HopcroftKarp hk(n, n, &adj);
                int msize = hk.maxMatching();
                if (msize == n) {
                    for (int u = 1; u <= n; u++) p[u] = hk.matchL[u];
                    cout << "!";
                    for (int i = 1; i <= n; i++) cout << " " << p[i];
                    cout << "\n" << flush;
                } else {
                    // simple cycle derangement
                    cout << "!";
                    for (int i = 1; i <= n; i++) {
                        int v = (i % n) + 1;
                        cout << " " << v;
                    }
                    cout << "\n" << flush;
                }
            } else {
                cout << "!";
                for (int i = 1; i <= n; i++) {
                    int v = (i % n) + 1;
                    cout << " " << v;
                }
                cout << "\n" << flush;
            }
        }

    next_case:
        continue;
    }

    return 0;
}