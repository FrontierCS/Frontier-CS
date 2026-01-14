#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

std::vector<std::vector<int>> create_map(int N, int M,
    std::vector<int> A, std::vector<int> B) {

    if (N == 0) {
        return {{1}};
    }

    std::vector<std::vector<bool>> adj(N + 1, std::vector<bool>(N + 1, false));
    for (int i = 0; i < M; ++i) {
        adj[A[i]][B[i]] = adj[B[i]][A[i]] = true;
    }

    std::vector<int> p(N);
    std::iota(p.begin(), p.end(), 1);

    std::vector<int> color(N + 1, 0);
    int num_colors = 0;

    for (int i = 1; i <= N; ++i) {
        std::vector<bool> used_colors(N + 1, false);
        for (int j = 1; j <= N; ++j) {
            if (i != j && !adj[i][j] && color[j] != 0) {
                used_colors[color[j]] = true;
            }
        }
        int c = 1;
        while (used_colors[c]) {
            c++;
        }
        color[i] = c;
        if (c > num_colors) {
            num_colors = c;
        }
    }

    std::vector<std::vector<int>> cliques(num_colors);
    for (int i = 1; i <= N; ++i) {
        cliques[color[i] - 1].push_back(i);
    }
    
    int K = 2 * num_colors;
    if (K == 0) K = 1;

    std::vector<std::vector<int>> res(K, std::vector<int>(K));

    for (int i = 0; i < num_colors; ++i) {
        int default_color = cliques[i].empty() ? 1 : cliques[i][0];
        for (int j = 0; j < K; ++j) {
            res[2 * i][j] = default_color;
            res[2 * i + 1][j] = default_color;
        }
    }

    int col_idx = 0;

    // Condition 1: Ensure all countries appear
    for (int i = 0; i < num_colors; ++i) {
        for (int country : cliques[i]) {
            res[2 * i][col_idx] = country;
            res[2 * i + 1][col_idx] = country;
            col_idx = (col_idx + 1) % K;
        }
    }
    
    // Condition 2: Ensure all adjacencies are present
    for (int i = 0; i < M; ++i) {
        int u = A[i], v = B[i];
        int u_c = color[u] - 1;
        int v_c = color[v] - 1;

        if (u_c == v_c) { // Intra-clique
            res[2 * u_c][col_idx] = u;
            res[2 * u_c + 1][col_idx] = v;
        } else { // Inter-clique
            int c1 = std::min(u_c, v_c);
            int c2 = std::max(u_c, v_c);
            res[2 * c1 + 1][col_idx] = (u_c < v_c) ? u : v;
            res[2 * c2][col_idx] = (u_c < v_c) ? v : u;
        }
        col_idx = (col_idx + 1) % K;
    }

    return res;
}