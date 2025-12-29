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

    std::vector<int> dist(n + 1, -1);
    std::vector<int> q;
    q.push_back(1);
    dist[1] = 0;
    int head = 0;
    std::vector<int> p1(n + 1, 0);

    while(head < (int)q.size()){
        int u = q[head++];
        for(int v : adj[u]){
            if(dist[v] == -1){
                dist[v] = dist[u] + 1;
                p1[v] = u;
                q.push_back(v);
            }
        }
    }

    std::vector<std::vector<int>> B(2);
    for (int i = 1; i <= n; ++i) {
        B[dist[i] % 2].push_back(i);
    }

    int query_part_idx = 0;
    if (B[1].size() < B[0].size()) {
        query_part_idx = 1;
    }
    
    if (B[query_part_idx].empty()) {
        query_part_idx = 1 - query_part_idx;
    }

    std::cout << "? 1 " << B[query_part_idx].size();
    for (int node : B[query_part_idx]) {
        std::cout << " " << node;
    }
    std::cout << std::endl;

    long long S_part;
    std::cin >> S_part;

    int root_part_in_B_of_query_part;
    if ((std::abs(S_part) % 2) == (B[query_part_idx].size() % 2)) {
        root_part_in_B_of_query_part = 1;
    } else {
        root_part_in_B_of_query_part = 0;
    }
    
    int root_dist_parity;
    if (root_part_in_B_of_query_part) {
        root_dist_parity = query_part_idx;
    } else {
        root_dist_parity = 1 - query_part_idx;
    }

    std::vector<int> par_f(n + 1);
    for (int i = 1; i <= n; ++i) {
        int dist1_i_parity = dist[i] % 2;
        int depth_R_parity = (root_dist_parity + dist1_i_parity) % 2;
        par_f[i] = (depth_R_parity + 1) % 2;
    }

    std::vector<long long> S_pair(n + 1);
    if (n > 1) {
        for (int i = 2; i <= n; ++i) {
            std::cout << "? 1 2 1 " << i << std::endl;
            std::cin >> S_pair[i];
        }
    }
    
    int p_of_1 = 0;
    if (!adj[1].empty()) {
        p_of_1 = adj[1][0];
    }
    
    long long f1;
    if (p_of_1 != 0) {
        long long Sp = S_pair[p_of_1];

        long long f1_cand1 = (Sp - 1) / 2;
        long long f1_cand2 = (Sp + 1) / 2;
        
        if ((((f1_cand1 % 2) + 2) % 2) == par_f[1]) {
            f1 = f1_cand1;
        } else {
            f1 = f1_cand2;
        }
    } else { // n=1 case, not possible by constraints, but for safety
        if (par_f[1] == 1) f1 = 1; else f1 = -1; // arbitrary odd/even; f(root) could be anything odd/even
                                                // but values are +-1, so f(root)=v_root is +-1 (odd)
                                                // thus par_f[1] must be 1.
        if (par_f[1] == 1) f1 = 1; else f1 = -1; // Let's guess, it's consistent if we assume value is 1 or -1
    }
    
    std::vector<long long> f(n + 1);
    f[1] = f1;
    for (int i = 2; i <= n; ++i) {
        f[i] = S_pair[i] - f[1];
    }

    std::vector<int> v_final(n + 1);
    v_final[1] = f[1];
    
    for (int node : q) {
        if (node == 1) continue;
        v_final[node] = f[node] - f[p1[node]];
    }

    std::cout << "!";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << v_final[i];
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