#include <bits/stdc++.h>
using namespace std;

static inline void flush_out() { cout.flush(); }

int ask(int u, int v) {
    if (u == v) return 0;
    cout << "? " << u << " " << v << "\n";
    flush_out();
    int d;
    if (!(cin >> d)) exit(0);
    return d;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Number of beacons to use
    const int K = 5;

    vector<int> beacons;
    beacons.reserve(K);

    // Choose beacons greedily: start with 1
    beacons.push_back(1);

    // Distances from each beacon to all nodes
    vector<vector<int>> D(K, vector<int>(n + 1, 0));
    auto compute_distances = [&](int idx, int b) {
        for (int i = 1; i <= n; ++i) {
            if (i == b) { D[idx][i] = 0; continue; }
            D[idx][i] = ask(b, i);
        }
    };

    // Compute distances for first beacon
    compute_distances(0, beacons[0]);

    // Select remaining beacons
    for (int k = 1; k < K; ++k) {
        int best = 1, bestVal = -1;
        for (int i = 1; i <= n; ++i) {
            bool used = false;
            for (int b : beacons) if (b == i) { used = true; break; }
            if (used) continue;
            int mn = INT_MAX;
            for (int j = 0; j < k; ++j) mn = min(mn, D[j][i]);
            if (mn > bestVal) { bestVal = mn; best = i; }
        }
        beacons.push_back(best);
        compute_distances(k, best);
    }

    // Build signatures for all nodes: array of K distances (to K beacons)
    struct SigNode {
        array<int, K> sig;
        int id;
    };
    vector<SigNode> nodes(n);
    for (int i = 1; i <= n; ++i) {
        SigNode sn;
        for (int k = 0; k < K; ++k) sn.sig[k] = D[k][i];
        sn.id = i;
        nodes[i - 1] = sn;
    }

    auto cmpSig = [](const SigNode &a, const SigNode &b) {
        for (int i = 0; i < K; ++i) {
            if (a.sig[i] != b.sig[i]) return a.sig[i] < b.sig[i];
        }
        return a.id < b.id;
    };
    sort(nodes.begin(), nodes.end(), cmpSig);

    auto equal_range_sig = [&](const array<int, K> &key) -> pair<int,int> {
        // returns [l,r) indices in nodes with signature == key
        auto lb = lower_bound(nodes.begin(), nodes.end(), SigNode{key, 0}, cmpSig);
        auto ub = upper_bound(nodes.begin(), nodes.end(), SigNode{key, INT_MAX}, cmpSig);
        int l = int(lb - nodes.begin());
        int r = int(ub - nodes.begin());
        return {l, r};
    };

    // Build layers by distance to first beacon (root r0)
    int r0 = beacons[0];
    vector<vector<int>> layer;
    int maxD0 = 0;
    for (int i = 1; i <= n; ++i) maxD0 = max(maxD0, D[0][i]);
    layer.assign(maxD0 + 1, {});
    for (int i = 1; i <= n; ++i) layer[D[0][i]].push_back(i);

    vector<int> parent(n + 1, -1);
    parent[r0] = 0; // root has no parent
    vector<vector<int>> g(n + 1);

    // For each node (except root), find parent using beacon signatures
    for (int dist = 1; dist <= maxD0; ++dist) {
        for (int v : layer[dist]) {
            vector<int> cands;
            // Enumerate all sign vectors s for beacons 1..K-1 (2^(K-1) masks), with s0 fixed at -1
            for (int mask = 0; mask < (1 << (K - 1)); ++mask) {
                array<int, K> key;
                bool ok = true;
                for (int b = 0; b < K; ++b) {
                    int val = D[b][v] + (b == 0 ? -1 : ((mask & (1 << (b - 1))) ? +1 : -1));
                    if (val < 0) { ok = false; break; }
                    key[b] = val;
                }
                if (!ok) continue;
                auto range = equal_range_sig(key);
                for (int i = range.first; i < range.second; ++i) {
                    int u = nodes[i].id;
                    if (D[0][u] != dist - 1) continue; // ensure in previous layer
                    cands.push_back(u);
                }
            }
            if (cands.empty()) {
                // Fallback: scan previous layer searching for the true parent by querying
                // This should be rare with well-chosen beacons
                bool found = false;
                for (int u : layer[dist - 1]) {
                    int dv = ask(u, v);
                    if (dv == 1) {
                        parent[v] = u;
                        g[u].push_back(v);
                        g[v].push_back(u);
                        found = true;
                        break;
                    }
                }
                if (!found) {
                    // As a very unlikely fallback, connect to r0's neighbor if anything goes wrong
                    // but try exhaustive scan all nodes (extremely unlikely path)
                    for (int u = 1; u <= n && !found; ++u) if (u != v) {
                        int dv = ask(u, v);
                        if (dv == 1) {
                            parent[v] = u;
                            g[u].push_back(v);
                            g[v].push_back(u);
                            found = true;
                            break;
                        }
                    }
                }
                continue;
            }
            sort(cands.begin(), cands.end());
            cands.erase(unique(cands.begin(), cands.end()), cands.end());
            if ((int)cands.size() == 1) {
                int u = cands[0];
                parent[v] = u;
                g[u].push_back(v);
                g[v].push_back(u);
            } else {
                // Disambiguate by querying
                bool found = false;
                for (int u : cands) {
                    int dv = ask(u, v);
                    if (dv == 1) {
                        parent[v] = u;
                        g[u].push_back(v);
                        g[v].push_back(u);
                        found = true;
                        break;
                    }
                }
                if (!found) {
                    // As a last resort, scan previous layer
                    for (int u : layer[dist - 1]) {
                        int dv = ask(u, v);
                        if (dv == 1) {
                            parent[v] = u;
                            g[u].push_back(v);
                            g[v].push_back(u);
                            found = true;
                            break;
                        }
                    }
                }
            }
        }
    }

    // Now we have reconstructed the tree g. Compute centroid.
    vector<int> sz(n + 1, 0);
    vector<int> maxComp(n + 1, 0);

    // Iterative post-order DFS
    vector<int> st;
    vector<int> par(n + 1, -1);
    st.reserve(2 * n);
    // Root at r0
    vector<int> order;
    order.reserve(n);
    // BFS to get traversal order
    {
        vector<int> q;
        q.reserve(n);
        q.push_back(r0);
        par[r0] = 0;
        for (size_t qi = 0; qi < q.size(); ++qi) {
            int v = q[qi];
            order.push_back(v);
            for (int u : g[v]) if (u != par[v]) {
                par[u] = v;
                q.push_back(u);
            }
        }
    }
    // Post-order
    for (int i = (int)order.size() - 1; i >= 0; --i) {
        int v = order[i];
        sz[v] = 1;
        int mxc = 0;
        for (int u : g[v]) if (u != par[v]) {
            sz[v] += sz[u];
            mxc = max(mxc, sz[u]);
        }
        mxc = max(mxc, n - sz[v]);
        maxComp[v] = mxc;
    }
    int centroid = 1;
    for (int v = 1; v <= n; ++v) {
        if (maxComp[v] < maxComp[centroid]) centroid = v;
    }

    cout << "! " << centroid << "\n";
    flush_out();

    return 0;
}