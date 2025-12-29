#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
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
        int xx, yy;
        cin >> xx >> yy;
    }
    vector<int> depth(N, H);
    auto lambda = [&](int i, int j) {
        if (A[i] != A[j]) return A[i] < A[j];
        return i < j;
    };
    bool changed = true;
    while (changed) {
        changed = false;
        vector<int> violators;
        for (int v = 0; v < N; v++) {
            if (depth[v] > 0) {
                bool sup = false;
                for (int u : adj[v]) {
                    if (depth[u] == depth[v] - 1) {
                        sup = true;
                        break;
                    }
                }
                if (!sup) {
                    violators.push_back(v);
                }
            }
        }
        if (violators.empty()) {
            changed = false;
            continue;
        }
        sort(violators.begin(), violators.end(), lambda);
        for (int v : violators) {
            if (depth[v] == 0) continue;
            bool sup = false;
            for (int u : adj[v]) {
                if (depth[u] == depth[v] - 1) {
                    sup = true;
                    break;
                }
            }
            if (!sup) {
                depth[v]--;
                changed = true;
            }
        }
    }
    vector<int> p(N, -1);
    for (int v = 0; v < N; v++) {
        if (depth[v] == 0) continue;
        for (int u : adj[v]) {
            if (depth[u] == depth[v] - 1) {
                p[v] = u;
                break;
            }
        }
    }
    for (int i = 0; i < N; i++) {
        if (i > 0) cout << " ";
        cout << p[i];
    }
    cout << "\n";
    return 0;
}