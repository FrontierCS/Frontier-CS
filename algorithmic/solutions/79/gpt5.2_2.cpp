#include <bits/stdc++.h>
using namespace std;

static inline int bitsLen(uint64_t x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

static inline int mulTime(uint64_t x, uint64_t y) {
    return (bitsLen(x) + 1) * (bitsLen(y) + 1);
}

static inline uint64_t modMul(uint64_t a, uint64_t b, uint64_t mod) {
    return (uint64_t)((unsigned __int128)a * b % mod);
}

static long long squaringTime(uint64_t a, uint64_t n) {
    long long t = 0;
    uint64_t cur = a;
    for (int i = 0; i < 60; ++i) {
        t += mulTime(cur, cur);
        cur = modMul(cur, cur, n);
    }
    return t;
}

static long long simulateTime(uint64_t a, uint64_t d, uint64_t n) {
    long long t = 0;
    uint64_t r = 1;
    uint64_t cur = a;
    for (int i = 0; i < 60; ++i) {
        if ((d >> i) & 1ULL) {
            t += mulTime(r, cur);
            r = modMul(r, cur, n);
        }
        t += mulTime(cur, cur);
        cur = modMul(cur, cur, n);
    }
    return t;
}

struct Cand {
    uint64_t d = 1;
    shared_ptr<vector<uint64_t>> r;
    shared_ptr<vector<long long>> u;
    long double score = 0;
};

static bool reconstructD(const vector<uint64_t>& a0, const vector<long long>& ucond, uint64_t n, int beamWidth, uint64_t &dout) {
    const int N = (int)a0.size();
    if (N == 0) return false;

    vector<uint64_t> A(N);
    vector<uint8_t> BA(N);

    auto r0 = make_shared<vector<uint64_t>>(N);
    auto u0 = make_shared<vector<long long>>(N);

    for (int j = 0; j < N; ++j) {
        (*r0)[j] = a0[j];
        long long cost0 = 2LL * (bitsLen(a0[j]) + 1); // bit0 is always 1
        long long uu = ucond[j] - cost0;
        if (uu < 0) return false;
        (*u0)[j] = uu;
        A[j] = modMul(a0[j], a0[j], n);
        BA[j] = (uint8_t)(bitsLen(A[j]) + 1);
    }

    vector<Cand> beam;
    beam.reserve(beamWidth);
    beam.push_back(Cand{1, r0, u0, 0});

    vector<uint16_t> Xbuf(N);

    for (int i = 1; i < 60; ++i) {
        vector<Cand> next;
        next.reserve(beam.size() * 2);

        for (const Cand &cand : beam) {
            const auto &r = *cand.r;
            const auto &u = *cand.u;

            __int128 sumU = 0, sumX = 0, sumUX = 0, sumX2 = 0;
            bool allSameX = true;
            uint16_t firstX = 0;

            for (int j = 0; j < N; ++j) {
                uint16_t x = (uint16_t)((bitsLen(r[j]) + 1) * (int)BA[j]);
                Xbuf[j] = x;
                if (j == 0) firstX = x;
                else if (x != firstX) allSameX = false;

                sumU += ( __int128)u[j];
                sumX += ( __int128)x;
                sumUX += ( __int128)u[j] * ( __int128)x;
                sumX2 += ( __int128)x * ( __int128)x;
            }

            __int128 NN = ( __int128)N;
            __int128 Cn = NN * sumUX - sumU * sumX;       // cov numerator * N^2
            __int128 Vn = NN * sumX2 - sumX * sumX;       // varX numerator * N^2 (>=0)

            long double s0 = 0, s1 = 0;
            if (Vn != 0) {
                long double denom = (long double)Vn;
                s0 = fabsl((long double)Cn) / denom;
                s1 = fabsl((long double)(Cn - Vn)) / denom;
            } else {
                // X constant across traces; covariance doesn't help.
                // Keep both branches with no score penalty.
                (void)allSameX;
            }

            // child with bit i = 0
            Cand c0 = cand;
            c0.score += s0;
            next.push_back(std::move(c0));

            // child with bit i = 1 (only if feasible: u - x >= 0 for all)
            bool valid1 = true;
            auto r1 = make_shared<vector<uint64_t>>(N);
            auto u1 = make_shared<vector<long long>>(N);
            for (int j = 0; j < N; ++j) {
                long long uu = u[j] - (long long)Xbuf[j];
                if (uu < 0) { valid1 = false; break; }
                (*u1)[j] = uu;
                (*r1)[j] = modMul(r[j], A[j], n);
            }
            if (valid1) {
                Cand c1;
                c1.d = cand.d | (1ULL << i);
                c1.r = std::move(r1);
                c1.u = std::move(u1);
                c1.score = cand.score + s1;
                next.push_back(std::move(c1));
            }
        }

        sort(next.begin(), next.end(), [](const Cand& a, const Cand& b) {
            if (a.score != b.score) return a.score < b.score;
            return a.d < b.d;
        });
        if ((int)next.size() > beamWidth) next.resize(beamWidth);
        beam.swap(next);

        // update A, BA for next iteration
        for (int j = 0; j < N; ++j) {
            A[j] = modMul(A[j], A[j], n);
            BA[j] = (uint8_t)(bitsLen(A[j]) + 1);
        }
    }

    // find a candidate with all residuals exactly 0
    for (const auto &cand : beam) {
        const auto &u = *cand.u;
        bool ok = true;
        for (int j = 0; j < N; ++j) {
            if (u[j] != 0) { ok = false; break; }
        }
        if (ok) {
            dout = cand.d;
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

    const int MAXQ = 30000;
    int usedQ = 0;

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());
    auto randA = [&]() -> uint64_t {
        while (true) {
            uint64_t a = (n == 0 ? 0 : (rng() % n));
            if (a > 1 && a < n) return a;
        }
    };

    vector<uint64_t> a0;
    vector<long long> ucond;

    int target = 6000;
    while (true) {
        while ((int)a0.size() < target && usedQ < MAXQ - 10) {
            uint64_t a = randA();
            cout << "? " << a << "\n" << flush;
            long long t;
            if (!(cin >> t)) return 0;
            ++usedQ;

            long long s = squaringTime(a, n);
            long long uc = t - s;
            a0.push_back(a);
            ucond.push_back(uc);
        }

        bool solved = false;
        uint64_t d = 1;

        for (int bw : {8, 16, 32, 64, 128}) {
            if (reconstructD(a0, ucond, n, bw, d)) {
                // verify with a few extra queries
                bool ok = true;
                for (int v = 0; v < 3 && usedQ < MAXQ; ++v) {
                    uint64_t a = randA();
                    cout << "? " << a << "\n" << flush;
                    long long t;
                    if (!(cin >> t)) return 0;
                    ++usedQ;
                    long long expT = simulateTime(a, d, n);
                    if (expT != t) { ok = false; break; }
                }
                if (ok) {
                    cout << "! " << d << "\n" << flush;
                    return 0;
                }
            }
        }

        if (usedQ >= MAXQ - 10) {
            cout << "! " << 1 << "\n" << flush;
            return 0;
        }
        target = min(MAXQ - 10, target * 2);
    }
}