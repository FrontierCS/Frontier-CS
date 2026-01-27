#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template <typename T>
    bool readInt(T &out) {
        char c;
        T sign = 1;
        T val = 0;
        c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c == '-') {
            sign = -1;
            c = getChar();
        }
        for (; c >= '0' && c <= '9'; c = getChar()) {
            val = val * 10 + (c - '0');
        }
        out = val * sign;
        return true;
    }
} In;

static inline int ctz64(uint64_t x) {
#if defined(_MSC_VER)
    unsigned long idx;
    _BitScanForward64(&idx, x);
    return (int)idx;
#else
    return __builtin_ctzll(x);
#endif
}

vector<char> greedyMIS(const vector<vector<int>>& g, mt19937_64 &rng) {
    int n = (int)g.size();
    vector<int> deg(n);
    for (int i = 0; i < n; ++i) deg[i] = (int)g[i].size();

    vector<char> active(n, 1), inSet(n, 0);
    vector<vector<int>> buckets(n + 1);
    for (int i = 0; i < n; ++i) buckets[deg[i]].push_back(i);
    int activeCount = n;
    int curMin = 0;

    auto removeNode = [&](int x) {
        if (!active[x]) return;
        active[x] = 0;
        --activeCount;
        for (int y : g[x]) {
            if (active[y]) {
                int nd = --deg[y];
                if (nd < 0) nd = 0;
                buckets[nd].push_back(y);
                if (nd < curMin) curMin = nd;
            }
        }
    };

    while (activeCount > 0) {
        int v = -1;
        while (curMin <= n) {
            auto &B = buckets[curMin];
            bool found = false;
            while (!B.empty()) {
                int idx = (int)B.size() - 1;
                if (B.size() > 1) {
                    idx = (int)(rng() % B.size());
                }
                int cand = B[idx];
                if (idx != (int)B.size() - 1) swap(B[idx], B.back());
                B.pop_back();
                if (!active[cand] || deg[cand] != curMin) continue;
                v = cand;
                found = true;
                break;
            }
            if (found) break;
            ++curMin;
        }
        if (v == -1) break;
        inSet[v] = 1;
        removeNode(v);
        for (int u : g[v]) {
            if (active[u]) {
                inSet[u] = 0;
                removeNode(u);
            }
        }
    }
    return inSet;
}

void twoSwapImprove(vector<char> &inSet,
                    const vector<vector<int>> &g,
                    const vector<vector<uint64_t>> &adjBits,
                    const chrono::steady_clock::time_point &deadline) {
    int n = (int)g.size();
    int W = (int)adjBits[0].size();
    vector<int> count(n, 0);

    for (int s = 0; s < n; ++s) if (inSet[s]) {
        for (int u : g[s]) if (!inSet[u]) ++count[u];
    }

    while (chrono::steady_clock::now() < deadline) {
        bool improved = false;

        for (int s = 0; s < n; ++s) {
            if (chrono::steady_clock::now() >= deadline) break;
            if (!inSet[s]) continue;

            vector<int> listC;
            listC.reserve(g[s].size());
            for (int u : g[s]) {
                if (!inSet[u] && count[u] == 1) listC.push_back(u);
            }
            if ((int)listC.size() < 2) continue;

            vector<uint64_t> cbits(W, 0);
            for (int u : listC) cbits[u >> 6] |= (1ULL << (u & 63));

            int uSel = -1, vSel = -1;
            for (int u : listC) {
                if (chrono::steady_clock::now() >= deadline) break;
                int wb = u >> 6;
                for (int b = 0; b < W; ++b) {
                    uint64_t mask = cbits[b] & ~adjBits[u][b];
                    if (b == wb) mask &= ~(1ULL << (u & 63));
                    if (mask) {
                        int bit = ctz64(mask);
                        int v = (b << 6) + bit;
                        if (v < n) {
                            uSel = u; vSel = v;
                            break;
                        }
                    }
                }
                if (uSel != -1) break;
            }

            if (uSel != -1) {
                inSet[s] = 0;
                for (int z : g[s]) if (!inSet[z]) --count[z];

                inSet[uSel] = 1;
                for (int z : g[uSel]) if (!inSet[z]) ++count[z];

                inSet[vSel] = 1;
                for (int z : g[vSel]) if (!inSet[z]) ++count[z];

                improved = true;
                break;
            }
        }

        if (!improved) break;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!In.readInt(N)) return 0;
    In.readInt(M);

    int W = (N + 63) >> 6;
    vector<vector<int>> g(N);
    vector<vector<uint64_t>> adjBits(N, vector<uint64_t>(W, 0));

    for (int i = 0; i < M; ++i) {
        int u, v;
        if (!In.readInt(u)) break;
        In.readInt(v);
        --u; --v;
        if (u == v || u < 0 || u >= N || v < 0 || v >= N) continue;
        int wv = v >> 6, wu = u >> 6;
        uint64_t mv = 1ULL << (v & 63);
        if ((adjBits[u][wv] & mv) == 0) {
            adjBits[u][wv] |= mv;
            adjBits[v][wu] |= (1ULL << (u & 63));
            g[u].push_back(v);
            g[v].push_back(u);
        }
    }

    mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    auto start = chrono::steady_clock::now();
    auto totalDeadline = start + chrono::milliseconds(1950);
    auto greedyDeadline = start + chrono::milliseconds(1300);

    vector<char> bestSel(N, 0);
    int bestK = -1;

    int iter = 0;
    while (chrono::steady_clock::now() < greedyDeadline) {
        vector<char> sel = greedyMIS(g, rng);
        int k = 0;
        for (char c : sel) if (c) ++k;
        if (k > bestK) {
            bestK = k;
            bestSel = move(sel);
        }
        ++iter;
        if (iter > 2000) break; // safety
    }

    if (bestK < 0) {
        bestSel = greedyMIS(g, rng);
        bestK = 0;
        for (char c : bestSel) if (c) ++bestK;
    }

    // Try 2-improvement on best solution with remaining time
    if (chrono::steady_clock::now() < totalDeadline) {
        twoSwapImprove(bestSel, g, adjBits, totalDeadline);
    }

    // Output
    string out;
    out.reserve((size_t)N * 2);
    for (int i = 0; i < N; ++i) {
        out.push_back(bestSel[i] ? '1' : '0');
        out.push_back('\n');
    }
    fwrite(out.c_str(), 1, out.size(), stdout);
    return 0;
}