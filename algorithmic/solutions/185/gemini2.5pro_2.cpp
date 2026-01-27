#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <bitset>

const int MAXN = 1001;

bool adj_mat[MAXN][MAXN];
std::bitset<MAXN> adj[MAXN];
int degree[MAXN];

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N, M;
    std::cin >> N >> M;

    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj_mat[u][v] = adj_mat[v][u] = true;
    }

    for (int i = 1; i <= N; ++i) {
        for (int j = 1; j <= N; ++j) {
            if (adj_mat[i][j]) {
                adj[i][j] = 1;
                degree[i]++;
            }
        }
    }

    std::vector<int> p(N);
    std::iota(p.begin(), p.end(), 1);
    
    std::sort(p.begin(), p.end(), [&](int u, int v) {
        return degree[u] > degree[v];
    });

    std::bitset<MAXN> best_clique_mask;
    int max_k = 0;

    for (int start_node : p) {
        if (degree[start_node] + 1 <= max_k) {
            continue;
        }

        std::bitset<MAXN> current_clique_mask;
        current_clique_mask[start_node] = 1;

        std::vector<int> candidates;
        for (int j = 1; j <= N; ++j) {
            if (adj[start_node][j]) {
                candidates.push_back(j);
            }
        }
        
        std::sort(candidates.begin(), candidates.end(), [&](int u, int v) {
            return degree[u] > degree[v];
        });

        for (int v : candidates) {
            if ((current_clique_mask & adj[v]) == current_clique_mask) {
                current_clique_mask[v] = 1;
            }
        }

        int current_k = current_clique_mask.count();
        if (current_k > max_k) {
            max_k = current_k;
            best_clique_mask = current_clique_mask;
        }
    }

    for (int i = 1; i <= N; ++i) {
        std::cout << best_clique_mask[i] << "\n";
    }

    return 0;
}