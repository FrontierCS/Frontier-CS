#include <bits/stdc++.h>
using namespace std;

using u64 = uint64_t;
using u128 = __uint128_t;

static inline u64 mod_mul(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
}

static inline u64 mod_pow(u64 a, u64 e, u64 mod) {
    u64 r = 1;
    while (e) {
        if (e & 1) r = mod_mul(r, a, mod);
        a = mod_mul(a, a, mod);
        e >>= 1;
    }
    return r;
}

static inline u64 gcd_u64(u64 a, u64 b) {
    while (b) {
        u64 t = a % b;
        a = b;
        b = t;
    }
    return a;
}

static bool isPrime64(u64 n) {
    if (n < 2) return false;
    for (u64 p : {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL, 19ULL, 23ULL, 29ULL, 31ULL, 37ULL}) {
        if (n % p == 0) return n == p;
    }
    u64 d = n - 1, s = 0;
    while ((d & 1) == 0) { d >>= 1; ++s; }

    auto witness = [&](u64 a) -> bool {
        if (a % n == 0) return false;
        u64 x = mod_pow(a % n, d, n);
        if (x == 1 || x == n - 1) return false;
        for (u64 i = 1; i < s; i++) {
            x = mod_mul(x, x, n);
            if (x == n - 1) return false;
        }
        return true;
    };

    // Deterministic for 64-bit:
    for (u64 a : {2ULL, 325ULL, 9375ULL, 28178ULL, 450775ULL, 9780504ULL, 1795265022ULL}) {
        if (witness(a)) return false;
    }
    return true;
}

static u64 pollard_rho(u64 n, std::mt19937_64 &rng) {
    if ((n & 1ULL) == 0) return 2;
    if (n % 3ULL == 0) return 3;

    std::uniform_int_distribution<u64> dist(2, n - 2);

    while (true) {
        u64 c = dist(rng);
        u64 x = dist(rng);
        u64 y = x;
        u64 d = 1;

        auto f = [&](u64 v) -> u64 {
            return (mod_mul(v, v, n) + c) % n;
        };

        while (d == 1) {
            x = f(x);
            y = f(f(y));
            u64 diff = (x > y) ? (x - y) : (y - x);
            d = gcd_u64(diff, n);
        }
        if (d != n) return d;
    }
}

static void factor_rec(u64 n, vector<u64> &fac, std::mt19937_64 &rng) {
    if (n == 1) return;
    if (isPrime64(n)) {
        fac.push_back(n);
        return;
    }
    u64 d = pollard_rho(n, rng);
    factor_rec(d, fac, rng);
    factor_rec(n / d, fac, rng);
}

