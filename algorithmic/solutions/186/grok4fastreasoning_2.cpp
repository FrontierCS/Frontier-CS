#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N, M;
    cin >> N >> M;
    vector<vector<int>> adj(N+1);
    for(int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<int> deg(N+1);
    for(int i=1; i<=N; i++) {
        sort(adj[i].begin(), adj[i].end());
        auto it = unique(adj[i].begin(), adj[i].end());
        adj[i].resize(it - adj[i].begin());
        deg[i] = adj[i].size();
    }
    // Greedy with degree descending order
    vector<pair<int, int>> pairs;
    for(int i=1; i<=N; i++) {
        pairs.emplace_back(-deg[i], i);
    }
    sort(pairs.begin(), pairs.end());
    vector<int> order(N);
    for(int i=0; i<N; i++) {
        order[i] = pairs[i].second;
    }
    vector<int> color(N+1, 0);
    for(int idx : order) {
        vector<char> forbidden(N+2, 0);
        for(int j : adj[idx]) {
            int c = color[j];
            if(c > 0) forbidden[c] = 1;
        }
        int col = 1;
        while(col <= N+1 && forbidden[col]) ++col;
        color[idx] = col;
    }
    // Iterative improvement
    bool changed = true;
    while(changed) {
        changed = false;
        for(int i=1; i<=N; i++) {
            int old = color[i];
            if(old == 1) continue;
            for(int newc=1; newc < old; ++newc) {
                bool safe = true;
                for(int j : adj[i]) {
                    if(color[j] == newc) {
                        safe = false;
                        break;
                    }
                }
                if(safe) {
                    color[i] = newc;
                    changed = true;
                    break;
                }
            }
        }
    }
    // Output
    for(int i=1; i<=N; i++) {
        cout << color[i] << '\n';
    }
    return 0;
}