#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <cstdlib>

using namespace std;

// Function to perform a query
// Prints "? c u1 u2 ... uc" and reads the response
pair<int, int> query(const vector<int>& nodes) {
    if (nodes.empty()) return {-1, -1};
    cout << "? " << nodes.size();
    for (int u : nodes) {
        cout << " " << u;
    }
    cout << endl; // Flushes output
    
    int node, dist;
    cin >> node >> dist;
    if (node == -1 && dist == -1) exit(0); // Exit immediately on invalid query/verdict
    return {node, dist};
}

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

    // Step 1: Query all nodes to find a node on the path between hidden nodes
    // and the distance D between them.
    vector<int> all_nodes(n);
    for (int i = 0; i < n; ++i) all_nodes[i] = i + 1;
    pair<int, int> root_info = query(all_nodes);
    int root = root_info.first;
    int D = root_info.second;

    // Step 2: Root the tree at the returned node and compute depths
    // Since 'root' is on the simple path between the hidden nodes s and f,
    // the path goes from s -> ... -> root -> ... -> f.
    // Thus dist(s, f) = dist(s, root) + dist(f, root) = depth[s] + depth[f] = D.
    // This implies max(depth[s], depth[f]) >= ceil(D/2).
    
    vector<int> depth(n + 1, -1);
    vector<vector<int>> nodes_at_depth(n + 1);
    queue<int> q;
    
    depth[root] = 0;
    nodes_at_depth[0].push_back(root);
    q.push(root);
    
    int max_depth = 0;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        max_depth = max(max_depth, depth[u]);
        
        for (int v : adj[u]) {
            if (depth[v] == -1) {
                depth[v] = depth[u] + 1;
                nodes_at_depth[depth[v]].push_back(v);
                q.push(v);
            }
        }
    }

    // Step 3: Binary search to find the deeper hidden node.
    // We search for the largest depth 'd' such that querying all nodes at depth 'd'
    // returns a node with sum of distances equal to D.
    // The node returned at this maximum depth must be one of the hidden nodes.
    
    int s_final = -1;
    int l = (D + 1) / 2;       // Lower bound: at least one node has depth >= D/2
    int r = min(D, max_depth); // Upper bound: depth cannot exceed D or tree height
    
    while (l <= r) {
        int mid = (l + r) / 2;
        if (nodes_at_depth[mid].empty()) {
            r = mid - 1;
            continue;
        }
        
        pair<int, int> res = query(nodes_at_depth[mid]);
        if (res.second == D) {
            s_final = res.first; // Found a candidate, try to find a deeper one
            l = mid + 1;
        } else {
            r = mid - 1; // The hidden nodes are not at this depth or deeper
        }
    }
    
    // Step 4: Find the second hidden node.
    // We identified one node 's_final'. The other node 'f_final' must be at distance D from 's_final'.
    // We query all nodes at distance D from 's_final'.
    
    vector<int> dist_from_s(n + 1, -1);
    vector<int> candidates_f;
    
    queue<int> q2;
    dist_from_s[s_final] = 0;
    q2.push(s_final);
    
    while (!q2.empty()) {
        int u = q2.front();
        q2.pop();
        
        if (dist_from_s[u] == D) {
            candidates_f.push_back(u);
        }
        
        for (int v : adj[u]) {
            if (dist_from_s[v] == -1) {
                dist_from_s[v] = dist_from_s[u] + 1;
                q2.push(v);
            }
        }
    }
    
    pair<int, int> f_res = query(candidates_f);
    int f_final = f_res.first;
    
    cout << "! " << s_final << " " << f_final << endl;
    
    string feedback;
    cin >> feedback;
    if (feedback != "Correct") exit(0);
}

int main() {
    // Optimization for faster I/O is not strictly necessary but good practice.
    // We rely on endl to flush, so tying doesn't matter much here, but keep sync false.
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}