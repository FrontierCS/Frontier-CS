#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <queue>

std::vector<std::vector<int>> create_map(int N, int M,
                                         std::vector<int> A,
                                         std::vector<int> B) {
    if (N == 0) {
        return {};
    }

    std::vector<std::vector<bool>> adj(N + 1, std::vector<bool>(N + 1, false));
    for (int i = 0; i < M; ++i) {
        adj[A[i]][B[i]] = adj[B[i]][A[i]] = true;
    }

    std::vector<int> component(N + 1, 0);
    int comp_count = 0;
    std::vector<std::vector<int>> comp_nodes;

    for (int i = 1; i <= N; ++i) {
        if (component[i] == 0) {
            comp_count++;
            comp_nodes.emplace_back();
            std::queue<int> q;
            q.push(i);
            component[i] = comp_count;
            comp_nodes.back().push_back(i);
            while(!q.empty()){
                int u = q.front();
                q.pop();
                for(int v = 1; v <= N; ++v){
                    if(u != v && !adj[u][v] && component[v] == 0){
                        component[v] = comp_count;
                        comp_nodes.back().push_back(v);
                        q.push(v);
                    }
                }
            }
        }
    }

    if (comp_count > 1) {
        std::vector<int> reps;
        for (int i = 0; i < comp_count; ++i) {
            reps.push_back(*std::min_element(comp_nodes[i].begin(), comp_nodes[i].end()));
        }

        int max_comp_size = 0;
        for (const auto& c : comp_nodes) {
            max_comp_size = std::max(max_comp_size, (int)c.size());
        }

        int K = comp_count + max_comp_size - 1;
        std::vector<std::vector<int>> C(K, std::vector<int>(K));

        for (int i = 0; i < comp_count; ++i) {
            for (int j = 0; j < K; ++j) {
                C[i][j] = reps[i];
            }
        }
        for (int i = comp_count; i < K; ++i) {
            for (int j = 0; j < comp_count; ++j) {
                C[i][j] = reps[j];
            }
        }

        for (int i = 0; i < comp_count; ++i) {
            int current_rep = reps[i];
            for (int node : comp_nodes[i]) {
                if (node == current_rep) continue;
                bool placed = false;
                for(int j=comp_count; j < K; ++j) {
                    if (C[i][j] == current_rep && C[j][i] == current_rep) {
                        C[i][j] = node;
                        C[j][i] = node;
                        placed = true;
                        break;
                    }
                }
            }
        }
        
        for (int i = comp_count; i < K; ++i) {
            for(int j = comp_count; j < K; ++j) {
                if (C[i][j] == 0) C[i][j] = reps[0];
            }
        }
        return C;

    } else { // comp_count == 1
        std::vector<int> color(N + 1, 0);
        bool is_bipartite = true;
        for (int i = 1; i <= N; ++i) {
            if (color[i] == 0) {
                std::queue<int> q;
                q.push(i);
                color[i] = 1;
                while(!q.empty()){
                    int u = q.front();
                    q.pop();
                    for (int v = 1; v <= N; ++v) {
                        if (u == v || adj[u][v]) continue;
                        if (color[v] == 0) {
                            color[v] = 3 - color[u];
                            q.push(v);
                        } else if (color[v] == color[u]) {
                            is_bipartite = false;
                        }
                    }
                }
            }
        }

        if (is_bipartite) {
            std::vector<int> groupA, groupB;
            for (int i = 1; i <= N; ++i) {
                if (color[i] == 1) groupA.push_back(i);
                else groupB.push_back(i);
            }
            int K = std::max(groupA.size(), groupB.size()) + std::min(groupA.size(), groupB.size());
            if (K == 0) return {{1}};
            
            std::vector<std::vector<int>> C(K, std::vector<int>(K));
            
            for(size_t i = 0; i < K; ++i) {
                int country_row = (i < groupA.size()) ? groupA[i] : groupB[i - groupA.size()];
                for(size_t j = 0; j < K; ++j) {
                    int country_col = (j < groupB.size()) ? groupB[j] : groupA[j - groupB.size()];
                    if (adj[country_row][country_col]) {
                        C[i][j] = country_row;
                    } else {
                        C[i][j] = (i < groupA.size()) ? groupA[i] : groupB[i - groupA.size()];
                    }
                }
            }

            for(size_t i = 0; i < groupA.size(); ++i) {
                for(size_t j = 0; j < groupB.size(); ++j) {
                    if(adj[groupA[i]][groupB[j]]) {
                         C[i][groupA.size() + j] = groupB[j];
                    }
                }
            }
            return C;
        }

        // Fallback for non-bipartite G'
        int K = 2 * N;
        std::vector<std::vector<int>> C(K, std::vector<int>(K, 1));
        for(int i=0; i<N; ++i) {
            int u = i+1;
            C[2*i][2*i] = u;
            C[2*i+1][2*i] = u;
            C[2*i][2*i+1] = u;
            C[2*i+1][2*i+1] = u;
        }
        int r = 0, c = 1;
        for (int i = 0; i < M; ++i) {
            int u = A[i], v = B[i];
            while (r < K) {
                if (C[r][c] == 1 && c + 1 < K && C[r][c + 1] == 1) {
                    C[r][c] = u;
                    C[r][c+1] = v;
                    c += 2;
                    if (c >= K) {
                        c = 1;
                        r += 2;
                    }
                    break;
                }
                c += 2;
                if (c >= K) {
                    c = 1;
                    r += 2;
                }
            }
        }
        return C;
    }
}