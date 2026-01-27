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
    double best_score = -1.0;
    vector<int> best_color(n + 1);
    for (int attempt = 0; attempt < 5; attempt++) {
        vector<int> color(n + 1);
        for (int i = 1; i <= n; i++) {
            color[i] = rand() % 2;
        }
        vector<int> gain(n + 1, 0);
        for (int u = 1; u <= n; u++) {
            int same = 0;
            for (int v : adj[u]) {
                if (color[v] == color[u]) same++;
            }
            int opp = (int)adj[u].size() - same;
            gain[u] = same - opp;
        }
        while (true) {
            int maxg = 0;
            int bestv = -1;
            for (int u = 1; u <= n; u++) {
                if (gain[u] > maxg) {
                    maxg = gain[u];
                    bestv = u;
                }
            }
            if (maxg <= 0) break;
            int oldc = color[bestv];
            color[bestv] = 1 - oldc;
            gain[bestv] = -gain[bestv];
            for (int nei : adj[bestv]) {
                if (color[nei] == oldc) {
                    gain[nei] -= 2;
                } else {
                    gain[nei] += 2;
                }
            }
        }
        int cut = 0;
        for (int u = 1; u <= n; u++) {
            for (int v : adj[u]) {
                if (u < v && color[u] != color[v]) cut++;
            }
        }
        double score = (m == 0 ? 1.0 : (double)cut / m);
        if (score > best_score) {
            best_score = score;
            best_color = color;
        }
    }
    for (int i = 1; i <= n; i++) {
        cout << best_color[i];
        if (i < n) cout << " ";
        else cout << "\n";
    }
    return 0;
}