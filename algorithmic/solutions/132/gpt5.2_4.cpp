#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static inline int gc() { return getchar_unlocked(); }
    bool readInt(int &out) {
        int c = gc();
        while (c != EOF && c <= ' ') c = gc();
        if (c == EOF) return false;
        int sgn = 1;
        if (c == '-') { sgn = -1; c = gc(); }
        long long x = 0;
        while (c > ' ') { x = x * 10 + (c - '0'); c = gc(); }
        out = (int)(x * sgn);
        return true;
    }
};

static inline uint64_t splitmix64(uint64_t &x) {
    x += 0x9e3779b97f4a7c15ULL;
    uint64_t z = x;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

static inline void appendInt(string &s, int x) {
    char buf[16];
    int n = 0;
    if (x == 0) buf[n++] = '0';
    else {
        int v = x;
        char tmp[16];
        while (v > 0) { tmp[n++] = char('0' + (v % 10)); v /= 10; }
        for (int i = 0; i < n; i++) buf[i] = tmp[n - 1 - i];
    }
    s.append(buf, buf + n);
}

struct Bits {
    uint64_t lo, hi;
};

struct Entry {
    uint64_t lo, hi;
    uint16_t a, b; // 1-based positions
};

static inline bool entryLess(const Entry &x, const Entry &y) {
    if (x.hi != y.hi) return x.hi < y.hi;
    return x.lo < y.lo;
}

static inline bool bitAt(const Bits &w, int t) {
    if (t < 64) return (w.lo >> t) & 1ULL;
    return (w.hi >> (t - 64)) & 1ULL;
}

int main() {
    FastScanner fs;
    int R, H;
    if (!fs.readInt(R)) return 0;
    if (!fs.readInt(H)) return 0;

    const int N = 1000;
    const int m = R; // expected 75
    const int upperBits = max(0, m - 64);
    const uint64_t hiMask = (upperBits >= 64) ? ~0ULL : (upperBits == 0 ? 0ULL : ((1ULL << upperBits) - 1ULL));
    const uint64_t loMask = (m >= 64) ? ~0ULL : ((m == 0) ? 0ULL : ((1ULL << m) - 1ULL));

    const size_t M = (size_t)N * (N + 1) / 2;

    vector<Bits> words(N);
    vector<Entry> entries(M);

    auto build = [&](uint64_t seed) -> bool {
        uint64_t st = seed;

        for (int i = 0; i < N; i++) {
            uint64_t lo = splitmix64(st);
            uint64_t hi = splitmix64(st);

            lo &= loMask;
            if (m > 64) hi &= hiMask;
            else hi = 0;

            if ((lo | hi) == 0) lo = 1;

            words[i] = {lo, hi};
        }

        // Ensure all words distinct
        vector<pair<uint64_t, uint64_t>> tmp(N);
        for (int i = 0; i < N; i++) tmp[i] = {words[i].hi, words[i].lo};
        sort(tmp.begin(), tmp.end());
        for (int i = 1; i < N; i++) {
            if (tmp[i] == tmp[i - 1]) return false;
        }

        // Ensure each test has both 0 and 1 occurrences
        for (int t = 0; t < m; t++) {
            int cnt = 0;
            for (int i = 0; i < N; i++) cnt += bitAt(words[i], t);
            if (cnt == 0 || cnt == N) return false;
        }

        // Build OR signatures for all pairs
        size_t idx = 0;
        for (int i = 0; i < N; i++) {
            const uint64_t ilo = words[i].lo, ihi = words[i].hi;
            for (int j = i; j < N; j++) {
                entries[idx++] = Entry{(uint64_t)(ilo | words[j].lo), (uint64_t)(ihi | words[j].hi),
                                       (uint16_t)(i + 1), (uint16_t)(j + 1)};
            }
        }

        sort(entries.begin(), entries.end(), entryLess);

        for (size_t k = 1; k < M; k++) {
            if (entries[k].lo == entries[k - 1].lo && entries[k].hi == entries[k - 1].hi) return false;
        }
        return true;
    };

    bool ok = false;
    for (int attempt = 1; attempt <= 50 && !ok; attempt++) {
        uint64_t seed = 0x123456789abcdef0ULL ^ (uint64_t)attempt * 0x9e3779b97f4a7c15ULL;
        ok = build(seed);
    }
    if (!ok) {
        // Extremely unlikely; fallback to still proceed with last build attempt's data.
    }

    // Send all R queries (one per bit)
    for (int t = 0; t < m; t++) {
        vector<int> pos;
        pos.reserve(N / 2);
        for (int i = 0; i < N; i++) if (bitAt(words[i], t)) pos.push_back(i + 1);

        if (pos.empty()) pos.push_back(1); // safety (shouldn't happen)

        string line;
        line.reserve(4 + pos.size() * 5);
        line.push_back('?');
        line.push_back(' ');
        appendInt(line, (int)pos.size());
        for (int p : pos) {
            line.push_back(' ');
            appendInt(line, p);
        }
        line.push_back('\n');
        fwrite(line.data(), 1, line.size(), stdout);
        fflush(stdout);
    }

    // Get results
    {
        const char atLine[] = "@\n";
        fwrite(atLine, 1, 2, stdout);
        fflush(stdout);
    }

    int L;
    if (!fs.readInt(L)) return 0;
    Bits resp{0ULL, 0ULL};
    for (int i = 0; i < L; i++) {
        int x;
        if (!fs.readInt(x)) return 0;
        if (i < m && x == 1) {
            if (i < 64) resp.lo |= (1ULL << i);
            else resp.hi |= (1ULL << (i - 64));
        }
    }

    // Decode via binary search
    uint64_t keyHi = resp.hi;
    uint64_t keyLo = resp.lo;

    size_t l = 0, r = entries.size();
    while (l < r) {
        size_t mid = (l + r) >> 1;
        const Entry &e = entries[mid];
        if (e.hi < keyHi || (e.hi == keyHi && e.lo < keyLo)) l = mid + 1;
        else r = mid;
    }

    int ansA = 1, ansB = 1;
    if (l < entries.size() && entries[l].hi == keyHi && entries[l].lo == keyLo) {
        ansA = entries[l].a;
        ansB = entries[l].b;
    }

    string out;
    out.reserve(32);
    out.push_back('!');
    out.push_back(' ');
    appendInt(out, ansA);
    out.push_back(' ');
    appendInt(out, ansB);
    out.push_back('\n');
    fwrite(out.data(), 1, out.size(), stdout);
    fflush(stdout);

    return 0;
}