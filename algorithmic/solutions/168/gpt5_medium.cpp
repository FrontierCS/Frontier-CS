#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M, H;
    if (!(cin >> N >> M >> H)) return 0;
    vector<int> A(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    vector<vector<int>> adj(N);
    vector<pair<int,int>> edges(M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        edges[i] = {u, v};
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    // Read coordinates (unused)
    for (int i = 0; i < N; ++i) {
        int x, y;
        cin >> x >> y;
    }

    // Sort neighbor lists by ascending A to try to keep low-A closer to root
    {
        vector<int> order(N);
        for (int i = 0; i < N; ++i) order[i] = i;
        for (int u = 0; u < N; ++u) {
            sort(adj[u].begin(), adj[u].end(), [&](int lhs, int rhs){
                if (A[lhs] != A[rhs]) return A[lhs] < A[rhs];
                return lhs < rhs;
            });
        }
    }

    vector<int> idx(N);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int i, int j){
        if (A[i] != A[j]) return A[i] < A[j];
        return i < j;
    });

    vector<int> parent(N, -1);
    vector<int> depth(N, -1);
    vector<char> assigned(N, 0);
    deque<int> q;

    for (int s : idx) {
        if (assigned[s]) continue;
        // start new BFS from root s
        parent[s] = -1;
        depth[s] = 0;
        assigned[s] = 1;
        q.clear();
        q.push_back(s);
        while (!q.empty()) {
            int v = q.front(); q.pop_front();
            if (depth[v] == H) continue;
            for (int w : adj[v]) {
                if (!assigned[w]) {
                    assigned[w] = 1;
                    parent[w] = v;
                    depth[w] = depth[v] + 1;
                    q.push_back(w);
                }
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        if (i) cout << ' ';
        cout << parent[i];
    }
    cout << '\n';
    return 0;
}