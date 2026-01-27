#include <bits/stdc++.h>
using namespace std;

struct Key {
    int deg;
    uint32_t tie;
    int v;
};
struct Cmp {
    bool operator()(const Key& a, const Key& b) const {
        if (a.deg != b.deg) return a.deg > b.deg;
        return a.tie > b.tie;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<pair<int,int>> edges;
    edges.reserve(M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (u > v) swap(u, v);
        edges.emplace_back(u, v);
    }
    sort(edges.begin(), edges.end());
    edges.erase(unique(edges.begin(), edges.end()), edges.end());
    
    vector<int> degCount(N, 0);
    for (auto &e : edges) {
        degCount[e.first]++;
        degCount[e.second]++;
    }
    vector<vector<int>> adj(N);
    for (int i = 0; i < N; ++i) adj[i].reserve(degCount[i]);
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    edges.clear();
    edges.shrink_to_fit();
    
    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    
    auto runMIS = [&](vector<char>& inSetOut) {
        vector<int> degActive(N);
        vector<char> active(N, 1);
        inSetOut.assign(N, 0);
        for (int i = 0; i < N; ++i) degActive[i] = (int)adj[i].size();
        priority_queue<Key, vector<Key>, Cmp> pq;
        pq = priority_queue<Key, vector<Key>, Cmp>();
        for (int i = 0; i < N; ++i) {
            pq.push({degActive[i], rng(), i});
        }
        int activeCount = N;
        auto removeVertex = [&](int x, bool selectFlag) {
            if (!active[x]) return;
            active[x] = 0;
            if (selectFlag) inSetOut[x] = 1;
            activeCount--;
            for (int y : adj[x]) {
                if (active[y]) {
                    degActive[y]--;
                    pq.push({degActive[y], rng(), y});
                }
            }
        };
        while (activeCount > 0 && !pq.empty()) {
            Key k = pq.top(); pq.pop();
            int v = k.v;
            if (!active[v]) continue;
            if (k.deg != degActive[v]) continue;
            // Select v
            removeVertex(v, true);
            for (int u : adj[v]) {
                if (active[u]) removeVertex(u, false);
            }
        }
        int K = 0;
        for (int i = 0; i < N; ++i) if (inSetOut[i]) K++;
        return K;
    };
    
    auto improve12 = [&](vector<char>& inSet) {
        // One pass of 1-2 exchange improvements
        vector<int> sdeg(N, 0);
        for (int v = 0; v < N; ++v) {
            if (!inSet[v]) {
                int cnt = 0;
                for (int u : adj[v]) if (inSet[u]) cnt++;
                sdeg[v] = cnt;
            }
        }
        vector<char> mark(N, 0);
        vector<int> marked;
        for (int w = 0; w < N; ++w) {
            if (!inSet[w]) continue;
            // Collect neighbors of w that are non-selected and have sdeg==1
            vector<int> L;
            L.reserve(adj[w].size());
            for (int u : adj[w]) {
                if (!inSet[u] && sdeg[u] == 1) L.push_back(u);
            }
            if ((int)L.size() < 2) continue;
            // Try a few candidates for a
            int tries = min<int>(5, (int)L.size());
            // We'll pick first tries elements; optionally randomize a bit
            if ((int)L.size() > tries) {
                // partial shuffle
                for (int i = 0; i < tries; ++i) {
                    int j = i + (int)(rng() % (L.size() - i));
                    swap(L[i], L[j]);
                }
            }
            bool improved = false;
            for (int i = 0; i < tries && !improved; ++i) {
                int a = L[i];
                // mark neighbors of a (and a itself)
                mark[a] = 1; marked.push_back(a);
                for (int t : adj[a]) {
                    if (!mark[t]) { mark[t] = 1; marked.push_back(t); }
                }
                int b = -1;
                for (int j = 0; j < (int)L.size(); ++j) {
                    if (L[j] == a) continue;
                    if (!mark[L[j]]) { b = L[j]; break; }
                }
                // clear marks
                for (int t : marked) mark[t] = 0;
                marked.clear();
                if (b != -1) {
                    // perform exchange: remove w, add a and b
                    inSet[w] = 0;
                    for (int t : adj[w]) if (!inSet[t]) sdeg[t]--;
                    inSet[a] = 1;
                    for (int t : adj[a]) if (!inSet[t]) sdeg[t]++;
                    inSet[b] = 1;
                    for (int t : adj[b]) if (!inSet[t]) sdeg[t]++;
                    improved = true;
                }
            }
        }
    };
    
    vector<char> bestSet(N, 0), curSet(N, 0);
    int bestK = runMIS(curSet);
    bestSet = curSet;
    improve12(bestSet);
    bestK = 0;
    for (int i = 0; i < N; ++i) if (bestSet[i]) bestK++;
    
    for (int i = 0; i < N; ++i) {
        cout << (bestSet[i] ? 1 : 0) << '\n';
    }
    return 0;
}