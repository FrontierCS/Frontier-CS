#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <set>
#include <queue>

using namespace std;

int n, m, start_node, base_move_count;
vector<vector<int>> adj;
vector<int> degree;

void read_graph() {
    cin >> n >> m >> start_node >> base_move_count;
    adj.assign(n + 1, vector<int>());
    degree.assign(n + 1, 0);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    for (int i = 1; i <= n; ++i) {
        degree[i] = adj[i].size();
        sort(adj[i].begin(), adj[i].end());
    }
}

void solve() {
    read_graph();

    vector<bool> visited(n + 1, false);
    int visited_count = 0;

    int current_node = start_node;
    visited[current_node] = true;
    visited_count = 1;

    while (true) {
        if (visited_count == n) {
            string resp;
            cin >> resp; // "AC"
            break;
        }

        int d;
        cin >> d;
        vector<pair<int, int>> interactor_neighbors(d);
        for (int i = 0; i < d; ++i) {
            cin >> interactor_neighbors[i].first >> interactor_neighbors[i].second;
        }

        vector<int> unvisited_neighbors;
        for (int neighbor : adj[current_node]) {
            if (!visited[neighbor]) {
                unvisited_neighbors.push_back(neighbor);
            }
        }

        int target_node = -1;

        if (!unvisited_neighbors.empty()) {
            target_node = unvisited_neighbors[0]; // Simplest: pick smallest label
        } else {
            // Backtrack: find neighbor closest to an unvisited node
            queue<int> q;
            vector<int> dist(n + 1, -1);
            for (int i = 1; i <= n; ++i) {
                if (!visited[i]) {
                    q.push(i);
                    dist[i] = 0;
                }
            }
            while(!q.empty()){
                int u = q.front();
                q.pop();
                for(int v : adj[u]){
                    if(dist[v] == -1){
                        dist[v] = dist[u] + 1;
                        q.push(v);
                    }
                }
            }

            int min_dist = 1e9;
            for (int neighbor : adj[current_node]) {
                if (dist[neighbor] < min_dist) {
                    min_dist = dist[neighbor];
                    target_node = neighbor;
                }
            }
        }

        int target_degree = degree[target_node];
        bool target_is_visited = visited[target_node];

        int move_idx = -1;
        for (int i = 0; i < d; ++i) {
            if (interactor_neighbors[i].first == target_degree && interactor_neighbors[i].second == (int)target_is_visited) {
                move_idx = i + 1;
                break;
            }
        }
        cout << move_idx << endl;

        vector<int> possible_locations;
        for (int neighbor : adj[current_node]) {
            if (degree[neighbor] == target_degree && visited[neighbor] == target_is_visited) {
                possible_locations.push_back(neighbor);
            }
        }

        string resp;
        cin >> resp;
        if (resp == "AC" || resp == "F") {
            break;
        }
        
        int new_d = stoi(resp);
        multiset<pair<int, int>> received_sig;
        for (int i = 0; i < new_d; ++i) {
            int deg, flag;
            cin >> deg >> flag;
            received_sig.insert({deg, flag});
        }

        int new_current_node = -1;

        if (possible_locations.size() == 1) {
            new_current_node = possible_locations[0];
        } else {
            for (int cand : possible_locations) {
                if (degree[cand] != new_d) continue;

                vector<bool> visited_temp = visited;
                visited_temp[cand] = true;

                multiset<pair<int, int>> expected_sig;
                for (int neighbor_of_cand : adj[cand]) {
                    expected_sig.insert({degree[neighbor_of_cand], (int)visited_temp[neighbor_of_cand]});
                }

                if (expected_sig == received_sig) {
                    new_current_node = cand;
                    break;
                }
            }
        }
        
        current_node = new_current_node;
        if (!visited[current_node]) {
            visited[current_node] = true;
            visited_count++;
        }
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