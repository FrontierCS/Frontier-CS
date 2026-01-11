#include <bits/stdc++.h>
using namespace std;

static inline int bitlen_u64(uint64_t x) {
    return x ? (64 - __builtin_clzll(x)) : 0;
}
static inline int bitsPlus(uint64_t x) {
    return bitlen_u64(x) + 1;
}
static inline uint64_t mul_mod_u128(uint64_t a, uint64_t b, uint64_t mod) {
    __uint128_t t = ( (__uint128_t)a * (__uint128_t)b );
    t %= mod;
    return (uint64_t)t;
}

struct Sample {
    uint64_t a;
    uint64_t pow2[60];      // a^(2^i) mod n
    uint8_t  bp[60];        // bitsPlus(pow2[i])
    uint32_t suffixSq[61];  // sum_{j=i}^{59} bp[j]^2
    uint64_t T;             // total time reported by judge
    uint64_t Sprime;        // sum of square costs
    uint64_t Tprime;        // T - Sprime
};

uint64_t simulate_time(uint64_t a, uint64_t d, uint64_t n) {
    uint64_t r = 1;
    uint64_t t = 0;
    for (int i = 0; i < 60; ++i) {
        if ((d >> i) & 1ULL) {
            t += (uint64_t)bitsPlus(r) * (uint64_t)bitsPlus(a);
            r = mul_mod_u128(r, a, n);
        }
        t += (uint64_t)bitsPlus(a) * (uint64_t)bitsPlus(a);
        a = mul_mod_u128(a, a, n);
    }
    return t;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    uint64_t n;
    if (!(cin >> n)) {
        return 0;
    }

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    const int MAX_QUERIES = 30000;
    int targetN = 12000; // initial number of queries (we will include 1 and n-1 explicitly)
    int totalQueries = 0;

    vector<Sample> samples;
    samples.reserve(MAX_QUERIES);

    unordered_set<uint64_t> used;
    used.reserve(MAX_QUERIES * 2);
    auto add_sample = [&](uint64_t a) {
        if (used.find(a) != used.end()) return false;
        used.insert(a);
        Sample s;
        s.a = a;
        s.pow2[0] = a % n;
        s.bp[0] = (uint8_t)bitsPlus(s.pow2[0]);
        for (int i = 1; i < 60; ++i) {
            s.pow2[i] = mul_mod_u128(s.pow2[i-1], s.pow2[i-1], n);
            s.bp[i] = (uint8_t)bitsPlus(s.pow2[i]);
        }
        s.suffixSq[60] = 0;
        for (int i = 59; i >= 0; --i) {
            s.suffixSq[i] = s.suffixSq[i+1] + (uint32_t)s.bp[i] * (uint32_t)s.bp[i];
        }
        s.Sprime = s.suffixSq[0];
        // Query
        cout << "? " << a << endl;
        cout.flush();
        uint64_t T;
        if (!(cin >> T)) exit(0);
        s.T = T;
        s.Tprime = (T >= s.Sprime) ? (T - s.Sprime) : 0ULL;
        samples.push_back(std::move(s));
        ++totalQueries;
        return true;
    };

    // Ensure presence of a=1 and a=n-1
    add_sample(1);
    if (n > 1) add_sample(n - 1);

    // Fill remaining with random numbers
    while ((int)samples.size() < targetN && totalQueries < MAX_QUERIES) {
        uint64_t a = rng() % n;
        add_sample(a);
    }

    auto infer_d = [&](uint64_t &d_guess) -> void {
        int N = (int)samples.size();
        vector<long double> R(N);
        vector<uint64_t> r(N, 1ULL);

        for (int i = 0; i < N; ++i) {
            R[i] = (long double)samples[i].Tprime;
        }

        // Determine d0 exactly using a=1 and a=n-1
        uint64_t d = 0;
        int idx1 = -1, idxm1 = -1;
        for (int i = 0; i < N; ++i) {
            if (samples[i].a == 1 && idx1 == -1) idx1 = i;
            if (samples[i].a == ((n>0)?(n-1):0) && idxm1 == -1) idxm1 = i;
        }
        if (idx1 != -1 && idxm1 != -1) {
            uint64_t Tm1p = samples[idxm1].Tprime;
            uint64_t T1p  = samples[idx1].Tprime;
            uint64_t diff = (Tm1p >= T1p) ? (Tm1p - T1p) : (T1p - Tm1p);
            uint64_t bn1p = bitsPlus(n - 1);
            uint64_t expected = 2ULL * bn1p - 4ULL;
            if (diff == expected) {
                d |= 1ULL;
            } else {
                // Keep as 0
            }
        } else {
            // Fallback to regression for bit 0
            long double q1 = 0, q2 = 0;
            for (int i = 0; i < N; ++i) {
                long double w = 1.0L / (1.0L + (long double)samples[i].suffixSq[1]);
                int br = bitsPlus(r[i]);
                int F = (int)samples[i].bp[0] * br; // bp[0]*(bitsPlus(1)=2) since r=1 but generalize
                q1 += w * (long double)F * (long double)F;
                q2 += w * (long double)F * R[i];
            }
            if (2.0L * q2 > q1) d |= 1ULL;
        }
        // Update residuals and r for bit 0
        {
            for (int i = 0; i < N; ++i) {
                int br = bitsPlus(r[i]);
                int F = (int)samples[i].bp[0] * br;
                if (d & 1ULL) {
                    R[i] -= (long double)F;
                    r[i] = mul_mod_u128(r[i], samples[i].pow2[0], n);
                }
            }
        }

        // Bits 1..59 via weighted regression
        for (int bit = 1; bit < 60; ++bit) {
            long double q1 = 0.0L, q2 = 0.0L;
            // Compute weighted sums
            for (int i = 0; i < N; ++i) {
                long double w = 1.0L / (1.0L + (long double)samples[i].suffixSq[bit+1]); // inverse noise approx
                int br = bitsPlus(r[i]);
                int F = (int)samples[i].bp[bit] * br;
                q1 += w * (long double)F * (long double)F;
                q2 += w * (long double)F * R[i];
            }
            bool bit1 = (2.0L * q2 > q1);
            if (bit1) d |= (1ULL << bit);
            // Update residuals and r
            if (bit1) {
                for (int i = 0; i < N; ++i) {
                    int br = bitsPlus(r[i]);
                    int F = (int)samples[i].bp[bit] * br;
                    R[i] -= (long double)F;
                    r[i] = mul_mod_u128(r[i], samples[i].pow2[bit], n);
                }
            }
        }
        d_guess = d;
    };

    auto verify_d = [&](uint64_t d) -> bool {
        for (const auto &s : samples) {
            uint64_t Tm = simulate_time(s.a, d, n);
            if (Tm != s.T) return false;
        }
        return true;
    };

    uint64_t d_guess = 0;
    infer_d(d_guess);
    if (!verify_d(d_guess)) {
        // Increase number of samples and retry, up to the limit
        while (totalQueries < MAX_QUERIES) {
            int add = min(4000, MAX_QUERIES - totalQueries);
            if (add <= 0) break;
            int added = 0;
            while (added < add && totalQueries < MAX_QUERIES) {
                uint64_t a = rng() % n;
                if (add_sample(a)) ++added;
            }
            infer_d(d_guess);
            if (verify_d(d_guess)) break;
            // If still not matching, try another round until query limit
        }
    }

    cout << "! " << d_guess << endl;
    cout.flush();
    return 0;
}