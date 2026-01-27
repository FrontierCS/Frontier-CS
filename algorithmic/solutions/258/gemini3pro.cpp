#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <cstdlib>

using namespace std;

// Global adjacency list
vector<vector<int>> adj;

// Helper to perform queries
// Prints "? c node1 node2 ... nodec" and returns {node, dist}
pair<int, int> query(const vector<int>& nodes) {
    if (nodes.empty()) return {-1, -1};
    cout << "? " << nodes.size();
    for (int node : nodes) {
        cout << " " << node;
    }
    cout << endl; // Flushes output
    
    int x, d;
    cin >> x >> d;
    if (x == -1 && d == -1) exit(0); // Terminate on invalid query/judge error
    return {x, d};
}

// BFS to compute distances from a source node
void bfs(int src, int n, vector<int>& dist) {
    dist.assign(n + 1, -1);
    queue<int> q;
    q.push(src);
    dist[src] = 0;
    
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (int v : adj[u]) {
            if (dist[v] == -1) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
    }
}

void solve() {
    int n;
    cin >> n;
    adj.assign(n + 1, vector<int>());
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Step 1: Query all nodes.
    // The returned node 'root' will be on the simple path between the two hidden nodes.
    // The returned distance 'L' is the distance between the two hidden nodes.
    vector<int> all_nodes(n);
    for (int i = 0; i < n; ++i) all_nodes[i] = i + 1;
    pair<int, int> res = query(all_nodes);
    int root = res.first;
    int L = res.second;

    // Step 2: BFS from 'root' to determine the depth of every node relative to 'root'.
    vector<int> depth;
    bfs(root, n, depth);
    
    int max_depth = 0;
    for (int i = 1; i <= n; ++i) {
        if (depth[i] > max_depth) max_depth = depth[i];
    }

    // Step 3: Binary search for the deepest node on the path between the two hidden nodes.
    // Since 'root' is on the path, the path goes down into the subtrees (or stays at root).
    // The hidden nodes are the "lowest" points of this path in the rooted tree.
    // At least one hidden node has depth >= ceil(L/2).
    // We look for a node at depth d such that dist(node, hidden) + dist(node, hidden) == L.
    // Since we query all nodes at depth d, if the result distance is L, 
    // it means at least one node at this depth is on the path.
    
    int low = (L + 1) / 2;
    int high = min(L, max_depth);
    int s = root; // Fallback, though s will be updated in loop

    while (low <= high) {
        int mid = (low + high) / 2;
        vector<int> nodes_at_mid;
        for (int i = 1; i <= n; ++i) {
            if (depth[i] == mid) {
                nodes_at_mid.push_back(i);
            }
        }
        
        if (nodes_at_mid.empty()) {
            high = mid - 1;
            continue;
        }

        pair<int, int> q_res = query(nodes_at_mid);
        if (q_res.second == L) {
            // Found a node on the path at this depth.
            // This node is a candidate for being one of the hidden nodes.
            // We try to find a deeper one.
            s = q_res.first;
            low = mid + 1;
        } else {
            // No node at this depth is on the path.
            high = mid - 1;
        }
    }

    // 's' is now determined to be one of the hidden nodes.
    // The other hidden node 'f' must be at distance L from 's'.
    vector<int> dist_s;
    bfs(s, n, dist_s);
    
    vector<int> candidates;
    for (int i = 1; i <= n; ++i) {
        if (dist_s[i] == L) {
            candidates.push_back(i);
        }
    }

    int f;
    if (candidates.size() == 1) {
        f = candidates[0];
    } else {
        // Query the candidates to distinguish 'f'
        pair<int, int> f_res = query(candidates);
        f = f_res.first;
    }

    cout << "! " << s << " " << f << endl;
    
    string feedback;
    cin >> feedback;
    if (feedback == "Incorrect") exit(0);
}

int main() {
    // Fast I/O
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