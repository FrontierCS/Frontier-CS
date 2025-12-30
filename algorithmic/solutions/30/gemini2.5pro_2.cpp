#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

void solve();

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}

// Globals for a single test case
int N;
std::vector<std::vector<int>> adj;
std::vector<int> parent, depth, tin, tout;
std::vector<std::vector<int>> up;
int timer;
const int LOGN = 13;

void dfs_precompute(int u, int p, int d) {
    parent[u] = p;
    depth[u] = d;
    tin[u] = ++timer;
    up[u][0] = p;
    for (int i = 1; i < LOGN; ++i) {
        up[u][i] = up[up[u][i - 1]][i - 1];
    }

    for (int v : adj[u]) {
        if (v != p) {
            dfs_precompute(v, u, d + 1);
        }
    }
    tout[u] = ++timer;
}

bool is_in_subtree(int u, int v) {
    if (u == 0 || v == 0) return false;
    return tin[u] <= tin[v] && tout[v] <= tout[u];
}

int get_ancestor(int u, int k) {
    if (k >= depth[u]) {
        return 1;
    }
    for (int i = 0; i < LOGN; ++i) {
        if ((k >> i) & 1) {
            u = up[u][i];
        }
    }
    return u;
}

void solve() {
    std::cin >> N;
    adj.assign(N + 1, std::vector<int>());
    for (int i = 0; i < N - 1; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    parent.assign(N + 1, 0);
    depth.assign(N + 1, 0);
    tin.assign(N + 1, 0);
    tout.assign(N + 1, 0);
    up.assign(N + 1, std::vector<int>(LOGN, 1));
    timer = 0;
    
    dfs_precompute(1, 1, 0);

    std::vector<int> S(N);
    for (int i = 0; i < N; ++i) S[i] = i + 1;
    int k = 0;

    while (S.size() > 1) {
        std::vector<std::pair<int, int>> s_and_pos;
        s_and_pos.reserve(S.size());
        for (int u : S) {
            s_and_pos.push_back({u, get_ancestor(u, k)});
        }
        
        std::vector<int> C;
        C.reserve(s_and_pos.size());
        for (const auto& p : s_and_pos) {
            C.push_back(p.second);
        }
        std::sort(C.begin(), C.end());
        C.erase(std::unique(C.begin(), C.end()), C.end());

        std::vector<std::pair<int, int>> C_tin;
        C_tin.reserve(C.size());
        for(int node : C) {
            C_tin.push_back({tin[node], node});
        }
        std::sort(C_tin.begin(), C_tin.end());
        
        int best_x = -1;
        long long min_diff = -1;

        for (size_t i = 0; i < C_tin.size(); ++i) {
            int c = C_tin[i].second;
            
            auto it = std::upper_bound(C_tin.begin() + i, C_tin.end(), std::make_pair(tout[c], N + 2));
            int sub_size = std::distance(C_tin.begin() + i, it);

            long long current_diff = std::abs((long long)C.size() - 2LL * sub_size);
            if (best_x == -1 || current_diff < min_diff) {
                min_diff = current_diff;
                best_x = c;
            } else if (current_diff == min_diff) {
                if (depth[c] < depth[best_x]) {
                    best_x = c;
                }
            }
        }

        std::cout << "? " << best_x << std::endl;
        int r;
        std::cin >> r;

        std::vector<int> S_new;
        S_new.reserve(S.size());
        if (r == 1) {
            for (const auto& p : s_and_pos) {
                if (is_in_subtree(best_x, p.second)) {
                    S_new.push_back(p.first);
                }
            }
        } else {
            for (const auto& p : s_and_pos) {
                if (!is_in_subtree(best_x, p.second)) {
                    S_new.push_back(p.first);
                }
            }
            k++;
        }
        S = S_new;
    }

    int final_pos = get_ancestor(S[0], k);
    std::cout << "! " << final_pos << std::endl;
}