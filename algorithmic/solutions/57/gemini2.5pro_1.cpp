#include <iostream>
#include <vector>
#include <numeric>
#include <queue>
#include <cmath>
#include <map>

using namespace std;

void solve() {
    int n;
    cin >> n;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<long long> f(n + 1);
    for (int i = 1; i <= n; ++i) {
        cout << "? 1 1 " << i << endl;
        cin >> f[i];
    }

    vector<int> candidate_roots_parity;
    for (int r = 1; r <= n; ++r) {
        vector<int> dist(n + 1, -1);
        queue<int> q;

        q.push(r);
        dist[r] = 0;

        vector<int> p_bfs;
        p_bfs.push_back(r);
        int head = 0;
        
        bool ok = true;
        while(head < p_bfs.size()){
            int u = p_bfs[head++];
            if ((f[u] % 2 + 2) % 2 != (dist[u] + 1) % 2) {
                ok = false;
                break;
            }
            for (int v : adj[u]) {
                if (dist[v] == -1) {
                    dist[v] = dist[u] + 1;
                    p_bfs.push_back(v);
                }
            }
        }
        
        if (ok) {
            candidate_roots_parity.push_back(r);
        }
    }

    vector<int> candidate_roots_final;
    for(int r : candidate_roots_parity) {
        vector<int> parent(n + 1, 0);
        queue<int> q;
        q.push(r);
        vector<bool> visited(n + 1, false);
        visited[r] = true;
        
        vector<int> bfs_order;
        bfs_order.push_back(r);
        int head = 0;

        while(head < bfs_order.size()){
            int u = bfs_order[head++];
            for(int v : adj[u]){
                if(!visited[v]){
                    visited[v] = true;
                    parent[v] = u;
                    bfs_order.push_back(v);
                }
            }
        }
        
        bool ok = true;
        for(int u : bfs_order) {
            long long val;
            if (u == r) {
                val = f[u];
            } else {
                val = f[u] - f[parent[u]];
            }
            if (val != 1 && val != -1) {
                ok = false;
                break;
            }
        }
        if (ok) {
            candidate_roots_final.push_back(r);
        }
    }

    int root = -1;
    int toggled_node = -1;

    if (candidate_roots_final.size() == 1) {
        root = candidate_roots_final[0];
    } else {
        int r1 = candidate_roots_final[0];
        int r2 = candidate_roots_final[1];

        vector<int> path_parent(n + 1, 0);
        vector<bool> visited(n + 1, false);
        
        queue<int> bfs_q;
        bfs_q.push(r1);
        visited[r1] = true;

        while(!bfs_q.empty()){
            int u = bfs_q.front();
            bfs_q.pop();
            if(u == r2) break;
            for(int v : adj[u]){
                if(!visited[v]){
                    visited[v] = true;
                    path_parent[v] = u;
                    bfs_q.push(v);
                }
            }
        }

        int c = r2;
        while(path_parent[c] != r1){
            c = path_parent[c];
        }

        toggled_node = c;

        long long f_r1_before = f[r1];
        cout << "? 2 " << c << endl;
        
        long long f_r1_after;
        cout << "? 1 1 " << r1 << endl;
        cin >> f_r1_after;
        
        if (f_r1_before == f_r1_after) {
            root = r1;
        } else {
            root = r2;
        }
    }
    
    vector<long long> final_values(n + 1);
    vector<int> parent(n + 1, 0);
    queue<int> q_bfs;
    q_bfs.push(root);
    vector<bool> visited_bfs(n + 1, false);
    visited_bfs[root] = true;
    
    vector<int> bfs_order;
    bfs_order.push_back(root);
    int head_bfs = 0;

    while(head_bfs < bfs_order.size()){
        int u = bfs_order[head_bfs++];
        for(int v : adj[u]){
            if(!visited_bfs[v]){
                visited_bfs[v] = true;
                parent[v] = u;
                bfs_order.push_back(v);
            }
        }
    }

    for(int u : bfs_order){
        if(u == root) final_values[u] = f[u];
        else final_values[u] = f[u] - f[parent[u]];
    }

    if (toggled_node != -1) {
        final_values[toggled_node] *= -1;
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << final_values[i];
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.flush();
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}