#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<int> par(N + 1, 0), deg(N + 1, 0);
    par[1] = 0;
    for (int i = 2; i <= N; ++i) {
        int p;
        cin >> p;
        par[i] = p;
        deg[i]++;
        deg[p]++;
    }

    // Find leaves (degree 1)
    vector<int> leaves;
    leaves.reserve(N);
    for (int i = 1; i <= N; ++i) {
        if (deg[i] == 1) leaves.push_back(i);
    }
    int k = (int)leaves.size();

    // Map leaf to position in the order (increasing labels)
    sort(leaves.begin(), leaves.end());
    vector<int> pos(N + 1, -1);
    for (int i = 0; i < k; ++i) pos[leaves[i]] = i;

    // prev and next leaf in cycle order
    vector<int> prv(N + 1, -1), nxt(N + 1, -1);
    if (k > 0) {
        for (int i = 0; i < k; ++i) {
            int v = leaves[i];
            int pidx = (i - 1 + k) % k;
            int nidx = (i + 1) % k;
            prv[v] = leaves[pidx];
            nxt[v] = leaves[nidx];
        }
    }

    int K = N + k;
    vector<vector<int>> bags(K + 1);

    // T_v bags for each vertex v: {v} or {v, par[v]}
    for (int v = 1; v <= N; ++v) {
        vector<int> b;
        b.push_back(v);
        if (v != 1) b.push_back(par[v]);
        sort(b.begin(), b.end());
        b.erase(unique(b.begin(), b.end()), b.end());
        bags[v] = move(b);
    }

    // C_l bags for each leaf l: {l, prev(l), next(l)}
    for (int i = 0; i < k; ++i) {
        int l = leaves[i];
        int idx = N + i + 1;
        vector<int> b;
        b.push_back(l);
        if (k >= 1) {
            b.push_back(prv[l]);
            b.push_back(nxt[l]);
        }
        sort(b.begin(), b.end());
        b.erase(unique(b.begin(), b.end()), b.end());
        bags[idx] = move(b);
    }

    // Build edges of the new tree
    vector<pair<int,int>> edges;
    edges.reserve(K - 1);
    // Connect T_v as the original tree structure
    for (int v = 2; v <= N; ++v) {
        edges.emplace_back(v, par[v]);  // indices are bag indices (T_v and T_par[v])
    }
    // Connect each C_l to its corresponding T_l
    for (int i = 0; i < k; ++i) {
        int l = leaves[i];
        int idx = N + i + 1;
        edges.emplace_back(idx, l);
    }

    // Output
    cout << K << '\n';
    for (int i = 1; i <= K; ++i) {
        cout << (int)bags[i].size();
        for (int x : bags[i]) cout << ' ' << x;
        cout << '\n';
    }
    for (auto &e : edges) {
        cout << e.first << ' ' << e.second << '\n';
    }

    return 0;
}