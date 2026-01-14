#include <iostream>
#include <vector>
#include <algorithm>
#include <set>
#include <string>

using namespace std;

// Global variables
int n, m, T;
vector<vector<int>> adj;
vector<int> topo_order;
vector<int> g; // Grundy values

// Function to compute Grundy values
void compute_grundy() {
    g.assign(n + 1, 0);
    // Process in reverse topological order
    for (int i = n - 1; i >= 0; --i) {
        int u = topo_order[i];
        set<int> seen;
        for (int v : adj[u]) {
            seen.insert(g[v]);
        }
        int mex = 0;
        while (seen.count(mex)) mex++;
        g[u] = mex;
    }
}

// Function to perform topological sort
void topo_sort() {
    topo_order.clear();
    vector<int> in_degree(n + 1, 0);
    for (int u = 1; u <= n; ++u) {
        for (int v : adj[u]) {
            in_degree[v]++;
        }
    }
    vector<int> q;
    for (int i = 1; i <= n; ++i) {
        if (in_degree[i] == 0) q.push_back(i);
    }
    int head = 0;
    while(head < (int)q.size()){
        int u = q[head++];
        topo_order.push_back(u);
        for(int v : adj[u]){
            in_degree[v]--;
            if(in_degree[v] == 0) q.push_back(v);
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m >> T)) return 0;

    adj.resize(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
    }

    topo_sort();
    compute_grundy();

    // Strategy: Assign unique target Grundy values to all vertices.
    // Target values will be close to 0..n-1 to minimize edges.
    // We assign targets greedily based on initial Grundy values to minimize increments.
    
    vector<pair<int, int>> nodes;
    for(int i=1; i<=n; ++i) nodes.push_back({g[i], i});
    sort(nodes.begin(), nodes.end());

    vector<int> target_g(n + 1);
    vector<bool> used_val(2 * n + 5000, false);
    
    for(auto p : nodes){
        int u = p.second;
        int val = p.first; 
        while(used_val[val]) val++;
        target_g[u] = val;
        used_val[val] = true;
    }

    vector<vector<int>> nodes_with_val(2 * n + 5000); 
    for(int i=1; i<=n; ++i){
        nodes_with_val[target_g[i]].push_back(i);
    }

    vector<string> ops;
    
    // Add edges to satisfy the new Grundy values
    for(int u=1; u<=n; ++u){
        set<int> present;
        for(int v : adj[u]){
            present.insert(target_g[v]);
        }
        for(int k=0; k < target_g[u]; ++k){
            if(present.find(k) == present.end()){
                if(!nodes_with_val[k].empty()){
                    int w = nodes_with_val[k][0];
                    ops.push_back("+ " + to_string(u) + " " + to_string(w));
                }
            }
        }
    }

    cout << ops.size() << endl;
    for(const string& s : ops) cout << s << endl;
    cout.flush();

    vector<int> val_to_node(2 * n + 5000, -1);
    for(int i=1; i<=n; ++i){
        val_to_node[target_g[i]] = i;
    }

    for(int t=0; t<T; ++t){
        // Linear scan using the unique Grundy values
        // Check candidates one by one.
        for(int k=1; k<=n; ++k){ 
             int val_k = target_g[k];
             cout << "? ";
             if(val_k == 0){
                 cout << "0" << endl;
             } else {
                 int u = val_to_node[val_k];
                 cout << "1 " << u << endl;
             }
             
             string res;
             cin >> res;
             if(res == "Lose"){
                 cout << "! " << k << endl;
                 string verdict;
                 cin >> verdict;
                 if(verdict == "Wrong") return 0;
                 break;
             }
        }
    }

    return 0;
}