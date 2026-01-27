#include <bits/stdc++.h>
using namespace std;

int main() {
    srand(time(0));
    int n, m;
    cin >> n >> m;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    auto get_cut = [&](const vector<int>& s) -> int {
        int c = 0;
        for (int u = 1; u <= n; u++) {
            for (int v : adj[u]) {
                if (v > u && s[u] != s[v]) c++;
            }
        }
        return c;
    };
    vector<int> best_side(n + 1);
    int best_c = -1;
    vector<int> side(n + 1);
    vector<int> gain(n + 1);
    auto compute_gains = [&]() {
        for (int u = 1; u <= n; u++) {
            int same = 0;
            for (int v : adj[u]) {
                if (side[u] == side[v]) same++;
            }
            gain[u] = 2 * same - (int)adj[u].size();
        }
    };
    auto local_search = [&]() {
        compute_gains();
        while (true) {
            int maxg = 0;
            int bestu = -1;
            for (int u = 1; u <= n; u++) {
                if (gain[u] > maxg) {
                    maxg = gain[u];
                    bestu = u;
                }
            }
            if (maxg <= 0) break;
            int old_side_val = side[bestu];
            int old_g = gain[bestu];
            side[bestu] = 1 - old_side_val;
            gain[bestu] = -old_g;
            for (int v : adj[bestu]) {
                bool was_same = (side[v] == old_side_val);
                int delta = was_same ? -1 : 1;
                gain[v] += 2 * delta;
            }
        }
    };
    // Try 1: coloring
    {
        vector<int> color(n + 1, -1);
        for (int i = 1; i <= n; i++) {
            if (color[i] != -1) continue;
            queue<int> q;
            q.push(i);
            color[i] = 0;
            while (!q.empty()) {
                int u = q.front(); q.pop();
                for (int v : adj[u]) {
                    if (color[v] == -1) {
                        color[v] = 1 - color[u];
                        q.push(v);
                    }
                }
            }
        }
        for (int i = 1; i <= n; i++) side[i] = color[i];
        local_search();
        int c = get_cut(side);
        best_c = c;
        best_side = side;
    }
    // Additional random tries
    int num_tries = 4;
    for (int tryy = 0; tryy < num_tries; tryy++) {
        for (int i = 1; i <= n; i++) {
            side[i] = rand() % 2;
        }
        local_search();
        int c = get_cut(side);
        if (c > best_c) {
            best_c = c;
            best_side = side;
        }
    }
    // Output
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << " ";
        cout << best_side[i];
    }
    cout << endl;
    return 0;
}