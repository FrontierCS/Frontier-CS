#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <string>

using namespace std;

int n;
vector<vector<int>> adj;
vector<int> depth;
vector<vector<int>> nodes_by_depth;

pair<int, int> ask(const vector<int>& nodes) {
    if (nodes.empty()) {
        return {-1, 1e9 + 7}; 
    }
    cout << "? " << nodes.size();
    for (int node : nodes) {
        cout << " " << node;
    }
    cout << endl;
    int x, d;
    cin >> x >> d;
    if (x == -1 && d == -1) {
        exit(0);
    }
    return {x, d};
}

void answer(int u, int v) {
    cout << "! " << u << " " << v << endl;
    string response;
    cin >> response;
    if (response == "Incorrect") {
        exit(0);
    }
}

void bfs(int start_node) {
    depth.assign(n + 1, -1);
    nodes_by_depth.assign(n + 1, vector<int>());
    vector<int> q;

    q.push_back(start_node);
    depth[start_node] = 0;
    nodes_by_depth[0].push_back(start_node);

    int head = 0;
    while(head < q.size()) {
        int u = q[head++];
        for (int v : adj[u]) {
            if (depth[v] == -1) {
                depth[v] = depth[u] + 1;
                if (depth[v] <= n) {
                    nodes_by_depth[depth[v]].push_back(v);
                }
                q.push_back(v);
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

    vector<int> all_nodes(n);
    iota(all_nodes.begin(), all_nodes.end(), 1);
    
    pair<int, int> res = ask(all_nodes);
    int root = res.first;
    int total_dist = res.second;

    bfs(root);
    
    int max_depth = 0;
    for(int i = n; i >= 0; --i) {
        if (!nodes_by_depth[i].empty()) {
            max_depth = i;
            break;
        }
    }
    
    int s1_dist = 0;
    int s1 = root;

    int low = (total_dist + 1) / 2;
    int high = min(total_dist, max_depth);

    if (low <= high) {
        while(low <= high) {
            int mid = low + (high - low) / 2;
            if (nodes_by_depth[mid].empty()) {
                high = mid - 1;
                continue;
            }
            res = ask(nodes_by_depth[mid]);
            if (res.second == total_dist) {
                s1_dist = mid;
                s1 = res.first;
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }
    }
    
    int s2_dist = total_dist - s1_dist;
    int s2;

    if (s1_dist == s2_dist) {
        vector<int> candidates;
        for (int node : nodes_by_depth[s2_dist]) {
            if (node != s1) {
                candidates.push_back(node);
            }
        }
        res = ask(candidates);
        s2 = res.first;
    } else {
        res = ask(nodes_by_depth[s2_dist]);
        s2 = res.first;
    }
    
    answer(s1, s2);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    while(t--) {
        solve();
    }
    return 0;
}