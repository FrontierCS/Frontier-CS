#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;
using i64 = long long;

// Compute number of bits in x as ceil(log2(x+1)) which equals usual bit length for x>0, and 0 for x=0
static inline int bits(u64 x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

// modular multiplication (a*b) % mod using 128-bit to avoid overflow
static inline u64 mul_mod(u64 a, u64 b, u64 mod) {
    return (u64)((u128)a * (u128)b % (u128)mod);
}

// Ask the judge for time of modPow(a, d, n)
u64 ask(u64 a) {
    cout << "? " << a << endl;
    cout.flush();
    u64 t;
    if (!(cin >> t)) exit(0);
    return t;
}

// Output the final answer
void answer(u64 d) {
    cout << "! " << d << endl;
    cout.flush();
}

struct Sample {
    u64 a;
    array<u64, 60> ai;      // ai[i] = a^(2^i) mod n
    array<uint8_t, 60> bl;  // bits(ai[i])
    u64 S;                  // sum of squares costs
    u64 T;                  // measured total time
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    u64 n;
    if (!(cin >> n)) return 0;

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    auto compute_S_ai = [&](u64 a) {
        Sample s;
        s.a = a;
        u64 cur = a;
        s.S = 0;
        for (int i = 0; i < 60; ++i) {
            s.ai[i] = cur;
            int b = bits(cur);
            s.bl[i] = (uint8_t)b;
            u64 c = (u64)(b + 1);
            s.S += c * c;
            cur = mul_mod(cur, cur, n);
        }
        return s;
    };

    auto costMul = [&](u64 x, u64 y) -> u64 {
        return (u64)( (u64)(bits(x) + 1) * (u64)(bits(y) + 1) );
    };

    // Special queries to get popcount(d) and bit 0
    Sample s1 = compute_S_ai(1);
    s1.T = ask(1);
    u64 H = 0;
    if (s1.S <= s1.T) {
        H = (s1.T - s1.S) / 4; // since each 'if' multiply with a=1 costs (1+1)*(1+1)=4
    }

    Sample sm1 = compute_S_ai(n - 1);
    sm1.T = ask(n - 1);
    u64 Fm1 = sm1.T - sm1.S;
    u64 F1 = s1.T - s1.S;
    bool d0 = false;
    // If d0==0 then F(-1)=F(1)=4*H, else F(-1)=2*(bits(n-1)+1)*H
    u64 twoBn1 = 2ull * (u64)(bits(n - 1) + 1);
    if (H == 0) {
        d0 = false;
    } else {
        if (Fm1 == F1) d0 = false;
        else d0 = (Fm1 == twoBn1 * H);
    }

    // Sample a set of random 'a' values (excluding 1 and n-1 to avoid duplication)
    const int maxQueries = 30000;
    vector<Sample> samples;
    samples.reserve(4096);

    // Include the two special samples in dataset to strengthen constraints
    samples.push_back(s1);
    samples.push_back(sm1);

    // Initial number of random samples
    int initialN = 1200;

    auto add_random_samples = [&](int cnt) {
        unordered_set<u64> used;
        used.reserve(samples.size() + cnt + 4);
        for (auto &s : samples) used.insert(s.a);
        used.insert(0); // avoid 0 for now
        while (cnt--) {
            u64 a;
            int tries = 0;
            do {
                a = (u64)(rng() % n);
                if (++tries > 1000) a = (a % (n - 2)) + 2;
            } while (used.count(a));
            used.insert(a);
            Sample s = compute_S_ai(a);
            s.T = ask(a);
            samples.push_back(move(s));
        }
    };

    int usedQueries = 2; // for 1 and n-1

    int addCnt = min(initialN, maxQueries - usedQueries);
    add_random_samples(addCnt);
    usedQueries += addCnt;

    // d vector initial guess
    array<int, 60> d{};
    d.fill(0);
    d[0] = d0 ? 1 : 0;

    // Precompute predicted contributions and residuals machinery
    int S = (int)samples.size();

    // Function to compute predicted F (extra cost due to if-multiplications) for a sample s with current d
    auto compute_F_for_sample = [&](const Sample &s, const array<int,60> &dloc) -> u64 {
        u64 r = 1;
        u64 F = 0;
        for (int i = 0; i < 60; ++i) {
            if (dloc[i]) {
                F += (u64)( (u64)(bits(r) + 1) * (u64)(s.bl[i] + 1) );
                r = mul_mod(r, s.ai[i], n);
            }
        }
        return F;
    };

    // Compute full predicted times and residuals
    vector<u64> Fpred(S, 0);
    vector<long long> E(S, 0); // residuals can be negative -> signed
    __int128 SSE = 0;

    auto recompute_pred_and_residuals = [&]() {
        SSE = 0;
        for (int si = 0; si < S; ++si) {
            u64 F = compute_F_for_sample(samples[si], d);
            Fpred[si] = F;
            long long e = (long long)(samples[si].T - (samples[si].S + F));
            E[si] = e;
            SSE += ( (__int128)e * (__int128)e );
        }
    };

    recompute_pred_and_residuals();

    // If already perfect, output d
    auto d_to_u64 = [&]() {
        u64 val = 0;
        for (int i = 59; i >= 0; --i) {
            val = (val << 1) | (u64)d[i];
        }
        return val;
    };

    if (SSE == 0) {
        answer(d_to_u64());
        return 0;
    }

    // Helper: precompute rprefix[j][si] = r after processing bits [0..j-1] under current d
    vector<array<u64, 61>> rprefix; // for each sample, 61 entries
    rprefix.resize(S);

    auto recompute_rprefix = [&]() {
        for (int si = 0; si < S; ++si) {
            rprefix[si][0] = 1;
            u64 r = 1;
            for (int j = 0; j < 60; ++j) {
                if (d[j]) r = mul_mod(r, samples[si].ai[j], n);
                rprefix[si][j+1] = r;
            }
        }
    };

    recompute_rprefix();

    // Function to compute deltaF for toggling bit i for sample si
    auto deltaF_toggle_bit_sample = [&](int i, int si) -> long long {
        const Sample &s = samples[si];
        u64 r_old_before_i = rprefix[si][i]; // r before step i
        long long delta = 0;
        bool oldbit = d[i] != 0;

        if (!oldbit) {
            // 0 -> 1
            // step i cost added
            delta += (long long)((u64)(bits(r_old_before_i) + 1) * (u64)(s.bl[i] + 1));
            u64 r_new = mul_mod(r_old_before_i, s.ai[i], n); // r after step i in new scenario
            // propagate through j > i
            for (int j = i + 1; j < 60; ++j) {
                if (!d[j]) continue;
                // old cost at step j:
                u64 r_old_before_j = rprefix[si][j];
                u64 oldc = (u64)( (u64)(bits(r_old_before_j) + 1) * (u64)(s.bl[j] + 1) );
                u64 newc = (u64)( (u64)(bits(r_new) + 1) * (u64)(s.bl[j] + 1) );
                delta += (long long)(newc - oldc);
                r_new = mul_mod(r_new, s.ai[j], n);
            }
        } else {
            // 1 -> 0
            // step i cost removed
            delta -= (long long)((u64)(bits(r_old_before_i) + 1) * (u64)(s.bl[i] + 1));
            u64 r_new = r_old_before_i; // without multiplying at i
            // propagate
            for (int j = i + 1; j < 60; ++j) {
                if (!d[j]) continue;
                // old cost at step j:
                u64 r_old_before_j = rprefix[si][j];
                u64 oldc = (u64)( (u64)(bits(r_old_before_j) + 1) * (u64)(s.bl[j] + 1) );
                u64 newc = (u64)( (u64)(bits(r_new) + 1) * (u64)(s.bl[j] + 1) );
                delta += (long long)(newc - oldc);
                r_new = mul_mod(r_new, s.ai[j], n);
            }
        }
        return delta;
    };

    // Greedy coordinate descent with occasional sampling expansion if stuck
    int max_outer_rounds = 6;
    bool solved = false;

    for (int round = 0; round < max_outer_rounds && !solved; ++round) {
        // Inner iterations
        int max_iter = 800; // per round
        bool improved = true;

        for (int iter = 0; iter < max_iter; ++iter) {
            // Evaluate all 60 bits for best improvement
            __int128 bestDeltaSSE = 0; // negative improves
            int bestBit = -1;
            vector<long long> tempDeltaF; // reuse later if flipping
            vector<long long> bestDeltaF; bestDeltaF.clear();

            for (int i = 0; i < 60; ++i) {
                // Compute deltaF_s for all samples
                tempDeltaF.assign(0, 0); // clear
                long long sumE_delta = 0;
                __int128 sum_delta2 = 0;

                // We will accumulate in a loop; to avoid reallocation, compute on the fly
                for (int si = 0; si < S; ++si) {
                    long long dF = deltaF_toggle_bit_sample(i, si);
                    // E and dF are signed 64-bit range safe
                    sumE_delta += E[si] * dF;
                    sum_delta2 += ( (__int128)dF * (__int128)dF );
                }

                __int128 deltaSSE = -2 * (__int128)sumE_delta + sum_delta2;
                if (deltaSSE < bestDeltaSSE) {
                    bestDeltaSSE = deltaSSE;
                    bestBit = i;
                }
            }

            if (bestBit == -1 || bestDeltaSSE >= 0) {
                improved = false;
                break;
            }

            // Apply flip
            // Recompute deltaF_s for bestBit and update E, Fpred
            for (int si = 0; si < S; ++si) {
                long long dF = deltaF_toggle_bit_sample(bestBit, si);
                Fpred[si] += dF;
                E[si] -= dF;
            }
            d[bestBit] ^= 1;
            SSE += bestDeltaSSE;
            // Recompute rprefix as d changed
            recompute_rprefix();

            if (SSE == 0) {
                solved = true;
                break;
            }
        }

        if (!solved && !improved) {
            // If stuck, try to add more samples (if possible) to escape local minima
            if (usedQueries >= maxQueries) break;
            int addMore = min(2000, maxQueries - usedQueries);
            add_random_samples(addMore);
            usedQueries += addMore;
            S = (int)samples.size();
            // Resize arrays
            Fpred.assign(S, 0);
            E.assign(S, 0);
            recompute_pred_and_residuals();
            rprefix.resize(S);
            recompute_rprefix();
            if (SSE == 0) {
                solved = true;
                break;
            }
        }
    }

    // If still not solved, do a final clean-up with brute per-bit refinement using full recomputation
    if (!solved) {
        // Try simple forward pass setting bits by testing which choice yields smaller SSE when flipped
        bool changed = true;
        int tries = 0;
        while (!solved && changed && tries < 5) {
            changed = false;
            ++tries;
            for (int i = 0; i < 60; ++i) {
                // Compute delta SSE for toggling bit i
                long long sumE_delta = 0;
                __int128 sum_delta2 = 0;
                for (int si = 0; si < S; ++si) {
                    long long dF = deltaF_toggle_bit_sample(i, si);
                    sumE_delta += E[si] * dF;
                    sum_delta2 += ( (__int128)dF * (__int128)dF );
                }
                __int128 deltaSSE = -2 * (__int128)sumE_delta + sum_delta2;
                if (deltaSSE < 0) {
                    // apply
                    for (int si = 0; si < S; ++si) {
                        long long dF = deltaF_toggle_bit_sample(i, si);
                        Fpred[si] += dF;
                        E[si] -= dF;
                    }
                    d[i] ^= 1;
                    SSE += deltaSSE;
                    recompute_rprefix();
                    changed = true;
                }
                if (SSE == 0) { solved = true; break; }
            }
        }
    }

    // As a last resort, ensure popcount matches H by small adjustments if needed
    if (!solved) {
        int curH = 0;
        for (int i = 0; i < 60; ++i) curH += d[i];
        // If too many ones, try to remove some greedily if it doesn't increase SSE
        while (!solved && curH > (int)H) {
            __int128 bestDelta = 0;
            int best = -1;
            for (int i = 0; i < 60; ++i) if (d[i]) {
                long long sumE_delta = 0;
                __int128 sum_delta2 = 0;
                for (int si = 0; si < S; ++si) {
                    long long dF = deltaF_toggle_bit_sample(i, si);
                    sumE_delta += E[si] * dF;
                    sum_delta2 += ( (__int128)dF * (__int128)dF );
                }
                __int128 deltaSSE = -2 * (__int128)sumE_delta + sum_delta2;
                if (deltaSSE < bestDelta) { bestDelta = deltaSSE; best = i; }
            }
            if (best == -1 || bestDelta >= 0) break;
            for (int si = 0; si < S; ++si) {
                long long dF = deltaF_toggle_bit_sample(best, si);
                Fpred[si] += dF;
                E[si] -= dF;
            }
            d[best] ^= 1;
            SSE += bestDelta;
            recompute_rprefix();
            curH--;
            if (SSE == 0) { solved = true; break; }
        }
        while (!solved && curH < (int)H) {
            __int128 bestDelta = 0;
            int best = -1;
            for (int i = 0; i < 60; ++i) if (!d[i]) {
                long long sumE_delta = 0;
                __int128 sum_delta2 = 0;
                for (int si = 0; si < S; ++si) {
                    long long dF = deltaF_toggle_bit_sample(i, si);
                    sumE_delta += E[si] * dF;
                    sum_delta2 += ( (__int128)dF * (__int128)dF );
                }
                __int128 deltaSSE = -2 * (__int128)sumE_delta + sum_delta2;
                if (deltaSSE < bestDelta) { bestDelta = deltaSSE; best = i; }
            }
            if (best == -1 || bestDelta >= 0) break;
            for (int si = 0; si < S; ++si) {
                long long dF = deltaF_toggle_bit_sample(best, si);
                Fpred[si] += dF;
                E[si] -= dF;
            }
            d[best] ^= 1;
            SSE += bestDelta;
            recompute_rprefix();
            curH++;
            if (SSE == 0) { solved = true; break; }
        }
    }

    // Output whatever we have (if not perfect, still attempt best guess)
    answer(d_to_u64());
    return 0;
}