#include <bits/stdc++.h>
using namespace std;

class FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    unsigned char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline void refill() {
        size = fread(buf, 1, BUFSIZE, stdin);
        idx = 0;
        if (size == 0) buf[0] = 0;
    }

public:
    inline unsigned char getChar() {
        if (idx >= size) refill();
        return buf[idx++];
    }

    inline bool skipBlanks() {
        unsigned char c;
        do {
            c = getChar();
            if (!c) return false;
        } while (c <= ' ');
        idx--;
        return true;
    }

    template <class T>
    bool readInt(T &out) {
        if (!skipBlanks()) return false;
        unsigned char c = getChar();
        bool neg = false;
        if constexpr (std::is_signed<T>::value) {
            if (c == '-') { neg = true; c = getChar(); }
        }
        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = getChar();
        }
        out = neg ? -val : val;
        return true;
    }

    bool readToken(char *s, int maxLen) {
        if (!skipBlanks()) return false;
        unsigned char c = getChar();
        int p = 0;
        while (c > ' ' && p + 1 < maxLen) {
            s[p++] = (char)c;
            c = getChar();
        }
        s[p] = 0;
        while (c > ' ') c = getChar(); // consume rest if too long
        return true;
    }
};

class FastOutput {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0;

public:
    ~FastOutput() { flush(); }

    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }

    inline void putChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }

    inline void writeUInt(uint32_t x) {
        char s[16];
        int n = 0;
        do { s[n++] = char('0' + (x % 10)); x /= 10; } while (x);
        for (int i = n - 1; i >= 0; --i) putChar(s[i]);
    }

    inline void writeIntSp(uint32_t x, bool last) {
        writeUInt(x);
        putChar(last ? '\n' : ' ');
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;

    uint32_t n = 0, k = 0;
    long long m_ll = 0;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m_ll);
    fs.readInt(k);
    char epsTok[64];
    fs.readToken(epsTok, 64);
    long double eps = strtold(epsTok, nullptr);

    vector<uint32_t> deg(n + 1, 0);
    vector<uint32_t> U;
    vector<uint32_t> V;
    U.reserve((size_t)max(0LL, m_ll));
    V.reserve((size_t)max(0LL, m_ll));

    for (long long i = 0; i < m_ll; ++i) {
        uint32_t u, v;
        fs.readInt(u);
        fs.readInt(v);
        if (u == v) continue;
        U.push_back(u);
        V.push_back(v);
        if (u <= n) deg[u]++;
        if (v <= n) deg[v]++;
    }

    size_t E = U.size();
    vector<uint32_t> off(n + 2, 0);
    uint64_t sum = 0;
    off[1] = 0;
    for (uint32_t i = 1; i <= n; ++i) {
        sum += deg[i];
        off[i + 1] = (uint32_t)sum;
    }

    vector<uint32_t> cur(off.begin(), off.end());
    vector<uint32_t> adj;
    adj.resize(sum);

    for (size_t i = 0; i < E; ++i) {
        uint32_t u = U[i], v = V[i];
        adj[cur[u]++] = v;
        adj[cur[v]++] = u;
    }
    vector<uint32_t>().swap(U);
    vector<uint32_t>().swap(V);
    vector<uint32_t>().swap(deg);

    uint32_t ideal = (n + k - 1) / k;
    long double cap_ld = floorl((1.0L + eps) * (long double)ideal + 1e-18L);
    uint32_t cap = (uint32_t)cap_ld;
    if (cap < 1) cap = 1;

    vector<uint32_t> part(n + 1, 0); // 0 = unassigned, else 1..k
    vector<uint32_t> psz(k, 0);

    // Min-heap of (size, partId)
    using PII = pair<uint32_t, uint32_t>;
    priority_queue<PII, vector<PII>, greater<PII>> pq;
    for (uint32_t p = 1; p <= k; ++p) pq.push({0, p});

    vector<int> cnt(k + 1, 0);
    vector<int> stamp(k + 1, 0);
    int curStamp = 1;

    auto ensureStamp = [&]() {
        if (curStamp == INT_MAX) {
            fill(stamp.begin(), stamp.end(), 0);
            curStamp = 1;
        }
        ++curStamp;
    };

    vector<uint32_t> touched;
    touched.reserve(64);

    auto getMinPartWithRoom = [&]() -> uint32_t {
        while (!pq.empty()) {
            auto [sz, p] = pq.top();
            if (sz != psz[p]) { pq.pop(); continue; }
            if (sz >= cap) { pq.pop(); continue; }
            return p;
        }
        // Fallback (should not happen)
        for (uint32_t p = 1; p <= k; ++p) if (psz[p] < cap) return p;
        return 1;
    };

    // Initial LDG-style streaming assignment
    for (uint32_t v = 1; v <= n; ++v) {
        ensureStamp();
        touched.clear();

        uint32_t begin = off[v], end = off[v + 1];
        for (uint32_t ei = begin; ei < end; ++ei) {
            uint32_t u = adj[ei];
            uint32_t pu = part[u];
            if (!pu) continue;
            if (stamp[pu] != curStamp) {
                stamp[pu] = curStamp;
                cnt[pu] = 1;
                touched.push_back(pu);
            } else {
                cnt[pu]++;
            }
        }

        uint32_t bestP = 0;
        long long bestScore = -1;

        for (uint32_t p : touched) {
            if (psz[p] >= cap) continue;
            long long score = 1LL * cnt[p] * (long long)(cap - psz[p]);
            if (score > bestScore || (score == bestScore && psz[p] < psz[bestP])) {
                bestScore = score;
                bestP = p;
            }
        }

        if (bestP == 0) bestP = getMinPartWithRoom();

        part[v] = bestP;
        psz[bestP]++;
        pq.push({psz[bestP], bestP});
    }

    // Balanced label propagation refinement
    int iters = 1;
    if (E <= 15000000ULL) iters = 2;

    for (int it = 0; it < iters; ++it) {
        bool rev = (it & 1);
        if (!rev) {
            for (uint32_t v = 1; v <= n; ++v) {
                uint32_t curP = part[v];
                ensureStamp();
                touched.clear();

                uint32_t begin = off[v], end = off[v + 1];
                for (uint32_t ei = begin; ei < end; ++ei) {
                    uint32_t u = adj[ei];
                    uint32_t pu = part[u];
                    if (stamp[pu] != curStamp) {
                        stamp[pu] = curStamp;
                        cnt[pu] = 1;
                        touched.push_back(pu);
                    } else cnt[pu]++;
                }

                int ccur = (stamp[curP] == curStamp) ? cnt[curP] : 0;
                long long curScore = 1LL * ccur * (long long)(cap - psz[curP]);

                uint32_t bestP = curP;
                long long bestScore = curScore;

                for (uint32_t p : touched) {
                    if (p == curP) continue;
                    if (psz[p] >= cap) continue;
                    long long score = 1LL * cnt[p] * (long long)(cap - psz[p]);
                    if (score > bestScore || (score == bestScore && psz[p] < psz[bestP])) {
                        bestScore = score;
                        bestP = p;
                    }
                }

                if (bestP != curP) {
                    if (bestScore > curScore || (bestScore == curScore && psz[bestP] + 1 < psz[curP])) {
                        // move
                        part[v] = bestP;
                        psz[curP]--;
                        psz[bestP]++;
                    }
                }
            }
        } else {
            for (uint32_t v = n; v >= 1; --v) {
                uint32_t curP = part[v];
                ensureStamp();
                touched.clear();

                uint32_t begin = off[v], end = off[v + 1];
                for (uint32_t ei = begin; ei < end; ++ei) {
                    uint32_t u = adj[ei];
                    uint32_t pu = part[u];
                    if (stamp[pu] != curStamp) {
                        stamp[pu] = curStamp;
                        cnt[pu] = 1;
                        touched.push_back(pu);
                    } else cnt[pu]++;
                }

                int ccur = (stamp[curP] == curStamp) ? cnt[curP] : 0;
                long long curScore = 1LL * ccur * (long long)(cap - psz[curP]);

                uint32_t bestP = curP;
                long long bestScore = curScore;

                for (uint32_t p : touched) {
                    if (p == curP) continue;
                    if (psz[p] >= cap) continue;
                    long long score = 1LL * cnt[p] * (long long)(cap - psz[p]);
                    if (score > bestScore || (score == bestScore && psz[p] < psz[bestP])) {
                        bestScore = score;
                        bestP = p;
                    }
                }

                if (bestP != curP) {
                    if (bestScore > curScore || (bestScore == curScore && psz[bestP] + 1 < psz[curP])) {
                        part[v] = bestP;
                        psz[curP]--;
                        psz[bestP]++;
                    }
                }

                if (v == 1) break;
            }
        }
    }

    // Output
    FastOutput fo;
    for (uint32_t i = 1; i <= n; ++i) {
        uint32_t p = part[i];
        if (p < 1) p = 1;
        if (p > k) p = k;
        fo.writeIntSp(p, i == n);
    }
    fo.flush();
    return 0;
}