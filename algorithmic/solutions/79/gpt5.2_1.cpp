#include <bits/stdc++.h>
using namespace std;

static inline int bits_u64(uint64_t x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

static inline uint64_t mulmod_u64(uint64_t a, uint64_t b, uint64_t mod) {
    return (uint64_t)((__uint128_t)a * b % mod);
}

static inline int mulCostFromBits(int bx, int by) {
    return (bx + 1) * (by + 1);
}

static inline long long simulateTime(uint64_t a, uint64_t d, uint64_t n) {
    uint64_t r = 1;
    long long t = 0;
    for (int i = 0; i < 60; ++i) {
        if ((d >> i) & 1ULL) {
            t += (long long)mulCostFromBits(bits_u64(r), bits_u64(a));
            r = mulmod_u64(r, a, n);
        }
        t += (long long)mulCostFromBits(bits_u64(a), bits_u64(a));
        a = mulmod_u64(a, a, n);
    }
    return t;
}

struct Sample {
    uint64_t a0{};
    array<uint64_t, 60> A{};
    array<uint8_t, 60> BA{};
    long long time{};
    long long cond{}; // time - sum(square costs)
};

static uint64_t Nmod;
static mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

static long long ask(uint64_t a) {
    cout << "? " << a << "\n" << flush;
    long long t;
    if (!(cin >> t)) exit(0);
    return t;
}

static uint64_t genA() {
    while (true) {
        uint64_t a;
        if (rng() & 1ULL) {
            uint64_t upper = min<uint64_t>(Nmod - 1, (1ULL << 30) - 1);
            if (upper < 2) continue;
            a = 2 + (uint64_t)(rng() % (upper - 1));
        } else {
            a = (uint64_t)(rng() % Nmod);
            if (a < 2) continue;
        }
        return a;
    }
}

static Sample makeSample(uint64_t a0, long long t) {
    Sample s;
    s.a0 = a0;
    s.time = t;

    uint64_t a = a0;
    long long sqTotal = 0;
    for (int i = 0; i < 60; ++i) {
        s.A[i] = a;
        int ba = bits_u64(a);
        s.BA[i] = (uint8_t)ba;
        sqTotal += (long long)mulCostFromBits(ba, ba);
        a = mulmod_u64(a, a, Nmod);
    }
    s.cond = t - sqTotal;
    return s;
}

static pair<uint64_t, bool> recoverD(const vector<Sample>& samples) {
    const int S = (int)samples.size();
    vector<uint64_t> r(S);
    vector<long long> rem(S);

    // d is coprime with phi(n) which is even => d is odd => bit0 = 1.
    uint64_t d = 1ULL;

    for (int s = 0; s < S; ++s) {
        rem[s] = samples[s].cond;
        // bit0 conditional multiplication: r=1, a=a0
        int f0 = 2 * ((int)samples[s].BA[0] + 1); // (bits(1)+1)=2
        rem[s] -= f0;
        if (rem[s] < 0) return {d, false};
        r[s] = samples[s].A[0]; // r = a0 % n (a0 < n)
    }

    vector<int> f(S);

    for (int i = 1; i < 60; ++i) {
        bool possible1 = true;

        long double sumR = 0, sumF = 0, sumRF = 0, sumF2 = 0;

        for (int s = 0; s < S; ++s) {
            int br = bits_u64(r[s]);
            int ba = (int)samples[s].BA[i];
            int fi = (br + 1) * (ba + 1);
            f[s] = fi;

            if (rem[s] < fi) possible1 = false;

            long double R = (long double)rem[s];
            long double F = (long double)fi;
            sumR += R;
            sumF += F;
            sumRF += R * F;
            sumF2 += F * F;
        }

        bool bit = false;
        if (possible1) {
            long double invS = 1.0L / (long double)S;
            long double meanR = sumR * invS;
            long double meanF = sumF * invS;

            long double cov0 = sumRF * invS - meanR * meanF;

            long double sumRm = sumR - sumF;
            long double meanRm = sumRm * invS;
            long double sumRmF = sumRF - sumF2;
            long double cov1 = sumRmF * invS - meanRm * meanF;

            long double a0 = fabsl(cov0);
            long double a1 = fabsl(cov1);

            if (a0 == a1) {
                long double varF = sumF2 * invS - meanF * meanF;
                long double beta = (varF > 1e-18L) ? (cov0 / varF) : 0.0L;
                bit = (beta > 0.5L);
            } else {
                bit = (a0 > a1);
            }
        } else {
            bit = false;
        }

        if (bit) {
            d |= (1ULL << i);
            for (int s = 0; s < S; ++s) {
                rem[s] -= f[s];
                if (rem[s] < 0) return {d, false};
                r[s] = mulmod_u64(r[s], samples[s].A[i], Nmod);
            }
        }
    }

    for (int s = 0; s < S; ++s) {
        if (rem[s] != 0) return {d, false};
    }
    return {d, true};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> Nmod)) return 0;

    vector<Sample> samples;
    samples.reserve(30000);

    int qcount = 0;
    const int QLIM = 30000;

    auto addQuery = [&](uint64_t a) {
        long long t = ask(a);
        ++qcount;
        samples.push_back(makeSample(a, t));
    };

    // Warm-up with some small values to diversify early steps
    for (uint64_t a = 2; a <= 200 && qcount < QLIM; ++a) addQuery(a);

    uint64_t lastD = 1;
    int target = 8000;
    int batch = 4000;

    while (qcount < QLIM) {
        while ((int)samples.size() < target && qcount < QLIM) {
            uint64_t a = genA();
            addQuery(a);
        }

        auto [d, ok] = recoverD(samples);
        lastD = d;

        if (ok) {
            bool verified = true;
            int V = 5;
            for (int i = 0; i < V && qcount < QLIM; ++i) {
                uint64_t a = genA();
                long long t = ask(a);
                ++qcount;

                if (simulateTime(a, d, Nmod) != t) verified = false;
                samples.push_back(makeSample(a, t));
                if (!verified) break;
            }

            if (verified) {
                cout << "! " << d << "\n" << flush;
                return 0;
            }
        }

        if (qcount >= QLIM) break;
        target = min(target + batch, 28000);
    }

    cout << "! " << lastD << "\n" << flush;
    return 0;
}