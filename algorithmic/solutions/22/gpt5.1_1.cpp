#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    vector<vector<int>> adj(N + 1);
    vector<int> treeDeg(N + 1, 0);

    for (int i = 2; i <= N; ++i) {
        int p;
        cin >> p;
        adj[i].push_back(p);
        adj[p].push_back(i);
        treeDeg[i]++;
        treeDeg[p]++;
    }

    // Find leaves in the tree (degree 1 in tree edges only)
    vector<int> leaves;
    leaves.reserve(N);
    for (int v = 1; v <= N; ++v) {
        if (treeDeg[v] == 1) leaves.push_back(v);
    }
    sort(leaves.begin(), leaves.end());
    int k = (int)leaves.size();

    // Add cycle edges between leaves in increasing order
    for (int i = 0; i < k; ++i) {
        int u = leaves[i];
        int v = leaves[(i + 1) % k];
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Degeneracy ordering with k=3
    vector<int> deg(N + 1);
    for (int v = 1; v <= N; ++v) deg[v] = (int)adj[v].size();

    vector<char> removed(N + 1, 0);
    vector<int> st;
    st.reserve(N);

    for (int v = 1; v <= N; ++v) {
        if (deg[v] <= 3) st.push_back(v);
    }

    vector<int> order;
    order.reserve(N);

    while (!st.empty()) {
        int v = st.back();
        st.pop_back();
        if (removed[v]) continue;
        removed[v] = 1;
        order.push_back(v);
        for (int u : adj[v]) {
            if (removed[u]) continue;
            if (--deg[u] == 3) st.push_back(u);
        }
    }

    // For valid inputs this must hold: degeneracy <= 3
    // so we must have removed all vertices.
    // (Assertion skipped in final code.)

    vector<int> pos(N + 1);
    for (int i = 0; i < N; ++i) pos[order[i]] = i;

    // Build bags and parent relations
    vector<vector<int>> bag(N + 1);
    vector<int> parent(N + 1, -1);

    for (int v = 1; v <= N; ++v) {
        bag[v].push_back(v);
        int bestPos = N + 5;
        int bestNeighbor = -1;
        for (int u : adj[v]) {
            if (pos[u] > pos[v]) {
                bag[v].push_back(u);
                if (pos[u] < bestPos) {
                    bestPos = pos[u];
                    bestNeighbor = u;
                }
            }
        }
        if (bestNeighbor != -1) {
            parent[v] = bestNeighbor;
        }
    }

    vector<pair<int,int>> edges;
    edges.reserve(N - 1);
    for (int v = 1; v <= N; ++v) {
        if (parent[v] != -1) edges.push_back({v, parent[v]});
    }

    int K = N;
    cout << K << '\n';
    for (int i = 1; i <= K; ++i) {
        cout << bag[i].size();
        for (int x : bag[i]) cout << ' ' << x;
        cout << '\n';
    }
    for (auto &e : edges) {
        cout << e.first << ' ' << e.second << '\n';
    }

    return 0;
}