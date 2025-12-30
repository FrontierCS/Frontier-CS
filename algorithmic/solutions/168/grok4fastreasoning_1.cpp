#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, M, H;
    cin >> N >> M >> H;
    vector<int> A(N);
    for (int i = 0; i < N; i++) {
        cin >> A[i];
    }
    vector<vector<int>> adj(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    for (int i = 0; i < N; i++) {
        int x, y;
        cin >> x >> y;
    }
    vector<pair<int, int>> order(N);
    for (int i = 0; i < N; i++) {
        order[i] = {A[i], i};
    }
    sort(order.begin(), order.end());
    vector<int> par(N, -2);
    vector<int> dep(N, -1);
    for (auto& pr : order) {
        int v = pr.second;
        int max_d = -1;
        int best_p = -1;
        for (int p : adj[v]) {
            if (par[p] != -2) {
                int wd = dep[p] + 1;
                if (wd <= H) {
                    if (wd > max_d || (wd == max_d && (best_p == -1 || A[p] < A[best_p]))) {
                        max_d = wd;
                        best_p = p;
                    }
                }
            }
        }
        if (best_p != -1) {
            par[v] = best_p;
            dep[v] = max_d;
        } else {
            par[v] = -1;
            dep[v] = 0;
        }
    }
    for (int i = 0; i < N; i++) {
        if (i > 0) cout << " ";
        cout << par[i];
    }
    cout << endl;
    return 0;
}