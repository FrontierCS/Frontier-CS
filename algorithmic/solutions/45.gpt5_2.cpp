#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const size_t BUFSIZE = 1 << 20;
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
    inline void skipBlanks() {
        char c;
        while ((c = getch())) {
            if (!isspace((unsigned char)c)) { idx--; break; }
        }
    }
    bool readInt(int &out) {
        skipBlanks();
        char c = getch();
        if (!c) return false;
        int sgn = 1;
        if (c == '-') { sgn = -1; c = getch(); }
        long long x = 0;
        while (c >= '0' && c <= '9') {
            x = x * 10 + (c - '0');
            c = getch();
        }
        out = (int)(x * sgn);
        return true;
    }
    bool readDouble(double &out) {
        skipBlanks();
        char c = getch();
        if (!c) return false;
        int sgn = 1;
        if (c == '-') { sgn = -1; c = getch(); }
        long long intPart = 0;
        while (c >= '0' && c <= '9') {
            intPart = intPart * 10 + (c - '0');
            c = getch();
        }
        double res = (double)intPart;
        if (c == '.') {
            double place = 0.1;
            c = getch();
            while (c >= '0' && c <= '9') {
                res += (c - '0') * place;
                place *= 0.1;
                c = getch();
            }
        }
        out = res * sgn;
        return true;
    }
} In;

