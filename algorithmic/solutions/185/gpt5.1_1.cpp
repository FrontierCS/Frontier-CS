#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1000;
bitset<MAXN> adj[MAXN];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    for (int i = 0; i < N; ++i) adj[i].reset();

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }

    vector<int> deg(N);
    for (int i = 0; i < N; ++i) {
        deg[i] = (int)adj[i].count();
    }

    vector<int> ord(N);
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });

    bitset<MAXN> bestClique;
    int bestSize = 0;

    for (int idx = 0; idx < N; ++idx) {
        int s = ord[idx];
        int maxPossible = deg[s] + 1;
        if (maxPossible <= bestSize) continue;

        bitset<MAXN> clique;
        bitset<MAXN> cand;

        clique.reset();
        cand.reset();

        clique.set(s);
        cand = adj[s];
        int curSize = 1;

        while (cand.any() && curSize + (int)cand.count() > bestSize) {
            int v = -1;
            for (int j = 0; j < N; ++j) {
                int u = ord[j];
                if (cand.test(u)) {
                    v = u;
                    break;
                }
            }
            if (v == -1) break;

            clique.set(v);
            ++curSize;
            cand &= adj[v];
        }

        if (curSize > bestSize) {
            bestSize = curSize;
            bestClique = clique;
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << (bestClique.test(i) ? 1 : 0) << '\n';
    }

    return 0;
}