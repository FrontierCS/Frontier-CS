#include <bits/stdc++.h>
using namespace std;

using ll = long long;
using ull = unsigned long long;

// Global distance cache: pair (min(u,v), max(u,v)) -> distance
static unordered_map<ull, ll> distCache;

// Edge set to avoid duplicates
static unordered_set<ull> edgeSet;
static vector<tuple<int,int,ll>> edges;

static int n;

// Pack a pair (u,v) with u < v into 64-bit key
inline ull packKey(int u, int v) {
    if (u > v) swap(u, v);
    return ( (ull)u << 32 ) | (ull)v;
}

ll getDist(int u, int v) {
    if (u == v) return 0;
    ull key = packKey(u, v);
    auto it = distCache.find(key);
    if (it != distCache.end()) return it->second;
    cout << "? " << u << " " << v << endl;
    cout.flush();
    ll ans;
    if (!(cin >> ans)) {
        // In case of input failure, exit gracefully
        exit(0);
    }
    distCache.emplace(key, ans);
    return ans;
}

inline void setCachedDist(int u, int v, ll d) {
    if (u == v) return;
    ull key = packKey(u, v);
    distCache.emplace(key, d);
}

inline void addEdge(int u, int v, ll w) {
    if (u == v) return;
    ull key = packKey(u, v);
    if (edgeSet.find(key) == edgeSet.end()) {
        edgeSet.insert(key);
        edges.emplace_back(u, v, w);
    }
}

void solveGroup(const vector<int>& S, int a) {
    if (S.size() <= 1) return;

    // Compute distances from anchor a to all in S (should be cached)
    ll maxd = -1;
    int b = a;
    vector<ll> da(S.size());
    for (size_t i = 0; i < S.size(); ++i) {
        ll d = getDist(a, S[i]);
        da[i] = d;
        if (d > maxd) {
            maxd = d;
            b = S[i];
        }
    }
    if ((int)S.size() == 2) {
        // Directly connect them
        int u = S[0], v = S[1];
        ll w = getDist(u, v);
        addEdge(u, v, w);
        return;
    }

    // Distances from b to all in S (query/cached)
    vector<ll> db(S.size());
    for (size_t i = 0; i < S.size(); ++i) {
        db[i] = getDist(b, S[i]);
    }

    ll D = getDist(a, b);

    // Identify on-path nodes and partition others by projection
    vector<pair<ll,int>> pathNodes; // (pos = da[v], v) for z=0
    pathNodes.reserve(S.size());

    // Map from path position (pos) to vertex id
    unordered_map<ll,int> pos2node;
    pos2node.reserve(S.size() * 2);

    // Groups attached to a path node (keyed by path node id)
    unordered_map<int, vector<int>> groups;

    for (size_t i = 0; i < S.size(); ++i) {
        ll z2 = da[i] + db[i] - D;
        // z = z2 / 2, guaranteed integer in tree metrics
        ll z = z2 / 2;
        if (z == 0) {
            ll pos = da[i]; // distance from a along the path
            pathNodes.emplace_back(pos, S[i]);
        }
    }

    sort(pathNodes.begin(), pathNodes.end());
    pos2node.reserve(pathNodes.size()*2 + 1);
    for (auto &p : pathNodes) {
        pos2node[p.first] = p.second;
    }

    // Add edges along the path between a and b
    for (size_t i = 1; i < pathNodes.size(); ++i) {
        int u = pathNodes[i-1].second;
        int v = pathNodes[i].second;
        ll w = pathNodes[i].first - pathNodes[i-1].first; // difference in pos equals edge weight
        addEdge(u, v, w);
    }

    // Now group off-path nodes and set cached distances from projection node
    for (size_t i = 0; i < S.size(); ++i) {
        ll z2 = da[i] + db[i] - D;
        ll z = z2 / 2;
        if (z > 0) {
            ll pos = da[i] - z;
            auto it = pos2node.find(pos);
            if (it == pos2node.end()) {
                // Should not happen in a valid tree
                continue;
            }
            int proj = it->second;
            groups[proj].push_back(S[i]);
            // Cache distance from proj to this node as z
            setCachedDist(proj, S[i], z);
        }
    }

    // Recurse on each group with anchor at the projection node
    for (auto &kv : groups) {
        int proj = kv.first;
        vector<int> sub;
        sub.reserve(kv.second.size() + 1);
        sub.push_back(proj);
        for (int v : kv.second) sub.push_back(v);
        solveGroup(sub, proj);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        if (!(cin >> n)) return 0;

        distCache.clear();
        distCache.reserve(1 << 20);
        edgeSet.clear();
        edgeSet.reserve((size_t)max(1, n - 1) * 2);
        edges.clear();
        edges.reserve(max(1, n - 1));

        if (n <= 1) {
            cout << "!" << endl;
            cout.flush();
            continue;
        }

        int s = 1;
        // Query distances from s to all
        vector<int> allNodes(n);
        for (int i = 0; i < n; ++i) allNodes[i] = i + 1;
        for (int i = 2; i <= n; ++i) {
            getDist(s, i);
        }

        // Start recursive decomposition from anchor s over all nodes
        solveGroup(allNodes, s);

        // Output the edges
        cout << "!";
        for (auto &e : edges) {
            int u, v; ll w;
            tie(u, v, w) = e;
            cout << " " << u << " " << v << " " << w;
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}