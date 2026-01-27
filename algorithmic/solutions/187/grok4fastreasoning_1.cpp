#include <bits/stdc++.h>
using namespace std;

const int MAXN = 501;
bitset<MAXN> adj[MAXN];
int deg[MAXN];

int greedy(const vector<int>& perm, vector<int>& coloring, const bitset<MAXN> adj_[], int N) {
    fill(coloring.begin(), coloring.begin() + N + 1, 0);
    int maxc = 0;
    for (size_t i = 0; i < (size_t)N; ++i) {
        int v = perm[i];
        vector<char> used(N + 2, 0);
        for (size_t j = 0; j < i; ++j) {
            int u = perm[j];
            if (coloring[u] != 0 && !adj_[u][v]) {
                used[coloring[u]] = 1;
            }
        }
        int c = 1;
        while (used[c]) ++c;
        coloring[v] = c;
        if (c > maxc) maxc = c;
    }
    return maxc;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    cin >> N >> M;
    memset(deg, 0, sizeof(deg));
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        int a = min(u, v), b = max(u, v);
        if (!adj[a][b]) {
            adj[a][b] = 1;
            adj[b][a] = 1;
            ++deg[a];
            ++deg[b];
        }
    }
    vector<pair<int, int>> vdeg;
    for (int i = 1; i <= N; ++i) {
        vdeg.emplace_back(deg[i], i);
    }
    vector<int> perm_inc(N), perm_dec(N), perm_nat(N);
    for (int i = 0; i < N; ++i) perm_nat[i] = i + 1;
    sort(vdeg.begin(), vdeg.end());
    for (int i = 0; i < N; ++i) perm_inc[i] = vdeg[i].second;
    sort(vdeg.rbegin(), vdeg.rend());
    for (int i = 0; i < N; ++i) perm_dec[i] = vdeg[i].second;
    vector<int> col_inc(N + 1, 0), col_dec(N + 1, 0), col_nat(N + 1, 0);
    int k_inc = greedy(perm_inc, col_inc, adj, N);
    int k_dec = greedy(perm_dec, col_dec, adj, N);
    int k_nat = greedy(perm_nat, col_nat, adj, N);
    const vector<int>* best_col;
    int best_k = min({k_inc, k_dec, k_nat});
    if (best_k == k_inc) {
        best_col = &col_inc;
    } else if (best_k == k_dec) {
        best_col = &col_dec;
    } else {
        best_col = &col_nat;
    }
    for (int i = 1; i <= N; ++i) {
        cout << (*best_col)[i] << '\n';
    }
    return 0;
}