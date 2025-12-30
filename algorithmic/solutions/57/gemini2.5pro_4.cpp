#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>

void solve() {
    int n;
    std::cin >> n;
    std::vector<std::vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    std::vector<int> color(n + 1, 0);
    std::vector<int> q_bipart;
    q_bipart.push_back(1);
    color[1] = 1;
    int head_bipart = 0;
    while(head_bipart < q_bipart.size()){
        int u = q_bipart[head_bipart++];
        for(int v : adj[u]){
            if(color[v] == 0){
                color[v] = 3 - color[u];
                q_bipart.push_back(v);
            }
        }
    }

    std::vector<long long> f(n + 1);

    std::cout << "? 1 1 1" << std::endl;
    std::cin >> f[1];

    std::vector<int> v_r_candidates;
    if ((f[1] % 2 + 2) % 2 != 0) { // f(1) is odd
        for (int i = 1; i <= n; ++i) {
            if (color[i] == color[1]) {
                v_r_candidates.push_back(i);
            }
        }
    } else { // f(1) is even
        for (int i = 1; i <= n; ++i) {
            if (color[i] != color[1]) {
                v_r_candidates.push_back(i);
            }
        }
    }

    for (int i = 2; i <= n; ++i) {
        std::cout << "? 1 1 " << i << std::endl;
        std::cin >> f[i];
    }

    std::vector<int> final_values(n + 1);

    for (int g : v_r_candidates) {
        std::vector<int> parent(n + 1, 0);
        std::vector<int> q_bfs;
        q_bfs.push_back(g);
        
        std::vector<bool> visited_bfs(n+1, false);
        visited_bfs[g] = true;
        parent[g] = 0; // Root has no parent
        
        int head_bfs = 0;
        while(head_bfs < q_bfs.size()){
            int u = q_bfs[head_bfs++];
            for(int v : adj[u]){
                if(!visited_bfs[v]){
                    visited_bfs[v] = true;
                    parent[v] = u;
                    q_bfs.push_back(v);
                }
            }
        }

        std::vector<int> vals_g(n + 1);
        bool ok = true;

        vals_g[g] = f[g];
        if (std::abs(vals_g[g]) != 1) {
            ok = false;
        }

        if (ok) {
            for (int i = 1; i <= n; ++i) {
                if (i == g) continue;
                vals_g[i] = f[i] - f[parent[i]];
                if (std::abs(vals_g[i]) != 1) {
                    ok = false;
                    break;
                }
            }
        }
        
        if (ok) {
            final_values = vals_g;
            break;
        }
    }

    std::cout << "! ";
    for (int i = 1; i <= n; ++i) {
        std::cout << final_values[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;
}

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