#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

using namespace std;

// Function to handle interaction with the judge
// Asks for the node with minimal sum of distances in the provided subset
pair<int, int> ask(const vector<int>& q_nodes) {
    if (q_nodes.empty()) return {-1, -1};
    cout << "? " << q_nodes.size();
    for (int x : q_nodes) cout << " " << x;
    cout << endl;
    int node, dist;
    cin >> node >> dist;
    if (node == -1 && dist == -1) exit(0); // Invalid query or limit exceeded
    return {node, dist};
}

void solve() {
    int n;
    if (!(cin >> n)) return;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Step 1: Query all nodes.
    // This gives us a node 'root' that lies on the simple path between the two hidden nodes,
    // and the sum of distances between the two hidden nodes 'total_dist'.
    vector<int> all_nodes(n);
    for(int i=0; i<n; ++i) all_nodes[i] = i+1;
    pair<int, int> root_res = ask(all_nodes);
    int root = root_res.first;
    int total_dist = root_res.second;

    // Step 2: BFS from 'root' to determine depths of all nodes.
    // Also organize nodes by depth for binary search.
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

    // Step 3: Binary search to find the deeper hidden node 's'.
    // Since 'root' is on the path, the path consists of two legs extending from 'root'.
    // The sum of depths of s and f is total_dist. Thus max(depth[s], depth[f]) >= total_dist / 2.
    // We search for the largest depth 'd' such that a query on all nodes at depth 'd' returns distance 'total_dist'.
    
    int low = (total_dist + 1) / 2;
    int high = min(total_dist, max_depth);
    int s = -1; // This will store the deeper hidden node

    // If for some reason the range is invalid (shouldn't happen given problem constraints and logic),
    // s would remain -1. In that case, root would essentially be s, but logic handles it.
    if (low > high) s = root; // Edge case if total_dist=0 (nodes same), though distinct implies total_dist >= 1

    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (nodes_at_depth[mid].empty()) {
            high = mid - 1;
            continue;
        }
        pair<int, int> r = ask(nodes_at_depth[mid]);
        if (r.second == total_dist) {
            // Found a node on the path at this depth. Since it's the deepest so far, update s.
            s = r.first;
            low = mid + 1;
        } else {
            // No node on path at this depth (too deep)
            high = mid - 1;
        }
    }

    // Step 4: Find the other hidden node 'f'.
    // We know 'f' is at distance 'total_dist' from 's'.
    vector<int> dist_s(n + 1, -1);
    queue<int> qs;
    qs.push(s);
    dist_s[s] = 0;
    
    vector<int> candidates_f;
    while (!qs.empty()) {
        int u = qs.front();
        qs.pop();
        if (dist_s[u] == total_dist) {
            candidates_f.push_back(u);
        }
        for (int v : adj[u]) {
            if (dist_s[v] == -1) {
                dist_s[v] = dist_s[u] + 1;
                qs.push(v);
            }
        }
    }

    pair<int, int> f_res = ask(candidates_f);
    int f = f_res.first;

    cout << "! " << s << " " << f << endl;
    
    string verdict;
    cin >> verdict;
    if (verdict != "Correct") exit(0);
}

int main() {
    // Optimize I/O operations
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