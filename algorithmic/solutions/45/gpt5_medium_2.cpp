#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template <typename T>
    bool nextInt(T &out) {
        char c; T sgn = 1; T x = 0;
        c = getChar(); if (!c) return false;
        while (c!='-' && (c<'0'||c>'9')) { c = getChar(); if (!c) return false; }
        if (c=='-') { sgn = -1; c = getChar(); }
        for (; c>='0' && c<='9'; c = getChar()) x = x*10 + (c - '0');
        out = x * sgn;
        return true;
    }
    bool nextDouble(double &out) {
        char c = getChar(); if (!c) return false;
        while (c!='-' && c!='.' && (c<'0'||c>'9')) { c = getChar(); if (!c) return false; }
        int sign = 1;
        if (c=='-') { sign = -1; c = getChar(); }
        double x = 0.0;
        while (c>='0' && c<='9') { x = x*10.0 + (c - '0'); c = getChar(); }
        if (c=='.') {
            double pow10 = 0.1;
            c = getChar();
            while (c>='0' && c<='9') {
                x += (c - '0') * pow10;
                pow10 *= 0.1;
                c = getChar();
            }
        }
        out = x * sign;
        return true;
    }
} In;

struct FastOutput {
    static const int BUFSIZE = 1 << 20;
    int idx;
    char buf[BUFSIZE];
    FastOutput(): idx(0) {}
    ~FastOutput(){ flush(); }
    inline void pushChar(char c) {
        if (idx >= BUFSIZE) { fwrite(buf,1,idx,stdout); idx=0; }
        buf[idx++] = c;
    }
    inline void writeInt(int x, char endc) {
        if (x==0) { pushChar('0'); pushChar(endc); return; }
        if (x<0) { pushChar('-'); x=-x; }
        char s[16]; int n=0;
        while (x) { s[n++] = char('0' + (x%10)); x/=10; }
        for (int i=n-1;i>=0;--i) pushChar(s[i]);
        pushChar(endc);
    }
    inline void flush() {
        if (idx) { fwrite(buf,1,idx,stdout); idx=0; }
    }
} Out;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m, k;
    double eps;
    if (!In.nextInt(n)) return 0;
    In.nextInt(m);
    In.nextInt(k);
    In.nextDouble(eps);

    vector<int> U; U.reserve(m);
    vector<int> V; V.reserve(m);

    vector<int> deg(n+1, 0);

    for (int i=0;i<m;i++) {
        int u,v;
        In.nextInt(u);
        In.nextInt(v);
        if (u<1 || u>n || v<1 || v>n) continue;
        if (u==v) continue; // ignore self-loops
        U.push_back(u);
        V.push_back(v);
        deg[u]++;
        deg[v]++;
    }
    int E = (int)U.size();

    // Build CSR adjacency
    vector<int> head(n+2, 0);
    for (int i=1;i<=n;i++) head[i+1] = head[i] + deg[i];
    vector<int> adj(2*E);
    vector<int> cur = head;
    for (int e=0;e<E;e++) {
        int u = U[e], v = V[e];
        adj[cur[u]++] = v;
        adj[cur[v]++] = u;
    }
    U.clear(); V.clear(); U.shrink_to_fit(); V.shrink_to_fit();

    // Capacity
    int ideal = (n + k - 1) / k; // ceil(n/k)
    int capEach = (int)floor((1.0 + eps) * ideal + 1e-9);
    if (capEach < 1) capEach = 1;

    vector<int> part(n+1, 0);
    vector<int> sizePart(k+1, 0);
    vector<int> capLeft(k+1, capEach);

    // Seed selection: random vertices, prefer deg>0
    mt19937 rng(712367);
    vector<int> seeds(k+1, 1);
    vector<char> used(n+1, 0);
    int picked = 0;
    // First try to pick deg>0
    for (int j=1; j<=k; ++j) {
        int v = 0;
        for (int tries=0; tries<50; ++tries) {
            int cand = (int)(rng()%n) + 1;
            if (!used[cand] && deg[cand]>0) { v = cand; break; }
        }
        if (v==0) {
            // fallback: any unused
            for (int t=0; t<50; ++t) {
                int cand = (int)(rng()%n) + 1;
                if (!used[cand]) { v = cand; break; }
            }
            if (v==0) {
                // linear scan
                for (int cand=1; cand<=n; ++cand) {
                    if (!used[cand]) { v = cand; break; }
                }
            }
        }
        if (v==0) v = 1;
        used[v] = 1;
        seeds[j] = v;
        ++picked;
    }

    // Multi-source BFS with capacity constraints
    deque<uint64_t> dq;
    dq.clear();
    for (int j=1; j<=k; ++j) {
        uint64_t pack = ((uint64_t)seeds[j] << 32) | (uint32_t)j;
        dq.push_back(pack);
    }

    int assigned = 0;
    int nextUnassigned = 1;

    while (assigned < n) {
        while (!dq.empty()) {
            uint64_t pack = dq.front(); dq.pop_front();
            int u = (int)(pack >> 32);
            int lbl = (int)(pack & 0xffffffffu);
            if (part[u] != 0) continue;
            if (capLeft[lbl] == 0) continue;
            part[u] = lbl;
            capLeft[lbl]--;
            sizePart[lbl]++;
            assigned++;
            // expand
            int start = head[u], end = head[u+1];
            for (int it = start; it < end; ++it) {
                int v = adj[it];
                if (part[v] == 0) {
                    uint64_t p2 = ((uint64_t)v << 32) | (uint32_t)lbl;
                    dq.push_back(p2);
                }
            }
        }
        if (assigned >= n) break;
        // Need to seed new fronts for remaining unassigned vertices
        int lbl = -1;
        for (int j=1; j<=k; ++j) { if (capLeft[j] > 0) { lbl = j; break; } }
        if (lbl == -1) break; // Should not happen if total capacity >= n
        while (nextUnassigned <= n && part[nextUnassigned] != 0) nextUnassigned++;
        if (nextUnassigned <= n) {
            uint64_t pack = ((uint64_t)nextUnassigned << 32) | (uint32_t)lbl;
            dq.push_back(pack);
            nextUnassigned++;
        } else {
            break;
        }
    }

    // One refinement pass: label propagation with capacity constraint
    // Only if k>1 and graph not trivial
    if (k > 1) {
        vector<int> cnt(k+1, 0);
        vector<int> touched; touched.reserve(32);
        vector<int> order(n);
        iota(order.begin(), order.end(), 1);
        shuffle(order.begin(), order.end(), rng);

        for (int idxv = 0; idxv < n; ++idxv) {
            int v = order[idxv];
            int curp = part[v];
            int start = head[v], end = head[v+1];
            int currCount = 0;
            touched.clear();
            for (int it = start; it < end; ++it) {
                int w = adj[it];
                int pw = part[w];
                if (pw == 0) continue;
                if (cnt[pw] == 0) touched.push_back(pw);
                cnt[pw]++;
            }
            currCount = cnt[curp];
            int bestp = curp;
            int bestc = currCount;
            for (int p2 : touched) {
                if (p2 == curp) continue;
                int c = cnt[p2];
                if (c > bestc && sizePart[p2] < capEach) {
                    bestc = c;
                    bestp = p2;
                }
            }
            if (bestp != curp && sizePart[bestp] < capEach) {
                // move if strictly better
                if (bestc > currCount) {
                    sizePart[curp]--;
                    sizePart[bestp]++;
                    part[v] = bestp;
                }
            }
            for (int p2 : touched) cnt[p2] = 0;
        }
    }

    // Output
    for (int i=1;i<=n;i++) {
        Out.writeInt(part[i] >= 1 && part[i] <= k ? part[i] : 1, i==n?'\n':' ');
    }
    Out.flush();
    return 0;
}