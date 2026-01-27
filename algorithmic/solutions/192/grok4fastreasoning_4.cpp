#include <bits/stdc++.h>
using namespace std;

int main() {
    srand(time(NULL));
    int n, m;
    cin >> n >> m;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    if (m == 0) {
        for (int i = 1; i <= n; i++) {
            cout << 0 << " ";
        }
        cout << endl;
        return 0;
    }
    // find components
    vector<bool> vis(n + 1, false);
    vector<vector<int>> comps;
    for (int i = 1; i <= n; i++) {
        if (!vis[i]) {
            vector<int> comp;
            queue<int> q;
            q.push(i);
            vis[i] = true;
            while (!q.empty()) {
                int u = q.front();
                q.pop();
                comp.push_back(u);
                for (int v : adj[u]) {
                    if (!vis[v]) {
                        vis[v] = true;
                        q.push(v);
                    }
                }
            }
            comps.push_back(comp);
        }
    }
    vector<int> side(n + 1);
    for (auto& comp : comps) {
        int k = comp.size();
        vector<int> comp_id(n + 1, -1);
        for (int j = 0; j < k; j++) {
            comp_id[comp[j]] = j;
        }
        if (k <= 10) {
            // brute force
            int max_local_cut = -1;
            int best_mask = 0;
            for (int mask = 0; mask < (1 << k); mask++) {
                vector<int> local_side(k);
                for (int j = 0; j < k; j++) {
                    local_side[j] = (mask & (1 << j)) ? 1 : 0;
                }
                int local_cut = 0;
                for (int ii = 0; ii < k; ii++) {
                    int u = comp[ii];
                    for (int v : adj[u]) {
                        if (u < v && comp_id[v] != -1 && local_side[ii] != local_side[comp_id[v]]) {
                            local_cut++;
                        }
                    }
                }
                if (local_cut > max_local_cut) {
                    max_local_cut = local_cut;
                    best_mask = mask;
                }
            }
            for (int j = 0; j < k; j++) {
                side[comp[j]] = (best_mask & (1 << j)) ? 1 : 0;
            }
        } else {
            // heuristic: multiple random + local search
            int num_trials = 10;
            int best_local_cut = -1;
            vector<int> best_local(k);
            for (int trial = 0; trial < num_trials; trial++) {
                vector<int> local_side(k);
                for (int j = 0; j < k; j++) {
                    local_side[j] = rand() % 2;
                }
                // local search
                bool changed = true;
                int iter = 0;
                while (changed && iter < 100) {
                    changed = false;
                    for (int i = 0; i < k; i++) {
                        int u = comp[i];
                        int same = 0, other = 0;
                        for (int v : adj[u]) {
                            int j = comp_id[v];
                            if (j != -1) {
                                if (local_side[j] == local_side[i]) same++;
                                else other++;
                            }
                        }
                        int delta = same - other;
                        if (delta > 0) {
                            local_side[i] = 1 - local_side[i];
                            changed = true;
                        }
                    }
                    iter++;
                }
                // compute local_cut
                int local_cut = 0;
                for (int ii = 0; ii < k; ii++) {
                    int u = comp[ii];
                    for (int v : adj[u]) {
                        if (u < v && comp_id[v] != -1 && local_side[ii] != local_side[comp_id[v]]) {
                            local_cut++;
                        }
                    }
                }
                if (local_cut > best_local_cut) {
                    best_local_cut = local_cut;
                    best_local = local_side;
                }
            }
            for (int j = 0; j < k; j++) {
                side[comp[j]] = best_local[j];
            }
        }
    }
    for (int i = 1; i <= n; i++) {
        cout << side[i] << " ";
    }
    cout << endl;
    return 0;
}