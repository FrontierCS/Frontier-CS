#include <bits/stdc++.h>
using namespace std;

int main() {
    srand(time(0));
    int N, M;
    cin >> N >> M;
    vector<bitset<1001>> neigh(N + 1);
    vector<int> deg(N + 1, 0);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        if (u != v) {
            neigh[u][v] = 1;
            neigh[v][u] = 1;
            deg[u]++;
            deg[v]++;
        }
    }
    for (int i = 1; i <= N; i++) {
        deg[i] = neigh[i].count();
    }
    // Degree-ordered run
    vector<pair<int, int>> verts;
    for (int i = 1; i <= N; i++) {
        verts.emplace_back(deg[i], i);
    }
    sort(verts.begin(), verts.end());
    vector<int> order_deg;
    for (auto& p : verts) {
        order_deg.push_back(p.second);
    }
    bitset<1001> best_selected;
    int max_k = 0;
    {
        bitset<1001> selected;
        int k = 0;
        for (int u : order_deg) {
            if ((neigh[u] & selected).any()) continue;
            selected[u] = 1;
            k++;
        }
        if (k > max_k) {
            max_k = k;
            best_selected = selected;
        }
    }
    // Random runs
    const int NUM_RUNS = 1000;
    for (int run = 0; run < NUM_RUNS; run++) {
        vector<int> order;
        for (int i = 1; i <= N; i++) order.push_back(i);
        random_shuffle(order.begin(), order.end());
        bitset<1001> selected;
        int k = 0;
        for (int u : order) {
            if ((neigh[u] & selected).any()) continue;
            selected[u] = 1;
            k++;
        }
        if (k > max_k) {
            max_k = k;
            best_selected = selected;
        }
    }
    for (int i = 1; i <= N; i++) {
        cout << best_selected[i] << '\n';
    }
    return 0;
}