#include <bits/stdc++.h>
using namespace std;

static inline uint64_t now64() {
    return chrono::steady_clock::now().time_since_epoch().count();
}

vector<vector<int>> buildAdjUnique(int N, const vector<pair<int,int>>& edges) {
    vector<vector<int>> adj(N);
    adj.reserve(N);
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    for (int i = 0; i < N; ++i) {
        auto &a = adj[i];
        sort(a.begin(), a.end());
        a.erase(unique(a.begin(), a.end()), a.end());
    }
    return adj;
}

pair<vector<char>, vector<char>> degree1Reduction(const vector<vector<int>>& adj) {
    int N = (int)adj.size();
    vector<int> deg(N);
    vector<char> alive(N, 1), forced(N, 0);
    deque<int> q;
    for (int i = 0; i < N; ++i) {
        deg[i] = (int)adj[i].size();
        if (deg[i] == 1) q.push_back(i);
    }
    while (!q.empty()) {
        int u = q.front(); q.pop_front();
        if (!alive[u]) continue;
        if (deg[u] != 1) continue;
        int v = -1;
        for (int w : adj[u]) {
            if (alive[w]) { v = w; break; }
        }
        if (v == -1) continue;
        if (!alive[v]) continue;
        forced[v] = 1;
        if (alive[v]) {
            alive[v] = 0;
            for (int w : adj[v]) {
                if (alive[w]) {
                    deg[w]--;
                    if (deg[w] == 1) q.push_back(w);
                }
            }
        }
    }
    return {forced, alive};
}

vector<char> refineCover(const vector<vector<int>>& adj, vector<char> selected, mt19937 &rng) {
    int N = (int)adj.size();
    vector<int> unselCnt(N, 0);
    for (int v = 0; v < N; ++v) {
        int cnt = 0;
        for (int u : adj[v]) if (!selected[u]) cnt++;
        unselCnt[v] = cnt;
    }
    // Step 1: remove vertices whose all neighbors are selected
    deque<int> dq;
    for (int v = 0; v < N; ++v) {
        if (selected[v] && unselCnt[v] == 0) dq.push_back(v);
    }
    while (!dq.empty()) {
        int v = dq.front(); dq.pop_front();
        if (!selected[v]) continue;
        if (unselCnt[v] != 0) continue;
        selected[v] = 0;
        for (int w : adj[v]) {
            if (selected[w]) {
                unselCnt[w]++; // v turned to unselected neighbor for w
            }
        }
    }
    // Step 2: one-pass 1-swap improvement
    vector<int> cand;
    cand.reserve(N);
    for (int v = 0; v < N; ++v) if (selected[v] && unselCnt[v] == 1) cand.push_back(v);
    shuffle(cand.begin(), cand.end(), rng);
    for (int v : cand) {
        if (!(selected[v] && unselCnt[v] == 1)) continue;
        int u = -1;
        for (int w : adj[v]) if (!selected[w]) { u = w; break; }
        if (u == -1) continue;
        // select u
        selected[u] = 1;
        for (int x : adj[u]) {
            if (selected[x]) {
                unselCnt[x]--;
            }
        }
        // unselect v
        selected[v] = 0;
        for (int x : adj[v]) {
            if (selected[x]) {
                unselCnt[x]++; // v becomes unselected neighbor
            }
        }
        // remove any newly removable vertices due to selecting u
        deque<int> q2;
        for (int x : adj[u]) {
            if (selected[x] && unselCnt[x] == 0) q2.push_back(x);
        }
        while (!q2.empty()) {
            int s = q2.front(); q2.pop_front();
            if (!selected[s] || unselCnt[s] != 0) continue;
            selected[s] = 0;
            for (int t : adj[s]) {
                if (selected[t]) {
                    unselCnt[t]++; // removing s increases unselCnt of its selected neighbors
                }
            }
        }
    }
    // Step 3: final prune if any new zero-count after swaps (rare but safe)
    for (int v = 0; v < N; ++v) {
        if (selected[v] && unselCnt[v] == 0) dq.push_back(v);
    }
    while (!dq.empty()) {
        int v = dq.front(); dq.pop_front();
        if (!selected[v]) continue;
        if (unselCnt[v] != 0) continue;
        selected[v] = 0;
        for (int w : adj[v]) {
            if (selected[w]) {
                unselCnt[w]++;
            }
        }
    }
    return selected;
}

