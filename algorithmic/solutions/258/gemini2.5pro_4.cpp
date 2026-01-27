#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <queue>
#include <string>

using namespace std;

vector<vector<int>> adj;
int n;

pair<int, int> ask(const vector<int>& nodes) {
    if (nodes.empty()) {
        return {-1, -1};
    }
    cout << "? " << nodes.size();
    for (int node : nodes) {
        cout << " " << node;
    }
    cout << endl;
    int x, d;
    cin >> x >> d;
    if (x == -1) exit(0);
    return {x, d};
}

void answer(int u, int v) {
    cout << "! " << u << " " << v << endl;
    string response;
    cin >> response;
    if (response == "Incorrect") exit(0);
}

void bfs(int start, vector<int>& dist) {
    dist.assign(n + 1, -1);
    queue<int> q;

    dist[start] = 0;
    q.push(start);

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
    pair<int, int> response = ask(all_nodes);
    int root = response.first;
    int total_dist = response.second;

    vector<int> dist_from_root;
    bfs(root, dist_from_root);

    int endpoint1 = root;

    int low = 0, high = total_dist;
    
    while (low <= high) {
        int mid = low + (high - low) / 2;
        
        vector<int> nodes_at_dist;
        for (int i = 1; i <= n; ++i) {
            if (dist_from_root[i] == mid) {
                nodes_at_dist.push_back(i);
            }
        }

        if (nodes_at_dist.empty()) {
            high = mid - 1;
            continue;
        }

        response = ask(nodes_at_dist);
        if (response.second == total_dist) {
            endpoint1 = response.first;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }

    vector<int> dist_from_endpoint1;
    bfs(endpoint1, dist_from_endpoint1);

    int endpoint2 = -1;
    vector<int> candidates;
    for (int i = 1; i <= n; ++i) {
        if (dist_from_endpoint1[i] == total_dist) {
            candidates.push_back(i);
        }
    }
    
    if (candidates.size() == 1) {
        endpoint2 = candidates[0];
    } else {
        response = ask(candidates);
        endpoint2 = response.first;
    }
    
    answer(endpoint1, endpoint2);
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