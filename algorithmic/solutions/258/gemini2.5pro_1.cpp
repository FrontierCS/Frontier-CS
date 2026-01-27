#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

vector<int> adj[1005];
int n;

// Function to perform a query
pair<int, int> do_query(const vector<int>& nodes) {
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
    if (x == -1 && d == -1) {
        exit(0);
    }
    return {x, d};
}

// Function to output the answer
void answer(int u, int v) {
    cout << "! " << u << " " << v << endl;
    string response;
    cin >> response;
    if (response == "Incorrect") {
        exit(0);
    }
}

// Standard BFS to compute distances from a starting node
void bfs(int start, vector<int>& dist) {
    dist.assign(n + 1, -1);
    vector<int> q;
    q.push_back(start);
    dist[start] = 0;
    int head = 0;
    while(head < (int)q.size()){
        int u = q[head++];
        for(int v : adj[u]){
            if(dist[v] == -1){
                dist[v] = dist[u] + 1;
                q.push_back(v);
            }
        }
    }
}

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

    // Stage 1: Query all nodes to find a node `r` on the path and path length `L`
    vector<int> all_nodes(n);
    iota(all_nodes.begin(), all_nodes.end(), 1);

    pair<int, int> res = do_query(all_nodes);
    int r = res.first;
    int L = res.second;

    vector<int> dist_r;
    bfs(r, dist_r);

    vector<vector<int>> levels(n);
    for (int i = 1; i <= n; ++i) {
        if (dist_r[i] != -1 && dist_r[i] < n) {
            levels[dist_r[i]].push_back(i);
        }
    }

    // Stage 2: Find one of the hidden nodes, s1
    int s1;
    // The distance from r to the farther endpoint is at least ceil(L/2)
    int low = (L + 1) / 2, high = L;
    int endpoint_candidate = r;
    
    // Binary search for the distance to the farther endpoint
    while(low <= high) {
        int mid = low + (high - low) / 2;
        if (mid >= n || levels[mid].empty()) {
            high = mid - 1;
            continue;
        }
        res = do_query(levels[mid]);
        if (res.second == L) {
            endpoint_candidate = res.first;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    s1 = endpoint_candidate;

    // We have one endpoint s1, find the other (s2) which is at distance L
    vector<int> dist_s1;
    bfs(s1, dist_s1);

    vector<int> candidates;
    for (int i = 1; i <= n; ++i) {
        if (dist_s1[i] == L) {
            candidates.push_back(i);
        }
    }

    int s2;
    if (candidates.size() == 1) {
        s2 = candidates[0];
    } else {
        res = do_query(candidates);
        s2 = res.first;
    }

    answer(s1, s2);
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