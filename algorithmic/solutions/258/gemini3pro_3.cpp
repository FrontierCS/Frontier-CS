#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <numeric>
#include <cstdlib>

using namespace std;

const int MAXN = 1005;

vector<int> adj[MAXN];
int depths[MAXN];
int n;

// BFS to compute depths of all nodes from a given root
void bfs_depths(int root) {
    for(int i = 1; i <= n; ++i) {
        depths[i] = -1;
    }
    queue<int> q;
    q.push(root);
    depths[root] = 0;
    
    while(!q.empty()){
        int u = q.front();
        q.pop();
        for(int v : adj[u]){
            if(depths[v] == -1){
                depths[v] = depths[u] + 1;
                q.push(v);
            }
        }
    }
}

// BFS to compute distances from a source node to all other nodes
vector<int> bfs_dist(int src) {
    vector<int> d(n + 1, -1);
    queue<int> q;
    q.push(src);
    d[src] = 0;
    while(!q.empty()){
        int u = q.front();
        q.pop();
        for(int v : adj[u]){
            if(d[v] == -1){
                d[v] = d[u] + 1;
                q.push(v);
            }
        }
    }
    return d;
}

// Function to perform a query
pair<int, int> ask(const vector<int>& nodes) {
    if(nodes.empty()) return {-1, -1};
    cout << "? " << nodes.size();
    for(int x : nodes) {
        cout << " " << x;
    }
    cout << endl;
    int x, d;
    cin >> x >> d;
    if(x == -1 && d == -1) exit(0);
    return {x, d};
}

void solve() {
    cin >> n;
    for(int i = 1; i <= n; ++i) adj[i].clear();
    for(int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Step 1: Query all nodes to find a node 'root' on the simple path between s and f
    // and the distance L = dist(s, f).
    vector<int> all_nodes(n);
    iota(all_nodes.begin(), all_nodes.end(), 1);
    pair<int, int> initial = ask(all_nodes);
    int root = initial.first;
    int L = initial.second;

    // Step 2: Root the tree at 'root'. Now LCA(s, f) = root.
    // Calculate depths. s and f are in subtrees of root (or one is root).
    bfs_depths(root);
    
    int max_d = 0;
    for(int i = 1; i <= n; ++i) max_d = max(max_d, depths[i]);

    // Step 3: Binary search for the deeper node among s and f. Let's say s is deeper.
    // We know depth(s) + depth(f) = L.
    // Thus, depth(s) >= ceil(L/2).
    // We search for the maximum depth 'd' such that querying nodes at depth 'd' returns a distance sum of L.
    // The node returned by the successful query at the maximum depth will be s.
    
    int low = (L + 1) / 2;
    int high = min(L, max_d);
    int s_node = -1;

    while(low <= high) {
        int mid = (low + high) / 2;
        vector<int> layer;
        for(int i = 1; i <= n; ++i) {
            if(depths[i] == mid) layer.push_back(i);
        }

        if(layer.empty()) {
            high = mid - 1;
            continue;
        }

        pair<int, int> res = ask(layer);
        // If dist sum is L, then there is a node on the s-f path at this depth.
        // Since we are looking at depths >= L/2, this node must be an ancestor of s (or s itself).
        if(res.second == L) {
            s_node = res.first;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }

    // Step 4: We found s (s_node). Now we need to find f.
    // We know dist(s, f) = L.
    // We query all nodes at distance L from s. f is guaranteed to be one of them and will have min dist sum L.
    vector<int> dist_s = bfs_dist(s_node);
    vector<int> candidates_f;
    for(int i = 1; i <= n; ++i) {
        if(dist_s[i] == L) candidates_f.push_back(i);
    }

    pair<int, int> res_f = ask(candidates_f);
    int f_node = res_f.first;

    cout << "! " << s_node << " " << f_node << endl;
    
    string result;
    cin >> result;
    if(result != "Correct") exit(0);
}

int main() {
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}