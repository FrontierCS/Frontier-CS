#include <iostream>
#include <vector>
#include <queue>
#include <numeric>
#include <algorithm>

using namespace std;

// Function to perform a query
// Prints query in specified format and reads the response
pair<int, int> ask(const vector<int>& nodes) {
    if (nodes.empty()) return {-1, -1};
    cout << "? " << nodes.size();
    for (int u : nodes) {
        cout << " " << u;
    }
    cout << endl; // Flushes output
    
    int x, d;
    cin >> x >> d;
    if (x == -1) exit(0); // Should terminate if invalid query or limit exceeded
    return {x, d};
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

    // Step 1: Query all nodes.
    // The returned node 'root' implies it lies on the simple path between the two hidden nodes.
    // The returned distance is exactly dist(s, f).
    vector<int> all_nodes(n);
    iota(all_nodes.begin(), all_nodes.end(), 1);
    pair<int, int> info = ask(all_nodes);
    int root = info.first;
    int dist_sf = info.second;

    // Step 2: BFS from 'root' to organize nodes by depth (layers).
    vector<int> depth(n + 1, -1);
    vector<vector<int>> layers(n + 1);
    queue<int> q;
    
    depth[root] = 0;
    layers[0].push_back(root);
    q.push(root);
    
    int max_depth = 0;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        max_depth = max(max_depth, depth[u]);
        for (int v : adj[u]) {
            if (depth[v] == -1) {
                depth[v] = depth[u] + 1;
                layers[depth[v]].push_back(v);
                q.push(v);
            }
        }
    }

    // Step 3: Binary Search to find one of the hidden nodes.
    // The path between s and f consists of a segment going 'down' from root to s,
    // and/or a segment going 'down' from root to f. 
    // At least one of the nodes is at depth >= ceil(dist_sf / 2).
    // We search for the deepest node that is still on the path (dist from s+f is minimal).
    
    int l = (dist_sf + 1) / 2;
    int r = min(max_depth, dist_sf);
    int node1 = -1; 

    while (l <= r) {
        int mid = l + (r - l) / 2;
        if (layers[mid].empty()) {
            r = mid - 1;
            continue;
        }
        
        pair<int, int> res = ask(layers[mid]);
        if (res.second == dist_sf) {
            // If the minimum sum of distances is still dist_sf, then a node on the path
            // exists at this depth. The returned node 'res.first' is on the path.
            node1 = res.first;
            l = mid + 1; // Try to go deeper
        } else {
            // If distance > dist_sf, then no node at this depth is on the path.
            r = mid - 1;
        }
    }

    // Fallback if binary search didn't find anything (unlikely given problem constraints + logic)
    if (node1 == -1) node1 = root;

    // Step 4: Find the second hidden node.
    // We found one node 'node1'. The other node 'node2' must be exactly dist_sf away from 'node1'.
    vector<int> dist_from_node1(n + 1, -1);
    queue<int> q2;
    q2.push(node1);
    dist_from_node1[node1] = 0;
    
    vector<int> candidates;
    
    while (!q2.empty()) {
        int u = q2.front(); q2.pop();
        if (dist_from_node1[u] == dist_sf) {
            candidates.push_back(u);
        }
        for (int v : adj[u]) {
            if (dist_from_node1[v] == -1) {
                dist_from_node1[v] = dist_from_node1[u] + 1;
                q2.push(v);
            }
        }
    }
    
    // Query the candidate set. The system considers sum of distances to hid nodes.
    // Since 'node2' is in candidates, sum = d(node2, node1) + d(node2, node2) = dist_sf + 0 = dist_sf.
    // This is minimal, so 'node2' will (or an equivalent valid node) be returned.
    pair<int, int> res_node2 = ask(candidates);
    int node2 = res_node2.first;

    cout << "! " << node1 << " " << node2 << endl;
    
    string verdict;
    cin >> verdict;
    if (verdict != "Correct") exit(0);
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