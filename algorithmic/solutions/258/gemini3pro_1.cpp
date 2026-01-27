#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <numeric>

using namespace std;

// Global variables to store graph and depth information
int n;
vector<int> adj[1005];
int depth[1005];
vector<int> nodes_by_depth[1005];

// Function to perform a query to the interactive judge
// Returns a pair {node, sum_of_distances}
pair<int, int> ask(const vector<int>& nodes) {
    if (nodes.empty()) return {-1, -1};
    cout << "? " << nodes.size();
    for (int u : nodes) cout << " " << u;
    cout << endl;
    int x, d;
    cin >> x >> d;
    if (x == -1 && d == -1) exit(0); // Invalid query or limit exceeded
    return {x, d};
}

void solve() {
    cin >> n;
    // Clear data structures for the new test case
    for (int i = 1; i <= n; ++i) {
        adj[i].clear();
        nodes_by_depth[i].clear();
    }
    nodes_by_depth[0].clear();

    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Initial query with all nodes.
    // This gives us the distance between the two hidden nodes (dist_sf)
    // and one node 'r' that lies on the simple path between them.
    vector<int> all_nodes(n);
    iota(all_nodes.begin(), all_nodes.end(), 1);
    pair<int, int> res = ask(all_nodes);
    int r = res.first;
    int dist_sf = res.second;

    // Root the tree at node 1 and compute depths of all nodes
    fill(depth, depth + n + 1, -1);
    queue<int> q;
    q.push(1);
    depth[1] = 0;
    nodes_by_depth[0].push_back(1);
    
    int max_h = 0;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        max_h = max(max_h, depth[u]);
        for (int v : adj[u]) {
            if (depth[v] == -1) {
                depth[v] = depth[u] + 1;
                nodes_by_depth[depth[v]].push_back(v);
                q.push(v);
            }
        }
    }

    // Binary search for the deeper hidden node s.
    // We know r is on the path. Let s be the node on the path with the greatest depth.
    // Then depth[s] >= depth[r].
    // We search for the largest depth d such that a query with nodes of depth >= d returns distance dist_sf.
    int best_node = r;
    int low = depth[r] + 1;
    int high = max_h;
    
    while (low <= high) {
        int mid = (low + high) / 2;
        vector<int> query_nodes;
        // Collect all nodes with depth >= mid
        for (int d = mid; d <= max_h; ++d) {
            for (int u : nodes_by_depth[d]) {
                query_nodes.push_back(u);
            }
        }
        
        if (query_nodes.empty()) {
            high = mid - 1;
            continue;
        }
        
        pair<int, int> q_res = ask(query_nodes);
        // If the minimal distance is dist_sf, then one of the hidden nodes is in the query set.
        // Since we query deeper nodes, this means the deeper node s has depth >= mid.
        if (q_res.second == dist_sf) {
            best_node = q_res.first;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    
    int s = best_node;
    
    // Now we have found s. We need to find f.
    // We know dist(s, f) = dist_sf.
    // We query all nodes at exactly distance dist_sf from s.
    // The response will be f.
    
    vector<int> dist_s(n + 1, -1);
    q.push(s); // q is empty here
    dist_s[s] = 0;
    vector<int> candidates;
    
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        if (dist_s[u] == dist_sf) {
            candidates.push_back(u);
        }
        // Optimization: we don't need to traverse beyond distance dist_sf
        if (dist_s[u] < dist_sf) {
            for (int v : adj[u]) {
                if (dist_s[v] == -1) {
                    dist_s[v] = dist_s[u] + 1;
                    q.push(v);
                }
            }
        }
    }
    
    pair<int, int> f_res = ask(candidates);
    int f = f_res.first;
    
    cout << "! " << s << " " << f << endl;
    
    string feedback;
    cin >> feedback;
    if (feedback != "Correct") exit(0);
}

int main() {
    // Optimize I/O operations (though flush is needed, cin/cout with endl is safe enough)
    // ios_base::sync_with_stdio(false); cin.tie(NULL); 
    
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}