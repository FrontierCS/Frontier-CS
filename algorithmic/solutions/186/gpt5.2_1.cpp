#include <bits/stdc++.h>
using namespace std;

static inline int maxColor(const vector<int>& col) {
    int mx = 0;
    for (int c : col) mx = max(mx, c);
    return mx;
}

static inline bool validateColoring(const vector<vector<int>>& g, const vector<int>& col) {
    int n = (int)g.size();
    for (int v = 0; v < n; ++v) {
        for (int u : g[v]) {
            if (u > v && col[u] == col[v]) return false;
        }
    }
    return true;
}

static inline bool isFeasible(int v, int c, const vector<int>& col, const vector<vector<int>>& g) {
    for (int u : g[v]) if (col[u] == c) return false;
    return true;
}

static bool recolorVertex(
    int v,
    int maxC,
    int depth,
    int banned,
    vector<int>& col,
    const vector<vector<int>>& g,
    vector<char>& inStack,
    vector<pair<int,int>>& changes
) {
    if (inStack[v]) return false;
    inStack[v] = 1;

    int old = col[v];

    // Direct recolor
    for (int c = 1; c <= maxC; ++c) {
        if (c == banned || c == old) continue;
        if (isFeasible(v, c, col, g)) {
            changes.push_back({v, old});
            col[v] = c;
            inStack[v] = 0;
            return true;
        }
    }

    if (depth == 0) {
        inStack[v] = 0;
        return false;
    }

    // Try to free a color by recoloring blockers
    vector<pair<int,int>> opts; // (blockersCount, color)
    opts.reserve(maxC);
    for (int c = 1; c <= maxC; ++c) {
        if (c == banned || c == old) continue;
        int cnt = 0;
        for (int u : g[v]) if (col[u] == c) ++cnt;
        if (cnt > 0) opts.push_back({cnt, c});
    }
    sort(opts.begin(), opts.end(), [](auto& a, auto& b){
        if (a.first != b.first) return a.first < b.first;
        return a.second < b.second;
    });

    for (auto [cnt, c] : opts) {
        vector<int> blockers;
        blockers.reserve(cnt);
        for (int u : g[v]) if (col[u] == c) blockers.push_back(u);

        size_t snap = changes.size();
        bool ok = true;
        for (int u : blockers) {
            if (!recolorVertex(u, maxC, depth - 1, c, col, g, inStack, changes)) {
                ok = false;
                break;
            }
        }

        if (ok && isFeasible(v, c, col, g)) {
            changes.push_back({v, old});
            col[v] = c;
            inStack[v] = 0;
            return true;
        }

        // Revert
        while (changes.size() > snap) {
            auto [x, prev] = changes.back();
            changes.pop_back();
            col[x] = prev;
        }
    }

    inStack[v] = 0;
    return false;
}

static bool tryEliminateMaxColor(
    vector<int>& col,
    const vector<vector<int>>& g,
    const vector<int>& deg,
    mt19937& rng
) {
    int t = maxColor(col);
    if (t <= 1) return false;

    vector<int> verts;
    verts.reserve(col.size());
    for (int i = 0; i < (int)col.size(); ++i) if (col[i] == t) verts.push_back(i);
    if (verts.empty()) return true;

    int trials = 18;
    for (int tr = 0; tr < trials; ++tr) {
        vector<int> backup = col;

        shuffle(verts.begin(), verts.end(), rng);
        stable_sort(verts.begin(), verts.end(), [&](int a, int b){
            return deg[a] > deg[b];
        });

        bool ok = true;
        for (int v : verts) {
            if (col[v] != t) continue;
            vector<pair<int,int>> changes;
            vector<char> inStack(col.size(), 0);
            if (!recolorVertex(v, t - 1, 2, 0, col, g, inStack, changes)) {
                ok = false;
                break;
            }
        }

        if (ok) {
            bool any = false;
            for (int c : col) if (c == t) { any = true; break; }
            if (!any) return true;
        }

        col.swap(backup);
    }
    return false;
}

static void reduceColors(
    vector<int>& col,
    const vector<vector<int>>& g,
    const vector<int>& deg,
    mt19937& rng
) {
    while (true) {
        int t = maxColor(col);
        if (t <= 1) break;
        if (!tryEliminateMaxColor(col, g, deg, rng)) break;
    }
}

static vector<int> dsaturColoring(
    const vector<vector<int>>& g,
    const vector<int>& deg,
    mt19937& rng
) {
    int n = (int)g.size();
    vector<int> col(n, 0);
    vector<int> satDeg(n, 0);
    vector<bitset<512>> used(n);

    int uncolored = n;
    int curMaxColor = 0;

    while (uncolored > 0) {
        int bestSat = -1, bestDeg = -1;
        vector<int> cand;
        cand.reserve(n);

        for (int v = 0; v < n; ++v) {
            if (col[v] != 0) continue;
            int s = satDeg[v];
            int d = deg[v];
            if (s > bestSat || (s == bestSat && d > bestDeg)) {
                bestSat = s;
                bestDeg = d;
                cand.clear();
                cand.push_back(v);
            } else if (s == bestSat && d == bestDeg) {
                cand.push_back(v);
            }
        }

        int v = cand.empty() ? 0 : cand[uniform_int_distribution<int>(0, (int)cand.size() - 1)(rng)];

        int chosen = 1;
        for (int c = 1; c <= curMaxColor + 1; ++c) {
            if (!used[v].test(c - 1)) { chosen = c; break; }
        }

        col[v] = chosen;
        curMaxColor = max(curMaxColor, chosen);
        --uncolored;

        for (int u : g[v]) {
            if (col[u] != 0) continue;
            if (!used[u].test(chosen - 1)) {
                used[u].set(chosen - 1);
                satDeg[u]++;
            }
        }
    }

    return col;
}

static void compressColors(vector<int>& col) {
    int mx = maxColor(col);
    vector<int> mp(mx + 1, 0);
    for (int c : col) if (c >= 1 && c <= mx) mp[c] = 1;
    int k = 0;
    for (int c = 1; c <= mx; ++c) if (mp[c]) mp[c] = ++k;
    for (int& c : col) c = mp[c];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;

    vector<bitset<500>> adj(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }

    vector<vector<int>> g(N);
    g.assign(N, {});
    for (int i = 0; i < N; ++i) {
        g[i].reserve(N);
        for (int j = 0; j < N; ++j) {
            if (adj[i].test(j)) g[i].push_back(j);
        }
    }

    vector<int> deg(N, 0);
    for (int i = 0; i < N; ++i) deg[i] = (int)g[i].size();

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)N * 0x9e3779b97f4a7c15ULL;
    seed ^= (uint64_t)M * 0xbf58476d1ce4e5b9ULL;
    mt19937 rng((uint32_t)(seed ^ (seed >> 32)));

    auto start = chrono::steady_clock::now();
    vector<int> bestCol;
    int bestK = INT_MAX;

    int iter = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > 1.75) break;

        vector<int> col = dsaturColoring(g, deg, rng);
        reduceColors(col, g, deg, rng);
        compressColors(col);

        int k = maxColor(col);
        if (k < bestK && validateColoring(g, col)) {
            bestK = k;
            bestCol = col;
            if (bestK == 1) break;
        }

        ++iter;
        if (iter >= 200) break;
    }

    if (bestCol.empty()) {
        bestCol = dsaturColoring(g, deg, rng);
        compressColors(bestCol);
        if (!validateColoring(g, bestCol)) {
            // Fallback: trivial coloring
            bestCol.resize(N);
            iota(bestCol.begin(), bestCol.end(), 1);
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << bestCol[i] << "\n";
    }
    return 0;
}