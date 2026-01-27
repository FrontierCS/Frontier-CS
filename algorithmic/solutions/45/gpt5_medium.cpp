#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char getch() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<class T>
    bool readInt(T &out) {
        char c; T sign = 1; T val = 0;
        c = getch();
        if (!c) return false;
        while (c!='-' && (c<'0'||c>'9')) {
            c = getch();
            if (!c) return false;
        }
        if (c=='-') { sign = -1; c = getch(); }
        for (; c>='0' && c<='9'; c = getch()) val = val*10 + (c - '0');
        out = val * sign;
        return true;
    }
    bool readDouble(double &out) {
        char c = getch();
        if (!c) return false;
        while (isspace((unsigned char)c)) { c = getch(); if (!c) return false; }
        char s[64]; int p = 0;
        while (c && !isspace((unsigned char)c) && p < 63) { s[p++] = c; c = getch(); }
        s[p] = 0;
        out = strtod(s, nullptr);
        return true;
    }
} in;

struct FastOutput {
    static const int BUFSIZE = 1 << 20;
    int idx;
    char buf[BUFSIZE];
    FastOutput(): idx(0) {}
    ~FastOutput() { flush(); }
    inline void pushChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }
    inline void writeInt(int x) {
        if (x == 0) { pushChar('0'); return; }
        if (x < 0) { pushChar('-'); x = -x; }
        char s[16]; int n = 0;
        while (x) { s[n++] = char('0' + x % 10); x /= 10; }
        while (n--) pushChar(s[n]);
    }
    inline void writeSpace() { pushChar(' '); }
    inline void writeNewline() { pushChar('\n'); }
    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }
} out;

