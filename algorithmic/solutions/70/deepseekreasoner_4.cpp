#include <bits/stdc++.h>
using namespace std;

void solve_one() {
    int n, m, start, base_move_count;
    cin >> n >> m >> start >> base_move_count;
    vector<vector<int>> adj(n + 1);
    vector<int> degree(n + 1, 0);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    for (int i = 1; i <= n; ++i) {
        degree[i] = adj[i].size();
    }
    vector<bool> visited(n + 1, false);
    int current = start;
    visited[current] = true;
    while (true) {
        int d;
        cin >> d;
        vector<pair<int, int>> cur_nei(d);
        for (int i = 0; i < d; ++i) {
            cin >> cur_nei[i].first >> cur_nei[i].second;
        }
        // BFS to find nearest unvisited vertex
        vector<int> parent(n + 1, -1);
        queue<int> q;
        q.push(current);
        parent[current] = 0;
        int target = -1;
        while (!q.empty()) {
            int v = q.front();
            q.pop();
            if (!visited[v]) {
                target = v;
                break;
            }
            for (int w : adj[v]) {
                if (parent[w] == -1) {
                    parent[w] = v;
                    q.push(w);
                }
            }
        }
        if (target == -1) {
            // Should not happen, but fallback
            cout << 1 << endl;
            string token;
            cin >> token;
            if (token == "AC" || token == "F") break;
            // If it's a description, we must read the rest and continue
            int d_new = stoi(token);
            for (int i = 0; i < d_new; ++i) {
                int deg, flag;
                cin >> deg >> flag;
            }
            continue;
        }
        // Determine first step on the shortest path
        int next_v = target;
        while (parent[next_v] != current) {
            next_v = parent[next_v];
        }
        // Choose an index matching (degree[next_v], visited[next_v])
        pair<int, int> target_pair = {degree[next_v], visited[next_v]};
        int chosen_index = -1;
        for (int i = 0; i < d; ++i) {
            if (cur_nei[i] == target_pair) {
                chosen_index = i + 1;
                break;
            }
        }
        if (chosen_index == -1) {
            chosen_index = 1; // fallback
        }
        cout << chosen_index << endl;
        // Read response
        string token;
        cin >> token;
        if (token == "AC") {
            break;
        } else if (token == "F") {
            break;
        } else {
            int d_new = stoi(token);
            vector<pair<int, int>> new_nei(d_new);
            for (int i = 0; i < d_new; ++i) {
                cin >> new_nei[i].first >> new_nei[i].second;
            }
            // Identify new vertex
            int deg_chosen = cur_nei[chosen_index - 1].first;
            int flag_chosen = cur_nei[chosen_index - 1].second;
            vector<int> candidates;
            for (int w : adj[current]) {
                if (degree[w] == deg_chosen && visited[w] == flag_chosen) {
                    candidates.push_back(w);
                }
            }
            vector<int> matched;
            for (int w : candidates) {
                if (degree[w] != d_new) continue;
                vector<pair<int, int>> expected;
                for (int u : adj[w]) {
                    expected.push_back({degree[u], visited[u]});
                }
                sort(expected.begin(), expected.end());
                vector<pair<int, int>> observed = new_nei;
                sort(observed.begin(), observed.end());
                if (expected == observed) {
                    matched.push_back(w);
                }
            }
            int new_vertex;
            if (matched.empty()) {
                // Fallback: first candidate with correct degree
                for (int w : candidates) {
                    if (degree[w] == d_new) {
                        matched.push_back(w);
                        break;
                    }
                }
                if (matched.empty()) {
                    // Last resort: first candidate
                    if (!candidates.empty()) {
                        matched.push_back(candidates[0]);
                    } else {
                        // This should not happen; stay put
                        new_vertex = current;
                        visited[new_vertex] = true;
                        current = new_vertex;
                        continue;
                    }
                }
            }
            new_vertex = matched[0];
            if (!visited[new_vertex]) {
                visited[new_vertex] = true;
            }
            current = new_vertex;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int t;
    cin >> t;
    while (t--) {
        solve_one();
    }
    return 0;
}