#include <bits/stdc++.h>
using namespace std;

struct State {
    vector<int> col;               // color of each vertex (0,1,2)
    vector<array<int,3>> cnt;      // cnt[v][c] = number of neighbors of v with color c
    int conflicts;                 // number of conflicting edges

    State(int n) : col(n), cnt(n, {0,0,0}), conflicts(0) {}
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    if (m == 0) {
        // no edges, any coloring works
        for (int i = 0; i < n; ++i) {
            cout << 1 << " \n"[i == n-1];
        }
        return 0;
    }

    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;   // to 0-index
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // random device
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> col_dist(0, 2);

    const int MAX_RESTARTS = 30;
    int best_conflicts = m + 1;
    vector<int> best_col(n);

    for (int restart = 0; restart < MAX_RESTARTS; ++restart) {
        State s(n);

        // random initial coloring
        for (int i = 0; i < n; ++i) {
            s.col[i] = col_dist(rng);
        }

        // compute initial neighbor counts and conflicts
        s.conflicts = 0;
        for (int u = 0; u < n; ++u) {
            for (int v : adj[u]) {
                if (v > u) continue; // count each edge once
                s.cnt[u][s.col[v]]++;
                s.cnt[v][s.col[u]]++;
                if (s.col[u] == s.col[v]) {
                    s.conflicts++;
                }
            }
        }

        // local improvement loop
        bool improved = true;
        int passes = 0;
        while (improved && passes < 100) {
            improved = false;
            passes++;

            // random order of vertices
            vector<int> order(n);
            iota(order.begin(), order.end(), 0);
            shuffle(order.begin(), order.end(), rng);

            for (int v : order) {
                int old_c = s.col[v];
                int old_conf = s.cnt[v][old_c];
                int best_c = old_c;
                int best_conf = old_conf;

                // try other colors
                for (int c = 0; c < 3; ++c) {
                    if (c == old_c) continue;
                    if (s.cnt[v][c] < best_conf) {
                        best_conf = s.cnt[v][c];
                        best_c = c;
                    }
                }

                if (best_c != old_c) {
                    // change vertex v to best_c
                    int delta = best_conf - old_conf; // negative
                    s.conflicts += delta;

                    // update neighbor counts
                    for (int w : adj[v]) {
                        s.cnt[w][old_c]--;
                        s.cnt[w][best_c]++;
                    }

                    s.col[v] = best_c;
                    improved = true;
                }
            }
        }

        if (s.conflicts < best_conflicts) {
            best_conflicts = s.conflicts;
            best_col = s.col;
            if (best_conflicts == 0) break; // optimal found
        }
    }

    // output colors (1-indexed)
    for (int i = 0; i < n; ++i) {
        cout << best_col[i] + 1 << " \n"[i == n-1];
    }

    return 0;
}