#include <bits/stdc++.h>
using namespace std;

struct Entry {
    uint64_t key;
    uint16_t a, b;
};

static inline void appendInt(string &s, int x) {
    char buf[16];
    int n = 0;
    if (x == 0) {
        s.push_back('0');
        return;
    }
    while (x > 0) {
        buf[n++] = char('0' + (x % 10));
        x /= 10;
    }
    for (int i = n - 1; i >= 0; --i) s.push_back(buf[i]);
}

static inline void radixSortByKey(vector<Entry> &a) {
    const size_t N = a.size();
    vector<Entry> tmp(N);
    static vector<uint32_t> cnt(1u << 16);

    for (int pass = 0; pass < 4; ++pass) {
        fill(cnt.begin(), cnt.end(), 0);
        int shift = 16 * pass;
        for (size_t i = 0; i < N; ++i) {
            ++cnt[(a[i].key >> shift) & 0xFFFFu];
        }
        uint32_t sum = 0;
        for (size_t i = 0; i < cnt.size(); ++i) {
            uint32_t c = cnt[i];
            cnt[i] = sum;
            sum += c;
        }
        for (size_t i = 0; i < N; ++i) {
            uint32_t d = (a[i].key >> shift) & 0xFFFFu;
            tmp[cnt[d]++] = a[i];
        }
        a.swap(tmp);
    }
}

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed) : x(seed) {}
    inline uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
};

int main() {
    int R, H;
    if (scanf("%d %d", &R, &H) != 2) return 0;

    const int N = 1000;
    int M = min(R, 63);
    if (M <= 0) return 0;
    int W = 12;
    if (W > M) W = M;

    vector<uint64_t> code(N + 1);
    vector<vector<int>> tests;

    vector<Entry> entries;
    entries.reserve((size_t)N * (N + 1) / 2);

    uint64_t baseSeed = 0x1234567890abcdefULL;

    while (true) {
        SplitMix64 rng(baseSeed);
        baseSeed += 0x9e3779b97f4a7c15ULL;

        uint64_t mask = (M == 64) ? ~0ULL : ((1ULL << M) - 1ULL);

        for (int i = 1; i <= N; ++i) {
            uint64_t x = 0;
            int cnt = 0;
            while (cnt < W) {
                int b = (int)(rng.next() % (uint64_t)M);
                uint64_t bit = 1ULL << b;
                if ((x & bit) == 0) {
                    x |= bit;
                    ++cnt;
                }
            }
            x &= mask;
            if (x == 0) x = 1ULL;
            code[i] = x;
        }

        entries.clear();
        for (uint16_t i = 1; i <= N; ++i) {
            uint64_t ci = code[i];
            for (uint16_t j = i; j <= N; ++j) {
                entries.push_back(Entry{ci | code[j], i, j});
            }
        }

        radixSortByKey(entries);

        bool ok = true;
        for (size_t i = 1; i < entries.size(); ++i) {
            if (entries[i].key == entries[i - 1].key) {
                ok = false;
                break;
            }
        }
        if (!ok) {
            if (M < min(R, 63)) M = min(R, 63);
            if (W < min(16, M)) W++;
            continue;
        }

        tests.assign(M, {});
        for (int pos = 1; pos <= N; ++pos) {
            uint64_t x = code[pos];
            while (x) {
                int b = __builtin_ctzll(x);
                if (b < M) tests[b].push_back(pos);
                x &= x - 1;
            }
        }

        break;
    }

    for (int b = 0; b < M; ++b) {
        auto &lst = tests[b];
        string out;
        out.reserve(3 + 6 + lst.size() * 5);
        out.push_back('?');
        out.push_back(' ');
        appendInt(out, (int)lst.size());
        for (int p : lst) {
            out.push_back(' ');
            appendInt(out, p);
        }
        out.push_back('\n');
        fwrite(out.data(), 1, out.size(), stdout);
        fflush(stdout);
    }

    {
        const char atline[] = "@\n";
        fwrite(atline, 1, 2, stdout);
        fflush(stdout);
    }

    int L;
    if (scanf("%d", &L) != 1) return 0;
    if (L < 0) return 0;

    uint64_t resp = 0;
    for (int i = 0; i < L; ++i) {
        int v;
        if (scanf("%d", &v) != 1) return 0;
        if (v == 1 && i < 64) resp |= (1ULL << i);
    }

    auto it = lower_bound(entries.begin(), entries.end(), resp,
                          [](const Entry &e, uint64_t k) { return e.key < k; });

    uint16_t a = 1, b = 1;
    if (it != entries.end() && it->key == resp) {
        a = it->a;
        b = it->b;
    } else {
        // Should not happen if construction is correct; output something valid.
        a = 1; b = 1;
    }

    printf("! %u %u\n", (unsigned)a, (unsigned)b);
    fflush(stdout);
    return 0;
}