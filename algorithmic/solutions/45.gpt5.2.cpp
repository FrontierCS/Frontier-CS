#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    unsigned char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline unsigned char readByte() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    inline bool skipBlanks() {
        unsigned char c;
        do {
            c = readByte();
            if (!c) return false;
        } while (c <= ' ');
        idx--;
        return true;
    }

    template <class T>
    bool readInt(T &out) {
        if (!skipBlanks()) return false;
        unsigned char c = readByte();
        bool neg = false;
        if (c == '-') { neg = true; c = readByte(); }
        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readByte();
        }
        out = neg ? -val : val;
        return true;
    }

    bool readDouble(double &out) {
        if (!skipBlanks()) return false;
        unsigned char c = readByte();
        bool neg = false;
        if (c == '-') { neg = true; c = readByte(); }

        long long intPart = 0;
        while (c > ' ' && c != '.' && c != 'e' && c != 'E') {
            intPart = intPart * 10 + (c - '0');
            c = readByte();
        }

        double val = (double)intPart;

        if (c == '.') {
            double place = 0.1;
            c = readByte();
            while (c > ' ' && c != 'e' && c != 'E') {
                val += (c - '0') * place;
                place *= 0.1;
                c = readByte();
            }
        }

        if (c == 'e' || c == 'E') {
            c = readByte();
            bool eneg = false;
            if (c == '-') { eneg = true; c = readByte(); }
            else if (c == '+') { c = readByte(); }
            int expv = 0;
            while (c > ' ') {
                expv = expv * 10 + (c - '0');
                c = readByte();
            }
            val *= pow(10.0, eneg ? -expv : expv);
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

    inline void writeInt(int x, char endc) {
        if (x == 0) {
            pushChar('0');
            pushChar(endc);
            return;
        }
        if (x < 0) {
            pushChar('-');
            x = -x;
        }
        char s[24];
        int n = 0;
        while (x) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        while (n--) pushChar(s[n]);
        pushChar(endc);
    }
};

static inline uint64_t splitmix64(uint64_t &x) {
    uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;

    int n, k;
    long long m;
    double eps;

    if (!fs.readInt(n)) return 0;
    fs.readInt(m);
    fs.readInt(k);
    fs.readDouble(eps);

    long long ideal = (n + (long long)k - 1) / (long long)k; // ceil(n/k)
    long long cap = (long long)floor((1.0 + eps) * (double)ideal + 1e-12);
    cap = max(cap, ideal);
    if (cap < 1) cap = 1;

    if (k <= 1) {
        FastOutput fo;
        for (int i = 1; i <= n; i++) fo.writeInt(1, (i == n) ? '\n' : ' ');
        return 0;
    }

    vector<int> head(n + 1, -1);
    size_t alloc = (size_t)max(0LL, m) * 2ull;
    vector<int> to;
    vector<int> nxt;
    try {
        to.resize(alloc);
        nxt.resize(alloc);
    } catch (...) {
        // Fallback: if allocation fails, output trivial balanced by round-robin without using edges.
        long long maxsz = cap;
        vector<int> sz(k + 1, 0);
        FastOutput fo;
        int curp = 1;
        for (int i = 1; i <= n; i++) {
            while (curp <= k && sz[curp] >= maxsz) curp++;
            if (curp > k) curp = 1;
            sz[curp]++;
            fo.writeInt(curp, (i == n) ? '\n' : ' ');
        }
        return 0;
    }

    size_t idx = 0;
    auto addEdge = [&](int u, int v) {
        to[idx] = v;
        nxt[idx] = head[u];
        head[u] = (int)idx;
        ++idx;
    };

    for (long long i = 0; i < m; i++) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        if (u == v) continue;
        if (idx + 2 <= alloc) {
            addEdge(u, v);
            addEdge(v, u);
        }
    }

    vector<int> part(n + 1, 0);
    vector<int> sz(k + 1, 0);

    vector<int> cnt(k + 1, 0), seen(k + 1, 0);
    int stamp = 1;
    vector<int> touched;
    touched.reserve(64);

    using PII = pair<int,int>;
    priority_queue<PII, vector<PII>, greater<PII>> pq;
    for (int p = 1; p <= k; p++) pq.push({0, p});

    auto getMinPartNotFull = [&]() -> int {
        while (!pq.empty()) {
            auto [s, p] = pq.top();
            if (s != sz[p]) { pq.pop(); continue; }
            if (sz[p] >= cap) { pq.pop(); continue; }
            return p;
        }
        // should not happen; fallback scan
        int best = 1;
        for (int p = 2; p <= k; p++) if (sz[p] < sz[best]) best = p;
        return best;
    };

    // Initial streaming LDG-style assignment
    for (int v = 1; v <= n; v++) {
        ++stamp;
        touched.clear();

        for (int e = head[v]; e != -1; e = nxt[e]) {
            int u = to[e];
            int pu = part[u];
            if (pu == 0) continue;
            if (seen[pu] != stamp) {
                seen[pu] = stamp;
                cnt[pu] = 0;
                touched.push_back(pu);
            }
            cnt[pu]++;
        }

        int bestPart = -1;
        double bestScore = -1e100;

        for (int p : touched) {
            if (sz[p] >= cap) continue;
            double bal = 1.0 - (double)sz[p] / (double)cap;
            if (bal < 0) bal = 0;
            double score = (double)cnt[p] * bal;
            if (score > bestScore + 1e-12 || (fabs(score - bestScore) <= 1e-12 && (bestPart == -1 || sz[p] < sz[bestPart]))) {
                bestScore = score;
                bestPart = p;
            }
        }

        if (bestPart == -1) bestPart = getMinPartNotFull();

        part[v] = bestPart;
        sz[bestPart]++;
        pq.push({sz[bestPart], bestPart});
    }

    // Refinement passes: balanced label propagation
    uint64_t rng = 0x123456789abcdefULL ^ (uint64_t)n ^ ((uint64_t)m << 1) ^ (uint64_t)k;

    auto refinePass = [&](int rounds) {
        for (int pass = 0; pass < rounds; pass++) {
            if (n <= 1) return;

            size_t start = (size_t)(splitmix64(rng) % (uint64_t)n);
            size_t step = (size_t)((splitmix64(rng) % (uint64_t)n) | 1ULL);
            if (step == 0) step = 1;
            while (std::gcd(step, (size_t)n) != 1) {
                step += 2;
                if (step >= (size_t)n) step = (step % (size_t)n) | 1ULL;
                if (step == 0) step = 1;
            }

            for (int it = 0; it < n; it++) {
                int v = (int)((start + (size_t)it * step) % (size_t)n) + 1;
                int cur = part[v];

                ++stamp;
                touched.clear();

                for (int e = head[v]; e != -1; e = nxt[e]) {
                    int u = to[e];
                    int pu = part[u];
                    if (seen[pu] != stamp) {
                        seen[pu] = stamp;
                        cnt[pu] = 0;
                        touched.push_back(pu);
                    }
                    cnt[pu]++;
                }
                if (seen[cur] != stamp) {
                    seen[cur] = stamp;
                    cnt[cur] = 0;
                    touched.push_back(cur);
                }

                int curCnt = cnt[cur];
                double curScore = (double)curCnt * (1.0 - (double)sz[cur] / (double)cap);

                int best = cur;
                int bestCnt = curCnt;
                double bestScore = curScore;

                for (int p : touched) {
                    if (p == cur) continue;
                    if (sz[p] >= cap) continue;
                    int c = cnt[p];

                    // Prefer improving (or at least not worsening) local edge agreement
                    if (c < bestCnt) continue;

                    double bal = 1.0 - (double)sz[p] / (double)cap;
                    if (bal < 0) bal = 0;
                    double score = (double)c * bal;

                    if (c > bestCnt ||
                        score > bestScore + 1e-12 ||
                        (fabs(score - bestScore) <= 1e-12 && sz[p] < sz[best])) {
                        best = p;
                        bestCnt = c;
                        bestScore = score;
                    }
                }

                if (best != cur) {
                    // Require strict improvement in cnt OR meaningful balance improvement with equal cnt
                    if (bestCnt > curCnt || (bestCnt == curCnt && sz[best] + 1 < sz[cur])) {
                        if (sz[best] < cap) {
                            sz[cur]--;
                            sz[best]++;
                            part[v] = best;
                            pq.push({sz[cur], cur});
                            pq.push({sz[best], best});
                        }
                    }
                }
            }
        }
    };

    refinePass(2);

    FastOutput fo;
    for (int i = 1; i <= n; i++) {
        fo.writeInt(part[i], (i == n) ? '\n' : ' ');
    }
    fo.flush();
    return 0;
}