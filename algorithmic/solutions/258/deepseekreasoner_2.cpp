#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <string>

using namespace std;

vector<vector<int>> adj;
vector<int> depth;
int n;

void bfs_depth(int root, int &max_d) {
    fill(depth.begin(), depth.end(), -1);
    queue<int> q;
    
    depth[root] = 0;
    q.push(root);
    max_d = 0;
    
    while(!q.empty()){
        int u = q.front();
        q.pop();
        max_d = max(max_d, depth[u]);
        
        for(int v : adj[u]){
            if(depth[v] == -1){
                depth[v] = depth[u] + 1;
                q.push(v);
            }
        }
    }
}

void bfs_dist(int start, vector<int>& d) {
    fill(d.begin(), d.end(), -1);
    queue<int> q;
    d[start] = 0;
    q.push(start);
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
}

void solve() {
    if (!(cin >> n)) return;
    adj.assign(n + 1, vector<int>());
    depth.assign(n + 1, 0);
    
    for(int i = 0; i < n - 1; ++i){
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Attempt to find a node on the path between hidden nodes by querying all nodes.
    // The returned node 'root' will be on the simple path between s and f.
    // The returned distance 'D' will be dist(s, f).
    cout << "? " << n;
    for(int i = 1; i <= n; ++i) cout << " " << i;
    cout << endl;

    int root, D;
    cin >> root >> D;
    if(root == -1) exit(0);

    // Root the tree at 'root' and compute depths.
    int max_d;
    bfs_depth(root, max_d);

    vector<vector<int>> layers(max_d + 1);
    for(int i = 1; i <= n; ++i){
        layers[depth[i]].push_back(i);
    }

    // Binary search to find the node on the path with maximum depth.
    // Since root is on the path, the path from s to f passes through root.
    // Thus dist(s, f) = depth(s) + depth(f) = D.
    // Let n1 be the hidden node with greater depth. Then depth(n1) >= D/2.
    // We search in range [ceil(D/2), min(max_d, D)].
    // A query at depth 'mid' with return distance D implies the path reaches depth 'mid'.
    
    int low = (D + 1) / 2;
    int high = min(max_d, D);
    int n1 = -1;
    
    while(low <= high){
        int mid = low + (high - low) / 2;
        if(layers[mid].empty()){
             high = mid - 1;
             continue;
        }

        cout << "? " << layers[mid].size();
        for(int x : layers[mid]) cout << " " << x;
        cout << endl;

        int node, dist_sum;
        cin >> node >> dist_sum;
        if(node == -1) exit(0);

        if(dist_sum == D){
            n1 = node;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    
    // n1 is now one of the hidden nodes.
    // finding n2: n2 is at distance D from n1.
    vector<int> dists(n + 1);
    bfs_dist(n1, dists);
    
    vector<int> candidates;
    for(int i = 1; i <= n; ++i){
        if(dists[i] == D){
            candidates.push_back(i);
        }
    }

    int n2 = -1;
    if(candidates.empty()){
        // Should not happen
    } else {
        cout << "? " << candidates.size();
        for(int x : candidates) cout << " " << x;
        cout << endl;
        
        int node, dist_sum;
        cin >> node >> dist_sum;
        if(node == -1) exit(0);
        n2 = node;
    }

    cout << "! " << n1 << " " << n2 << endl;
    
    string check;
    cin >> check;
    if(check != "Correct") exit(0);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while(t--){
            solve();
        }
    }
    return 0;
}