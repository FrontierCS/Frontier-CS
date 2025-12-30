#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char readChar() {
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
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') { neg = true; c = readChar(); }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = neg ? -val : val;
        return true;
    }
};

struct FastOutput {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0;

    ~FastOutput() { flush(); }

    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }

    inline void pushChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }

    inline void writeInt(int x) {
        if (x == 0) { pushChar('0'); return; }
        if (x < 0) { pushChar('-'); x = -x; }
        char s[12];
        int n = 0;
        while (x) { s[n++] = char('0' + (x % 10)); x /= 10; }
        while (n--) pushChar(s[n]);
    }
};

struct XorShift64 {
    uint64_t x;
    explicit XorShift64(uint64_t seed = 88172645463325252ull) : x(seed ? seed : 88172645463325252ull) {}
    inline uint64_t nextU64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
};

struct Node {
    int nb[8];
    uint8_t cnt;
};

struct Frame {
    int u;
    uint16_t tried;
};

static inline uint64_t mix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ull;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ull;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebull;
    return x ^ (x >> 31);
}

static bool findTourAttempt(
    int N,
    const vector<Node> &g,
    int start,
    int blocked,
    int targetLen,
    uint64_t seed,
    chrono::steady_clock::time_point deadline,
    vector<int> &outPath
) {
    const int S = N * N;
    vector<uint8_t> vis(S, 0);
    if (blocked >= 0) vis[blocked] = 1;
    if (vis[start]) return false;

    vector<uint8_t> deg(S, 0);
    for (int i = 0; i < S; i++) {
        if (vis[i]) continue;
        uint8_t d = 0;
        const Node &nd = g[i];
        for (uint8_t k = 0; k < nd.cnt; k++) {
            int v = nd.nb[k];
            if (!vis[v]) d++;
        }
        deg[i] = d;
    }

    auto visit = [&](int v) {
        vis[v] = 1;
        const Node &nd = g[v];
        for (uint8_t k = 0; k < nd.cnt; k++) {
            int to = nd.nb[k];
            if (!vis[to]) deg[to]--;
        }
        deg[v] = 0;
    };

    auto unvisit = [&](int v) {
        vis[v] = 0;
        const Node &nd = g[v];
        uint8_t d = 0;
        for (uint8_t k = 0; k < nd.cnt; k++) {
            int to = nd.nb[k];
            if (!vis[to]) d++;
        }
        deg[v] = d;
        for (uint8_t k = 0; k < nd.cnt; k++) {
            int to = nd.nb[k];
            if (!vis[to]) deg[to]++;
        }
    };

    auto secondaryScore = [&](int v) -> int {
        int s = 0;
        const Node &nd = g[v];
        for (uint8_t k = 0; k < nd.cnt; k++) {
            int w = nd.nb[k];
            if (!vis[w]) s += deg[w];
        }
        return s;
    };

    XorShift64 rng(mix64(seed));

    vector<Frame> st;
    vector<int> path;
    st.reserve((size_t)targetLen);
    path.reserve((size_t)targetLen);

    visit(start);
    st.push_back({start, 0});
    path.push_back(start);

    uint64_t backtracks = 0;
    uint64_t stepOps = 0;

    while (true) {
        if ((int)path.size() == targetLen) {
            outPath.swap(path);
            return true;
        }
        if ((stepOps++ & 0x3FFFu) == 0) {
            if (chrono::steady_clock::now() >= deadline) return false;
        }

        Frame &fr = st.back();
        int u = fr.u;
        const Node &nd = g[u];

        int bestPos = -1;
        int bestD = 1000000;
        int bestS = 1000000;
        int ties = 0;

        for (uint8_t i = 0; i < nd.cnt; i++) {
            if (fr.tried & (uint16_t(1) << i)) continue;
            int v = nd.nb[i];
            if (vis[v]) continue;

            int d = deg[v];
            if (d > bestD) continue;

            int s = (d < bestD) ? secondaryScore(v) : secondaryScore(v);

            if (d < bestD || (d == bestD && s < bestS)) {
                bestD = d;
                bestS = s;
                bestPos = i;
                ties = 1;
            } else if (d == bestD && s == bestS) {
                ties++;
                if ((int)(rng.nextU32() % (uint32_t)ties) == 0) bestPos = i;
            }
        }

        if (bestPos >= 0) {
            fr.tried |= (uint16_t(1) << bestPos);
            int v = nd.nb[bestPos];
            visit(v);
            st.push_back({v, 0});
            path.push_back(v);
        } else {
            if (st.size() == 1) return false;
            int cur = st.back().u;
            st.pop_back();
            path.pop_back();
            unvisit(cur);
            backtracks++;
            if (backtracks > 20000000ULL && N >= 200) return false;
        }
    }
}

