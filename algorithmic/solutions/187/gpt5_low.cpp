#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    const int MAXN = 512;
    vector< bitset<MAXN> > adj(N);
    for (int i = 0; i < N; ++i) adj[i].reset();
    for (int i = 0; i < M; ++i) {
        int u, v; cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }
    // Complement adjacency (exclude self)
    vector< bitset<MAXN> > comp(N);
    bitset<MAXN> mask;
    for (int i = 0; i < N; ++i) mask.set(i);
    for (int i = 0; i < N; ++i) {
        comp[i] = (~adj[i]) & mask;
        comp[i].reset(i);
    }
    vector<int> deg_comp(N, 0);
    for (int i = 0; i < N; ++i) deg_comp[i] = (int)comp[i].count();

    vector<int> color(N, 0);
    vector< bitset<MAXN> > satmask(N); // colors used by colored neighbors in complement
    for (int i = 0; i < N; ++i) satmask[i].reset();
    vector<int> satdeg(N, 0);
    int K = 0;

    for (int it = 0; it < N; ++it) {
        // pick uncolored vertex with max saturation degree; tie by comp degree, then index
        int best = -1, best_sat = -1, best_deg = -1;
        for (int v = 0; v < N; ++v) {
            if (color[v] != 0) continue;
            int sd = satdeg[v];
            int dg = deg_comp[v];
            if (sd > best_sat || (sd == best_sat && (dg > best_deg || (dg == best_deg && v < best)))) {
                best = v; best_sat = sd; best_deg = dg;
            }
        }
        int v = best;
        // find smallest available color
        int c = 1;
        for (; c <= K; ++c) {
            if (!satmask[v].test(c)) break;
        }
        if (c == K + 1) K++;
        color[v] = c;
        // update neighbors in complement
        for (int u = 0; u < N; ++u) {
            if (color[u] == 0 && comp[v].test(u)) {
                if (!satmask[u].test(c)) {
                    satmask[u].set(c);
                    satdeg[u]++;
                }
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << color[i] << '\n';
    }
    return 0;
}