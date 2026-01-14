#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <map>

std::vector<std::vector<int>> create_map(int N, int M,
    std::vector<int> A, std::vector<int> B) {

    std::vector<std::vector<bool>> adj(N + 1, std::vector<bool>(N + 1, false));
    std::vector<int> degree(N + 1, 0);
    for (int i = 0; i < M; ++i) {
        adj[A[i]][B[i]] = adj[B[i]][A[i]] = true;
        degree[A[i]]++;
        degree[B[i]]++;
    }

    std::vector<int> p(N);
    std::iota(p.begin(), p.end(), 1);
    std::sort(p.begin(), p.end(), [&](int u, int v) {
        return degree[u] > degree[v];
    });

    std::vector<int> c1(N + 1, 0), c2(N + 1, 0);
    int k_r = 0, k_c = 0;

    std::set<std::pair<int, int>> used_coords;

    for (int v_node : p) {
        int best_i = -1, best_j = -1;
        int min_new_max_k = 1e9;

        for (int d = 1; ; ++d) {
            for (int i = 1; i <= d; ++i) {
                int j = d;
                for (int iter = 0; iter < 2; ++iter) {
                    if (i == j && iter == 1) continue;
                    
                    int cur_i = (iter == 0) ? i : j;
                    int cur_j = (iter == 0) ? j : i;
                    
                    if (used_coords.count({cur_i, cur_j})) {
                        continue;
                    }

                    bool ok = true;
                    for (int u_node : p) {
                        if (c1[u_node] == 0) continue;
                        if ((adj[u_node][v_node] && (c1[u_node] != cur_i && c2[u_node] != cur_j)) ||
                            (!adj[u_node][v_node] && u_node != v_node && (c1[u_node] == cur_i || c2[u_node] == cur_j))) {
                            ok = false;
                            break;
                        }
                    }

                    if (ok) {
                        int new_max_k = std::max({k_r, k_c, cur_i, cur_j});
                        if (best_i == -1 || new_max_k < min_new_max_k) {
                            min_new_max_k = new_max_k;
                            best_i = cur_i;
                            best_j = cur_j;
                        }
                    }
                }
            }
            if (best_i != -1) {
                break;
            }
        }
        
        c1[v_node] = best_i;
        c2[v_node] = best_j;
        used_coords.insert({best_i, best_j});
        k_r = std::max(k_r, best_i);
        k_c = std::max(k_c, best_j);
    }

    if (N == 0) return {};
    if (k_r == 0) k_r = 1;
    if (k_c == 0) k_c = 1;
    
    int K = std::max(k_r, k_c);

    std::vector<std::vector<int>> node_at(k_r + 1, std::vector<int>(k_c + 1, 0));
    for (int i = 1; i <= N; ++i) {
        node_at[c1[i]][c2[i]] = i;
    }

    for (int i = 1; i <= k_r; ++i) {
        for (int j = 1; j <= k_c; ++j) {
            if (node_at[i][j] == 0) {
                if (i > 1) {
                    node_at[i][j] = node_at[i - 1][j];
                } else if (j > 1) {
                    node_at[i][j] = node_at[i][j - 1];
                }
            }
        }
    }
    
    for (int i = 1; i <= k_r; ++i) {
        for (int j = 1; j <= k_c; ++j) {
            if (node_at[i][j] == 0) {
                 if (j > 1) {
                    node_at[i][j] = node_at[i][j - 1];
                } else if (i > 1) {
                    node_at[i][j] = node_at[i - 1][j];
                }
            }
        }
    }
    
    if (node_at[1][1] == 0) {
        for (int i=1; i<=k_r; ++i) for (int j=1; j<=k_c; ++j) if(node_at[i][j] == 0) node_at[i][j] = p[0];
    }
    
    std::vector<std::vector<int>> map(K, std::vector<int>(K));
    for (int r = 0; r < K; ++r) {
        for (int c = 0; c < K; ++c) {
            int i = (long long)r * k_r / K + 1;
            int j = (long long)c * k_c / K + 1;
            map[r][c] = node_at[i][j];
        }
    }

    return map;
}