int main() {
    FastScanner fs;
    int N;
    int r0, c0;
    if (!fs.readInt(N)) return 0;
    fs.readInt(r0);
    fs.readInt(c0);
    int sr = r0 - 1, sc = c0 - 1;
    int S = N * N;
    int start = sr * N + sc;

    vector<Node> g(S);
    static const int dr[8] = { 2, 2, 1, 1, -1, -1, -2, -2 };
    static const int dc[8] = { 1, -1, 2, -2, 2, -2, 1, -1 };

    for (int r = 0; r < N; r++) {
        for (int c = 0; c < N; c++) {
            int id = r * N + c;
            Node nd;
            nd.cnt = 0;
            for (int k = 0; k < 8; k++) {
                int nr = r + dr[k], nc = c + dc[k];
                if ((unsigned)nr < (unsigned)N && (unsigned)nc < (unsigned)N) {
                    nd.nb[nd.cnt++] = nr * N + nc;
                }
            }
            g[id] = nd;
        }
    }

    int startColor = (r0 + c0) & 1; // 0 even, 1 odd
    int targetLen;
    vector<int> blockedCandidates;

    if ((N & 1) == 0) {
        targetLen = S;
        blockedCandidates.push_back(-1);
    } else {
        // On odd N, (1,1) is majority color (even).
        if (startColor == 0) {
            targetLen = S;
            blockedCandidates.push_back(-1);
        } else {
            targetLen = S - 1;
            auto addIfValid = [&](int rr, int cc) {
                int idx = (rr - 1) * N + (cc - 1);
                if (idx == start) return;
                if (((rr + cc) & 1) != 0) return; // must be majority (even)
                blockedCandidates.push_back(idx);
            };
            addIfValid(1, 1);
            addIfValid(1, N);
            addIfValid(N, 1);
            addIfValid(N, N);
            addIfValid((N + 1) / 2, (N + 1) / 2);
            addIfValid(1, (N + 1) / 2);
            addIfValid(N, (N + 1) / 2);
            addIfValid((N + 1) / 2, 1);
            addIfValid((N + 1) / 2, N);
            sort(blockedCandidates.begin(), blockedCandidates.end());
            blockedCandidates.erase(unique(blockedCandidates.begin(), blockedCandidates.end()), blockedCandidates.end());
            if (blockedCandidates.empty()) blockedCandidates.push_back(0); // fallback
        }
    }

    vector<int> path, bestPath;
    bestPath.clear();

    auto tStart = chrono::steady_clock::now();
    auto deadline = tStart + chrono::milliseconds(900);

    bool ok = false;
    uint64_t baseSeed = mix64((uint64_t)N * 1000003ull ^ (uint64_t)(start + 1) * 10007ull);

    int maxSeeds = (N <= 20 ? 200 : (N <= 60 ? 80 : (N <= 120 ? 40 : 20)));
    for (int bc : blockedCandidates) {
        for (int t = 0; t < maxSeeds; t++) {
            if (chrono::steady_clock::now() >= deadline) break;
            uint64_t seed = mix64(baseSeed ^ (uint64_t)(bc + 2) * 0x9e3779b97f4a7c15ull ^ (uint64_t)t * 0xD1B54A32D192ED03ull);
            path.clear();
            if (findTourAttempt(N, g, start, bc, targetLen, seed, deadline, path)) {
                ok = true;
                break;
            } else {
                if ((int)path.size() > (int)bestPath.size()) bestPath = path;
            }
        }
        if (ok) break;
    }

    if (!ok) {
        // As a last resort, output the best partial path found (should not happen on valid tests).
        path = bestPath;
        if (path.empty()) path.push_back(start);
    }

    FastOutput fo;
    fo.writeInt((int)path.size());
    fo.pushChar('\n');
    for (size_t i = 0; i < path.size(); i++) {
        int id = path[i];
        int rr = id / N + 1;
        int cc = id - (rr - 1) * N + 1;
        fo.writeInt(rr);
        fo.pushChar(' ');
        fo.writeInt(cc);
        if (i + 1 < path.size()) fo.pushChar('\n');
    }
    fo.pushChar('\n');
    fo.flush();
    return 0;
}