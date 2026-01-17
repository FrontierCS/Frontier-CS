#include <bits/stdc++.h>
using namespace std;

const int RESTART_COUNT = 4;
const int MAX_ITER = 50;

// Given an initial coloring, run local search to reduce conflicts.
// Returns final coloring and number of conflicting edges.
pair<vector<int>, int> improve(vector<int> col, const vector<vector<int>>& adj) {
    int n = adj.size();
    vector<array<int,3>> cnt(n, {0,0,0});

    // Compute neighbor color counts
    for (int v = 0; v < n; ++v) {
        for (int u : adj[v]) {
            cnt[v][col[u]]++;
        }
    }

    random_device rd;
    mt19937 g(rd());
    vector<int> vertices(n);
    iota(vertices.begin(), vertices.end(), 0);

    bool changed = true;
    int iter = 0;
    while (changed && iter < MAX_ITER) {
        iter++;
        changed = false;
        shuffle(vertices.begin(), vertices.end(), g);

        for (int v : vertices) {
            int cur = col[v];
            int best = 0;
            for (int c = 1; c < 3; ++c) {
                if (cnt[v][c] < cnt[v][best]) {
                    best = c;
                }
            }
            if (cnt[v][best] < cnt[v][cur]) {
                // Change color of v to best
                col[v] = best;
                for (int u : adj[v]) {
                    cnt[u][cur]--;
                    cnt[u][best]++;
                }
                changed = true;
            }
        }
    }

    // Compute number of conflicting edges
    int conflicts = 0;
    for (int v = 0; v < n; ++v) {
        for (int u : adj[v]) {
            if (u > v && col[u] == col[v]) {
                conflicts++;
            }
        }
    }
    return {col, conflicts};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Greedy initial coloring (by degree descending)
    vector<int> col_greedy(n, -1);
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return adj[a].size() > adj[b].size();
    });

    for (int v : order) {
        array<int,3> cnt_col = {0,0,0};
        for (int u : adj[v]) {
            if (col_greedy[u] != -1) {
                cnt_col[col_greedy[u]]++;
            }
        }
        int best = 0;
        for (int c = 1; c < 3; ++c) {
            if (cnt_col[c] < cnt_col[best]) {
                best = c;
            }
        }
        col_greedy[v] = best;
    }

    auto [best_col, best_conf] = improve(col_greedy, adj);

    // Random restarts
    mt19937 rng(random_device{}());
    uniform_int_distribution<int> dist(0, 2);
    for (int restart = 0; restart < RESTART_COUNT; ++restart) {
        vector<int> col_rand(n);
        for (int i = 0; i < n; ++i) {
            col_rand[i] = dist(rng);
        }
        auto [col_new, conf_new] = improve(col_rand, adj);
        if (conf_new < best_conf) {
            best_conf = conf_new;
            best_col = col_new;
        }
    }

    // Output coloring (1-indexed colors)
    for (int i = 0; i < n; ++i) {
        cout << best_col[i] + 1 << " \n"[i == n-1];
    }

    return 0;
}