#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<vector<int>> G(N + 1);
    vector<int> parent(N + 1, 0);
    vector<int> degTree(N + 1, 0);
    for (int i = 2; i <= N; ++i) {
        int p; cin >> p;
        parent[i] = p;
        G[p].push_back(i);
        G[i].push_back(p);
        degTree[p]++; degTree[i]++;
    }
    // Collect leaves in increasing order
    vector<int> leaves;
    leaves.reserve(N);
    for (int i = 1; i <= N; ++i) if (degTree[i] == 1) leaves.push_back(i);
    sort(leaves.begin(), leaves.end());
    int k = (int)leaves.size();
    // Add ring edges
    if (k >= 2) {
        if (k == 2) {
            int u = leaves[0], v = leaves[1];
            G[u].push_back(v);
            G[v].push_back(u);
        } else {
            for (int i = 0; i < k; ++i) {
                int u = leaves[i];
                int v = leaves[(i + 1) % k];
                G[u].push_back(v);
                G[v].push_back(u);
            }
        }
    }
    // Degeneracy ordering (k=3)
    vector<int> deg(N + 1, 0);
    for (int i = 1; i <= N; ++i) deg[i] = (int)G[i].size();
    vector<char> removed(N + 1, 0);
    vector<int> order;
    order.reserve(N);
    vector<int> st;
    st.reserve(N);
    for (int i = 1; i <= N; ++i) if (deg[i] <= 3) st.push_back(i);
    while (!st.empty()) {
        int u = st.back(); st.pop_back();
        if (removed[u]) continue;
        if (deg[u] > 3) continue;
        removed[u] = 1;
        order.push_back(u);
        for (int v : G[u]) {
            if (!removed[v]) {
                if (--deg[v] <= 3) st.push_back(v);
            }
        }
    }
    // In case (theoretically shouldn't happen), process remaining vertices
    // This fallback keeps producing some order, but should not be needed for valid inputs.
    if ((int)order.size() < N) {
        for (int i = 1; i <= N; ++i) if (!removed[i]) {
            removed[i] = 1;
            order.push_back(i);
        }
    }
    // Compute ord (position) and later neighbors
    vector<int> ord(N + 1, 0);
    for (int i = 0; i < N; ++i) ord[order[i]] = i;
    vector<vector<int>> later(N + 1);
    for (int u = 1; u <= N; ++u) {
        for (int v : G[u]) {
            if (ord[u] < ord[v]) later[u].push_back(v);
        }
    }
    // Output K = N
    int K = N;
    cout << K << "\n";
    // Print bags in elimination order
    for (int i = 0; i < N; ++i) {
        int v = order[i];
        int sz = 1 + (int)later[v].size();
        cout << sz;
        cout << " " << v;
        for (int x : later[v]) cout << " " << x;
        cout << "\n";
    }
    // Build tree edges: parent is the later neighbor with minimal ord (if exists)
    // Bags are indexed 1..K corresponding to order[0..N-1]
    for (int i = 0; i < N; ++i) {
        int v = order[i];
        if (!later[v].empty()) {
            int best = later[v][0];
            for (int x : later[v]) {
                if (ord[x] < ord[best]) best = x;
            }
            int a = i + 1;
            int b = ord[best] + 1;
            cout << a << " " << b << "\n";
        }
    }
    return 0;
}