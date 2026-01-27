#include <bits/stdc++.h>
using namespace std;

static inline vector<char> greedy_cover_bucket(const vector<vector<int>>& adj, const vector<int>& deg) {
    int n = (int)adj.size() - 1;
    vector<int> remdeg = deg;
    vector<char> inS(n + 1, 0);

    int maxDeg = 0;
    for (int i = 1; i <= n; ++i) maxDeg = max(maxDeg, remdeg[i]);

    vector<vector<int>> buckets(maxDeg + 1);
    buckets.reserve(maxDeg + 1);
    for (int i = 1; i <= n; ++i) {
        buckets[remdeg[i]].push_back(i);
    }

    int curMax = maxDeg;
    while (curMax > 0) {
        while (curMax > 0 && buckets[curMax].empty()) --curMax;
        if (curMax == 0) break;
        int v = buckets[curMax].back();
        buckets[curMax].pop_back();
        if (inS[v]) continue;
        if (remdeg[v] != curMax) continue;

        inS[v] = 1;
        for (int u : adj[v]) {
            if (!inS[u]) {
                if (remdeg[u] > 0) {
                    --remdeg[u];
                    buckets[remdeg[u]].push_back(u);
                }
            }
        }
        remdeg[v] = 0;
    }
    return inS;
}

static inline vector<char> matching_cover(const vector<pair<int,int>>& edges, int n) {
    vector<char> matched(n + 1, 0), inS(n + 1, 0);
    for (const auto &e : edges) {
        int u = e.first, v = e.second;
        if (!matched[u] && !matched[v]) {
            matched[u] = matched[v] = 1;
            inS[u] = inS[v] = 1;
        }
    }
    return inS;
}

static inline void prune_cover(vector<char>& inS, const vector<vector<int>>& adj) {
    int n = (int)adj.size() - 1;
    vector<int> cand;
    cand.reserve(n);
    for (int v = 1; v <= n; ++v) {
        if (inS[v]) {
            bool allIn = true;
            for (int u : adj[v]) {
                if (!inS[u]) { allIn = false; break; }
            }
            if (allIn) cand.push_back(v);
        }
    }
    while (!cand.empty()) {
        int v = cand.back(); cand.pop_back();
        if (!inS[v]) continue;
        bool allIn = true;
        for (int u : adj[v]) {
            if (!inS[u]) { allIn = false; break; }
        }
        if (allIn) inS[v] = 0;
    }
}

static inline bool check_cover(const vector<char>& inS, const vector<pair<int,int>>& edges) {
    for (const auto &e : edges) {
        int u = e.first, v = e.second;
        if (!inS[u] && !inS[v]) return false;
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    vector<pair<int,int>> edges;
    edges.reserve(M);
    vector<int> deg(N + 1, 0);
    edges.reserve(M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        edges.emplace_back(u, v);
        ++deg[u];
        ++deg[v];
    }
    vector<vector<int>> adj(N + 1);
    for (int i = 1; i <= N; ++i) adj[i].reserve(deg[i]);
    for (const auto &e : edges) {
        int u = e.first, v = e.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<char> bestS;
    int bestK = INT_MAX;

    // Greedy degree-based cover + prune
    {
        vector<char> s1 = greedy_cover_bucket(adj, deg);
        prune_cover(s1, adj);
        if (!check_cover(s1, edges)) {
            // fallback safety: mark all to ensure validity
            fill(s1.begin(), s1.end(), 1);
        }
        int K1 = 0;
        for (int i = 1; i <= N; ++i) if (s1[i]) ++K1;
        bestS = s1;
        bestK = K1;
    }
    // Maximal matching cover + prune
    {
        vector<char> s2 = matching_cover(edges, N);
        prune_cover(s2, adj);
        if (!check_cover(s2, edges)) {
            fill(s2.begin(), s2.end(), 1);
        }
        int K2 = 0;
        for (int i = 1; i <= N; ++i) if (s2[i]) ++K2;
        if (K2 < bestK) {
            bestK = K2;
            bestS = move(s2);
        }
    }

    // Ensure we have a valid solution
    if (bestS.empty()) {
        bestS.assign(N + 1, 1);
    }

    for (int i = 1; i <= N; ++i) {
        cout << (bestS[i] ? 1 : 0) << '\n';
    }
    return 0;
}