static uint64_t rng_state = 0x9e3779b97f4a7c15ULL;
static inline uint64_t rng64() {
    uint64_t z = (rng_state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}
static inline uint32_t rng32() { return (uint32_t)rng64(); }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, k;
    double eps;
    if (!in.readInt(n)) return 0;
    in.readInt(m);
    in.readInt(k);
    in.readDouble(eps);

    vector<int> deg(n, 0);
    vector<int> U; U.reserve(m);
    vector<int> V; V.reserve(m);

    for (int i = 0; i < m; ++i) {
        int u, v;
        if (!in.readInt(u)) u = 0;
        in.readInt(v);
        if (u == v) continue;
        --u; --v;
        if ((unsigned)u >= (unsigned)n || (unsigned)v >= (unsigned)n) continue;
        U.push_back(u);
        V.push_back(v);
        deg[u]++; deg[v]++;
    }
    int E = (int)U.size();
    vector<int> off(n+1, 0);
    for (int i = 0; i < n; ++i) off[i+1] = off[i] + deg[i];
    vector<int> adj(2*E);
    vector<int> cur = off;
    for (int i = 0; i < E; ++i) {
        int a = U[i], b = V[i];
        adj[cur[a]++] = b;
        adj[cur[b]++] = a;
    }
    U.clear(); U.shrink_to_fit();
    V.clear(); V.shrink_to_fit();

    // balance parameters
    int ideal = (n + k - 1) / k;
    int cap = (int)floor((1.0 + eps) * ideal + 1e-9);
    if (cap < 1) cap = 1;

    // seed selection
    vector<int> order(n);
    for (int i = 0; i < n; ++i) order[i] = i;
    // Seed rng
    rng_state ^= (uint64_t)n + ((uint64_t)m<<32) + ((uint64_t)k<<16);

    int S = n;
    if (S > 20000) S = 20000;
    if (S < k) S = min(n, max(k, 1000));
    for (int i = 0; i < S; ++i) {
        int j = i + (int)(rng64() % (uint64_t)(n - i));
        swap(order[i], order[j]);
    }
    vector<int> sample(order.begin(), order.begin() + S);
    int take = min(k, S);
    // Partial sort to get top 'take' by degree
    nth_element(sample.begin(), sample.begin()+take, sample.end(), [&](int a, int b){ return deg[a] > deg[b]; });
    sample.resize(take);

    vector<char> chosen(n, 0);
    vector<int> seeds;
    seeds.reserve(k);
    for (int x : sample) {
        if (!chosen[x]) {
            seeds.push_back(x);
            chosen[x] = 1;
            if ((int)seeds.size() == k) break;
        }
    }
    if ((int)seeds.size() < k) {
        for (int i = S; i < n && (int)seeds.size() < k; ++i) {
            int x = order[i];
            if (!chosen[x]) { seeds.push_back(x); chosen[x] = 1; }
        }
        for (int i = 0; i < S && (int)seeds.size() < k; ++i) {
            int x = order[i];
            if (!chosen[x]) { seeds.push_back(x); chosen[x] = 1; }
        }
        // If still not enough due to some edge case, fill randomly
        for (int i = 0; (int)seeds.size() < k && i < n; ++i) {
            int x = i;
            if (!chosen[x]) { seeds.push_back(x); chosen[x] = 1; }
        }
        while ((int)seeds.size() < k) {
            int x = (int)(rng64() % (uint64_t)n);
            seeds.push_back(x);
        }
    }

    vector<int> part(n, -1);
    vector<int> sizes(k, 0);

    deque<int> dq;
    for (int i = 0; i < k; ++i) {
        int s = seeds[i % seeds.size()];
        if (part[s] == -1) {
            part[s] = i;
            sizes[i]++;
            dq.push_back(s);
        } else {
            // find next unassigned
            int probe = 0;
            while (probe < n && part[order[probe]] != -1) ++probe;
            int v = (probe < n ? order[probe] : s);
            part[v] = i;
            sizes[i]++;
            dq.push_back(v);
        }
    }

    // Multi-source BFS growth with capacity
    while (!dq.empty()) {
        int u = dq.front(); dq.pop_front();
        int pid = part[u];
        if (sizes[pid] >= cap) continue;
        int l = off[u], r = off[u+1];
        for (int ei = l; ei < r; ++ei) {
            int v = adj[ei];
            if (part[v] == -1 && sizes[pid] < cap) {
                part[v] = pid;
                sizes[pid]++;
                dq.push_back(v);
            }
            if (sizes[pid] >= cap) break;
        }
    }

    // Assign remaining unassigned vertices
    vector<int> counts(k, 0), seen(k, 0);
    int tag = 1;
    // Shuffle order for fill
    for (int i = 0; i < n; ++i) {
        int j = i + (int)(rng64() % (uint64_t)(n - i));
        swap(order[i], order[j]);
    }
    for (int idx = 0; idx < n; ++idx) {
        int v = order[idx];
        if (part[v] != -1) continue;
        tag++;
        vector<int> visited;
        visited.reserve(8);
        int l = off[v], r = off[v+1];
        for (int ei = l; ei < r; ++ei) {
            int u = adj[ei];
            int pid = part[u];
            if (pid >= 0) {
                if (seen[pid] != tag) { seen[pid] = tag; counts[pid] = 1; visited.push_back(pid); }
                else counts[pid]++;
            }
        }
        int best = -1, bestCnt = -1;
        for (int pid : visited) {
            if (sizes[pid] >= cap) continue;
            int c = counts[pid];
            if (c > bestCnt || (c == bestCnt && best != -1 && sizes[pid] < sizes[best])) {
                best = pid; bestCnt = c;
            }
        }
        if (best == -1) {
            // choose smallest size part with room
            int minPart = -1;
            int minSize = INT_MAX;
            for (int pid = 0; pid < k; ++pid) {
                if (sizes[pid] < cap && sizes[pid] < minSize) {
                    minSize = sizes[pid];
                    minPart = pid;
                }
            }
            if (minPart == -1) {
                // Should not happen, but fallback: pick any
                minPart = (int)(rng64() % (uint64_t)k);
            }
            best = minPart;
        }
        part[v] = best;
        sizes[best]++;
    }

    // Constrained label propagation refinement
    size_t arcs = adj.size();
    int T = 3;
    if (arcs > 15000000u) T = 2;
    else if (arcs <= 5000000u) T = 5;
    // prepare order (already shuffled). We'll alternate direction.
    vector<int> visitedParts; visitedParts.reserve(64);
    int moves_total = 0;
    for (int it = 0; it < T; ++it) {
        int moves = 0;
        bool forward = (it % 2 == 0);
        if (!forward) {
            // reverse traversal without reversing vector
            for (int ii = n - 1; ii >= 0; --ii) {
                int v = order[ii];
                int curp = part[v];
                int l = off[v], r = off[v+1];
                ++tag;
                visitedParts.clear();
                for (int ei = l; ei < r; ++ei) {
                    int u = adj[ei];
                    int pid = part[u];
                    if (pid >= 0) {
                        if (seen[pid] != tag) { seen[pid] = tag; counts[pid] = 1; visitedParts.push_back(pid); }
                        else counts[pid]++;
                    }
                }
                int currCnt = (seen[curp] == tag ? counts[curp] : 0);
                int best = curp;
                int bestCnt = currCnt;
                for (int pid : visitedParts) {
                    if (pid == curp) continue;
                    if (sizes[pid] >= cap) continue;
                    int c = counts[pid];
                    if (c > bestCnt || (c == bestCnt && sizes[pid] < sizes[best])) {
                        best = pid; bestCnt = c;
                    }
                }
                if (best != curp && bestCnt > currCnt) {
                    sizes[curp]--; sizes[best]++; part[v] = best; moves++;
                }
            }
        } else {
            for (int ii = 0; ii < n; ++ii) {
                int v = order[ii];
                int curp = part[v];
                int l = off[v], r = off[v+1];
                ++tag;
                visitedParts.clear();
                for (int ei = l; ei < r; ++ei) {
                    int u = adj[ei];
                    int pid = part[u];
                    if (pid >= 0) {
                        if (seen[pid] != tag) { seen[pid] = tag; counts[pid] = 1; visitedParts.push_back(pid); }
                        else counts[pid]++;
                    }
                }
                int currCnt = (seen[curp] == tag ? counts[curp] : 0);
                int best = curp;
                int bestCnt = currCnt;
                for (int pid : visitedParts) {
                    if (pid == curp) continue;
                    if (sizes[pid] >= cap) continue;
                    int c = counts[pid];
                    if (c > bestCnt || (c == bestCnt && sizes[pid] < sizes[best])) {
                        best = pid; bestCnt = c;
                    }
                }
                if (best != curp && bestCnt > currCnt) {
                    sizes[curp]--; sizes[best]++; part[v] = best; moves++;
                }
            }
        }
        moves_total += moves;
        if (moves == 0) break;
    }

    // Final output
    for (int i = 0; i < n; ++i) {
        out.writeInt(part[i] + 1);
        if (i + 1 < n) out.writeSpace();
    }
    out.writeNewline();
    out.flush();
    return 0;
}