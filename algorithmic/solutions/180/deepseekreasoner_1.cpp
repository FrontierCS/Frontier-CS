#include <bits/stdc++.h>
using namespace std;
using uint64 = uint64_t;

// Compute a pair of 64-bit hashes for a vector of integers.
pair<uint64, uint64> compute_hash(const vector<int>& v) {
    uint64 h1 = 0, h2 = 0;
    const uint64 p1 = 1000000007, p2 = 1000000009;
    for (int x : v) {
        h1 = h1 * p1 + x;
        h2 = h2 * p2 + x;
    }
    return {h1, h2};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    vector<vector<int>> adj1(n), adj2(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj1[u].push_back(v);
        adj1[v].push_back(u);
    }
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
    }

    // Initial colors: degrees
    vector<int> color1(n), color2(n);
    for (int i = 0; i < n; ++i) {
        color1[i] = adj1[i].size();
        color2[i] = adj2[i].size();
    }

    const int ITERS = 5;
    for (int iter = 0; iter < ITERS; ++iter) {
        // Build signatures for both graphs
        vector<vector<int>> sig1(n), sig2(n);
        vector<pair<uint64, uint64>> hash1(n), hash2(n);

        // Graph 1
        for (int i = 0; i < n; ++i) {
            vector<int> nb_col;
            nb_col.reserve(adj1[i].size());
            for (int nb : adj1[i]) {
                nb_col.push_back(color1[nb]);
            }
            sort(nb_col.begin(), nb_col.end());
            sig1[i].push_back(color1[i]);
            sig1[i].insert(sig1[i].end(), nb_col.begin(), nb_col.end());
            hash1[i] = compute_hash(sig1[i]);
        }

        // Graph 2
        for (int i = 0; i < n; ++i) {
            vector<int> nb_col;
            nb_col.reserve(adj2[i].size());
            for (int nb : adj2[i]) {
                nb_col.push_back(color2[nb]);
            }
            sort(nb_col.begin(), nb_col.end());
            sig2[i].push_back(color2[i]);
            sig2[i].insert(sig2[i].end(), nb_col.begin(), nb_col.end());
            hash2[i] = compute_hash(sig2[i]);
        }

        // Collect all vertices with their hash and signature pointer
        using Item = tuple<pair<uint64, uint64>, int, int, vector<int>*>;
        vector<Item> items;
        items.reserve(2 * n);
        for (int i = 0; i < n; ++i) {
            items.emplace_back(hash1[i], 0, i, &sig1[i]);
        }
        for (int i = 0; i < n; ++i) {
            items.emplace_back(hash2[i], 1, i, &sig2[i]);
        }

        // Sort by hash
        sort(items.begin(), items.end(), [](const Item& a, const Item& b) {
            return get<0>(a) < get<0>(b);
        });

        // Assign new colors
        int new_color = 0;
        pair<uint64, uint64> prev_hash = {0, 0};
        vector<int>* prev_sig = nullptr;
        for (const auto& item : items) {
            auto cur_hash = get<0>(item);
            int g = get<1>(item);
            int v = get<2>(item);
            vector<int>* cur_sig = get<3>(item);

            if (prev_sig == nullptr || cur_hash != prev_hash || *cur_sig != *prev_sig) {
                ++new_color;
                prev_hash = cur_hash;
                prev_sig = cur_sig;
            }
            if (g == 0) {
                color1[v] = new_color;
            } else {
                color2[v] = new_color;
            }
        }
    }

    // Create sorted lists of (color, vertex) for both graphs
    vector<pair<int, int>> list1, list2;
    list1.reserve(n);
    list2.reserve(n);
    for (int i = 0; i < n; ++i) {
        list1.emplace_back(color1[i], i);
        list2.emplace_back(color2[i], i);
    }
    sort(list1.begin(), list1.end());
    sort(list2.begin(), list2.end());

    // Build the permutation p: vertex in G2 -> vertex in G1
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        int v2 = list2[i].second;
        int v1 = list1[i].second;
        p[v2] = v1;
    }

    // Output 1‑based permutation
    for (int i = 0; i < n; ++i) {
        cout << p[i] + 1 << (i == n - 1 ? '\n' : ' ');
    }

    return 0;
}