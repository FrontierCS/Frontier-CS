#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 22;
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
    template<typename T>
    bool nextInt(T &out) {
        char c;
        T sign = 1;
        T val = 0;
        c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c == '-') { sign = -1; c = getChar(); }
        for (; c >= '0' && c <= '9'; c = getChar()) {
            val = val * 10 + (c - '0');
        }
        out = val * sign;
        return true;
    }
    bool nextDouble(double &out) {
        char c = getChar();
        if (!c) return false;
        while (c != '-' && c != '.' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        bool neg = false;
        if (c == '-') { neg = true; c = getChar(); }
        long long intPart = 0;
        while (c >= '0' && c <= '9') { intPart = intPart * 10 + (c - '0'); c = getChar(); }
        double res = (double)intPart;
        if (c == '.') {
            c = getChar();
            double frac = 0.0, base = 1.0;
            while (c >= '0' && c <= '9') {
                frac = frac * 10.0 + (c - '0');
                base *= 10.0;
                c = getChar();
            }
            res += frac / base;
        }
        out = neg ? -res : res;
        return true;
    }
} In;

struct FastOutput {
    static const int BUFSIZE = 1 << 20;
    int idx;
    char buf[BUFSIZE];
    FastOutput() : idx(0) {}
    ~FastOutput() { flush(); }
    inline void pushChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }
    inline void writeInt(int x) {
        if (x == 0) { pushChar('0'); return; }
        if (x < 0) { pushChar('-'); x = -x; }
        char s[16]; int n = 0;
        while (x) { s[n++] = char('0' + (x % 10)); x /= 10; }
        while (n--) pushChar(s[n]);
    }
    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }
} Out;

