#include <bits/stdc++.h>
using namespace std;

struct Key {
    array<int, 5> a;
    int len;
    bool operator==(Key const& other) const {
        if (len != other.len) return false;
        for (int i = 0; i < len; ++i) if (a[i] != other.a[i]) return false;
        return true;
    }
};

struct KeyHash {
    size_t operator()(Key const& k) const noexcept {
        uint64_t h = 1469598103934665603ULL; // FNV offset
        for (int i = 0; i < k.len; ++i) {
            uint64_t x = (uint64_t)k.a[i] + 0x9e3779b97f4a7c15ULL;
            h ^= x;
            h *= 1099511628211ULL;
        }
        h ^= (uint64_t)k.len + 0x9e3779b97f4a7c15ULL + (h<<6) + (h>>2);
        return (size_t)h;
    }
};

int ask(int u, int v) {
    cout << "? " << u << " " << v << endl;
    cout.flush();
    int d;
    if (!(cin >> d)) {
        // In interactive problems, failing to read means interactor ended.
        exit(0);
    }
    return d;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const int M = 5; // number of anchors
    vector<int> A; A.reserve(M);
    vector<vector<int>> D(M, vector<int>(n + 1, -1));

    auto compute_dists = [&](int idx, int source) {
        for (int v = 1; v <= n; ++v) {
            if (v == source) {
                D[idx][v] = 0;
            } else {
                D[idx][v] = ask(source, v);
            }
        }
    };

    // Anchor 0: r = 1
    A.push_back(1);
    compute_dists(0, A[0]);

    // Choose next anchors by farthest chain
    for (int i = 1; i < M; ++i) {
        int prev_anchor = A[i - 1];
        int far = prev_anchor;
        int bestd = -1;
        for (int v = 1; v <= n; ++v) {
            if (D[i - 1][v] > bestd) {
                bestd = D[i - 1][v];
                far = v;
            }
        }
        A.push_back(far);
        compute_dists(i, A[i]);
    }

    // Build signature map
    unordered_map<Key, int, KeyHash> uniq;
    unordered_map<Key, vector<int>, KeyHash> multi;
    uniq.reserve(n * 2);
    multi.reserve(n / 4 + 1);

    for (int x = 1; x <= n; ++x) {
        Key k;
        k.len = M;
        for (int j = 0; j < M; ++j) k.a[j] = D[j][x];
        auto it = uniq.find(k);
        if (it == uniq.end()) {
            uniq.emplace(k, x);
        } else {
            int prev = it->second;
            if (prev != -1) {
                // first collision
                it->second = -1;
                Key kk = k;
                auto &vec = multi[kk];
                vec.clear();
                vec.push_back(prev);
                vec.push_back(x);
            } else {
                auto &vec = multi[k];
                vec.push_back(x);
            }
        }
    }

    int r = A[0];
    vector<int> parent(n + 1, 0);
    parent[r] = 0;

    auto compute_parent_sig = [&](int v) {
        Key k;
        k.len = M;
        for (int j = 0; j < M; ++j) {
            int dv = D[j][v];
            int drv = D[0][v]; // distance to r
            int drt = D[j][r]; // distance between anchor j and r
            int L = (dv + drv - drt) / 2;
            int delta = (L >= 1) ? -1 : +1;
            k.a[j] = dv + delta;
        }
        return k;
    };

    // Build parent array
    for (int v = 1; v <= n; ++v) {
        if (v == r) continue;
        Key ps = compute_parent_sig(v);
        auto it = uniq.find(ps);
        if (it != uniq.end() && it->second > 0) {
            parent[v] = it->second;
        } else {
            // ambiguous or not found, disambiguate by direct queries
            vector<int> candidates;
            if (it != uniq.end() && it->second == -1) {
                auto mit = multi.find(ps);
                if (mit != multi.end()) candidates = mit->second;
            } else {
                // not found uniquely, but maybe in multi map
                auto mit = multi.find(ps);
                if (mit != multi.end()) candidates = mit->second;
            }
            int found = 0;
            for (int u : candidates) {
                int d = ask(u, v);
                if (d == 1) {
                    found = u;
                    break;
                }
            }
            if (found == 0) {
                // As a fallback (extremely unlikely), search over all nodes with same level (distance to r decreased by 1)
                // This is expensive but should not happen often.
                int targetLevel = D[0][v] - 1;
                for (int u = 1; u <= n; ++u) {
                    if (D[0][u] != targetLevel) continue;
                    int ok = 1;
                    for (int j = 0; j < M; ++j) {
                        int dv = D[j][v];
                        int drt = D[j][r];
                        int drv = D[0][v];
                        int L = (dv + drv - drt) / 2;
                        int delta = (L >= 1) ? -1 : +1;
                        if (D[j][u] != dv + delta) { ok = 0; break; }
                    }
                    if (ok) {
                        int d = ask(u, v);
                        if (d == 1) {
                            found = u;
                            break;
                        }
                    }
                }
            }
            parent[v] = found;
        }
    }

    // Build adjacency
    vector<vector<int>> g(n + 1);
    g.reserve(n + 1);
    for (int v = 1; v <= n; ++v) {
        if (v == r) continue;
        int u = parent[v];
        if (u >= 1) {
            g[u].push_back(v);
            g[v].push_back(u);
        } else {
            // should not happen
        }
    }

    // Compute subtree sizes and centroid
    vector<int> sz(n + 1, 0);
    vector<int> par(n + 1, 0);
    // Root at r
    par[r] = 0;
    vector<int> order;
    order.reserve(n);
    // iterative DFS to get postorder
    {
        vector<int> st;
        st.reserve(n);
        st.push_back(r);
        par[r] = 0;
        while (!st.empty()) {
            int u = st.back(); st.pop_back();
            order.push_back(u);
            for (int w : g[u]) {
                if (w == par[u]) continue;
                par[w] = u;
                st.push_back(w);
            }
        }
    }
    // postorder
    for (int i = (int)order.size() - 1; i >= 0; --i) {
        int u = order[i];
        sz[u] = 1;
        for (int w : g[u]) if (w != par[u]) sz[u] += sz[w];
    }

    int best_node = 1;
    int best_val = n;
    for (int u = 1; u <= n; ++u) {
        int mx = n - sz[u];
        for (int w : g[u]) if (w != par[u]) mx = max(mx, sz[w]);
        if (mx < best_val) {
            best_val = mx;
            best_node = u;
        }
    }

    cout << "! " << best_node << endl;
    cout.flush();
    return 0;
}