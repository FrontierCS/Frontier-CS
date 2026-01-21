#include <bits/stdc++.h>
using namespace std;

static uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct ArrHash {
    size_t operator()(const array<int,4>& a) const noexcept {
        uint64_t h = 0x243f6a8885a308d3ULL;
        for (int i = 0; i < 4; i++) {
            h ^= splitmix64((uint64_t)(uint32_t)a[i] + 0x9e3779b97f4a7c15ULL + (h << 6) + (h >> 2));
        }
        return (size_t)h;
    }
};

static long long queryCount = 0;

static int ask(int u, int v) {
    cout << "? " << u << " " << v << "\n";
    cout.flush();
    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    ++queryCount;
    return ans;
}

static void fill_dist(int n, int pivot, vector<int>& d) {
    d.assign(n + 1, 0);
    for (int i = 1; i <= n; i++) {
        if (i == pivot) d[i] = 0;
        else d[i] = ask(pivot, i);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    vector<int> d0, d1, d2, d3;

    // Pivot 0 = 1
    fill_dist(n, 1, d0);
    int a = 1;
    for (int i = 2; i <= n; i++) if (d0[i] > d0[a]) a = i;

    // Pivot 1 = a
    fill_dist(n, a, d1);
    int b = 1;
    for (int i = 1; i <= n; i++) if (d1[i] > d1[b]) b = i;

    // Pivot 2 = b
    fill_dist(n, b, d2);

    int D = d1[b];

    // Pivot 3 = c, pick far from diameter (a-b) and far from previous pivots
    auto is_used = [&](int x) {
        return x == 1 || x == a || x == b;
    };

    int c = -1;
    long long bestH = -1, bestMinD = -1, bestSum = -1;
    for (int i = 1; i <= n; i++) {
        if (is_used(i)) continue;
        long long h = ( (long long)d1[i] + (long long)d2[i] - (long long)D ) / 2LL;
        long long mind = min({(long long)d0[i], (long long)d1[i], (long long)d2[i]});
        long long sumd = (long long)d0[i] + d1[i] + d2[i];
        if (h > bestH || (h == bestH && (mind > bestMinD || (mind == bestMinD && sumd > bestSum)))) {
            bestH = h;
            bestMinD = mind;
            bestSum = sumd;
            c = i;
        }
    }
    if (c == -1) {
        for (int i = 1; i <= n; i++) if (!is_used(i)) { c = i; break; }
        if (c == -1) c = 1;
    }

    fill_dist(n, c, d3);

    // Build signature map
    unordered_map<array<int,4>, vector<int>, ArrHash> mp;
    mp.reserve((size_t)n * 2);

    for (int i = 1; i <= n; i++) {
        array<int,4> key{d0[i], d1[i], d2[i], d3[i]};
        mp[key].push_back(i);
    }

    // Order nodes by depth from root 1 (d0)
    vector<int> nodes;
    nodes.reserve(n - 1);
    for (int i = 2; i <= n; i++) nodes.push_back(i);
    sort(nodes.begin(), nodes.end(), [&](int x, int y) {
        return d0[x] < d0[y];
    });

    vector<int> parent(n + 1, 0);
    parent[1] = 0;

    // Build parent for each node
    for (int v : nodes) {
        int dep = d0[v];
        if (dep == 1) {
            parent[v] = 1;
            continue;
        }

        vector<pair<int, const vector<int>*>> buckets;
        buckets.reserve(8);

        for (int mask = 0; mask < 8; mask++) {
            int s1 = (mask & 1) ? 1 : -1;
            int s2 = (mask & 2) ? 1 : -1;
            int s3 = (mask & 4) ? 1 : -1;

            int k0 = dep - 1;
            int k1 = d1[v] + s1;
            int k2 = d2[v] + s2;
            int k3 = d3[v] + s3;
            if (k0 < 0 || k1 < 0 || k2 < 0 || k3 < 0) continue;

            array<int,4> key{k0, k1, k2, k3};
            auto it = mp.find(key);
            if (it != mp.end()) {
                buckets.push_back({(int)it->second.size(), &it->second});
            }
        }

        if (buckets.empty()) {
            // Should not happen; fallback to root (will likely fail, but keep safe)
            parent[v] = 1;
            continue;
        }

        sort(buckets.begin(), buckets.end(), [](auto& L, auto& R) {
            return L.first < R.first;
        });

        int p = -1;
        for (auto &bk : buckets) {
            const vector<int>& vec = *bk.second;
            for (int u : vec) {
                if (u == v) continue;
                // u must be at depth dep-1 by construction of key, but keep safe:
                if (d0[u] != dep - 1) continue;
                int dv = ask(u, v);
                if (dv == 1) {
                    p = u;
                    break;
                }
            }
            if (p != -1) break;
        }

        if (p == -1) {
            // Extremely unlikely; as a last resort, scan a few more buckets (already scanned all)
            // Fallback to root
            p = 1;
        }
        parent[v] = p;
    }

    // Build adjacency list
    vector<vector<int>> g(n + 1);
    g.reserve(n + 1);
    for (int v = 2; v <= n; v++) {
        int p = parent[v];
        if (p <= 0) p = 1;
        g[p].push_back(v);
        g[v].push_back(p);
    }

    // Root at 1 for subtree sizes
    vector<int> par(n + 1, 0), order;
    order.reserve(n);
    {
        vector<int> st;
        st.reserve(n);
        st.push_back(1);
        par[1] = 0;
        while (!st.empty()) {
            int v = st.back();
            st.pop_back();
            order.push_back(v);
            for (int to : g[v]) {
                if (to == par[v]) continue;
                par[to] = v;
                st.push_back(to);
            }
        }
    }

    vector<int> sz(n + 1, 1);
    for (int i = (int)order.size() - 1; i >= 0; i--) {
        int v = order[i];
        sz[v] = 1;
        for (int to : g[v]) {
            if (to == par[v]) continue;
            sz[v] += sz[to];
        }
    }

    int centroid = 1;
    int best = n + 1;
    for (int v = 1; v <= n; v++) {
        int mx = n - sz[v];
        for (int to : g[v]) {
            if (to == par[v]) continue;
            mx = max(mx, sz[to]);
        }
        if (mx < best || (mx == best && v < centroid)) {
            best = mx;
            centroid = v;
        }
    }

    cout << "! " << centroid << "\n";
    cout.flush();
    return 0;
}