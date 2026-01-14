#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

using namespace std;

const int INF = 1e9;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    int m;
    cin >> n >> m;

    vector<int> initial_state(n);
    vector<int> target_state(n);
    vector<vector<int>> adj(n);

    for (int i = 0; i < n; ++i) cin >> initial_state[i];
    for (int i = 0; i < n; ++i) cin >> target_state[i];

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<vector<int>> dist(n, vector<int>(2, INF));

    for (int color = 0; color < 2; ++color) {
        queue<int> q;
        for (int i = 0; i < n; ++i) {
            if (initial_state[i] == color) {
                dist[i][color] = 0;
                q.push(i);
            }
        }

        while (!q.empty()) {
            int u = q.front();
            q.pop();

            for (int v : adj[u]) {
                if (dist[v][color] == INF) {
                    dist[v][color] = dist[u][color] + 1;
                    q.push(v);
                }
            }
        }
    }

    vector<int> fix_time(n, 0);
    for (int i = 0; i < n; ++i) {
        if (initial_state[i] != target_state[i]) {
            fix_time[i] = dist[i][target_state[i]];
        }
    }

    for (int iter = 0; iter < n; ++iter) {
        vector<int> next_fix_time = fix_time;
        for (int i = 0; i < n; ++i) {
            if (initial_state[i] != target_state[i]) {
                int min_prev_time = INF;
                
                for (int neighbor : adj[i]) {
                    if (target_state[neighbor] == target_state[i]) {
                        min_prev_time = min(min_prev_time, fix_time[neighbor]);
                    }
                }
                
                // Also consider self, if its target color matches.
                if (target_state[i] == target_state[i]) {
                    min_prev_time = min(min_prev_time, fix_time[i]);
                }
                
                if (min_prev_time != INF) {
                    next_fix_time[i] = max(next_fix_time[i], min_prev_time + 1);
                }
            }
        }
        fix_time = next_fix_time;
    }

    int k = 0;
    for (int i = 0; i < n; ++i) {
        k = max(k, fix_time[i]);
    }

    vector<vector<int>> states;
    states.push_back(initial_state);

    vector<int> current_state = initial_state;
    for (int t = 1; t <= k; ++t) {
        vector<int> next_state = current_state;
        for (int i = 0; i < n; ++i) {
            if (t >= fix_time[i] && initial_state[i] != target_state[i]) {
                next_state[i] = target_state[i];
            }
        }
        states.push_back(next_state);
        current_state = next_state;
    }

    cout << k << endl;
    for (const auto& state : states) {
        for (int i = 0; i < n; ++i) {
            cout << state[i] << (i == n - 1 ? "" : " ");
        }
        cout << endl;
    }

    return 0;
}