struct RNG {
    uint64_t s;
    RNG(uint64_t seed=88172645463393265ull) : s(seed) {}
    inline uint64_t next() {
        uint64_t x = s;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        s = x;
        return x * 2685821657736338717ULL;
    }
    inline int nextInt(int l, int r) { // inclusive
        return l + (int)(next() % (uint64_t)(r - l + 1));
    }
    template<typename T>
    void shuffleVec(vector<T>& a) {
        for (int i = (int)a.size() - 1; i > 0; --i) {
            int j = (int)(next() % (uint64_t)(i + 1));
            swap(a[i], a[j]);
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    auto tStart = chrono::steady_clock::now();

    int n, k;
    long long m_ll;
    double eps;
    if (!In.nextInt(n)) return 0;
    In.nextInt(m_ll);
    In.nextInt(k);
    In.nextDouble(eps);
    size_t m = (size_t)m_ll;

    // Read edges, build degrees ignoring self-loops
    vector<int> deg(n + 1, 0);
    vector<int> U; U.resize(m);
    vector<int> V; V.resize(m);
    for (size_t i = 0; i < m; ++i) {
        int u, v;
        In.nextInt(u);
        In.nextInt(v);
        U[i] = u;
        V[i] = v;
        if (u != v) {
            if (u >= 1 && u <= n) deg[u]++;
            if (v >= 1 && v <= n) deg[v]++;
        }
    }

    // Build CSR adjacency
    vector<int> offset(n + 2, 0);
    for (int i = 1; i <= n; ++i) {
        offset[i + 1] = offset[i] + deg[i];
    }
    int tot = offset[n + 1];
    vector<int> adj;
    adj.resize(tot);
    vector<int> cur = offset;
    for (size_t i = 0; i < m; ++i) {
        int u = U[i], v = V[i];
        if (u == v) continue;
        if ((unsigned)u <= (unsigned)n && (unsigned)v <= (unsigned)n) {
            adj[cur[u]++] = v;
            adj[cur[v]++] = u;
        }
    }
    U.clear(); U.shrink_to_fit();
    V.clear(); V.shrink_to_fit();

    // Partition parameters
    int ideal = (n + k - 1) / k;
    int cap = (int)floor((1.0 + eps) * ideal);
    if (cap < 1) cap = 1;

    vector<int> part(n + 1, 0);
    vector<int> partSize(k + 1, 0);

    RNG rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    // Choose seeds
    int sCount = min(k, n);
    vector<char> used(n + 1, 0);
    vector<int> seeds; seeds.reserve(sCount);
    for (int i = 1; i <= sCount; ++i) {
        int v;
        int tries = 0;
        do {
            v = rng.nextInt(1, n);
            ++tries;
            if (tries > 5 && deg[v] == 0) { // try to avoid isolated nodes if possible
                v = rng.nextInt(1, n);
            }
        } while (used[v]);
        used[v] = 1;
        seeds.push_back(v);
    }

    // Multi-source BFS growth
    vector<int> q; q.reserve(n);
    for (int i = 0; i < sCount; ++i) {
        int v = seeds[i];
        part[v] = i + 1;
        partSize[i + 1] = 1;
        q.push_back(v);
    }
    size_t qi = 0;
    while (qi < q.size()) {
        int v = q[qi++];
        int p = part[v];
        if (partSize[p] >= cap) continue;
        int begin = offset[v], end = offset[v + 1];
        for (int e = begin; e < end; ++e) {
            int u = adj[e];
            if (part[u] == 0) {
                if (partSize[p] >= cap) break;
                part[u] = p;
                partSize[p]++;
                q.push_back(u);
            }
        }
    }

    // Assign unassigned vertices to underfull parts based on neighbor majority; fallback to min-size part
    vector<int> counts(k + 1, 0);
    vector<int> usedParts;
    usedParts.reserve(64);
    priority_queue<pair<int,int>, vector<pair<int,int>>, greater<pair<int,int>>> heap;
    for (int p = 1; p <= k; ++p) {
        if (partSize[p] < cap) heap.emplace(partSize[p], p);
    }
    for (int v = 1; v <= n; ++v) {
        if (part[v] != 0) continue;
        usedParts.clear();
        int begin = offset[v], end = offset[v + 1];
        for (int e = begin; e < end; ++e) {
            int u = adj[e];
            int pu = part[u];
            if (pu > 0) {
                if (counts[pu] == 0) usedParts.push_back(pu);
                counts[pu]++;
            }
        }
        int dest = -1, bestCnt = -1;
        for (int p : usedParts) {
            if (partSize[p] < cap) {
                int c = counts[p];
                if (c > bestCnt || (c == bestCnt && partSize[p] < (dest == -1 ? INT_MAX : partSize[dest]))) {
                    bestCnt = c; dest = p;
                }
            }
        }
        for (int p : usedParts) counts[p] = 0;
        if (dest == -1) {
            // pick globally smallest part
            while (!heap.empty()) {
                auto [s, p] = heap.top();
                if (s != partSize[p] || partSize[p] >= cap) heap.pop();
                else break;
            }
            if (!heap.empty()) dest = heap.top().second;
            else {
                // Fallback linear scan if heap exhausted (shouldn't happen)
                int minP = -1, minS = INT_MAX;
                for (int p = 1; p <= k; ++p) {
                    if (partSize[p] < cap && partSize[p] < minS) { minS = partSize[p]; minP = p; }
                }
                if (minP == -1) dest = 1; else dest = minP;
            }
        }
        part[v] = dest;
        partSize[dest]++;
        heap.emplace(partSize[dest], dest);
    }

    // Build boundary list
    vector<int> boundary;
    boundary.reserve(n / 2);
    for (int v = 1; v <= n; ++v) {
        int pv = part[v];
        bool isBoundary = false;
        for (int e = offset[v], end = offset[v + 1]; e < end; ++e) {
            int u = adj[e];
            if (part[u] != pv) { isBoundary = true; break; }
        }
        if (isBoundary) boundary.push_back(v);
    }

    // Time-aware refinement: one pass over boundary if time allows
    auto timeSpent = chrono::duration<double>(chrono::steady_clock::now() - tStart).count();
    bool doRefine = timeSpent < 0.85; // leave time to print
    if (doRefine && !boundary.empty()) {
        // Shuffle boundary to avoid bias
        rng.shuffleVec(boundary);
        for (int v : boundary) {
            int curP = part[v];
            usedParts.clear();
            int begin = offset[v], end = offset[v + 1];
            for (int e = begin; e < end; ++e) {
                int u = adj[e];
                int pu = part[u];
                if (pu > 0) {
                    if (counts[pu] == 0) usedParts.push_back(pu);
                    counts[pu]++;
                }
            }
            int curCount = counts[curP];
            int bestP = curP;
            int bestCnt = curCount;
            for (int p : usedParts) {
                if (p == curP) continue;
                if (partSize[p] + 1 > cap) continue;
                int c = counts[p];
                if (c > bestCnt || (c == bestCnt && partSize[p] < partSize[bestP])) {
                    bestCnt = c;
                    bestP = p;
                }
            }
            for (int p : usedParts) counts[p] = 0;
            if (bestP != curP) {
                partSize[curP]--;
                partSize[bestP]++;
                part[v] = bestP;
            }
        }
    }

    // Output partition labels
    for (int i = 1; i <= n; ++i) {
        Out.writeInt(part[i] >= 1 && part[i] <= k ? part[i] : 1);
        if (i < n) Out.pushChar(' ');
    }
    Out.pushChar('\n');
    Out.flush();
    return 0;
}