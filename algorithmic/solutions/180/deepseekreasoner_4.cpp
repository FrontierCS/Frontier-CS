#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(0);
    int n, m;
    cin >> n >> m;
    vector<int> deg1(n, 0), deg2(n, 0);
    vector<vector<int>> adj2(n);
    vector<bitset<2000>> adj1(n);
    vector<pair<int,int>> edges2;
    edges2.reserve(m);
    
    // Read G1 edges
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        u--; v--;
        adj1[u][v] = 1;
        adj1[v][u] = 1;
        deg1[u]++;
        deg1[v]++;
    }
    // Read G2 edges
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        u--; v--;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
        deg2[u]++;
        deg2[v]++;
        edges2.emplace_back(u, v);
    }
    
    // Initial permutation based on degree sorting
    vector<int> order1(n), order2(n);
    iota(order1.begin(), order1.end(), 0);
    iota(order2.begin(), order2.end(), 0);
    sort(order1.begin(), order1.end(), [&](int i, int j) {
        if (deg1[i] != deg1[j]) return deg1[i] > deg1[j];
        return i < j;
    });
    sort(order2.begin(), order2.end(), [&](int i, int j) {
        if (deg2[i] != deg2[j]) return deg2[i] > deg2[j];
        return i < j;
    });
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        p[order2[i]] = order1[i];
    }
    
    // Compute initial score
    int score = 0;
    for (auto& e : edges2) {
        int u = e.first, v = e.second;
        if (adj1[p[u]][p[v]]) score++;
    }
    int best_score = score;
    vector<int> best_p = p;
    
    // Simulated annealing parameters
    double T = 10.0;
    const double alpha = 0.99999;
    const int MAX_ITER = 100000;
    
    random_device rd;
    mt19937 gen(rd());
    uniform_int_distribution<int> vertex_dist(0, n-1);
    uniform_real_distribution<double> prob_dist(0.0, 1.0);
    
    for (int iter = 0; iter < MAX_ITER; ++iter) {
        int a = vertex_dist(gen);
        int b = vertex_dist(gen);
        while (b == a) b = vertex_dist(gen);
        
        int pa = p[a];
        int pb = p[b];
        int delta = 0;
        // For neighbors of a
        for (int v : adj2[a]) {
            if (v == b) continue;
            int pv = p[v];
            bool old_e = adj1[pa][pv];
            bool new_e = adj1[pb][pv];
            if (new_e && !old_e) delta++;
            else if (!new_e && old_e) delta--;
        }
        // For neighbors of b
        for (int v : adj2[b]) {
            if (v == a) continue;
            int pv = p[v];
            bool old_e = adj1[pb][pv];
            bool new_e = adj1[pa][pv];
            if (new_e && !old_e) delta++;
            else if (!new_e && old_e) delta--;
        }
        
        if (delta >= 0 || prob_dist(gen) < exp(delta / T)) {
            // accept swap
            swap(p[a], p[b]);
            score += delta;
            if (score > best_score) {
                best_score = score;
                best_p = p;
                if (best_score == m) break; // perfect match
            }
        }
        T *= alpha;
    }
    
    p = best_p;
    for (int i = 0; i < n; ++i) {
        cout << p[i] + 1 << (i == n-1 ? '\n' : ' ');
    }
    
    return 0;
}