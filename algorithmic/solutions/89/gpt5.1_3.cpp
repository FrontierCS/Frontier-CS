#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int root = 1;

    // anc[x][v] = 1 if v lies on path from root to x
    vector<vector<unsigned char>> anc(n + 1, vector<unsigned char>(n + 1, 0));

    // For x != root, query for all v != root, v != x
    for (int x = 1; x <= n; ++x) {
        if (x == root) continue;
        for (int v = 1; v <= n; ++v) {
            if (v == root || v == x) continue;
            cout << "? 2 " << v << " " << root << " " << x << endl;
            int res;
            if (!(cin >> res)) return 0;
            if (res == -1) return 0;
            anc[x][v] = (res == 1);
        }
        anc[x][root] = 1;
        anc[x][x] = 1;
    }
    anc[root][root] = 1;

    vector<int> depth(n + 1, 0);
    depth[root] = 0;

    // Compute depths from root
    for (int x = 1; x <= n; ++x) {
        if (x == root) continue;
        int cnt = 0;
        for (int v = 1; v <= n; ++v) {
            if (anc[x][v]) ++cnt;
        }
        depth[x] = cnt - 1;
    }

    vector<pair<int,int>> edges;
    edges.reserve(n - 1);

    // Find parent for each node (except root)
    for (int x = 1; x <= n; ++x) {
        if (x == root) continue;
        int targetDepth = depth[x] - 1;
        int parent = -1;
        for (int v = 1; v <= n; ++v) {
            if (anc[x][v] && depth[v] == targetDepth) {
                parent = v;
                break;
            }
        }
        if (parent == -1) parent = root; // Fallback (should not happen)
        edges.push_back({parent, x});
    }

    cout << "!" << endl;
    for (auto &e : edges) {
        cout << e.first << " " << e.second << endl;
    }
    cout.flush();

    return 0;
}