#include <bits/stdc++.h>
using namespace std;

int query(const vector<int>& seq) {
    cout << "? " << seq.size();
    for (int x : seq) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

int main() {
    int n, ty;
    cin >> n >> ty;
    
    // comparability matrix: cmp[i][j] = true if i and j are comparable
    vector<vector<bool>> cmp(n+1, vector<bool>(n+1, false));
    for (int i = 1; i <= n; i++) cmp[i][i] = true;
    
    // Query all pairs
    for (int i = 1; i <= n; i++) {
        for (int j = i+1; j <= n; j++) {
            vector<int> seq = {i, j};
            int res = query(seq);
            cmp[i][j] = cmp[j][i] = (res == 1);
        }
    }
    
    // Find root: node comparable to all others
    int root = -1;
    for (int i = 1; i <= n; i++) {
        bool ok = true;
        for (int j = 1; j <= n; j++) {
            if (!cmp[i][j]) {
                ok = false;
                break;
            }
        }
        if (ok) {
            root = i;
            break;
        }
    }
    
    // For each node, determine parent
    vector<int> parent(n+1, 0);
    parent[root] = 0;
    
    for (int v = 1; v <= n; v++) {
        if (v == root) continue;
        // Collect possible ancestors of v
        vector<int> ancestors;
        for (int u = 1; u <= n; u++) {
            if (u == v) continue;
            if (cmp[u][v]) {
                // Check if u is ancestor of v
                bool is_ancestor = true;
                for (int w = 1; w <= n; w++) {
                    if (w == u || w == v) continue;
                    if (cmp[u][w] && !cmp[v][w]) {
                        is_ancestor = false;
                        break;
                    }
                }
                if (is_ancestor)
                    ancestors.push_back(u);
            }
        }
        // Among ancestors, find the one with no other ancestor in between
        int best = -1;
        for (int u : ancestors) {
            bool ok = true;
            for (int w : ancestors) {
                if (w == u) continue;
                if (cmp[u][w] && cmp[w][v]) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                best = u;
                break;
            }
        }
        parent[v] = best;
    }
    
    cout << "!";
    for (int i = 1; i <= n; i++) {
        cout << " " << parent[i];
    }
    cout << endl;
    
    return 0;
}