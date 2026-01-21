#include <bits/stdc++.h>
using namespace std;

const int MAXN = 3005;

bitset<MAXN> compMat[MAXN]; // compMat[i][j] = 1 if i and j are comparable

int ask2(int a, int b) {
    cout << "? 2 " << a << " " << b << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) {
        exit(0);
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, ty;
    if (!(cin >> n >> ty)) return 0;

    if (n == 1) {
        cout << "! 0" << endl;
        cout.flush();
        return 0;
    }

    // Build full comparability matrix: for each pair (i,j), i<j
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            int res = ask2(i, j);
            bool comparable = (res == 1); // size 1 => comparable, size 2 => incomparable
            compMat[i][j] = comparable;
            compMat[j][i] = comparable;
        }
    }

    // Compute |C(v)| = number of nodes comparable with v (excluding itself)
    vector<int> sizeC(n + 1);
    for (int i = 1; i <= n; ++i) {
        sizeC[i] = (int)compMat[i].count(); // compMat[i][i] is 0
    }

    // Find root: node with maximum |C(v)|
    int root = 1;
    for (int i = 2; i <= n; ++i) {
        if (sizeC[i] > sizeC[root]) root = i;
    }

    vector<int> parent(n + 1, 0);
    parent[root] = 0;

    // For each node v != root, find its parent:
    // parent[v] = ancestor u with comparable[u][v] and sizeC[u] > sizeC[v],
    // having minimal sizeC[u].
    for (int v = 1; v <= n; ++v) {
        if (v == root) continue;
        int best = -1;
        int bestSize = INT_MAX;
        for (int u = 1; u <= n; ++u) {
            if (u == v) continue;
            if (compMat[u][v] && sizeC[u] > sizeC[v]) {
                if (sizeC[u] < bestSize) {
                    bestSize = sizeC[u];
                    best = u;
                }
            }
        }
        parent[v] = best;
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << parent[i];
    }
    cout << endl;
    cout.flush();

    return 0;
}