vector<char> coverFromMatchingWithReductions(
    int N,
    const vector<pair<int,int>>& edges,
    const vector<vector<int>>& adj,
    mt19937 &rng,
    int tries = 10
) {
    auto red = degree1Reduction(adj);
    vector<char> forced = move(red.first);
    vector<char> alive  = move(red.second);
    vector<pair<int,int>> edgesR;
    edgesR.reserve(edges.size());
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        if (alive[u] && alive[v]) edgesR.emplace_back(u, v);
    }
    vector<char> bestSel(N, 0);
    int bestK = INT_MAX;
    // If reduced graph has no edges, we can just use forced
    if (edgesR.empty()) {
        vector<char> selected = forced;
        selected = refineCover(adj, selected, rng);
        int K = 0; for (int i = 0; i < N; ++i) if (selected[i]) K++;
        if (K < bestK) { bestK = K; bestSel = move(selected); }
        return bestSel;
    }
    vector<int> order(edgesR.size());
    iota(order.begin(), order.end(), 0);
    for (int t = 0; t < tries; ++t) {
        shuffle(order.begin(), order.end(), rng);
        vector<char> matched(N, 0);
        for (int idx : order) {
            int u = edgesR[idx].first, v = edgesR[idx].second;
            if (!matched[u] && !matched[v]) {
                matched[u] = matched[v] = 1;
            }
        }
        vector<char> selected(N, 0);
        for (int i = 0; i < N; ++i) selected[i] = (forced[i] || matched[i]) ? 1 : 0;
        selected = refineCover(adj, selected, rng);
        int K = 0; for (int i = 0; i < N; ++i) if (selected[i]) K++;
        if (K < bestK) {
            bestK = K;
            bestSel = move(selected);
        }
    }
    return bestSel;
}

vector<char> coverFromMIS(int N, const vector<vector<int>>& adj, mt19937 &rng) {
    vector<int> deg(N);
    vector<char> removed(N, 0), inMIS(N, 0);
    for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].size();
    struct Node { int deg; uint32_t tie; int v; };
    struct Cmp { bool operator()(const Node &a, const Node &b) const {
        if (a.deg != b.deg) return a.deg > b.deg;
        return a.tie > b.tie;
    }};
    priority_queue<Node, vector<Node>, Cmp> pq;
    vector<uint32_t> tieRand(N);
    for (int i = 0; i < N; ++i) tieRand[i] = rng();
    for (int i = 0; i < N; ++i) pq.push({deg[i], tieRand[i], i});
    while (!pq.empty()) {
        Node cur = pq.top(); pq.pop();
        int v = cur.v;
        if (removed[v]) continue;
        if (cur.deg != deg[v]) continue;
        // add v to MIS
        inMIS[v] = 1;
        removed[v] = 1;
        // remove neighbors
        for (int u : adj[v]) {
            if (removed[u]) continue;
            removed[u] = 1;
            for (int w : adj[u]) {
                if (!removed[w]) {
                    deg[w]--;
                    pq.push({deg[w], tieRand[w], w});
                }
            }
        }
    }
    vector<char> selected(N, 0);
    for (int i = 0; i < N; ++i) selected[i] = inMIS[i] ? 0 : 1;
    return selected;
}

bool checkCover(const vector<pair<int,int>>& edges, const vector<char>& selected) {
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        if (!(selected[u] || selected[v])) return false;
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
    for (int i = 0; i < M; ++i) {
        int u, v; cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        edges.emplace_back(u, v);
    }
    // Build unique adjacency for heuristics
    vector<vector<int>> adj = buildAdjUnique(N, edges);

    mt19937 rng((uint64_t)now64() ^ (uint64_t)(uintptr_t(new int)));

    // Candidate 1: Matching with degree-1 reductions
    vector<char> cand1 = coverFromMatchingWithReductions(N, edges, adj, rng, 10);
    cand1 = refineCover(adj, cand1, rng);

    // Candidate 2: MIS complement
    vector<char> cand2 = coverFromMIS(N, adj, rng);
    cand2 = refineCover(adj, cand2, rng);

    // Choose best valid candidate
    vector<char> best = cand1;
    int bestK = INT_MAX;
    if (checkCover(edges, cand1)) {
        int K = 0; for (int i = 0; i < N; ++i) if (cand1[i]) K++;
        best = cand1; bestK = K;
    }
    if (checkCover(edges, cand2)) {
        int K = 0; for (int i = 0; i < N; ++i) if (cand2[i]) K++;
        if (K < bestK) { best = cand2; bestK = K; }
    }
    // Fallback to a simple greedy maximal matching without reductions if needed
    if (bestK == INT_MAX) {
        vector<int> order(edges.size());
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        vector<char> matched(N, 0), selected(N, 0);
        for (int idx : order) {
            int u = edges[idx].first, v = edges[idx].second;
            if (!matched[u] && !matched[v]) matched[u] = matched[v] = 1;
        }
        for (int i = 0; i < N; ++i) selected[i] = matched[i];
        selected = refineCover(adj, selected, rng);
        if (!checkCover(edges, selected)) {
            // ultimate fallback: select all
            selected.assign(N, 1);
        }
        best = move(selected);
    }

    for (int i = 0; i < N; ++i) {
        cout << (best[i] ? 1 : 0) << '\n';
    }
    return 0;
}