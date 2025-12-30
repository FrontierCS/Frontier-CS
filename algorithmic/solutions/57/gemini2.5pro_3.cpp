#include <iostream>
#include <vector>
#include <numeric>
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

    std::vector<int> f(n + 1, 0);
    std::cout << "? 1 1 1" << std::endl;
    std::cout.flush();
    std::cin >> f[1];

    for (int i = 2; i <= n; ++i) {
        std::cout << "? 1 2 1 " << i << std::endl;
        std::cout.flush();
        int sum;
        std::cin >> sum;
        f[i] = sum - f[1];
    }

    std::vector<int> colors(n + 1, -1);
    std::vector<int> q_bfs;
    q_bfs.push_back(1);
    colors[1] = 0;
    int head = 0;
    while(head < (int)q_bfs.size()){
        int u = q_bfs[head++];
        for (int v : adj[u]) {
            if (colors[v] == -1) {
                colors[v] = 1 - colors[u];
                q_bfs.push_back(v);
            }
        }
    }
    
    int root_color_val;
    // f(u) = sum of values on path r->u. Length of path is dist(r,u). Number of nodes is dist(r,u)+1.
    // Each value is 1 or -1. So f(u) has same parity as dist(r,u)+1.
    // f(u) % 2 == (dist(r,u)+1) % 2
    // For u=1:
    // f(1) is odd -> dist(r,1) is even -> color(r) == color(1)
    // f(1) is even -> dist(r,1) is odd -> color(r) != color(1)
    if ( (f[1] % 2 != 0 && f[1] > 0) || (f[1]%2 == 0 && f[1]<0) ) { // odd
        root_color_val = colors[1];
    } else { // even
        root_color_val = 1 - colors[1];
    }
    
    int root = -1;
    for (int i = 1; i <= n; ++i) {
        if (colors[i] == root_color_val) {
            if (f[i] == 1 || f[i] == -1) {
                root = i;
                break;
            }
        }
    }

    std::vector<int> final_values(n + 1);
    final_values[root] = f[root];
    
    std::vector<int> parent(n + 1, 0);
    q_bfs.clear();
    q_bfs.push_back(root);
    std::vector<bool> visited(n + 1, false);
    visited[root] = true;
    head = 0;
    while(head < (int)q_bfs.size()){
        int u = q_bfs[head++];
        for(int v : adj[u]){
            if(!visited[v]){
                visited[v] = true;
                parent[v] = u;
                q_bfs.push_back(v);
            }
        }
    }

    for (int i = 1; i <= n; ++i) {
        if (i == root) continue;
        final_values[i] = f[i] - f[parent[i]];
    }

    std::cout << "!";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << final_values[i];
    }
    std::cout << std::endl;
    std::cout.flush();
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