struct FastOutput {
    static const size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx;
    FastOutput(): idx(0) {}
    ~FastOutput() { flush(); }
    inline void pushChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }
    inline void writeInt(int x) {
        if (x == 0) { pushChar('0'); return; }
        if (x < 0) { pushChar('-'); x = -x; }
        char s[16];
        int n = 0;
        while (x) { s[n++] = char('0' + (x % 10)); x /= 10; }
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
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, k;
    double eps;
    if (!In.readInt(n)) return 0;
    In.readInt(m);
    In.readInt(k);
    In.readDouble(eps);

    // Graph adjacency using forward-star (head/to/next)
    vector<int> head(n + 1, 0);
    vector<int> deg(n + 1, 0);
    // Allocate arrays for up to 2*m edges (skip self loops, so capacity sufficient)
    vector<int> to(2 * (size_t)m + 5);
    vector<int> nxt(2 * (size_t)m + 5);
    int ecnt = 0;

    auto addEdge = [&](int u, int v) {
        to[++ecnt] = v; nxt[ecnt] = head[u]; head[u] = ecnt; deg[u]++;
        to[++ecnt] = u; nxt[ecnt] = head[v]; head[v] = ecnt; deg[v]++;
    };

    for (int i = 0; i < m; ++i) {
        int u, v;
        In.readInt(u);
        In.readInt(v);
        if (u < 1 || u > n || v < 1 || v > n) continue;
        if (u == v) continue; // skip self-loops
        addEdge(u, v);
    }

    // Compute balance parameters
    long long ideal = (n + k - 1) / k;
    long double ld = (long double)ideal * (1.0L + (long double)eps);
    long long limit = (long long)floor(ld);
    if (limit < 1) limit = 1; // safety net

    // Choose up to k seeds (prefer high degree nodes)
    int seedsWanted = min(k, n);
    vector<int> seeds; seeds.reserve(seedsWanted);
    if (seedsWanted > 0) {
        using PII = pair<int,int>;
        priority_queue<PII, vector<PII>, greater<PII>> pq;
        for (int u = 1; u <= n; ++u) {
            if ((int)pq.size() < seedsWanted) pq.emplace(deg[u], u);
            else if (deg[u] > pq.top().first) {
                pq.pop();
                pq.emplace(deg[u], u);
            }
        }
        while (!pq.empty()) { seeds.push_back(pq.top().second); pq.pop(); }
        // sort seeds for determinism
        sort(seeds.begin(), seeds.end());
        if ((int)seeds.size() > seedsWanted) seeds.resize(seedsWanted);
    }

    // Initialize partition arrays
    vector<int> part(n + 1, 0);
    vector<int> sizes(k + 1, 0);
    vector<char> isSeed(n + 1, 0);
    for (int i = 0; i < (int)seeds.size(); ++i) {
        int s = seeds[i];
        int pid = i + 1; // map seed i -> part i+1
        isSeed[s] = 1;
        part[s] = pid;
        sizes[pid] = 1;
    }

    // Build BFS visit order (multi-source from seeds); nodes excluding seeds
    vector<char> visited(n + 1, 0);
    vector<int> order; order.reserve(n);
    vector<int> q; q.reserve(n);
    for (int i = 0; i < (int)seeds.size(); ++i) {
        int s = seeds[i];
        visited[s] = 1;
        q.push_back(s);
    }
    size_t qi = 0;
    while (qi < q.size()) {
        int v = q[qi++];
        for (int e = head[v]; e; e = nxt[e]) {
            int u = to[e];
            if (!visited[u]) {
                visited[u] = 1;
                q.push_back(u);
                if (!isSeed[u]) order.push_back(u);
            }
        }
    }
    // Add any unvisited nodes (disconnected components), then BFS them
    for (int u = 1; u <= n; ++u) {
        if (!visited[u]) {
            visited[u] = 1;
            q.push_back(u);
            if (!isSeed[u]) order.push_back(u);
        }
    }
    while (qi < q.size()) {
        int v = q[qi++];
        for (int e = head[v]; e; e = nxt[e]) {
            int u = to[e];
            if (!visited[u]) {
                visited[u] = 1;
                q.push_back(u);
                if (!isSeed[u]) order.push_back(u);
            }
        }
    }

    // Targets for round-robin fallback to keep near-perfect balance
    vector<int> target(k + 1, 0);
    int base = n / k, rem = n % k;
    for (int i = 1; i <= k; ++i) target[i] = base + (i <= rem ? 1 : 0);

    // Ensure seed assignments respect target and limit; if k > n, some targets=0 parts remain empty
    // Now assign remaining nodes in BFS order using neighbor majority with capacity constraints
    vector<int> cnt(k + 1, 0);
    vector<int> touched; touched.reserve(64);
    int rr_ptr = 1; // round-robin pointer for fallback

    auto pickFallbackPart = [&]() -> int {
        // Try fill up to target in round-robin
        for (int t = 0; t < k; ++t) {
            int p = rr_ptr;
            rr_ptr++; if (rr_ptr > k) rr_ptr = 1;
            if (sizes[p] < target[p]) return p;
        }
        // Otherwise, pick any part with remaining capacity (scan once)
        int bestP = -1;
        int minSize = INT_MAX;
        for (int p = 1; p <= k; ++p) {
            if (sizes[p] < limit) {
                if (sizes[p] < minSize) { minSize = sizes[p]; bestP = p; }
            }
        }
        if (bestP == -1) {
            // Should not happen as total capacity >= n, but fallback safely: pick smallest size part
            for (int p = 1; p <= k; ++p) {
                if (sizes[p] < minSize) { minSize = sizes[p]; bestP = p; }
            }
        }
        return bestP < 1 ? 1 : bestP;
    };

    // Assign non-seed nodes
    for (int idx = 0; idx < (int)order.size(); ++idx) {
        int v = order[idx];
        // Count neighbor parts already assigned
        for (int e = head[v]; e; e = nxt[e]) {
            int u = to[e];
            int p = part[u];
            if (p == 0) continue;
            if (cnt[p] == 0) touched.push_back(p);
            cnt[p]++;
        }
        int bestP = 0, bestC = -1;
        // Choose best part among neighbors respecting capacity
        for (int p : touched) {
            if (sizes[p] >= limit) continue;
            int c = cnt[p];
            if (c > bestC) { bestC = c; bestP = p; }
            else if (c == bestC) {
                // tie-breaker: prefer smaller current size
                if (bestP == 0 || sizes[p] < sizes[bestP]) bestP = p;
            }
        }
        if (bestP == 0) {
            // no neighbor assigned or all neighbor parts full: fallback
            bestP = pickFallbackPart();
        }
        part[v] = bestP;
        sizes[bestP]++;

        // reset counts
        for (int p : touched) cnt[p] = 0;
        touched.clear();
    }

    // Optional refinement: single pass label propagation for local improvement
    // Move vertex to neighboring majority part if capacity allows and improves local agreement
    {
        for (int v = 1; v <= n; ++v) {
            // Count neighbor parts
            int curP = part[v];
            if (head[v] == 0) continue; // isolated
            for (int e = head[v]; e; e = nxt[e]) {
                int u = to[e];
                int p = part[u];
                if (p == 0) continue;
                if (cnt[p] == 0) touched.push_back(p);
                cnt[p]++;
            }
            int curCnt = cnt[curP];
            int bestP2 = curP, bestC2 = curCnt;
            for (int p : touched) {
                if (p == curP) continue;
                if (sizes[p] >= limit) continue;
                int c = cnt[p];
                if (c > bestC2) { bestC2 = c; bestP2 = p; }
                else if (c == bestC2 && p != curP) {
                    // slight bias towards smaller size to also help balance and CV
                    if (sizes[p] + 1 < sizes[bestP2]) bestP2 = p;
                }
            }
            if (bestP2 != curP && bestC2 > curCnt) {
                part[v] = bestP2;
                sizes[bestP2]++;
                sizes[curP]--;
            }
            for (int p : touched) cnt[p] = 0;
            touched.clear();
        }
    }

    // Output
    FastOutput Out;
    for (int i = 1; i <= n; ++i) {
        int p = part[i];
        if (p < 1) p = pickFallbackPart(), sizes[p]++, part[i] = p; // safety
        Out.writeInt(p);
        if (i < n) Out.writeSpace();
    }
    Out.writeNewline();
    Out.flush();
    return 0;
}