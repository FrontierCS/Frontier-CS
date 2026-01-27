#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 500;
static const int MAXC = 512;

static int maxColorCount(const vector<int>& col) {
    int mx = 0;
    for (int c : col) mx = max(mx, c);
    return mx;
}

static vector<int> compressColors(vector<int> col) {
    int n = (int)col.size();
    int mx = maxColorCount(col);
    vector<int> mp(mx + 1, 0);
    int nxt = 0;
    for (int i = 0; i < n; i++) {
        int c = col[i];
        if (mp[c] == 0) mp[c] = ++nxt;
        col[i] = mp[c];
    }
    return col;
}

static vector<int> dsaturColoring(const vector<vector<int>>& comp, const vector<int>& deg, mt19937& rng) {
    int n = (int)comp.size();
    vector<int> color(n, 0), satDeg(n, 0);
    vector<bitset<MAXC>> satMask(n);

    int uncolored = n;
    int maxCol = 0;

    while (uncolored) {
        int bestSat = -1, bestDeg = -1;
        vector<int> cand;
        cand.reserve(n);

        for (int v = 0; v < n; v++) if (color[v] == 0) {
            int s = satDeg[v], d = deg[v];
            if (s > bestSat || (s == bestSat && d > bestDeg)) {
                bestSat = s;
                bestDeg = d;
                cand.clear();
                cand.push_back(v);
            } else if (s == bestSat && d == bestDeg) {
                cand.push_back(v);
            }
        }

        int v = cand.size() == 1 ? cand[0] : cand[uniform_int_distribution<int>(0, (int)cand.size() - 1)(rng)];

        int c;
        for (c = 1; c <= maxCol; c++) if (!satMask[v].test(c)) break;
        if (c == maxCol + 1) maxCol++;

        color[v] = c;
        uncolored--;

        for (int nb : comp[v]) {
            if (color[nb] == 0 && !satMask[nb].test(c)) {
                satMask[nb].set(c);
                satDeg[nb]++;
            }
        }
    }

    return color;
}

static vector<int> greedyColoringOrder(const vector<vector<int>>& comp, const vector<int>& order) {
    int n = (int)comp.size();
    vector<int> col(n, 0);
    int maxCol = 0;

    static int stamp[MAXN + 1];
    int curStamp = 1;

    for (int v : order) {
        curStamp++;
        for (int nb : comp[v]) {
            int c = col[nb];
            if (c) stamp[c] = curStamp;
        }
        int c;
        for (c = 1; c <= maxCol; c++) if (stamp[c] != curStamp) break;
        if (c == maxCol + 1) maxCol++;
        col[v] = c;
    }
    return col;
}

static vector<int> reduceEliminateMaxColor(vector<int> col, const vector<vector<int>>& comp, const vector<int>& deg) {
    int n = (int)col.size();
    col = compressColors(move(col));

    static int stamp[MAXN + 1];
    int curStamp = 1;

    while (true) {
        int K = maxColorCount(col);
        if (K <= 1) break;

        int target = K;
        vector<int> verts;
        for (int i = 0; i < n; i++) if (col[i] == target) verts.push_back(i);
        if (verts.empty()) {
            col = compressColors(move(col));
            continue;
        }

        sort(verts.begin(), verts.end(), [&](int a, int b) {
            return deg[a] > deg[b];
        });

        vector<int> attempt = col;
        bool ok = true;

        for (int v : verts) {
            curStamp++;
            for (int nb : comp[v]) {
                int c = attempt[nb];
                if (c && c < target) stamp[c] = curStamp;
            }
            int chosen = 0;
            for (int c = 1; c < target; c++) {
                if (stamp[c] != curStamp) { chosen = c; break; }
            }
            if (!chosen) { ok = false; break; }
            attempt[v] = chosen;
        }

        if (!ok) break;
        col = compressColors(move(attempt));
    }

    return col;
}

static bool validateCliqueCover(const vector<bitset<MAXN>>& adjOrig, const vector<int>& id, int n) {
    for (int u = 0; u < n; u++) {
        for (int v = u + 1; v < n; v++) {
            if (id[u] == id[v] && !adjOrig[u].test(v)) return false;
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    int M;
    if (!(cin >> N >> M)) return 0;

    vector<bitset<MAXN>> adjOrig(N);
    for (int i = 0; i < N; i++) adjOrig[i].reset();

    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adjOrig[u].set(v);
        adjOrig[v].set(u);
    }
    for (int i = 0; i < N; i++) adjOrig[i].reset(i);

    vector<vector<int>> comp(N);
    comp.assign(N, {});
    for (int u = 0; u < N; u++) {
        comp[u].reserve(N);
        for (int v = 0; v < N; v++) {
            if (u == v) continue;
            if (!adjOrig[u].test(v)) comp[u].push_back(v);
        }
    }

    vector<int> deg(N);
    for (int i = 0; i < N; i++) deg[i] = (int)comp[i].size();

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    mt19937 rng((uint32_t)(seed ^ (seed >> 32)));

    auto start = chrono::high_resolution_clock::now();
    auto elapsedSec = [&]() -> double {
        auto now = chrono::high_resolution_clock::now();
        return chrono::duration<double>(now - start).count();
    };

    vector<int> best = reduceEliminateMaxColor(dsaturColoring(comp, deg, rng), comp, deg);
    best = compressColors(move(best));
    int bestK = maxColorCount(best);

    for (int iter = 0; iter < 100000; iter++) {
        if (elapsedSec() > 1.85) break;

        vector<int> col;
        if (iter % 3 != 2) {
            mt19937 r2((uint32_t)(rng() ^ (uint32_t)(iter * 2654435761u)));
            col = dsaturColoring(comp, deg, r2);
        } else {
            vector<int> order(N);
            iota(order.begin(), order.end(), 0);
            mt19937 r2((uint32_t)(rng() ^ (uint32_t)(iter * 2166136261u)));
            shuffle(order.begin(), order.end(), r2);
            stable_sort(order.begin(), order.end(), [&](int a, int b) {
                return deg[a] > deg[b];
            });
            col = greedyColoringOrder(comp, order);
        }

        col = reduceEliminateMaxColor(move(col), comp, deg);
        col = compressColors(move(col));
        int K = maxColorCount(col);

        if (K < bestK) {
            bestK = K;
            best = move(col);
            if (bestK == 1) break;
        }
    }

    if (!validateCliqueCover(adjOrig, best, N)) {
        // Fallback: each vertex its own clique
        for (int i = 0; i < N; i++) cout << (i + 1) << "\n";
        return 0;
    }

    for (int i = 0; i < N; i++) {
        cout << best[i] << "\n";
    }
    return 0;
}