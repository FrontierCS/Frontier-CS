#include <bits/stdc++.h>
using namespace std;

static constexpr int MAXN = 100;

struct XorShift64 {
    uint64_t x = 88172645463325252ull;
    inline uint64_t nextU64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
    inline int nextInt(int mod) { return (int)(nextU64() % (uint64_t)mod); }
    inline double nextDouble() { // [0,1)
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

struct SimResult {
    long long err = (1LL<<62);
    array<int, MAXN> cnt{};
};

static inline SimResult simulate(const array<int, MAXN>& a, const array<int, MAXN>& b, const array<int, MAXN>& T, int N, int L) {
    SimResult r;
    r.cnt.fill(0);
    int cur = 0;
    for (int step = 0; step < L; ++step) {
        int c = ++r.cnt[cur];
        if (step == L - 1) break;
        cur = (c & 1) ? a[cur] : b[cur];
    }
    long long e = 0;
    for (int i = 0; i < N; ++i) e += llabs((long long)r.cnt[i] - (long long)T[i]);
    r.err = e;
    return r;
}

static inline int sample_dest_deficit(const array<int, MAXN>& cnt, const array<int, MAXN>& T, int N, XorShift64& rng) {
    long long sum = 0;
    long long w[MAXN];
    for (int j = 0; j < N; ++j) {
        long long d = (long long)T[j] - (long long)cnt[j];
        if (d < 0) d = 0;
        w[j] = d + 1;
        sum += w[j];
    }
    long long r = (long long)(rng.nextU64() % (uint64_t)sum);
    long long acc = 0;
    for (int j = 0; j < N; ++j) {
        acc += w[j];
        if (r < acc) return j;
    }
    return N - 1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, L;
    cin >> N >> L;
    array<int, MAXN> T{};
    for (int i = 0; i < N; ++i) cin >> T[i];

    XorShift64 rng;

    vector<int> perm(N);
    iota(perm.begin(), perm.end(), 0);
    stable_sort(perm.begin(), perm.end(), [&](int i, int j) {
        if (T[i] != T[j]) return T[i] > T[j];
        return i < j;
    });

    int bestK = 0;
    long double bestApprox = 1e100L;
    for (int K = 0; K <= N; ++K) {
        int P = N + K;
        long double base = (long double)L / (long double)P;
        long double e = 0;
        for (int idx = 0; idx < N; ++idx) {
            int i = perm[idx];
            long double pred = base * (idx < K ? 2.0L : 1.0L);
            e += fabsl(pred - (long double)T[i]);
        }
        if (e < bestApprox) {
            bestApprox = e;
            bestK = K;
        }
    }

    array<int, MAXN> curA{}, curB{};
    // Initialize as a cyclic order over perm; top bestK nodes get 2-week dwell (a=i, b=next).
    vector<int> pos(N);
    for (int k = 0; k < N; ++k) pos[perm[k]] = k;
    for (int k = 0; k < N; ++k) {
        int i = perm[k];
        int nxt = perm[(k + 1) % N];
        if (k < bestK) {
            curA[i] = i;
            curB[i] = nxt;
        } else {
            curA[i] = nxt;
            curB[i] = nxt;
        }
    }

    SimResult curRes = simulate(curA, curB, T, N, L);
    array<int, MAXN> bestA = curA, bestB = curB;
    SimResult bestRes = curRes;

    auto tStart = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.85;
    const double T0 = 2500.0;
    const double T1 = 1.0;

    int iters = 0;
    while (true) {
        ++iters;
        auto tNow = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(tNow - tStart).count();
        if (elapsed >= TIME_LIMIT) break;
        double frac = elapsed / TIME_LIMIT;
        double temp = T0 * pow(T1 / T0, frac);

        int i = rng.nextInt(N);
        int which = (int)(rng.nextU64() & 1ull);

        int old = (which == 0 ? curA[i] : curB[i]);

        int j;
        if ((rng.nextU64() % 10ull) < 7ull) {
            j = sample_dest_deficit(curRes.cnt, T, N, rng);
        } else {
            j = rng.nextInt(N);
        }
        if (j == old) continue;

        if (which == 0) curA[i] = j;
        else curB[i] = j;

        SimResult newRes = simulate(curA, curB, T, N, L);
        long long delta = newRes.err - curRes.err;

        bool accept = false;
        if (delta <= 0) {
            accept = true;
        } else {
            double p = exp(-(double)delta / temp);
            if (rng.nextDouble() < p) accept = true;
        }

        if (accept) {
            curRes = newRes;
            if (curRes.err < bestRes.err) {
                bestRes = curRes;
                bestA = curA;
                bestB = curB;
            }
        } else {
            if (which == 0) curA[i] = old;
            else curB[i] = old;
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << bestA[i] << ' ' << bestB[i] << "\n";
    }
    return 0;
}