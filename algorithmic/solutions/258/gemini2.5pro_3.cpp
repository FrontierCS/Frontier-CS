#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <queue>

using namespace std;

vector<int> adj[1005];
int n;

void solve() {
    cin >> n;
    for (int i = 1; i <= n; ++i) {
        adj[i].clear();
    }
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    cout << "? " << n;
    for (int i = 1; i <= n; ++i) {
        cout << " " << i;
    }
    cout << endl;

    int root, total_dist;
    cin >> root >> total_dist;

    vector<int> dist_from_root(n + 1, -1);
    vector<vector<int>> nodes_at_dist(n);
    vector<int> bfs_q;
    
    dist_from_root[root] = 0;
    bfs_q.push_back(root);
    nodes_at_dist[0].push_back(root);
    int head = 0;
    int max_d = 0;

    while(head < bfs_q.size()){
        int u = bfs_q[head++];
        max_d = dist_from_root[u];
        for(int v : adj[u]){
            if(dist_from_root[v] == -1){
                dist_from_root[v] = dist_from_root[u] + 1;
                bfs_q.push_back(v);
                if (dist_from_root[v] < n) {
                    nodes_at_dist[dist_from_root[v]].push_back(v);
                }
            }
        }
    }

    int s1 = root;
    int best_dist_from_root = 0;
    
    int low = (total_dist + 1) / 2;
    int high = min(max_d, total_dist);
    
    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (nodes_at_dist[mid].empty()) {
            high = mid - 1;
            continue;
        }

        cout << "? " << nodes_at_dist[mid].size();
        for (int node : nodes_at_dist[mid]) {
            cout << " " << node;
        }
        cout << endl;

        int x, d;
        cin >> x >> d;

        if (d == total_dist) {
            s1 = x;
            best_dist_from_root = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    
    int s2;
    if (best_dist_from_root == total_dist) {
        s2 = root;
    } else {
        vector<int> s2_candidates;
        int target_dist = total_dist - best_dist_from_root;
        if (target_dist >= 0 && target_dist < n) {
            s2_candidates = nodes_at_dist[target_dist];
        }
        
        cout << "? " << s2_candidates.size();
        for(int node : s2_candidates) {
            cout << " " << node;
        }
        cout << endl;
        
        int d2;
        cin >> s2 >> d2;
    }

    cout << "! " << s1 << " " << s2 << endl;

    string result;
    cin >> result;
    if (result == "Incorrect") {
        return;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}