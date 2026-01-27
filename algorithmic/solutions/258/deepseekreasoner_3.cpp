#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <string>

using namespace std;

// Global variables, resized per test case
int n;
vector<vector<int>> adj;
vector<int> depth;

// Function to perform a query
pair<int, int> query(const vector<int>& nodes) {
    if (nodes.empty()) return {-1, -1};
    cout << "? " << nodes.size();
    for (int x : nodes) {
        cout << " " << x;
    }
    cout << endl; // Auto-flush
    
    int node, d;
    cin >> node >> d;
    if (node == -1 && d == -1) exit(0); // Exit on error or query limit exceeded
    return {node, d};
}

// Function to calculate depths or distances using BFS
void bfs(int start, vector<int>& d_out) {
    fill(d_out.begin(), d_out.end(), -1);
    d_out[start] = 0;
    queue<int> q;
    q.push(start);
    while(!q.empty()){
        int u = q.front();
        q.pop();
        for(int v : adj[u]){
            if(d_out[v] == -1){
                d_out[v] = d_out[u] + 1;
                q.push(v);
            }
        }
    }
}

void solve() {
    cin >> n;
    adj.assign(n + 1, vector<int>());
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Step 1: Initial query with all nodes to find the total distance L between hidden nodes
    // and a node 'root_path' that lies on the path between them.
    vector<int> nodes(n);
    for(int i=0; i<n; ++i) nodes[i] = i+1;
    
    pair<int, int> info = query(nodes);
    int root_path = info.first;
    int L = info.second;

    // Step 2: BFS from node 1 to assign depths to all nodes.
    // We root the tree arbitrarily at 1 to define "depth".
    depth.assign(n + 1, 0);
    bfs(1, depth);

    int max_depth_tree = 0;
    for(int i=1; i<=n; ++i) max_depth_tree = max(max_depth_tree, depth[i]);

    // Step 3: Binary Search to find the deepest node on the simple path between hidden nodes.
    // Since the path is a contiguous set of nodes, there exists a unique "deepest" node 
    // (relative to root 1) which must be one of the endpoints (hidden nodes).
    // We search for the maximum depth D such that there is a node on the path with depth D.
    
    int low = depth[root_path]; // We know 'root_path' is on the path
    int high = max_depth_tree;
    int f = root_path; // 'f' will eventually store one of the hidden nodes

    while (low < high) {
        int mid = (low + high + 1) / 2;
        vector<int> q_nodes;
        for(int i=1; i<=n; ++i) {
            if (depth[i] >= mid) q_nodes.push_back(i);
        }
        
        if (q_nodes.empty()) {
            high = mid - 1;
            continue; 
        }

        pair<int, int> res = query(q_nodes);
        if (res.second == L) {
            // intersection of query set and path is non-empty
            // There is a path node at depth >= mid
            f = res.first; // Update candidate to the returned node (which is on the path)
            low = mid;
        } else {
            // intersection is empty (the minimal sum of distances > L)
            high = mid - 1;
        }
    }

    // Step 4: 'f' is now one of the hidden nodes (the deeper one).
    // The other node 's' is at distance L from 'f'. query all such candidates.
    vector<int> d_from_f(n + 1);
    bfs(f, d_from_f);
    
    vector<int> s_candidates;
    for(int i=1; i<=n; ++i) {
        if (d_from_f[i] == L) s_candidates.push_back(i);
    }

    int s;
    if (s_candidates.size() == 1) {
        s = s_candidates[0];
    } else {
        // If multiple nodes are at distance L, the query will return the one minimizing dist(u, f) + dist(u, s)
        // Since u is in candidates, dist(u, f) = L. We want to find s.
        // For s, dist(s, s) = 0, so sum is L. For u!=s, dist(u, s) > 0, sum > L.
        // Thus, the query is guaranteed to return s.
        pair<int, int> res = query(s_candidates);
        s = res.first;
    }

    cout << "! " << f << " " << s << endl;

    string verdict;
    cin >> verdict;
    if (verdict != "Correct") exit(0);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}