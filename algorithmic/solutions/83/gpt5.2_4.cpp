#include <bits/stdc++.h>
using namespace std;

struct RNG {
    uint64_t s;
    explicit RNG(uint64_t seed) : s(seed ? seed : 0x9e3779b97f4a7c15ULL) {}
    inline uint64_t next() {
        s ^= s >> 12;
        s ^= s << 25;
        s ^= s >> 27;
        return s * 2685821657736338717ULL;
    }
    inline int bit() { return (int)(next() & 1ULL); }
};

struct FastOutput {
    static constexpr size_t SZ = 1 << 20;
    char buf[SZ];
    size_t idx = 0;

    inline void flush() {
        if (idx) fwrite(buf, 1, idx, stdout);
        idx = 0;
    }
    inline void pushChar(char c) {
        if (idx == SZ) flush();
        buf[idx++] = c;
    }
    inline void writeVal(int8_t v) {
        if (v == 1) {
            pushChar('1');
        } else {
            pushChar('-');
            pushChar('1');
        }
    }
    ~FastOutput() { flush(); }
};

static inline int iabs_int(int x) { return x < 0 ? -x : x; }

int evalFromSigns(int n, const vector<int> &spf, const vector<int8_t> &sign, vector<int8_t> &curF) {
    curF[1] = 1;
    int pref = 1;
    int mx = 1;
    for (int i = 2; i <= n; ++i) {
        int p = spf[i];
        curF[i] = (int8_t)(curF[i / p] * sign[p]);
        pref += (int)curF[i];
        int a = iabs_int(pref);
        if (a > mx) mx = a;
    }
    return mx;
}

int evalGreedy(int n, const vector<int> &spf, vector<int8_t> &sign, vector<int8_t> &curF, RNG &rng) {
    curF[1] = 1;
    sign[1] = 1;
    int pref = 1;
    int mx = 1;

    for (int i = 2; i <= n; ++i) {
        int p = spf[i];
        if (p == i) {
            int8_t s;
            if ((rng.next() & 7ULL) == 0ULL) {
                s = rng.bit() ? (int8_t)1 : (int8_t)-1;
            } else if (pref > 0) {
                s = -1;
            } else if (pref < 0) {
                s = 1;
            } else {
                s = rng.bit() ? (int8_t)1 : (int8_t)-1;
            }
            sign[p] = s;
        }
        curF[i] = (int8_t)(curF[i / p] * sign[p]);
        pref += (int)curF[i];
        int a = iabs_int(pref);
        if (a > mx) mx = a;
    }
    return mx;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> spf(n + 1, 0);
    vector<int> primes;
    primes.reserve(max(1, (int)(n / log(max(2, n)))));

    spf[1] = 1;
    for (int i = 2; i <= n; ++i) {
        if (spf[i] == 0) {
            spf[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            long long x = 1LL * p * i;
            if (x > n) break;
            spf[(int)x] = p;
            if (p == spf[i]) break;
        }
    }

    vector<int8_t> sign(n + 1, 1);
    vector<int8_t> curF(n + 1, 1);
    vector<int8_t> bestF(n + 1, 1);

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&n;
    RNG rng(seed);

    int bestMx = INT_MAX;

    // Trial 1: Liouville (f(p) = -1 for all primes)
    sign[1] = 1;
    for (int p : primes) sign[p] = -1;
    {
        int mx = evalFromSigns(n, spf, sign, curF);
        bestMx = mx;
        memcpy(bestF.data(), curF.data(), (n + 1) * sizeof(int8_t));
    }

    // Greedy trials
    int greedyTrials = 20;
    for (int t = 0; t < greedyTrials; ++t) {
        int mx = evalGreedy(n, spf, sign, curF, rng);
        if (mx < bestMx) {
            bestMx = mx;
            memcpy(bestF.data(), curF.data(), (n + 1) * sizeof(int8_t));
        }
    }

    // Random trials
    int randomTrials = 20;
    for (int t = 0; t < randomTrials; ++t) {
        sign[1] = 1;
        for (int p : primes) sign[p] = rng.bit() ? (int8_t)1 : (int8_t)-1;
        int mx = evalFromSigns(n, spf, sign, curF);
        if (mx < bestMx) {
            bestMx = mx;
            memcpy(bestF.data(), curF.data(), (n + 1) * sizeof(int8_t));
        }
    }

    FastOutput out;
    for (int i = 1; i <= n; ++i) {
        if (i > 1) out.pushChar(' ');
        out.writeVal(bestF[i]);
    }
    out.pushChar('\n');
    out.flush();
    return 0;
}