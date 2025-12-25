#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

const int N_MAX = 5005;
const int LOGN_MAX = 13;

int n;
std::vector<int> adj[N_MAX];
int parent[N_MAX], depth[N_MAX];
int tin[N_MAX], tout[N_MAX], timer;
int up[N_MAX][LOGN_MAX];
std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

void dfs_precompute(int u, int p, int d) {
    parent[u] = p;
    depth[u] = d;
    tin[u] = ++timer;
    up[u][0] = p;
    for (int i = 1; i < LOGN_MAX; ++i) {
        up[u][i] = up[up[u][i - 1]][i - 1];
    }
    for (int v : adj[u]) {
        if (v != p) {
            dfs_precompute(v, u, d + 1);
        }
    }
    tout[u] = ++timer;
}

bool is_ancestor(int u, int v) {
    return tin[u] <= tin[v] && tout[u] >= tout[v];
}

int get_ancestor(int u, int k) {
    for (int i = 0; i < LOGN_MAX; ++i) {
        if ((k >> i) & 1) {
            u = up[u][i];
        }
    }
    return u;
}

void solve_case() {
    std::cin >> n;
    for (int i = 1; i <= n; ++i) {
        adj[i].clear();
    }
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    timer = 0;
    dfs_precompute(1, 1, 0);

    std::vector<int> L(n);
    std::iota(L.begin(), L.end(), 1);
    int k = 0;

    while (L.size() > 1) {
        std::uniform_int_distribution<int> distrib(0, L.size() - 1);
        int sample_s = L[distrib(rng)];
        int c = get_ancestor(sample_s, k);

        std::vector<int> path;
        int curr = c;
        while (true) {
            path.push_back(curr);
            if (curr == 1) break;
            curr = parent[curr];
        }
        std::reverse(path.begin(), path.end());

        int best_q = c;
        int low = 0, high = path.size() - 1;
        int ans_idx = path.size() - 1;

        while (low <= high) {
            int mid_idx = low + (high - low) / 2;
            int q_cand = path[mid_idx];
            
            int count = 0;
            for (int s : L) {
                int node_pos = get_ancestor(s, k);
                if (is_ancestor(q_cand, node_pos)) {
                    count++;
                }
            }
            
            if (count * 2 >= L.size()) {
                ans_idx = mid_idx;
                high = mid_idx - 1;
            } else {
                low = mid_idx + 1;
            }
        }
        best_q = path[ans_idx];
        
        std::cout << "? " << best_q << std::endl;
        int r;
        std::cin >> r;

        std::vector<int> L_new;
        if (r == 1) {
            for (int s : L) {
                if (is_ancestor(best_q, get_ancestor(s, k))) {
                    L_new.push_back(s);
                }
            }
        } else {
            for (int s : L) {
                if (!is_ancestor(best_q, get_ancestor(s, k))) {
                    L_new.push_back(s);
                }
            }
            k++;
        }
        L = L_new;
    }

    int final_s = L[0];
    int final_pos = get_ancestor(final_s, k);
    std::cout << "! " << final_pos << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int t;
    std::cin >> t;
    while (t--) {
        solve_case();
    }
    return 0;
}