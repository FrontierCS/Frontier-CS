#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <numeric>

using namespace std;

// Global variables to store tree structure
vector<vector<int>> adj;
vector<int> depth_arr;
int n;

// BFS to compute depths from a given root
void bfs(int root) {
    fill(depth_arr.begin(), depth_arr.end(), -1);
    queue<int> q;
    q.push(root);
    depth_arr[root] = 0;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (int v : adj[u]) {
            if (depth_arr[v] == -1) {
                depth_arr[v] = depth_arr[u] + 1;
                q.push(v);
            }
        }
    }
}

// Function to perform a query
pair<int, int> query(const vector<int>& nodes) {
    if (nodes.empty()) return {-1, -1};
    cout << "? " << nodes.size();
    for (int u : nodes) cout << " " << u;
    cout << endl;
    int x, d;
    cin >> x >> d;
    if (x == -1) exit(0); // Invalid query or limit exceeded
    return {x, d};
}

void solve() {
    cin >> n;
    adj.assign(n + 1, vector<int>());
    depth_arr.assign(n + 1, 0);
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Query 1: Find a node on the path between hidden nodes (R) and the distance between them (L)
    // R minimizes the sum of distances, so it lies on the path between s and f.
    // L is exactly dist(s, f).
    vector<int> all_nodes(n);
    iota(all_nodes.begin(), all_nodes.end(), 1);
    pair<int, int> root_info = query(all_nodes);
    int R = root_info.first;
    int L = root_info.second;

    // Root the tree at R and compute depths relative to R
    bfs(R);
    
    // Group nodes by depth
    vector<vector<int>> nodes_by_depth(n + 1);
    int max_d = 0;
    for (int i = 1; i <= n; ++i) {
        nodes_by_depth[depth_arr[i]].push_back(i);
        max_d = max(max_d, depth_arr[i]);
    }

    // Binary search to find the deeper hidden node.
    // The deeper node (among s and f) must have depth at least ceil(L/2) relative to R.
    // We search for the largest depth h such that a query of all nodes at depth h returns distance L.
    int lo = (L + 1) / 2;
    int hi = min(max_d, L);
    int s = -1;

    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (nodes_by_depth[mid].empty()) {
            hi = mid - 1;
            continue;
        }
        
        pair<int, int> res = query(nodes_by_depth[mid]);
        if (res.second == L) {
            s = res.first; // Found a candidate at this depth, try deeper to find the exact node
            lo = mid + 1;
        } else {
            // Distance > L means no node at this depth is on the path between s and f
            hi = mid - 1;
        }
    }

    // s is now one of the hidden nodes.
    // To find the other node f, we know dist(s, f) = L.
    // We compute distances from s to all other nodes and query all nodes at distance L from s.
    // Since f is one of the hidden nodes, D(f) = L, and it is the unique node in this set with D(f) = L
    // (other nodes at dist L from s are not f, so they have sum of distances > L).
    
    vector<int> dist_s(n + 1, -1);
    queue<int> q;
    q.push(s);
    dist_s[s] = 0;
    while(!q.empty()){
        int u = q.front();
        q.pop();
        for(int v : adj[u]){
            if(dist_s[v] == -1){
                dist_s[v] = dist_s[u] + 1;
                q.push(v);
            }
        }
    }

    vector<int> candidates;
    for(int i=1; i<=n; ++i){
        if(dist_s[i] == L) candidates.push_back(i);
    }

    pair<int, int> res_f = query(candidates);
    int f = res_f.first;

    cout << "! " << s << " " << f << endl;
    
    string feedback;
    cin >> feedback;
    if (feedback != "Correct") exit(0);
}

int main() {
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}