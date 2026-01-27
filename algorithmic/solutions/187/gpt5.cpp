#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 512;

struct RNG {
    uint64_t state;
    RNG() {
        uint64_t x = chrono::high_resolution_clock::now().time_since_epoch().count();
        state = x + 0x9e3779b97f4a7c15ULL;
    }
    inline uint64_t next() {
        uint64_t z = (state += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    inline int randint(int l, int r) {
        return l + (int)(next() % (uint64_t)(r - l + 1));
    }
    inline bool coin() {
        return (next() >> 63) & 1;
    }
};

int calcMaxColor(const vector<int>& color) {
    int K = 0;
    for (int c : color) if (c > K) K = c;
    return K;
}

vector<int> dsatur_coloring(const vector< bitset<MAXN> >& comp, const vector<int>& deg, RNG& rng) {
    int N = (int)comp.size();
    vector<int> color(N, 0);
    vector<int> sat(N, 0);
    vector< bitset<MAXN> > usedColors(N); // colors used by neighbors (in complement)
    vector< bitset<MAXN> > colorSets; // vertices with given color
    colorSets.emplace_back(); // dummy for 0-index
    int K = 0;

    for (int it = 0; it < N; ++it) {
        int u = -1;
        int bestSat = -1;
        int bestDeg = -1;
        for (int i = 0; i < N; ++i) {
            if (color[i] != 0) continue;
            if (sat[i] > bestSat) {
                bestSat = sat[i];
                bestDeg = deg[i];
                u = i;
            } else if (sat[i] == bestSat) {
                if (deg[i] > bestDeg) {
                    bestDeg = deg[i];
                    u = i;
                } else if (deg[i] == bestDeg) {
                    if (u == -1 || rng.coin()) {
                        u = i;
                    }
                }
            }
        }
        int assignColor = 0;
        for (int c = 1; c <= K; ++c) {
            if ((comp[u] & colorSets[c]).any()) continue;
            assignColor = c;
            break;
        }
        if (assignColor == 0) {
            ++K;
            colorSets.emplace_back();
            assignColor = K;
        }
        color[u] = assignColor;
        colorSets[assignColor].set(u);

        // update saturation of neighbors in complement
        for (int v = 0; v < N; ++v) {
            if (color[v] == 0 && comp[u][v]) {
                if (!usedColors[v].test(assignColor)) {
                    usedColors[v].set(assignColor);
                    ++sat[v];
                }
            }
        }
    }
    return color;
}

void compressColors(vector<int>& color) {
    int N = (int)color.size();
    int K = calcMaxColor(color);
    vector<int> mapc(K + 1, 0);
    int nk = 0;
    for (int i = 0; i < N; ++i) {
        int c = color[i];
        if (c >= 1 && mapc[c] == 0) mapc[c] = ++nk;
    }
    for (int i = 0; i < N; ++i) color[i] = mapc[color[i]];
}

void relocate_reduce(vector<int>& color, const vector< bitset<MAXN> >& comp, const vector<int>& deg, int passes = 1) {
    int N = (int)color.size();
    if (N == 0) return;
    int K = calcMaxColor(color);
    vector< bitset<MAXN> > cset(K + 1);
    for (int v = 0; v < N; ++v) {
        int c = color[v];
        if (c >= 1) cset[c].set(v);
    }

    for (int pass = 0; pass < passes; ++pass) {
        bool changed = false;
        // Try to move vertices from higher colors into lower ones
        for (int c = K; c >= 1; --c) {
            if (cset[c].none()) continue;
            vector<int> members;
            members.reserve((int)cset[c].count());
            for (int v = 0; v < N; ++v) if (cset[c].test(v)) members.push_back(v);
            sort(members.begin(), members.end(), [&](int a, int b) {
                if (deg[a] != deg[b]) return deg[a] < deg[b];
                return a < b;
            });
            for (int v : members) {
                // try to move to smaller color
                for (int t = 1; t < c; ++t) {
                    if (cset[t].none()) continue;
                    if ((comp[v] & cset[t]).any()) continue;
                    // move v from c -> t
                    cset[c].reset(v);
                    cset[t].set(v);
                    color[v] = t;
                    changed = true;
                    break;
                }
            }
        }
        // compress colors (remove empties)
        if (changed) {
            vector<int> mapc(K + 1, 0);
            int nk = 0;
            for (int c = 1; c <= K; ++c) {
                if (cset[c].any()) mapc[c] = ++nk;
            }
            vector< bitset<MAXN> > nset(nk + 1);
            for (int c = 1; c <= K; ++c) {
                if (mapc[c]) {
                    nset[mapc[c]] = cset[c];
                }
            }
            cset.swap(nset);
            K = nk;
            for (int v = 0; v < N; ++v) {
                color[v] = 0;
            }
            for (int c = 1; c <= K; ++c) {
                for (int v = 0; v < N; ++v) if (cset[c].test(v)) color[v] = c;
            }
        } else {
            break;
        }
    }
    compressColors(color);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    vector< bitset<MAXN> > adj(N);
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

    vector< bitset<MAXN> > comp(N);
    for (int i = 0; i < N; ++i) {
        comp[i] = (~adj[i]) & mask;
        comp[i].reset(i);
    }
    vector<int> deg(N, 0);
    for (int i = 0; i < N; ++i) deg[i] = (int)comp[i].count();

    RNG rng;
    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.85; // seconds
    vector<int> bestColor(N, 1);
    int bestK = N + 1;
    int attempts = 0;

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > TIME_LIMIT) break;

        vector<int> cur = dsatur_coloring(comp, deg, rng);
        relocate_reduce(cur, comp, deg, 1);
        int curK = calcMaxColor(cur);
        if (curK < bestK) {
            bestK = curK;
            bestColor = cur;
        }
        attempts++;
        if (attempts >= 200) break; // safeguard
    }

    // Final small refinement on best
    relocate_reduce(bestColor, comp, deg, 2);
    compressColors(bestColor);

    for (int i = 0; i < N; ++i) {
        cout << bestColor[i] << '\n';
    }
    return 0;
}