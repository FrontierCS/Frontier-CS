#include <bits/stdc++.h>
using namespace std;

struct XorShift64 {
    uint64_t x;
    explicit XorShift64(uint64_t seed = 88172645463325252ull) : x(seed) {}
    uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    uint64_t next(uint64_t mod) { return mod ? next() % mod : 0; }
};

static long long exactSingleDistance(long long m, long long d) {
    if (m <= 0) return 0;
    if (d <= 0) return m;
    if (d > m) return m;

    long long q = m / d;
    long long rem = m % d;

    long long lenSmall = q;
    long long lenBig = q + 1;

    long long contribBig = (lenBig + 1) / 2;
    long long contribSmall = (lenSmall + 1) / 2;

    __int128 ans = (__int128)rem * contribBig + (__int128)(d - rem) * contribSmall;
    if (ans < 0) ans = 0;
    if (ans > m) ans = m;
    return (long long)ans;
}

struct ApproxMIS {
    long long a, b; // a <= b, gcd(a,b)=1 usually
    long long directCap = 3000000;
    long long maxSample = 8000000;

    bool sampleReady = false;
    int sampleRuns = 0;
    long long sampleLen = 0;
    long long sampleBest = 0;

    XorShift64 rng;

    explicit ApproxMIS(long long a_, long long b_)
        : a(min(a_, b_)), b(max(a_, b_)),
          rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count()) {}

    long long heuristicMIS(long long M, int runs) {
        if (M <= 0) return 0;
        if (M == 1) return 1;
        vector<uint8_t> chosen((size_t)M + 1);

        auto canPickForward = [&](long long i) -> bool {
            if (i > a && chosen[(size_t)(i - a)]) return false;
            if (i > b && chosen[(size_t)(i - b)]) return false;
            return true;
        };
        auto canPickReverse = [&](long long i) -> bool {
            if (i + a <= M && chosen[(size_t)(i + a)]) return false;
            if (i + b <= M && chosen[(size_t)(i + b)]) return false;
            return true;
        };
        auto canPickAny = [&](long long i) -> bool {
            if (i > a && chosen[(size_t)(i - a)]) return false;
            if (i + a <= M && chosen[(size_t)(i + a)]) return false;
            if (i > b && chosen[(size_t)(i - b)]) return false;
            if (i + b <= M && chosen[(size_t)(i + b)]) return false;
            return true;
        };

        long long best = 0;

        // Run 0: forward greedy
        {
            memset(chosen.data(), 0, (size_t)M + 1);
            long long cnt = 0;
            for (long long i = 1; i <= M; ++i) {
                if (canPickForward(i)) {
                    chosen[(size_t)i] = 1;
                    ++cnt;
                }
            }
            best = max(best, cnt);
        }

        if (runs >= 2) {
            // Run 1: reverse greedy
            memset(chosen.data(), 0, (size_t)M + 1);
            long long cnt = 0;
            for (long long i = M; i >= 1; --i) {
                if (canPickReverse(i)) {
                    chosen[(size_t)i] = 1;
                    ++cnt;
                }
            }
            best = max(best, cnt);
        }

        int randomRuns = max(0, runs - 2);
        for (int r = 0; r < randomRuns; ++r) {
            memset(chosen.data(), 0, (size_t)M + 1);
            long long cnt = 0;

            uint32_t MM = (uint32_t)M;
            uint32_t start = (uint32_t)rng.next(MM);
            uint32_t step;
            if (MM == 1) step = 0;
            else {
                // choose step in [1..M-1] with gcd(step,M)=1
                while (true) {
                    step = (uint32_t)(rng.next((uint64_t)(MM - 1)) + 1);
                    if (std::gcd(step, MM) == 1) break;
                }
            }

            uint32_t idx = start;
            for (uint32_t t = 0; t < MM; ++t) {
                long long i = (long long)idx + 1;
                if (canPickAny(i)) {
                    chosen[(size_t)i] = 1;
                    ++cnt;
                }
                idx += step;
                if (idx >= MM) idx -= MM; // since step < M, one subtraction is enough
            }

            best = max(best, cnt);
        }

        return best;
    }

    void ensureSample() {
        if (sampleReady) return;

        long long target = max(directCap, 2LL * (a + b));
        target = min(maxSample, target);
        target = max(target, b + 1);
        sampleLen = target;

        if (sampleLen <= 100000) sampleRuns = 20;
        else if (sampleLen <= 1000000) sampleRuns = 12;
        else if (sampleLen <= 3000000) sampleRuns = 8;
        else sampleRuns = 6;

        sampleBest = heuristicMIS(sampleLen, sampleRuns);
        sampleReady = true;
    }

    long long solve(long long m) {
        if (m <= 0) return 0;
        if (m == 1) return 1;

        if (a == b) {
            return exactSingleDistance(m, a);
        }

        if (a > m && b > m) return m;
        if (b > m) return exactSingleDistance(m, a);
        if (a > m) return exactSingleDistance(m, b);

        long long res = 0;

        if (m <= directCap) {
            int runs;
            if (m <= 100000) runs = 20;
            else if (m <= 1000000) runs = 12;
            else runs = 8;
            res = heuristicMIS(m, runs);
        } else {
            ensureSample();
            __int128 val = (__int128)sampleBest * m + sampleLen / 2;
            val /= sampleLen;
            if (val < 0) val = 0;
            if (val > m) val = m;
            res = (long long)val;
        }

        // Always-valid parity independent set if both distances are odd.
        if ((a & 1LL) && (b & 1LL)) {
            res = max(res, (m + 1) / 2);
        }

        if (res < 0) res = 0;
        if (res > m) res = m;
        return res;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n, x, y;
    cin >> n >> x >> y;

    if (n <= 0) {
        cout << 0 << "\n";
        return 0;
    }

    if (x > y) swap(x, y);

    long long g = std::gcd(x, y);
    long long a = x / g;
    long long b = y / g;

    long long q = n / g;
    long long rem = n % g;

    ApproxMIS solver(a, b);

    long long fq = solver.solve(q);
    long long fq1 = solver.solve(q + 1);

    __int128 ans = (__int128)(g - rem) * fq + (__int128)rem * fq1;
    if (ans < 0) ans = 0;
    if (ans > n) ans = n;

    cout << (long long)ans << "\n";
    return 0;
}