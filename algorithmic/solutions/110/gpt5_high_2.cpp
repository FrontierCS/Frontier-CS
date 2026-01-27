#include <bits/stdc++.h>
using namespace std;

int main() {
    // Random seed
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&seed;
    mt19937_64 rng(seed);

    // Build De Bruijn sequence of order 2 over alphabet {0..9} via Eulerian cycle on K_10 directed multigraph
    const int K = 10;
    vector<vector<int>> g(K);
    for (int u = 0; u < K; ++u) {
        g[u].resize(K);
        iota(g[u].begin(), g[u].end(), 0);
        shuffle(g[u].begin(), g[u].end(), rng);
    }
    int start = uniform_int_distribution<int>(0, K - 1)(rng);

    vector<int> idx(K, 0);
    vector<int> st;
    vector<int> res;
    st.push_back(start);
    while (!st.empty()) {
        int u = st.back();
        if (idx[u] < (int)g[u].size()) {
            int v = g[u][idx[u]++];
            st.push_back(v);
        } else {
            res.push_back(u);
            st.pop_back();
        }
    }
    reverse(res.begin(), res.end()); // res.size() == 100 edges + 1 = 101 vertices

    // Build serpentine Hamiltonian path over 8x14 grid
    const int R = 8, C = 14;
    vector<pair<int,int>> coords;
    coords.reserve(R*C);
    for (int r = 0; r < R; ++r) {
        if (r % 2 == 0) {
            for (int c = 0; c < C; ++c) coords.emplace_back(r, c);
        } else {
            for (int c = C - 1; c >= 0; --c) coords.emplace_back(r, c);
        }
    }

    // Fill grid digits using the de Bruijn vertex sequence, repeating if needed
    vector<string> grid(R, string(C, '0'));
    int L = (int)res.size(); // 101
    for (int i = 0; i < R*C; ++i) {
        int d = res[i % L];
        auto [r, c] = coords[i];
        grid[r][c] = char('0' + d);
    }

    // Output grid
    for (int r = 0; r < R; ++r) {
        cout << grid[r] << '\n';
    }
    return 0;
}