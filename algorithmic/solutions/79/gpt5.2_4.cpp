#include <bits/stdc++.h>
using namespace std;

static inline int bits_u64(uint64_t x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

static inline uint64_t mulmod_u64(uint64_t a, uint64_t b, uint64_t mod) {
    return (uint64_t)((__uint128_t)a * b % mod);
}

static inline long long mulCost(uint64_t x, uint64_t y) {
    long long bx = bits_u64(x);
    long long by = bits_u64(y);
    return (bx + 1) * (by + 1);
}

static long long computeTime(uint64_t a, uint64_t d, uint64_t n) {
    uint64_t r = 1;
    uint64_t cur = a;
    long long t = 0;
    for (int i = 0; i < 60; i++) {
        if ((d >> i) & 1ULL) {
            t += mulCost(r, cur);
            r = mulmod_u64(r, cur, n);
        }
        t += mulCost(cur, cur);
        cur = mulmod_u64(cur, cur, n);
    }
    return t;
}

struct Sample {
    uint64_t a0;
    long long totalTime;
};

static bool recoverD(const uint64_t n, const vector<Sample>& samples, uint64_t &d_out) {
    const int Q = (int)samples.size();
    if (Q < 1000) return false;

    constexpr int PREFIX_LEN = 40;
    const int K = 60 - PREFIX_LEN;

    vector<long long> mulTotal(Q);
    vector<uint64_t> r(Q, 1), aCur(Q);
    vector<long long> prefMul(Q, 0);

    for (int s = 0; s < Q; s++) {
        uint64_t a = samples[s].a0;
        aCur[s] = a;
        long long sqrSum = 0;
        uint64_t cur = a;
        for (int i = 0; i < 60; i++) {
            sqrSum += mulCost(cur, cur);
            cur = mulmod_u64(cur, cur, n);
        }
        mulTotal[s] = samples[s].totalTime - sqrSum;
        // mulTotal should be >= 0 always
        if (mulTotal[s] < 0) return false;
    }

    uint64_t prefixD = 0;
    for (int i = 0; i < PREFIX_LEN; i++) {
        // Compute score for hypothesis b=0 and b=1.
        // For each hypothesis, correlation between feature=bits(rNext)+1 and residual=mulTotal - prefMul - (b?cost:0)
        auto calcScore = [&](int b) -> long double {
            long double sumX = 0, sumY = 0, sumXX = 0, sumYY = 0, sumXY = 0;
            int negCnt = 0;
            for (int s = 0; s < Q; s++) {
                long long res0 = mulTotal[s] - prefMul[s];
                uint64_t featR;
                long long res;
                if (b == 0) {
                    featR = r[s];
                    res = res0;
                } else {
                    long long c = mulCost(r[s], aCur[s]);
                    res = res0 - c;
                    featR = mulmod_u64(r[s], aCur[s], n);
                }
                if (res < 0) negCnt++;
                long double X = (long double)(bits_u64(featR) + 1);
                long double Y = (long double)res;
                sumX += X;
                sumY += Y;
                sumXX += X * X;
                sumYY += Y * Y;
                sumXY += X * Y;
            }
            long double N = (long double)Q;
            long double denX = N * sumXX - sumX * sumX;
            long double denY = N * sumYY - sumY * sumY;
            long double corr = 0;
            if (denX > 0 && denY > 0) {
                long double num = N * sumXY - sumX * sumY;
                corr = fabsl(num) / sqrtl(denX * denY);
            }
            long double negProp = (long double)negCnt / (long double)Q;
            // Penalize negative residuals strongly.
            long double score = corr - 2.0L * negProp;
            return score;
        };

        long double score0 = calcScore(0);
        long double score1 = calcScore(1);
        int bit = (score1 > score0) ? 1 : 0;
        if (bit) prefixD |= (1ULL << i);

        // Update states with chosen bit.
        for (int s = 0; s < Q; s++) {
            if (bit) {
                prefMul[s] += mulCost(r[s], aCur[s]);
                r[s] = mulmod_u64(r[s], aCur[s], n);
            }
            aCur[s] = mulmod_u64(aCur[s], aCur[s], n);
        }
    }

    // Pick a few good samples for brute force constraints
    vector<int> idx;
    idx.reserve(6);
    for (int s = 0; s < Q && (int)idx.size() < 5; s++) {
        uint64_t a0 = samples[s].a0;
        if (a0 <= 1 || a0 >= n) continue;
        if (std::gcd(a0, n) != 1ULL) continue;
        idx.push_back(s);
    }
    if ((int)idx.size() < 3) {
        // relax gcd condition
        idx.clear();
        for (int s = 0; s < Q && (int)idx.size() < 4; s++) {
            uint64_t a0 = samples[s].a0;
            if (a0 <= 1 || a0 >= n) continue;
            idx.push_back(s);
        }
    }
    if ((int)idx.size() < 3) return false;
    int S = min(4, (int)idx.size());

    struct BFData {
        uint64_t r0;
        uint64_t a0;
        long long need;
        array<uint64_t, 20> aVal;
        array<int, 20> aBitsP1;
    };
    vector<BFData> bf(S);

    for (int j = 0; j < S; j++) {
        int s = idx[j];
        bf[j].r0 = r[s];
        bf[j].a0 = aCur[s];
        bf[j].need = mulTotal[s] - prefMul[s];
        uint64_t cur = bf[j].a0;
        for (int t = 0; t < K; t++) {
            bf[j].aVal[t] = cur;
            bf[j].aBitsP1[t] = bits_u64(cur) + 1;
            cur = mulmod_u64(cur, cur, n);
        }
    }

    auto verifyCandidate = [&](uint64_t dCand) -> bool {
        for (int s = 0; s < Q; s++) {
            long long tPred = computeTime(samples[s].a0, dCand, n);
            if (tPred != samples[s].totalTime) return false;
        }
        return true;
    };

    uint64_t limit = (K == 64 ? ~0ULL : (1ULL << K));
    for (uint64_t mask = 0; mask < limit; mask++) {
        bool ok = true;
        for (int j = 0; j < S; j++) {
            uint64_t rr = bf[j].r0;
            long long tm = 0;
            long long need = bf[j].need;
            for (int t = 0; t < K; t++) {
                if ((mask >> t) & 1ULL) {
                    tm += (long long)(bits_u64(rr) + 1) * (long long)bf[j].aBitsP1[t];
                    if (tm > need) break;
                    rr = mulmod_u64(rr, bf[j].aVal[t], n);
                }
            }
            if (tm != need) { ok = false; break; }
        }
        if (!ok) continue;

        uint64_t dCand = prefixD | (mask << PREFIX_LEN);
        if (verifyCandidate(dCand)) {
            d_out = dCand;
            return true;
        }
    }

    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    uint64_t n;
    if (!(cin >> n)) return 0;

    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto randA = [&]() -> uint64_t {
        uint64_t lo = 2;
        uint64_t hi = n >= 3 ? n - 2 : 0;
        if (hi < lo) return 1;
        // rejection sampling to reduce bias
        __uint128_t range = (__uint128_t)hi - lo + 1;
        while (true) {
            uint64_t x = rng();
            __uint128_t v = x;
            __uint128_t limit = (((__uint128_t)1 << 64) / range) * range;
            if (v < limit) return (uint64_t)(lo + (uint64_t)(v % range));
        }
    };

    vector<Sample> samples;
    samples.reserve(30000);

    auto query = [&](uint64_t a) -> long long {
        cout << "? " << a << "\n" << flush;
        long long t;
        if (!(cin >> t)) exit(0);
        return t;
    };

    uint64_t ansD = 1;
    bool found = false;

    const int rounds = 2;
    const int targetQ[rounds] = {24000, 29000};

    for (int round = 0; round < rounds && !found; round++) {
        int need = targetQ[round] - (int)samples.size();
        for (int i = 0; i < need; i++) {
            uint64_t a = randA();
            long long t = query(a);
            samples.push_back({a, t});
        }
        if (recoverD(n, samples, ansD)) {
            found = true;
            break;
        }
    }

    cout << "! " << ansD << "\n" << flush;
    return 0;
}