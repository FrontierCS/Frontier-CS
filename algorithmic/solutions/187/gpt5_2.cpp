#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 512;
static const int MAXC = 512;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<bitset<MAXN>> adj(N), comp(N);
    for (int i = 0; i < N; ++i) adj[i].reset();

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }

    bitset<MAXN> mask;
    mask.reset();
    for (int i = 0; i < N; ++i) mask.set(i);

    for (int i = 0; i < N; ++i) {
        comp[i] = (~adj[i]) & mask;
        comp[i].reset(i);
    }

    vector<int> degree(N, 0);
    for (int i = 0; i < N; ++i) degree[i] = (int)comp[i].count();

    vector<int> color(N, 0);
    vector<int> sat(N, 0);
    vector<bitset<MAXC>> neighborColors(N);
    for (int i = 0; i < N; ++i) neighborColors[i].reset();

    int K = 0; // number of colors used

    for (int it = 0; it < N; ++it) {
        int best = -1, bestSat = -1, bestDeg = -1;
        for (int i = 0; i < N; ++i) {
            if (color[i] != 0) continue;
            int s = sat[i];
            if (s > bestSat || (s == bestSat && degree[i] > bestDeg)) {
                best = i;
                bestSat = s;
                bestDeg = degree[i];
            }
        }
        int u = best;

        int chosen = -1;
        for (int c = 0; c < K; ++c) {
            if (!neighborColors[u].test(c)) { chosen = c + 1; break; }
        }
        if (chosen == -1) { K++; chosen = K; }
        color[u] = chosen;

        int cidx = chosen - 1;
        for (int v = 0; v < N; ++v) {
            if (color[v] == 0 && comp[u].test(v)) {
                if (!neighborColors[v].test(cidx)) {
                    neighborColors[v].set(cidx);
                    sat[v]++;
                }
            }
        }
    }

    // Local improvement: try to move vertices from higher colors to lower feasible colors
    vector<bitset<MAXN>> classSet(K + 1);
    for (int c = 1; c <= K; ++c) classSet[c].reset();
    for (int i = 0; i < N; ++i) classSet[color[i]].set(i);

    int passes = 2;
    for (int pass = 0; pass < passes; ++pass) {
        for (int c = K; c >= 2; --c) {
            if (classSet[c].none()) continue;
            bitset<MAXN> members = classSet[c];
            for (int u = 0; u < N; ++u) if (members.test(u)) {
                for (int t = 1; t < c; ++t) {
                    if ((comp[u] & classSet[t]).any()) continue;
                    // Move u from color c to color t
                    classSet[c].reset(u);
                    classSet[t].set(u);
                    color[u] = t;
                    break;
                }
            }
        }
    }

    // Compress colors to 1..T (remove empty classes)
    vector<int> remap(K + 1, 0);
    int T = 0;
    for (int c = 1; c <= K; ++c) {
        if (classSet[c].any()) remap[c] = ++T;
    }
    for (int i = 0; i < N; ++i) color[i] = remap[color[i]];

    for (int i = 0; i < N; ++i) {
        cout << color[i] << "\n";
    }

    return 0;
}