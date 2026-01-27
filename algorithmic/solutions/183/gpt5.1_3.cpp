#include <bits/stdc++.h>
using namespace std;

struct Node {
    int d;
    uint32_t rnd;
    int v;
    int ver;
};

struct Cmp {
    bool operator()(const Node &a, const Node &b) const {
        if (a.d != b.d) return a.d > b.d;      // smaller degree first
        if (a.rnd != b.rnd) return a.rnd > b.rnd;
        return a.v > b.v;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<int>> adj(N + 1);
    adj.reserve(N + 1);

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u < 1 || u > N || v < 1 || v > N || u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count();
    mt19937 rng((uint32_t)seed);

    vector<char> bestSel(N + 1, 0);
    int bestSize = 0;

    // Greedy: dynamic minimum-degree heuristic
    {
        vector<char> alive(N + 1, 1);
        vector<char> selected(N + 1, 0);
        vector<int> deg(N + 1);
        vector<int> ver(N + 1, 0);

        priority_queue<Node, vector<Node>, Cmp> pq;

        for (int v = 1; v <= N; ++v) {
            deg[v] = (int)adj[v].size();
            uint32_t r = rng();
            pq.push({deg[v], r, v, 0});
        }

        int cnt = 0;
        while (!pq.empty()) {
            Node cur = pq.top();
            pq.pop();
            int v = cur.v;
            if (!alive[v]) continue;
            if (cur.ver != ver[v]) continue;

            // Select vertex v into independent set
            alive[v] = 0;
            selected[v] = 1;
            ++cnt;

            // Remove neighbors and update degrees
            for (int u : adj[v]) {
                if (!alive[u]) continue;
                alive[u] = 0;
                for (int w : adj[u]) {
                    if (!alive[w]) continue;
                    --deg[w];
                    ++ver[w];
                    uint32_t r = rng();
                    pq.push({deg[w], r, w, ver[w]});
                }
            }
        }

        bestSize = cnt;
        bestSel = selected;
    }

    // Random-order greedy tries
    long long approx_per_run = (long long)N + (long long)M;
    const long long TARGET_OPS = 30000000LL;
    int tries = (int)(TARGET_OPS / max(1LL, approx_per_run));
    if (tries < 1) tries = 1;
    if (tries > 1000) tries = 1000;

    vector<int> perm(N);
    for (int i = 0; i < N; ++i) perm[i] = i + 1;

    vector<char> selectG(N + 1);
    vector<char> banned(N + 1);

    for (int t = 0; t < tries; ++t) {
        shuffle(perm.begin(), perm.end(), rng);
        fill(selectG.begin(), selectG.end(), 0);
        fill(banned.begin(), banned.end(), 0);
        int cnt = 0;

        for (int idx = 0; idx < N; ++idx) {
            int v = perm[idx];
            if (banned[v]) continue;
            selectG[v] = 1;
            ++cnt;
            for (int u : adj[v]) {
                banned[u] = 1;
            }
        }

        if (cnt > bestSize) {
            bestSize = cnt;
            bestSel = selectG;
        }
    }

    for (int i = 1; i <= N; ++i) {
        cout << (bestSel[i] ? 1 : 0) << '\n';
    }

    return 0;
}