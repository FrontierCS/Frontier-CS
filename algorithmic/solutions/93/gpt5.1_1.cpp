#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 3005;

bool compArr[MAXN][MAXN];
bitset<MAXN> comp_bs[MAXN];
bitset<MAXN> incomp_bs[MAXN];
bitset<MAXN> leafmask[MAXN];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, ty;
    if (!(cin >> n >> ty)) return 0;

    if (n == 1) {
        cout << "! 0\n";
        cout.flush();
        return 0;
    }

    // Build full comparability matrix via pair queries
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            cout << "? 2 " << i << ' ' << j << '\n';
            cout.flush();
            int r;
            if (!(cin >> r)) return 0;
            bool c = (r == 1); // 1 -> comparable, 2 -> incomparable
            compArr[i][j] = compArr[j][i] = c;
            if (c) {
                comp_bs[i].set(j);
                comp_bs[j].set(i);
            }
        }
    }

    // Prepare incomp bitsets
    bitset<MAXN> all;
    for (int i = 1; i <= n; ++i) all.set(i);
    for (int i = 1; i <= n; ++i) {
        incomp_bs[i] = all;
        incomp_bs[i].reset(i);
        incomp_bs[i] &= ~comp_bs[i];
    }

    // Detect leaves
    vector<int> leaves;
    vector<char> isLeaf(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        bool leaf = true;
        // i is leaf iff among nodes comparable with i, no two are incomparable
        for (int j = 1; j <= n && leaf; ++j) if (j != i && compArr[i][j]) {
            bitset<MAXN> tmp = comp_bs[i] & incomp_bs[j];
            if (tmp.any()) {
                leaf = false;
                break;
            }
        }
        isLeaf[i] = leaf;
        if (leaf) leaves.push_back(i);
    }

    int M = (int)leaves.size();

    // Build mapping from leaf node id to index [0..M-1]
    vector<int> leafId(n + 1, -1);
    for (int idx = 0; idx < M; ++idx) {
        leafId[leaves[idx]] = idx;
    }

    // Build leafmask for each node: set of descendant leaves
    for (int i = 1; i <= n; ++i) {
        leafmask[i].reset();
    }

    for (int idx = 0; idx < M; ++idx) {
        int l = leaves[idx];
        leafmask[l].set(idx); // leaf's own subtree
    }

    for (int v = 1; v <= n; ++v) {
        if (isLeaf[v]) continue; // already has its own mask
        for (int idx = 0; idx < M; ++idx) {
            int l = leaves[idx];
            if (v == l) continue;
            if (compArr[v][l]) {
                // v comparable with leaf l -> v is ancestor of l
                leafmask[v].set(idx);
            }
        }
    }

    // Compute leaf counts and find root (node with all leaves in its subtree)
    vector<int> leafCnt(n + 1);
    int root = -1;
    for (int v = 1; v <= n; ++v) {
        leafCnt[v] = (int)leafmask[v].count();
        if (leafCnt[v] == M) root = v;
    }
    if (root == -1) root = 1; // fallback, though shouldn't happen

    // Determine parent for each node via minimal strict superset of leafset
    vector<int> par(n + 1, 0);
    par[root] = 0;

    for (int v = 1; v <= n; ++v) {
        if (v == root) continue;
        int best = 0;
        int bestSz = INT_MAX;
        for (int u = 1; u <= n; ++u) {
            if (u == v) continue;
            if (leafCnt[u] <= leafCnt[v]) continue;
            // check if L(v) subset of L(u)
            bitset<MAXN> tmp = leafmask[v] & (~leafmask[u]);
            if (tmp.any()) continue; // not subset
            if (leafCnt[u] < bestSz) {
                bestSz = leafCnt[u];
                best = u;
            }
        }
        par[v] = best;
    }

    // Output final parent array
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << ' ' << par[i];
    }
    cout << '\n';
    cout.flush();

    return 0;
}