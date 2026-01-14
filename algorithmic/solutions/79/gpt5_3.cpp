#include <bits/stdc++.h>
using namespace std;

static inline int bits1(uint64_t x) {
    if (x == 0) return 1; // bits(0)+1 = 1
    return 1 + (64 - __builtin_clzll(x)); // bits(x)+1
}

static inline uint64_t mulmod(uint64_t a, uint64_t b, uint64_t mod) {
    __uint128_t r = ( (__uint128_t)a * (__uint128_t)b );
    r %= mod;
    return (uint64_t)r;
}

struct Sample {
    uint64_t a0;
    array<uint64_t, 60> avals;
    array<uint8_t, 60> abit1;
    long long S; // baseline sum of squares (line 7)
    long long T; // measured total time
    long long D; // T - S
};

static long long simulateTime(uint64_t n, uint64_t a, uint64_t d) {
    uint64_t r = 1;
    uint64_t cur = a % n;
    long long tot = 0;
    for (int i = 0; i < 60; ++i) {
        if ((d >> i) & 1ULL) {
            int br = bits1(r);
            int ba = bits1(cur);
            tot += 1LL * br * ba;
            r = mulmod(r, cur, n);
        }
        int ba = bits1(cur);
        tot += 1LL * ba * ba;
        cur = mulmod(cur, cur, n);
    }
    return tot;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    uint64_t n;
    if (!(cin >> n)) {
        return 0;
    }

    auto ask = [&](uint64_t a)->long long {
        cout << "? " << a << endl;
        cout.flush();
        long long t;
        if (!(cin >> t)) exit(0);
        return t;
    };

    // Query a=0 to get popcount of d
    long long t0 = ask(0);
    int ones_target = (int)(t0 - 61);
    if (ones_target < 0) ones_target = 0;
    if (ones_target > 60) ones_target = 60;

    // Storage for samples
    vector<Sample> samples;
    samples.reserve(30050);

    // Precompute sample from a
    auto precompute_sample = [&](uint64_t a)->Sample {
        Sample s;
        s.a0 = a % n;
        uint64_t cur = s.a0;
        long long S = 0;
        for (int i = 0; i < 60; ++i) {
            s.avals[i] = cur;
            uint8_t b = (uint8_t)bits1(cur);
            s.abit1[i] = b;
            S += 1LL * b * b;
            cur = mulmod(cur, cur, n);
        }
        s.S = S;
        s.T = ask(a);
        s.D = s.T - s.S;
        return s;
    };

    auto decode = [&](const vector<Sample>& smp)->pair<uint64_t, vector<double>> {
        int M = (int)smp.size();
        vector<uint64_t> r(M, 1);
        vector<long long> R(M);
        for (int j = 0; j < M; ++j) {
            R[j] = smp[j].D;
        }
        uint64_t d = 0;
        vector<double> alphas(60, 0.0);
        for (int i = 0; i < 60; ++i) {
            long double sumC2 = 0.0L;
            long double sumCR = 0.0L;
            // compute coefficients
            for (int j = 0; j < M; ++j) {
                int br = bits1(r[j]);
                int ba = smp[j].abit1[i];
                long long c = 1LL * br * ba;
                sumC2 += (long double)c * (long double)c;
                sumCR += (long double)c * (long double)R[j];
            }
            double alpha = 0.0;
            if (sumC2 > 0) alpha = (double)(sumCR / sumC2);
            alphas[i] = alpha;
            int bit = (alpha > 0.5) ? 1 : 0;
            if (bit) d |= (1ULL << i);
            // update R and r
            if (bit) {
                for (int j = 0; j < M; ++j) {
                    int br = bits1(r[j]);
                    int ba = smp[j].abit1[i];
                    long long c = 1LL * br * ba;
                    R[j] -= c;
                }
                for (int j = 0; j < M; ++j) {
                    r[j] = mulmod(r[j], smp[j].avals[i], n);
                }
            }
        }
        return {d, alphas};
    };

    // Schedules for number of samples
    vector<int> targets = {2000, 5000, 9000, 13000, 18000, 23000, 27000};
    // Keep some room for verification queries
    const int VERIFY_MAX = 20;
    int used_queries = 1; // already used a=0
    uint64_t d_found = 0;

    auto do_verify = [&](uint64_t d)->bool {
        int trials = min(VERIFY_MAX, 5 + (int)(60 - __builtin_popcountll(d)));
        for (int t = 0; t < trials; ++t) {
            if (used_queries + 1 > 30000) return false; // can't verify
            uint64_t a = (uint64_t) ( ( ( (unsigned long long)rand() << 32 ) ^ rand() ) % n );
            long long T_real = ask(a);
            ++used_queries;
            long long T_pred = simulateTime(n, a, d);
            if (T_real != T_pred) return false;
        }
        return true;
    };

    // main loop
    for (int ti = 0; ti < (int)targets.size(); ++ti) {
        int target = targets[ti];
        // ensure we don't exceed total query limit (keeping VERIFY_MAX spare)
        target = min(target, 30000 - VERIFY_MAX - used_queries);
        while ((int)samples.size() < target) {
            // Random a in [0, n-1]
            uint64_t a = (uint64_t) ( ( ( (unsigned long long)rand() << 32 ) ^ rand() ) % n );
            Sample s = precompute_sample(a);
            samples.push_back(std::move(s));
            ++used_queries;
            if (used_queries >= 30000 - VERIFY_MAX) break;
        }
        // Decode
        auto res = decode(samples);
        d_found = res.first;
        if ((int)__builtin_popcountll(d_found) != ones_target) {
            continue;
        }
        // Verify with additional queries
        if (do_verify(d_found)) {
            cout << "! " << d_found << endl;
            cout.flush();
            return 0;
        }
        // else, continue to collect more samples
    }

    // If still not verified, try with whatever remaining budget
    while (used_queries < 30000 - 1) {
        uint64_t a = (uint64_t) ( ( ( (unsigned long long)rand() << 32 ) ^ rand() ) % n );
        Sample s = precompute_sample(a);
        samples.push_back(std::move(s));
        ++used_queries;
        auto res = decode(samples);
        d_found = res.first;
        if ((int)__builtin_popcountll(d_found) == ones_target) {
            if (do_verify(d_found)) {
                cout << "! " << d_found << endl;
                cout.flush();
                return 0;
            }
        }
    }

    // As last resort output the best found (may be wrong, but we must output something)
    cout << "! " << d_found << endl;
    cout.flush();
    return 0;
}