#include <bits/stdc++.h>
using namespace std;

static const int MAXC = 512;

static inline double elapsedSec(const chrono::steady_clock::time_point& st) {
    return chrono::duration<double>(chrono::steady_clock::now() - st).count();
}

static int compressColors(vector<int>& color) {
    static int mp[MAXC];
    memset(mp, 0, sizeof(mp));
    int C = 0;
    for (int c : color) {
        if (c <= 0) continue;
        if (!mp[c]) mp[c] = ++C;
    }
    for (int &c : color) c = mp[c];
    return C;
}

static void polishColors(vector<int>& color, const vector<vector<int>>& adj, mt19937& rng, int passes = 2) {
    int N = (int)color.size();
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    static unsigned char used[MAXC];

    for (int pass = 0; pass < passes; pass++) {
        shuffle(order.begin(), order.end(), rng);
        for (int v : order) {
            int cur = color[v];
            if (cur <= 1) continue;
            memset(used, 0, MAXC);
            for (int u : adj[v]) used[color[u]] = 1;
            int c = 1;
            while (c < MAXC && used[c]) c++;
            if (c < cur) color[v] = c;
        }
    }
}

static int eliminateHighestColor(vector<int>& color, const vector<vector<int>>& adj) {
    int N = (int)color.size();
    int maxColor = 0;
    for (int c : color) maxColor = max(maxColor, c);

    static unsigned char used[MAXC];

    int k = maxColor;
    while (k > 1) {
        vector<int> verts;
        verts.reserve(N);
        for (int i = 0; i < N; i++) if (color[i] == k) verts.push_back(i);
        if (verts.empty()) { k--; continue; }

        vector<int> newc(verts.size(), 0);
        bool ok = true;

        for (size_t idx = 0; idx < verts.size(); idx++) {
            int v = verts[idx];
            memset(used, 0, MAXC);
            for (int u : adj[v]) {
                int c = color[u];
                if (c > 0 && c < k) used[c] = 1;
            }
            int nc = 0;
            for (int c = 1; c < k; c++) {
                if (!used[c]) { nc = c; break; }
            }
            if (nc == 0) { ok = false; break; }
            newc[idx] = nc;
        }

        if (!ok) break;
        for (size_t idx = 0; idx < verts.size(); idx++) color[verts[idx]] = newc[idx];
        k--;
    }

    return compressColors(color);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;

    vector<bitset<MAXC>> mat(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        if (!mat[u].test(v)) {
            mat[u].set(v);
            mat[v].set(u);
        }
    }

    vector<vector<int>> adj(N);
    adj.assign(N, {});
    for (int i = 0; i < N; i++) {
        adj[i].reserve(N);
        for (int j = 0; j < N; j++) if (mat[i].test(j)) adj[i].push_back(j);
    }

    vector<int> deg(N);
    for (int i = 0; i < N; i++) deg[i] = (int)adj[i].size();

    vector<int> baseOrder(N);
    iota(baseOrder.begin(), baseOrder.end(), 0);
    sort(baseOrder.begin(), baseOrder.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });

    auto greedyRun = [&](uint32_t seed) -> pair<int, vector<int>> {
        mt19937 rng(seed);
        vector<int> order = baseOrder;

        for (int i = 0; i < N; i++) {
            int span = min(12, N - i);
            int j = i + (int)(rng() % span);
            swap(order[i], order[j]);
        }

        vector<int> color(N, 0);
        static unsigned char used[MAXC];

        int maxColor = 0;
        for (int v : order) {
            memset(used, 0, MAXC);
            for (int u : adj[v]) if (color[u]) used[color[u]] = 1;
            int c = 1;
            while (c < MAXC && used[c]) c++;
            if (c >= MAXC) c = MAXC - 1;
            color[v] = c;
            maxColor = max(maxColor, c);
        }

        polishColors(color, adj, rng, 2);
        compressColors(color);
        int C = eliminateHighestColor(color, adj);
        return {C, std::move(color)};
    };

    vector<int> color(N), satDeg(N);
    vector<bitset<MAXC>> satMask(N);

    auto dsaturRun = [&](uint32_t seed) -> pair<int, vector<int>> {
        mt19937 rng(seed);

        fill(color.begin(), color.end(), 0);
        fill(satDeg.begin(), satDeg.end(), 0);
        for (int i = 0; i < N; i++) satMask[i].reset();

        int uncolored = N;
        int maxColor = 0;

        while (uncolored) {
            int best = -1;
            int bestSat = -1, bestDeg = -1;
            int tie = 0;

            for (int i = 0; i < N; i++) if (color[i] == 0) {
                int s = satDeg[i];
                int d = deg[i];
                if (s > bestSat || (s == bestSat && d > bestDeg)) {
                    best = i; bestSat = s; bestDeg = d;
                    tie = 1;
                } else if (s == bestSat && d == bestDeg) {
                    tie++;
                    if ((uint32_t)rng() % (uint32_t)tie == 0) best = i;
                }
            }

            int v = best;
            int c = 1;
            for (; c <= maxColor; c++) if (!satMask[v].test(c)) break;
            if (c == maxColor + 1) maxColor++;

            color[v] = c;
            uncolored--;

            for (int u : adj[v]) {
                if (color[u] == 0 && !satMask[u].test(c)) {
                    satMask[u].set(c);
                    satDeg[u]++;
                }
            }
        }

        vector<int> out = color;
        polishColors(out, adj, rng, 2);
        compressColors(out);
        int C = eliminateHighestColor(out, adj);
        return {C, std::move(out)};
    };

    auto st = chrono::steady_clock::now();
    const double TL = 1.92;

    vector<int> bestColor;
    int bestC = INT_MAX;

    {
        auto res = dsaturRun(1u);
        bestC = res.first;
        bestColor = std::move(res.second);
    }

    uint32_t seedBase = (uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    int iter = 0;

    while (elapsedSec(st) < TL) {
        uint32_t seed = seedBase + 10007u * (uint32_t)(iter + 1);

        pair<int, vector<int>> res;
        if (iter < 25 || (iter % 9 == 0)) res = greedyRun(seed);
        else res = dsaturRun(seed);

        if (res.first < bestC) {
            bestC = res.first;
            bestColor = std::move(res.second);
        }
        iter++;
    }

    for (int i = 0; i < N; i++) {
        cout << bestColor[i] << "\n";
    }

    return 0;
}