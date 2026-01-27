#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> adj(n + 1);
    adj.reserve(n + 1);
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }
    vector<int> degree(n + 1);
    for (int i = 1; i <= n; ++i) degree[i] = (int)adj[i].size();

    vector<int> order(n);
    iota(order.begin(), order.end(), 1);
    stable_sort(order.begin(), order.end(), [&](int a, int b){
        return degree[a] > degree[b];
    });

    mt19937 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto greedy = [&](vector<int>& color){
        // Greedy coloring by degree order
        fill(color.begin(), color.end(), 0);
        for (int u : order) {
            int cnt[4] = {0,0,0,0};
            for (int v : adj[u]) {
                int c = color[v];
                if (c) cnt[c]++;
            }
            int bestC = 1;
            int bestVal = cnt[1];
            for (int c = 2; c <= 3; ++c) {
                if (cnt[c] < bestVal) { bestVal = cnt[c]; bestC = c; }
                else if (cnt[c] == bestVal && uniform_int_distribution<int>(0,1)(rng)) {
                    bestC = c;
                }
            }
            color[u] = bestC;
        }
    };

    auto local_improve = [&](vector<int>& color){
        // Hill-climbing: change node color if it reduces conflicts
        bool improved = true;
        int max_pass = 20;
        while (improved && max_pass--) {
            improved = false;
            vector<int> nodes(n);
            iota(nodes.begin(), nodes.end(), 1);
            shuffle(nodes.begin(), nodes.end(), rng);
            for (int u : nodes) {
                int cnt[4] = {0,0,0,0};
                for (int v : adj[u]) {
                    cnt[color[v]]++;
                }
                int cur = color[u];
                int bestC = cur;
                int bestVal = cnt[cur];
                for (int c = 1; c <= 3; ++c) {
                    if (c == cur) continue;
                    if (cnt[c] < bestVal) {
                        bestVal = cnt[c];
                        bestC = c;
                    }
                }
                if (bestC != cur) {
                    color[u] = bestC;
                    improved = true;
                }
            }
        }
    };

    auto conflicts = [&](const vector<int>& color)->long long{
        long long b = 0;
        for (auto &e : edges) {
            if (color[e.first] == color[e.second]) b++;
        }
        return b;
    };

    vector<int> best_color(n + 1, 1), current(n + 1, 1);
    long long best_b = (long long)m; // max conflicts
    int restarts = 5;

    for (int r = 0; r < restarts; ++r) {
        greedy(current);
        local_improve(current);
        long long b = conflicts(current);
        if (b < best_b) {
            best_b = b;
            best_color = current;
        }
        // Slight perturbation for next restart
        for (int i = 1; i <= n; ++i) {
            if (uniform_int_distribution<int>(0, 9)(rng) == 0) {
                best_color[i] = uniform_int_distribution<int>(1,3)(rng);
            }
        }
    }

    // Output best found
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << best_color[i];
    }
    cout << '\n';
    return 0;
}