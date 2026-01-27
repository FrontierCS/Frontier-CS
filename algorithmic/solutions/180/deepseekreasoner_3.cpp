#include <bits/stdc++.h>
using namespace std;

const int ITER_WL = 5;
const int PASSES_LS = 5;
const int ATTEMPTS_PER_VERTEX = 20;

uint64_t compute_hash(int cur_color, vector<int>& nb_colors) {
    uint64_t hash = 14695981039346656037ULL;
    hash = (hash ^ cur_color) * 1099511628211ULL;
    for (int c : nb_colors) {
        hash = (hash ^ c) * 1099511628211ULL;
    }
    return hash;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n, m;
    cin >> n >> m;
    vector<vector<int>> adj1(n), adj2(n);
    vector<bitset<2000>> adj1_bits(n), adj2_bits(n);
    auto add_edge = [](vector<vector<int>>& adj, vector<bitset<2000>>& bits, int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
        bits[u].set(v);
        bits[v].set(u);
    };
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        u--; v--;
        add_edge(adj1, adj1_bits, u, v);
    }
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        u--; v--;
        add_edge(adj2, adj2_bits, u, v);
    }
    vector<int> deg1(n), deg2(n);
    for (int i = 0; i < n; i++) {
        deg1[i] = adj1[i].size();
        deg2[i] = adj2[i].size();
    }
    vector<int> color1(n), color2(n);
    for (int i = 0; i < n; i++) {
        color1[i] = deg1[i];
        color2[i] = deg2[i];
    }
    // Weisfeiler-Lehman iterations
    for (int iter = 0; iter < ITER_WL; iter++) {
        vector<tuple<uint64_t, int, int>> items; // (hash, graph, vertex)
        items.reserve(2 * n);
        // Graph 1
        for (int i = 0; i < n; i++) {
            vector<int> nb_colors;
            nb_colors.reserve(adj1[i].size());
            for (int nb : adj1[i]) {
                nb_colors.push_back(color1[nb]);
            }
            sort(nb_colors.begin(), nb_colors.end());
            uint64_t h = compute_hash(color1[i], nb_colors);
            items.emplace_back(h, 0, i);
        }
        // Graph 2
        for (int i = 0; i < n; i++) {
            vector<int> nb_colors;
            nb_colors.reserve(adj2[i].size());
            for (int nb : adj2[i]) {
                nb_colors.push_back(color2[nb]);
            }
            sort(nb_colors.begin(), nb_colors.end());
            uint64_t h = compute_hash(color2[i], nb_colors);
            items.emplace_back(h, 1, i);
        }
        sort(items.begin(), items.end(),
             [](const auto& a, const auto& b) { return get<0>(a) < get<0>(b); });
        vector<int> new_color1(n), new_color2(n);
        int new_color = 0;
        uint64_t prev_hash = 0;
        bool first = true;
        for (auto& item : items) {
            auto [h, graph, v] = item;
            if (first || h != prev_hash) {
                new_color++;
                prev_hash = h;
                first = false;
            }
            if (graph == 0) {
                new_color1[v] = new_color;
            } else {
                new_color2[v] = new_color;
            }
        }
        color1 = move(new_color1);
        color2 = move(new_color2);
    }
    // Build initial permutation from colors
    vector<tuple<int, int, int>> v1, v2; // (color, degree, vertex)
    for (int i = 0; i < n; i++) {
        v1.emplace_back(color1[i], deg1[i], i);
        v2.emplace_back(color2[i], deg2[i], i);
    }
    sort(v1.begin(), v1.end());
    sort(v2.begin(), v2.end());
    vector<int> p(n);
    for (int i = 0; i < n; i++) {
        int v2_vertex = get<2>(v2[i]);
        int v1_vertex = get<2>(v1[i]);
        p[v2_vertex] = v1_vertex;
    }
    // Local search by random swaps
    random_device rd;
    mt19937 gen(rd());
    uniform_int_distribution<> dis(0, n - 1);
    bool improved = true;
    for (int pass = 0; pass < PASSES_LS && improved; pass++) {
        improved = false;
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), gen);
        for (int u : order) {
            for (int t = 0; t < ATTEMPTS_PER_VERTEX; t++) {
                int v = dis(gen);
                if (v == u) continue;
                int a = p[u], b = p[v];
                int delta = 0;
                for (int w : adj2[u]) {
                    if (w == v) continue;
                    delta += adj1_bits[b][p[w]] - adj1_bits[a][p[w]];
                }
                for (int w : adj2[v]) {
                    if (w == u) continue;
                    delta += adj1_bits[a][p[w]] - adj1_bits[b][p[w]];
                }
                if (delta > 0) {
                    swap(p[u], p[v]);
                    improved = true;
                    break;
                }
            }
        }
    }
    // Output permutation (1-indexed)
    for (int i = 0; i < n; i++) {
        cout << p[i] + 1 << (i == n - 1 ? '\n' : ' ');
    }
    return 0;
}