#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 500;
static const int MAXC = 512;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = read();
            if (!c) return false;
        } while (c <= ' ');
        bool neg = false;
        if (c == '-') { neg = true; c = read(); }
        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = read();
        }
        out = neg ? -val : val;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int N, M;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M);

    vector<bitset<MAXN>> adj(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        fs.readInt(u); fs.readInt(v);
        --u; --v;
        if (u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }

    bitset<MAXN> full;
    for (int i = 0; i < N; i++) full.set(i);

    vector<bitset<MAXN>> compMask(N);
    for (int i = 0; i < N; i++) {
        compMask[i] = full;
        compMask[i].reset(i);
        compMask[i] &= (~adj[i]);
    }

    vector<vector<int>> compAdj(N);
    for (int i = 0; i < N; i++) compAdj[i].reserve(N);
    for (int i = 0; i < N; i++) {
        for (int j = i + 1; j < N; j++) {
            if (!adj[i].test(j)) {
                compAdj[i].push_back(j);
                compAdj[j].push_back(i);
            }
        }
    }
    vector<int> degComp(N);
    for (int i = 0; i < N; i++) degComp[i] = (int)compAdj[i].size();

    vector<int> color(N, 0);
    vector<char> uncolored(N, 1);
    vector<bitset<MAXC>> used(N);
    vector<int> satDeg(N, 0);

    int maxColor = 0, coloredCnt = 0;

    while (coloredCnt < N) {
        int best = -1;
        int bestSat = -1, bestDeg = -1;
        for (int v = 0; v < N; v++) if (uncolored[v]) {
            int s = satDeg[v];
            int d = degComp[v];
            if (s > bestSat || (s == bestSat && d > bestDeg)) {
                bestSat = s;
                bestDeg = d;
                best = v;
            }
        }

        int c = 1;
        for (; c <= maxColor; c++) {
            if (!used[best].test((size_t)c)) break;
        }
        if (c == maxColor + 1) maxColor++;

        color[best] = c;
        uncolored[best] = 0;
        coloredCnt++;

        for (int u : compAdj[best]) {
            if (!uncolored[u]) continue;
            if (!used[u].test((size_t)c)) {
                used[u].set((size_t)c);
                satDeg[u]++;
            }
        }
    }

    auto compressColors = [&](vector<int>& col, int &K) {
        vector<char> present(K + 1, 0);
        for (int v = 0; v < N; v++) present[col[v]] = 1;
        vector<int> remap(K + 1, 0);
        int nk = 0;
        for (int c = 1; c <= K; c++) if (present[c]) remap[c] = ++nk;
        for (int v = 0; v < N; v++) col[v] = remap[col[v]];
        K = nk;
    };

    compressColors(color, maxColor);

    // Local improvement: try moving vertices to lower colors, multiple passes.
    for (int pass = 0; pass < 3; pass++) {
        vector<bitset<MAXN>> colorVerts(maxColor + 1);
        for (int v = 0; v < N; v++) colorVerts[color[v]].set(v);

        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b) {
            if (color[a] != color[b]) return color[a] > color[b];
            return degComp[a] > degComp[b];
        });

        bool changed = false;
        for (int v : order) {
            int cur = color[v];
            for (int c = 1; c < cur; c++) {
                if ((compMask[v] & colorVerts[c]).none()) {
                    colorVerts[cur].reset(v);
                    colorVerts[c].set(v);
                    color[v] = c;
                    changed = true;
                    break;
                }
            }
        }

        int oldK = maxColor;
        compressColors(color, maxColor);
        if (!changed && maxColor == oldK) break;
    }

    for (int i = 0; i < N; i++) {
        cout << color[i] << "\n";
    }
    return 0;
}