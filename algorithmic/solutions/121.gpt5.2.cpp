#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct U64Hash {
    size_t operator()(uint64_t x) const noexcept {
        return (size_t)splitmix64(x);
    }
};

struct Mask {
    array<uint64_t, 8> w{};
};

static int gBlocks = 0;

static inline bool operator==(const Mask& a, const Mask& b) {
    for (int i = 0; i < gBlocks; i++) if (a.w[i] != b.w[i]) return false;
    return true;
}

struct MaskHash {
    size_t operator()(const Mask& m) const noexcept {
        uint64_t h = 0x1234567890abcdefULL;
        for (int i = 0; i < gBlocks; i++) {
            h = splitmix64(h ^ splitmix64(m.w[i] + 0x9e3779b97f4a7c15ULL * (uint64_t)(i + 1)));
        }
        return (size_t)h;
    }
};

static inline bool isEmpty(const Mask& m) {
    for (int i = 0; i < gBlocks; i++) if (m.w[i]) return false;
    return true;
}

static inline Mask andMask(const Mask& a, const Mask& b) {
    Mask r;
    for (int i = 0; i < gBlocks; i++) r.w[i] = a.w[i] & b.w[i];
    return r;
}

static inline uint8_t charToMask(char c) {
    switch (c) {
        case 'A': return 1;
        case 'C': return 2;
        case 'G': return 4;
        case 'T': return 8;
        case '?': return 15;
    }
    return 0;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m0;
    cin >> n >> m0;
    vector<string> ss(m0);
    for (int i = 0; i < m0; i++) cin >> ss[i];

    sort(ss.begin(), ss.end());
    ss.erase(unique(ss.begin(), ss.end()), ss.end());
    int m = (int)ss.size();

    vector<uint8_t> allow((size_t)m * (size_t)n);
    vector<int> qcnt(m, 0);
    for (int i = 0; i < m; i++) {
        int qc = 0;
        for (int j = 0; j < n; j++) {
            char c = ss[i][j];
            if (c == '?') qc++;
            allow[(size_t)i * n + j] = charToMask(c);
        }
        qcnt[i] = qc;
    }

    // Remove patterns subsumed by more general ones (with more '?') if m not too large.
    if (m <= 2000) {
        vector<int> idx(m);
        iota(idx.begin(), idx.end(), 0);
        sort(idx.begin(), idx.end(), [&](int a, int b) {
            return qcnt[a] > qcnt[b];
        });
        vector<char> removed(m, 0);
        for (int ii = 0; ii < m; ii++) {
            int i = idx[ii];
            if (removed[i]) continue;

            // If this pattern is all '?', union prob is 1.
            if (qcnt[i] == n) {
                cout << setprecision(25) << (long double)1.0L << "\n";
                return 0;
            }

            for (int jj = ii + 1; jj < m; jj++) {
                int j = idx[jj];
                if (removed[j]) continue;
                // i subsumes j iff for all positions allow_j ⊆ allow_i
                bool sub = true;
                const uint8_t* pi = &allow[(size_t)i * n];
                const uint8_t* pj = &allow[(size_t)j * n];
                for (int p = 0; p < n; p++) {
                    uint8_t a = pi[p], b = pj[p];
                    if ((uint8_t)(b & (uint8_t)(~a)) != 0) { sub = false; break; }
                }
                if (sub) removed[j] = 1;
            }
        }
        vector<string> ss2;
        vector<int> q2;
        ss2.reserve(m);
        q2.reserve(m);
        for (int i = 0; i < m; i++) if (!removed[i]) {
            ss2.push_back(ss[i]);
            q2.push_back(qcnt[i]);
        }
        ss.swap(ss2);
        m = (int)ss.size();

        allow.assign((size_t)m * (size_t)n, 0);
        qcnt.assign(m, 0);
        for (int i = 0; i < m; i++) {
            int qc = 0;
            for (int j = 0; j < n; j++) {
                char c = ss[i][j];
                if (c == '?') qc++;
                allow[(size_t)i * n + j] = charToMask(c);
            }
            qcnt[i] = qc;
        }
    } else {
        // Quick all-'?' check
        for (int i = 0; i < m; i++) {
            if (qcnt[i] == n) {
                cout << setprecision(25) << (long double)1.0L << "\n";
                return 0;
            }
        }
    }

    if (m == 0) {
        cout << setprecision(25) << (long double)0.0L << "\n";
        return 0;
    }

    // Decide method
    bool useIE = false;
    if (m <= 25) {
        uint64_t states = 1ULL << m;
        __int128 work = (__int128)n * (__int128)states;
        // ~150M subset-position updates
        if (work <= (__int128)150000000) useIE = true;
    }

    long double ans = 0.0L;

    if (useIE) {
        uint32_t M = 1u << m;
        vector<long double> prob(M, 1.0L);
        vector<uint8_t> val(M);
        int pc[16];
        for (int x = 0; x < 16; x++) pc[x] = __builtin_popcount((unsigned)x);

        for (int pos = 0; pos < n; pos++) {
            val[0] = 15;
            for (uint32_t mask = 1; mask < M; mask++) {
                uint32_t lsb = mask & -mask;
                int bit = __builtin_ctz(lsb);
                uint8_t prev = val[mask ^ lsb];
                uint8_t a = allow[(size_t)bit * n + pos];
                uint8_t cur = (uint8_t)(prev & a);
                val[mask] = cur;
                int cnt = pc[cur];
                if (cnt == 0) prob[mask] = 0.0L;
                else if (cnt == 1) prob[mask] *= 0.25L;
                // cnt==4 => *=1
            }
        }

        long double sum = 0.0L;
        for (uint32_t mask = 1; mask < M; mask++) {
            int k = __builtin_popcount(mask);
            if (k & 1) sum += prob[mask];
            else sum -= prob[mask];
        }
        ans = sum;
    } else if (m <= 60) {
        vector<array<uint64_t, 4>> allowMask((size_t)n);
        for (int pos = 0; pos < n; pos++) {
            allowMask[pos] = {0ULL, 0ULL, 0ULL, 0ULL};
        }
        for (int i = 0; i < m; i++) {
            uint64_t bit = 1ULL << i;
            for (int pos = 0; pos < n; pos++) {
                uint8_t a = allow[(size_t)i * n + pos];
                if (a == 15) {
                    allowMask[pos][0] |= bit;
                    allowMask[pos][1] |= bit;
                    allowMask[pos][2] |= bit;
                    allowMask[pos][3] |= bit;
                } else if (a == 1) allowMask[pos][0] |= bit;
                else if (a == 2) allowMask[pos][1] |= bit;
                else if (a == 4) allowMask[pos][2] |= bit;
                else if (a == 8) allowMask[pos][3] |= bit;
            }
        }

        uint64_t full = (m == 64) ? ~0ULL : ((1ULL << m) - 1ULL);

        unordered_map<uint64_t, long double, U64Hash> cur, nxt;
        cur.reserve(1024);
        nxt.reserve(1024);
        cur[full] = 1.0L;

        for (int pos = 0; pos < n; pos++) {
            nxt.clear();
            nxt.reserve(cur.size() * 2 + 8);
            const auto &am = allowMask[pos];
            for (const auto &kv : cur) {
                uint64_t mask = kv.first;
                long double p = kv.second * 0.25L;
                uint64_t m0 = mask & am[0];
                uint64_t m1 = mask & am[1];
                uint64_t m2 = mask & am[2];
                uint64_t m3 = mask & am[3];
                if (m0) nxt[m0] += p;
                if (m1) nxt[m1] += p;
                if (m2) nxt[m2] += p;
                if (m3) nxt[m3] += p;
            }
            cur.swap(nxt);
            if (cur.empty()) break;
        }

        long double sum = 0.0L;
        for (const auto &kv : cur) sum += kv.second;
        ans = sum;
    } else if (m <= 512) {
        gBlocks = (m + 63) / 64;

        vector<array<Mask, 4>> allowMask((size_t)n);
        for (int pos = 0; pos < n; pos++) {
            for (int l = 0; l < 4; l++) {
                allowMask[pos][l].w.fill(0ULL);
            }
        }

        for (int i = 0; i < m; i++) {
            int blk = i / 64;
            int off = i % 64;
            uint64_t bit = 1ULL << off;
            for (int pos = 0; pos < n; pos++) {
                uint8_t a = allow[(size_t)i * n + pos];
                if (a == 15) {
                    allowMask[pos][0].w[blk] |= bit;
                    allowMask[pos][1].w[blk] |= bit;
                    allowMask[pos][2].w[blk] |= bit;
                    allowMask[pos][3].w[blk] |= bit;
                } else if (a == 1) allowMask[pos][0].w[blk] |= bit;
                else if (a == 2) allowMask[pos][1].w[blk] |= bit;
                else if (a == 4) allowMask[pos][2].w[blk] |= bit;
                else if (a == 8) allowMask[pos][3].w[blk] |= bit;
            }
        }

        Mask full;
        full.w.fill(0ULL);
        for (int b = 0; b < gBlocks; b++) full.w[b] = ~0ULL;
        int rem = m % 64;
        if (rem != 0) full.w[gBlocks - 1] = (1ULL << rem) - 1ULL;

        unordered_map<Mask, long double, MaskHash> cur, nxt;
        cur.reserve(1024);
        nxt.reserve(1024);
        cur[full] = 1.0L;

        for (int pos = 0; pos < n; pos++) {
            nxt.clear();
            nxt.reserve(cur.size() * 2 + 8);
            for (const auto &kv : cur) {
                const Mask &mask = kv.first;
                long double p = kv.second * 0.25L;
                for (int l = 0; l < 4; l++) {
                    Mask nm = andMask(mask, allowMask[pos][l]);
                    if (!isEmpty(nm)) nxt[nm] += p;
                }
            }
            cur.swap(nxt);
            if (cur.empty()) break;
        }

        long double sum = 0.0L;
        for (const auto &kv : cur) sum += kv.second;
        ans = sum;
    } else {
        // Out of supported range for this implementation.
        ans = 0.0L;
    }

    if (ans < 0) ans = 0;
    if (ans > 1) ans = 1;

    cout.setf(std::ios::fmtflags(0), std::ios::floatfield);
    cout << setprecision(25) << ans << "\n";
    return 0;
}