static inline int bitlen(u64 x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

static inline u64 mul_cost(u64 x, u64 y) {
    return (u64)(bitlen(x) + 1) * (u64)(bitlen(y) + 1);
}

static u64 simulate_time(u64 a, u64 d, u64 n) {
    u64 r = 1;
    u64 time = 0;
    for (int i = 0; i < 60; i++) {
        if ((d >> i) & 1ULL) {
            time += mul_cost(r, a);
            r = mod_mul(r, a, n);
        }
        time += mul_cost(a, a);
        a = mod_mul(a, a, n);
    }
    return time;
}

struct Trace {
    array<u64, 60> aval{};
    array<uint8_t, 60> abits1{}; // bits(a)+1
    u64 totalTime = 0;
    u64 multTime = 0; // totalTime - squaresCost
};

static u64 N;
static int queries = 0;

static u64 ask(u64 a) {
    cout << "? " << a << "\n" << flush;
    long long t;
    if (!(cin >> t)) exit(0);
    if (t < 0) exit(0);
    queries++;
    return (u64)t;
}

static Trace buildTrace(u64 a, u64 t) {
    Trace tr;
    tr.totalTime = t;
    u64 sq = 0;
    u64 cur = a;
    for (int i = 0; i < 60; i++) {
        tr.aval[i] = cur;
        uint8_t b1 = (uint8_t)(bitlen(cur) + 1);
        tr.abits1[i] = b1;
        sq += (u64)b1 * (u64)b1;
        cur = mod_mul(cur, cur, N);
    }
    tr.multTime = tr.totalTime - sq;
    return tr;
}

static u64 randomCoprimeA(std::mt19937_64 &rng) {
    std::uniform_int_distribution<u64> dist(2, N - 2);
    while (true) {
        u64 a = dist(rng);
        if (gcd_u64(a, N) == 1) return a;
    }
}

static u64 recover_d(const vector<Trace> &traces, int popcnt) {
    int K = (int)traces.size();
    vector<u64> r(K, 1);
    vector<long long> res(K);
    for (int k = 0; k < K; k++) res[k] = (long long)traces[k].multTime;

    u64 d = 1ULL; // d is odd (phi(n) even => gcd(d,phi)=1 implies odd)
    int ones = 1;

    // Apply i=0 (bit always 1)
    for (int k = 0; k < K; k++) {
        u64 xk = 2ULL * (u64)traces[k].abits1[0]; // (bits(1)+1)=2
        res[k] -= (long long)xk;
        r[k] = traces[k].aval[0];
    }

    for (int i = 1; i < 60; i++) {
        int remaining = 60 - i;
        int needOnes = popcnt - ones;

        int bit = 0;
        if (needOnes <= 0) {
            bit = 0;
        } else if (needOnes >= remaining) {
            bit = 1;
        } else {
            // compute regression slope b = cov(X,res)/var(X), where X = (bits(r)+1)*(bits(a_i)+1)
            long double sumX = 0, sumY = 0;
            vector<u64> X(K);
            for (int k = 0; k < K; k++) {
                u64 Ri = (u64)bitlen(r[k]) + 1;
                u64 Ai = (u64)traces[k].abits1[i];
                u64 xk = Ri * Ai;
                X[k] = xk;
                sumX += (long double)xk;
                sumY += (long double)res[k];
            }
            long double meanX = sumX / (long double)K;
            long double meanY = sumY / (long double)K;

            long double varX = 0, covXY = 0;
            for (int k = 0; k < K; k++) {
                long double dx = (long double)X[k] - meanX;
                long double dy = (long double)res[k] - meanY;
                varX += dx * dx;
                covXY += dx * dy;
            }

            long double b = 0;
            if (varX > 0) b = covXY / varX;

            bit = (b > 0.5L) ? 1 : 0;

            // non-negativity constraint: if choosing 1 makes any residual negative, it must be 0
            if (bit == 1) {
                for (int k = 0; k < K; k++) {
                    if (res[k] < (long long)X[k]) {
                        bit = 0;
                        break;
                    }
                }
            }

            // popcount feasibility
            if (bit == 0 && needOnes > remaining - 1) bit = 1;
            if (bit == 1 && needOnes < 1) bit = 0;
        }

        if (bit) {
            d |= (1ULL << i);
            ones++;
            for (int k = 0; k < K; k++) {
                u64 xk = ((u64)bitlen(r[k]) + 1) * (u64)traces[k].abits1[i];
                res[k] -= (long long)xk;
                r[k] = mod_mul(r[k], traces[k].aval[i], N);
            }
        }

        // quick sanity: residuals should not go negative if correct so far
        // (we don't early abort here; used only for debugging/fallback)
    }

    return d;
}

static bool verify_with_traces(u64 d, const vector<Trace> &traces) {
    for (const auto &tr : traces) {
        u64 a0 = tr.aval[0];
        u64 pred = simulate_time(a0, d, N);
        if (pred != tr.totalTime) return false;
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N)) return 0;

    std::mt19937_64 rng((u64)chrono::high_resolution_clock::now().time_since_epoch().count());

    // Factor N to get phi(N) for sanity checks
    vector<u64> fac;
    factor_rec(N, fac, rng);
    sort(fac.begin(), fac.end());
    u64 p = 0, q = 0;
    if (fac.size() >= 2) {
        p = fac[0];
        q = 1;
        for (size_t i = 1; i < fac.size(); i++) q *= fac[i];
    } else {
        // Shouldn't happen given the problem statement
        p = 1; q = N;
    }
    u64 phi = (u64)((u128)(p - 1) * (u128)(q - 1));

    // Query popcount using a=1: time = 60*4 + popcount*4 = 240 + 4*popcount
    u64 t1 = ask(1);
    if (t1 < 240 || ((t1 - 240) % 4) != 0) {
        // fallback (should not happen)
    }
    int popcnt = (int)((t1 - 240) / 4);

    vector<Trace> traces;
    vector<int> targets = {6000, 12000, 20000, 26000};

    u64 bestD = 1;

    for (int target : targets) {
        while ((int)traces.size() < target && queries < 29950) {
            u64 a = randomCoprimeA(rng);
            u64 t = ask(a);
            traces.push_back(buildTrace(a, t));
        }

        u64 d = recover_d(traces, popcnt);
        bestD = d;

        if (!(d >= 1 && d < phi)) continue;
        if (gcd_u64(d, phi) != 1) continue;
        if (__builtin_popcountll(d) != popcnt) continue;

        if (!verify_with_traces(d, traces)) continue;

        // extra validation (also add to traces if we continue)
        bool ok = true;
        for (int it = 0; it < 12 && queries < 29990; it++) {
            u64 a = randomCoprimeA(rng);
            u64 t = ask(a);
            Trace tr = buildTrace(a, t);
            traces.push_back(tr);
            if (simulate_time(a, d, N) != t) {
                ok = false;
                break;
            }
        }
        if (ok) {
            cout << "! " << d << "\n" << flush;
            return 0;
        }
    }

    cout << "! " << bestD << "\n" << flush;
    return 0;
}