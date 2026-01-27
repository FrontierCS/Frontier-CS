#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

using namespace std;

// Maximum number of nodes as per constraints (N <= 1000)
const int MAXN = 1005;
vector<int> adj[MAXN];
vector<int> nodes_at_depth[MAXN];

// Function to perform a query
pair<int, int> ask(const vector<int>& nodes) {
    if (nodes.empty()) return {-1, -1};
    cout << "? " << nodes.size();
    for (int u : nodes) {
        cout << " " << u;
    }
    cout << endl;
    
    int x, d;
    cin >> x >> d;
    if (x == -1 && d == -1) {
        exit(0);
    }
    return {x, d};
}

void solve() {
    int n;
    cin >> n;
    
    // Clear data structures for new test case
    for (int i = 1; i <= n; ++i) {
        adj[i].clear();
    }
    for (int i = 0; i <= n; ++i) {
        nodes_at_depth[i].clear();
    }
    
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    // Step 1: Query all nodes to find the dist(s, f) and a node on the simple path between s and f
    vector<int> all_nodes(n);
    for (int i = 0; i < n; ++i) all_nodes[i] = i + 1;
    
    pair<int, int> root_res = ask(all_nodes);
    int root = root_res.first;
    int len = root_res.second;
    
    // Step 2: Root the tree at the returned node and calculate depths
    // Since 'root' is on the path between s and f, one of s or f is in one subtree (or is root)
    // and the other is in another subtree (or is root).
    vector<int> depth(n + 1, -1);
    queue<int> q;
    
    depth[root] = 0;
    q.push(root);
    nodes_at_depth[0].push_back(root);
    
    int max_d = 0;
    
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        
        if (depth[u] > max_d) max_d = depth[u];
        
        for (int v : adj[u]) {
            if (depth[v] == -1) {
                depth[v] = depth[u] + 1;
                nodes_at_depth[depth[v]].push_back(v);
                q.push(v);
            }
        }
    }
    
    // Step 3: Binary Search for the hidden node with the maximum depth from 'root'
    // Let's call this node 's'.
    // The path from root to 's' has length depth[s]. The path from root to 'f' has length depth[f].
    // len = depth[s] + depth[f].
    // Assuming s is the deeper node, depth[s] >= len / 2.
    // We search for the largest depth 'd' such that a node at depth 'd' is on the s-f path.
    
    int l = (len + 1) / 2;
    int r = min(max_d, len); 
    int s = -1;
    
    // If len=0 (not possible per problem statement "distinct nodes"), s=root.
    if (len == 0) s = root;

    while (l <= r) {
        int mid = l + (r - l) / 2;
        if (nodes_at_depth[mid].empty()) {
            r = mid - 1;
            continue;
        }
        
        pair<int, int> res = ask(nodes_at_depth[mid]);
        
        // If the query returns minimal possible distance 'len', 
        // it means one of the nodes at this depth is on the path.
        if (res.second == len) {
            s = res.first;
            l = mid + 1;
        } else {
            r = mid - 1;
        }
    }
    
    // Step 4: Find the second hidden node 'f'.
    // We know dist(s, f) = len.
    // Query all nodes that are at distance 'len' from 's'.
    vector<int> dist_from_s(n + 1, -1);
    vector<int> candidates;
    queue<int> q2;
    
    dist_from_s[s] = 0;
    q2.push(s);
    
    while (!q2.empty()) {
        int u = q2.front();
        q2.pop();
        
        if (dist_from_s[u] == len) {
            candidates.push_back(u);
        }
        
        if (dist_from_s[u] < len) {
            for (int v : adj[u]) {
                if (dist_from_s[v] == -1) {
                    dist_from_s[v] = dist_from_s[u] + 1;
                    q2.push(v);
                }
            }
        }
    }
    
    pair<int, int> f_res = ask(candidates);
    int f = f_res.first;
    
    cout << "! " << s << " " << f << endl;
    
    string verdict;
    cin >> verdict;
    if (verdict != "Correct") {
        exit(0);
    }
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