#include <bits/stdc++.h>
using namespace std;

static uint64_t rng_state = 88172645463325252ull;
static inline uint64_t rng() {
    uint64_t x = rng_state;
    x ^= x << 7;
    x ^= x >> 9;
    rng_state = x;
    return x;
}

static inline int bits64(uint64_t x) {
    if (!x) return 0;
    return 64 - __builtin_clzll(x);
}

uint64_t MODN;

static inline unsigned long long simulateTime(uint64_t a, uint64_t d) {
    unsigned long long t = 0;
    uint64_t r = 1;
    for (int i = 0; i < 60; ++i) {
        int ba = bits64(a);
        if (d & (1ULL << i)) {
            int br = bits64(r);
            t += (unsigned long long)(br + 1) * (unsigned long long)(ba + 1);
            unsigned __int128 prod = (unsigned __int128)r * (unsigned __int128)a;
            r = (uint64_t)(prod % MODN);
        }
        t += (unsigned long long)(ba + 1) * (unsigned long long)(ba + 1);
        unsigned __int128 prod2 = (unsigned __int128)a * (unsigned __int128)a;
        a = (uint64_t)(prod2 % MODN);
    }
    return t;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    unsigned long long n;
    if (!(cin >> n)) return 0;
    MODN = n;

    // Query a = 0 to get Hamming weight w of d.
    cout << "? " << 0 << "\n" << flush;
    long long t0;
    if (!(cin >> t0)) return 0;
    int w = (int)(t0 - 61);
    if (w < 0) w = 0;
    if (w > 59) w = 59;

    const int Q = 190;
    vector<uint64_t> a(Q);
    vector<long long> obs(Q);

    for (int i = 0; i < Q; ++i) {
        uint64_t ai;
        while (true) {
            ai = 2 + (uint64_t)(rng() % (n - 2));
            if (ai >= 2 && ai < n) break;
        }
        a[i] = ai;
        cout << "? " << ai << "\n" << flush;
        cin >> obs[i];
    }

    // Stage sizes (number of queries used in each optimization stage)
    vector<int> Rs;
    int r = 8;
    while (r < Q) {
        Rs.push_back(r);
        r <<= 1;
    }
    Rs.push_back(Q);
    int S = (int)Rs.size();

    const int TOT_EVAL = 120000;
    long long sumR = 0;
    for (int x : Rs) sumR += x;
    vector<int> stageIter(S);
    for (int i = 0; i < S; ++i) {
        stageIter[i] = (int)((long long)TOT_EVAL * Rs[i] / sumR);
        if (stageIter[i] < 1) stageIter[i] = 1;
    }

    auto randomCandidate = [&](int wbits) -> uint64_t {
        uint64_t d = 0;
        array<int, 60> pos;
        for (int i = 0; i < 60; ++i) pos[i] = i;
        for (int i = 0; i < 60; ++i) {
            int j = i + (int)(rng() % (60 - i));
            swap(pos[i], pos[j]);
        }
        if (wbits > 60) wbits = 60;
        for (int k = 0; k < wbits; ++k) d |= (1ULL << pos[k]);
        return d;
    };

    auto evalError = [&](uint64_t d, int R) -> unsigned long long {
        unsigned long long err = 0;
        for (int q = 0; q < R; ++q) {
            unsigned long long pred = simulateTime(a[q], d);
            long long diff = (long long)pred - obs[q];
            err += (unsigned long long)(diff * diff);
        }
        return err;
    };

    uint64_t current_d = 0;
    unsigned long long current_err = 0;
    bool first_stage = true;

    for (int s = 0; s < S; ++s) {
        int Rcur = Rs[s];
        long long budget = stageIter[s];

        if (first_stage) {
            const int INIT_CAND = 200;
            unsigned long long best_err = ULLONG_MAX;
            uint64_t best_d = 0;
            long long evalCount = 0;

            for (int k = 0; k < INIT_CAND && evalCount < budget / 2; ++k) {
                uint64_t dtmp = randomCandidate(w);
                unsigned long long e = evalError(dtmp, Rcur);
                ++evalCount;
                if (e < best_err) {
                    best_err = e;
                    best_d = dtmp;
                }
            }
            if (best_err == ULLONG_MAX) {
                best_d = randomCandidate(w);
                best_err = evalError(best_d, Rcur);
                ++evalCount;
            }
            current_d = best_d;
            current_err = best_err;

            uint64_t best_stage_d = current_d;
            unsigned long long best_stage_err = current_err;

            while (evalCount < budget) {
                if (rng() % 2000 == 0) {
                    uint64_t dtmp = randomCandidate(w);
                    unsigned long long e = evalError(dtmp, Rcur);
                    ++evalCount;
                    if (e < current_err) {
                        current_err = e;
                        current_d = dtmp;
                    }
                    if (e < best_stage_err) {
                        best_stage_err = e;
                        best_stage_d = dtmp;
                    }
                    continue;
                }

                int p1, p0;
                do { p1 = (int)(rng() % 60); } while (((current_d >> p1) & 1ULL) == 0ULL);
                do { p0 = (int)(rng() % 60); } while (((current_d >> p0) & 1ULL) == 1ULL);
                uint64_t cand = current_d ^ (1ULL << p1) ^ (1ULL << p0);
                unsigned long long e = evalError(cand, Rcur);
                ++evalCount;
                if (e <= current_err) {
                    current_err = e;
                    current_d = cand;
                    if (e < best_stage_err) {
                        best_stage_err = e;
                        best_stage_d = cand;
                    }
                }
            }

            current_d = best_stage_d;
            current_err = best_stage_err;
            first_stage = false;
        } else {
            long long evalCount = 0;
            current_err = evalError(current_d, Rcur);
            ++evalCount;
            uint64_t best_stage_d = current_d;
            unsigned long long best_stage_err = current_err;

            while (evalCount < budget) {
                if (rng() % 2000 == 0) {
                    uint64_t dtmp = randomCandidate(w);
                    unsigned long long e = evalError(dtmp, Rcur);
                    ++evalCount;
                    if (e < current_err) {
                        current_err = e;
                        current_d = dtmp;
                    }
                    if (e < best_stage_err) {
                        best_stage_err = e;
                        best_stage_d = dtmp;
                    }
                    continue;
                }

                int p1, p0;
                do { p1 = (int)(rng() % 60); } while (((current_d >> p1) & 1ULL) == 0ULL);
                do { p0 = (int)(rng() % 60); } while (((current_d >> p0) & 1ULL) == 1ULL);
                uint64_t cand = current_d ^ (1ULL << p1) ^ (1ULL << p0);
                unsigned long long e = evalError(cand, Rcur);
                ++evalCount;
                if (e <= current_err) {
                    current_err = e;
                    current_d = cand;
                    if (e < best_stage_err) {
                        best_stage_err = e;
                        best_stage_d = cand;
                    }
                }
                if (best_stage_err == 0) break;
            }

            current_d = best_stage_d;
            current_err = best_stage_err;
        }
    }

    // Final refinement on all queries if needed
    unsigned long long final_err = evalError(current_d, Q);
    if (final_err != 0) {
        int Rcur = Q;
        long long extraBudget = 40000;
        long long evalCount = 0;
        unsigned long long best_stage_err = final_err;
        uint64_t best_stage_d = current_d;
        unsigned long long cur_err = final_err;
        uint64_t cur_d = current_d;

        while (evalCount < extraBudget && best_stage_err != 0) {
            if (rng() % 2000 == 0) {
                uint64_t dtmp = randomCandidate(w);
                unsigned long long e = evalError(dtmp, Rcur);
                ++evalCount;
                if (e < cur_err) {
                    cur_err = e;
                    cur_d = dtmp;
                }
                if (e < best_stage_err) {
                    best_stage_err = e;
                    best_stage_d = dtmp;
                }
                continue;
            }

            int p1, p0;
            do { p1 = (int)(rng() % 60); } while (((cur_d >> p1) & 1ULL) == 0ULL);
            do { p0 = (int)(rng() % 60); } while (((cur_d >> p0) & 1ULL) == 1ULL);
            uint64_t cand = cur_d ^ (1ULL << p1) ^ (1ULL << p0);
            unsigned long long e = evalError(cand, Rcur);
            ++evalCount;
            if (e <= cur_err) {
                cur_err = e;
                cur_d = cand;
                if (e < best_stage_err) {
                    best_stage_err = e;
                    best_stage_d = cand;
                }
            }
        }
        current_d = best_stage_d;
    }

    cout << "! " << current_d << "\n" << flush;
    return 0;
}