#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct CustomHashLL {
    size_t operator()(long long x) const noexcept {
        return (size_t)splitmix64((uint64_t)x);
    }
};

static inline unsigned long long uabsll(long long x) {
    return x < 0 ? (unsigned long long)(-x) : (unsigned long long)x;
}

struct Mask128 {
    uint64_t lo = 0, hi = 0;
};
static inline void setBit(Mask128 &m, int pos) {
    if (pos < 64) m.lo |= (1ULL << pos);
    else m.hi |= (1ULL << (pos - 64));
}
static inline bool getBit(const Mask128 &m, int pos) {
    if (pos < 64) return (m.lo >> pos) & 1ULL;
    return (m.hi >> (pos - 64)) & 1ULL;
}

struct State {
    long long sum;
    Mask128 mask;
};

struct ModDP {
    int M = 0;
    int W = 0;
    uint64_t lastMask = ~0ULL;
    vector<uint64_t> dp;     // (n+1)*W
    vector<uint64_t> tmpL, tmpR, tmpRot;

    ModDP() = default;
    ModDP(int mod, int n) { init(mod, n); }

    void init(int mod, int n) {
        M = mod;
        W = (M + 63) / 64;
        int rem = M % 64;
        lastMask = (rem == 0) ? ~0ULL : ((1ULL << rem) - 1ULL);
        dp.assign((n + 1) * W, 0ULL);
        tmpL.assign(W, 0ULL);
        tmpR.assign(W, 0ULL);
        tmpRot.assign(W, 0ULL);
    }

    void shift_left(const uint64_t *src, uint64_t *dst, int sh) {
        if (sh == 0) {
            memcpy(dst, src, (size_t)W * sizeof(uint64_t));
            dst[W - 1] &= lastMask;
            return;
        }
        int wordSh = sh / 64;
        int bitSh = sh % 64;
        if (bitSh == 0) {
            for (int i = W - 1; i >= 0; --i) {
                int j = i - wordSh;
                dst[i] = (j >= 0) ? src[j] : 0ULL;
            }
        } else {
            for (int i = W - 1; i >= 0; --i) {
                uint64_t val = 0ULL;
                int j = i - wordSh;
                if (j >= 0) {
                    val = src[j] << bitSh;
                    if (j - 1 >= 0) val |= (src[j - 1] >> (64 - bitSh));
                }
                dst[i] = val;
            }
        }
        dst[W - 1] &= lastMask;
    }

    void shift_right(const uint64_t *src, uint64_t *dst, int sh) {
        if (sh == 0) {
            memcpy(dst, src, (size_t)W * sizeof(uint64_t));
            dst[W - 1] &= lastMask;
            return;
        }
        int wordSh = sh / 64;
        int bitSh = sh % 64;
        if (bitSh == 0) {
            for (int i = 0; i < W; ++i) {
                int j = i + wordSh;
                dst[i] = (j < W) ? src[j] : 0ULL;
            }
        } else {
            for (int i = 0; i < W; ++i) {
                uint64_t val = 0ULL;
                int j = i + wordSh;
                if (j < W) {
                    val = src[j] >> bitSh;
                    if (j + 1 < W) val |= (src[j + 1] << (64 - bitSh));
                }
                dst[i] = val;
            }
        }
        dst[W - 1] &= lastMask;
    }

    void rotate_left(const uint64_t *src, uint64_t *dst, int sh) {
        sh %= M;
        if (sh < 0) sh += M;
        if (sh == 0) {
            memcpy(dst, src, (size_t)W * sizeof(uint64_t));
            dst[W - 1] &= lastMask;
            return;
        }
        shift_left(src, tmpL.data(), sh);
        shift_right(src, tmpR.data(), M - sh);
        for (int i = 0; i < W; ++i) dst[i] = tmpL[i] | tmpR[i];
        dst[W - 1] &= lastMask;
    }

    void build(const vector<long long> &vals) {
        int n = (int)vals.size();
        // dp[n] has only residue 0 reachable (empty set)
        dp[n * W + 0] = 1ULL;
        for (int i = n - 1; i >= 0; --i) {
            const uint64_t *nxt = &dp[(i + 1) * W];
            uint64_t *cur = &dp[i * W];
            int sh = (int)(vals[i] % M);
            rotate_left(nxt, tmpRot.data(), sh);
            for (int w = 0; w < W; ++w) cur[w] = nxt[w] | tmpRot[w];
            cur[W - 1] &= lastMask;
        }
    }

    inline bool possible(int pos, long long residual) const {
        int r = (int)(residual % M);
        int w = r >> 6;
        int b = r & 63;
        return (dp[pos * W + w] >> b) & 1ULL;
    }
};

static bool exact_mitm_all(const vector<long long> &a, long long T, Mask128 &outMask) {
    int n = (int)a.size();
    int n1 = n / 2;
    int n2 = n - n1;

    int sz1 = 1 << n1;
    int sz2 = 1 << n2;

    vector<long long> sum1(sz1), sum2(sz2);
    vector<uint32_t> mask2(sz2);

    sum1[0] = 0;
    for (int m = 1; m < sz1; ++m) {
        int b = __builtin_ctz((unsigned)m);
        int pm = m & (m - 1);
        sum1[m] = sum1[pm] + a[b];
    }
    sum2[0] = 0;
    mask2[0] = 0;
    for (int m = 1; m < sz2; ++m) {
        int b = __builtin_ctz((unsigned)m);
        int pm = m & (m - 1);
        sum2[m] = sum2[pm] + a[n1 + b];
        mask2[m] = (uint32_t)m;
    }

    vector<int> ord2(sz2);
    iota(ord2.begin(), ord2.end(), 0);
    sort(ord2.begin(), ord2.end(), [&](int i, int j) {
        return sum2[i] < sum2[j];
    });

    long long bestSum = 0;
    uint64_t bestLo = 0, bestHi = 0;
    unsigned long long bestErr = ULLONG_MAX;

    vector<long long> sum2s(sz2);
    for (int i = 0; i < sz2; ++i) sum2s[i] = sum2[ord2[i]];

    for (int m = 0; m < sz1; ++m) {
        long long s1 = sum1[m];
        long long need = T - s1;
        auto it = lower_bound(sum2s.begin(), sum2s.end(), need);
        for (int k = 0; k < 2; ++k) {
            if (it == sum2s.end() && k == 0) continue;
            if (it == sum2s.begin() && k == 1) continue;
            long long s2 = 0;
            uint32_t m2 = 0;
            if (k == 0) {
                int idx = (int)(it - sum2s.begin());
                int real = ord2[idx];
                s2 = sum2[real];
                m2 = mask2[real];
            } else {
                int idx = (int)(it - sum2s.begin()) - 1;
                int real = ord2[idx];
                s2 = sum2[real];
                m2 = mask2[real];
            }
            long long s = s1 + s2;
            unsigned long long err = uabsll(s - T);
            if (err < bestErr) {
                bestErr = err;
                bestSum = s;
                bestLo = 0; bestHi = 0;
                // first half mask m (<=22)
                for (int i = 0; i < n1; ++i) if ((m >> i) & 1) setBit(outMask, i);
                // second half
                for (int i = 0; i < n2; ++i) if ((m2 >> i) & 1) setBit(outMask, n1 + i);
                // overwrite outMask properly
                outMask.lo = bestLo; outMask.hi = bestHi; // but we haven't set bestLo/Hi from above.
                // redo:
                outMask.lo = 0; outMask.hi = 0;
                for (int i = 0; i < n1; ++i) if ((m >> i) & 1) setBit(outMask, i);
                for (int i = 0; i < n2; ++i) if ((m2 >> i) & 1) setBit(outMask, n1 + i);
                if (bestErr == 0) return true;
            }
        }
    }
    (void)bestSum;
    return bestErr == 0;
}

struct DFSSolver {
    const vector<long long> *valsPtr = nullptr;
    int n = 0;
    long long T = 0;
    vector<long long> suffixSum;
    vector<char> choose;
    int pos0 = 0;

    // Tail precompute for fixed tail segment [pos0..n)
    int tailSize = 0;
    int ta = 0, tb = 0;
    vector<long long> tailASums;
    unordered_map<long long, uint32_t, CustomHashLL> tailBMap;

    const ModDP *dp1 = nullptr;
    const ModDP *dp2 = nullptr;

    chrono::steady_clock::time_point start;
    double timeLimitSec = 1.5;
    uint64_t nodes = 0;
    bool timeout = false;

    DFSSolver() = default;

    void init(const vector<long long> &vals, long long target, const ModDP &m1, const ModDP &m2,
              int tailSz, double tlim, chrono::steady_clock::time_point st) {
        valsPtr = &vals;
        n = (int)vals.size();
        T = target;
        dp1 = &m1;
        dp2 = &m2;
        start = st;
        timeLimitSec = tlim;
        timeout = false;
        nodes = 0;

        choose.assign(n, 0);
        suffixSum.assign(n + 1, 0);
        for (int i = n - 1; i >= 0; --i) suffixSum[i] = suffixSum[i + 1] + vals[i];

        tailSize = min(tailSz, n);
        pos0 = n - tailSize;
        ta = tailSize / 2;
        tb = tailSize - ta;

        tailASums.assign(1 << ta, 0);
        for (int m = 1; m < (1 << ta); ++m) {
            int b = __builtin_ctz((unsigned)m);
            int pm = m & (m - 1);
            tailASums[m] = tailASums[pm] + vals[pos0 + b];
        }

        tailBMap.clear();
        tailBMap.reserve((size_t)(1 << tb) * 2);
        vector<long long> sumB(1 << tb, 0);
        for (int m = 1; m < (1 << tb); ++m) {
            int b = __builtin_ctz((unsigned)m);
            int pm = m & (m - 1);
            sumB[m] = sumB[pm] + vals[pos0 + ta + b];
        }
        for (int m = 0; m < (1 << tb); ++m) {
            // keep first mask for a given sum
            tailBMap.emplace(sumB[m], (uint32_t)m);
        }
    }

    inline bool time_exceeded() {
        if (timeout) return true;
        double el = chrono::duration<double>(chrono::steady_clock::now() - start).count();
        if (el > timeLimitSec) {
            timeout = true;
            return true;
        }
        return false;
    }

    inline bool mod_ok(int pos, long long residual) const {
        return dp1->possible(pos, residual) && dp2->possible(pos, residual);
    }

    bool tail_match(long long residual) {
        // Enumerate all sums of tailA (size 2^ta) and lookup in tailBMap.
        // Time checks inside the loop.
        for (int mA = 0; mA < (1 << ta); ++mA) {
            if ((mA & 1023) == 0) {
                if (time_exceeded()) return false;
            }
            long long need = residual - tailASums[mA];
            if (need < 0) continue;
            auto it = tailBMap.find(need);
            if (it == tailBMap.end()) continue;

            uint32_t mB = it->second;
            // Fill tail bits.
            for (int i = 0; i < ta; ++i) choose[pos0 + i] = (mA >> i) & 1;
            for (int j = 0; j < tb; ++j) choose[pos0 + ta + j] = (mB >> j) & 1;
            return true;
        }
        return false;
    }

    bool dfs(int pos, long long residual) {
        if ((nodes++ & 8191ULL) == 0ULL) {
            if (time_exceeded()) return false;
        }
        if (timeout) return false;
        if (residual == 0) {
            for (int i = pos; i < pos0; ++i) choose[i] = 0;
            for (int i = pos0; i < n; ++i) choose[i] = 0;
            return true;
        }
        if (pos == pos0) {
            if (residual < 0 || residual > suffixSum[pos]) return false;
            return tail_match(residual);
        }
        if (residual < 0) return false;
        if (residual > suffixSum[pos]) return false;
        if (!mod_ok(pos, residual)) return false;

        const auto &vals = *valsPtr;
        long long v = vals[pos];
        long long remAfter = suffixSum[pos + 1];

        if (residual > remAfter) {
            // Must take v
            choose[pos] = 1;
            return dfs(pos + 1, residual - v);
        }
        if (v > residual) {
            // Can't take
            choose[pos] = 0;
            return dfs(pos + 1, residual);
        }

        bool canTake = (residual - v >= 0) && (residual - v <= remAfter) && mod_ok(pos + 1, residual - v);
        bool canSkip = (residual <= remAfter) && mod_ok(pos + 1, residual);

        // Simple heuristic: try take first.
        if (canTake) {
            choose[pos] = 1;
            if (dfs(pos + 1, residual - v)) return true;
        }
        if (canSkip) {
            choose[pos] = 0;
            if (dfs(pos + 1, residual)) return true;
        }
        return false;
    }
};

static vector<char> beam_closest(const vector<long long> &a, const vector<int> &perm, long long T, int K,
                                chrono::steady_clock::time_point start, double timeLimitSec) {
    int n = (int)perm.size();
    vector<long long> vals(n);
    for (int i = 0; i < n; ++i) vals[i] = a[perm[i]];

    vector<State> states;
    states.reserve(K + 1);
    State init;
    init.sum = 0;
    init.mask = {};
    states.push_back(init);

    auto better = [&](const State &x, const State &y) {
        unsigned long long ex = uabsll(x.sum - T);
        unsigned long long ey = uabsll(y.sum - T);
        if (ex != ey) return ex < ey;
        return x.sum < y.sum;
    };

    for (int i = 0; i < n; ++i) {
        double el = chrono::duration<double>(chrono::steady_clock::now() - start).count();
        if (el > timeLimitSec) break;

        vector<State> cand;
        cand.reserve(states.size() * 2);
        for (const auto &st : states) {
            cand.push_back(st);
            State t = st;
            t.sum += vals[i];
            setBit(t.mask, i);
            cand.push_back(t);
        }

        if ((int)cand.size() > K) {
            nth_element(cand.begin(), cand.begin() + K, cand.end(), better);
            cand.resize(K);
        }
        states.swap(cand);
    }

    State best = states[0];
    for (auto &st : states) if (uabsll(st.sum - T) < uabsll(best.sum - T)) best = st;

    vector<char> sel((int)a.size(), 0);
    for (int i = 0; i < n; ++i) {
        if (getBit(best.mask, i)) sel[perm[i]] = 1;
    }
    return sel;
}

static long long sum_selected(const vector<long long> &a, const vector<char> &sel) {
    long long s = 0;
    for (int i = 0; i < (int)a.size(); ++i) if (sel[i]) s += a[i];
    return s;
}

static void local_improve(const vector<long long> &a, long long T, vector<char> &sel,
                          chrono::steady_clock::time_point start, double timeLimitSec) {
    int n = (int)a.size();
    long long curSum = sum_selected(a, sel);
    unsigned long long curErr = uabsll(curSum - T);

    auto try_update = [&](int i) {
        long long newSum = curSum + (sel[i] ? -a[i] : a[i]);
        unsigned long long newErr = uabsll(newSum - T);
        if (newErr < curErr) {
            sel[i] ^= 1;
            curSum = newSum;
            curErr = newErr;
            return true;
        }
        return false;
    };

    bool improved = true;
    while (improved) {
        double el = chrono::duration<double>(chrono::steady_clock::now() - start).count();
        if (el > timeLimitSec) break;
        improved = false;
        for (int i = 0; i < n; ++i) {
            if (try_update(i)) improved = true;
            if ((i & 15) == 0) {
                el = chrono::duration<double>(chrono::steady_clock::now() - start).count();
                if (el > timeLimitSec) break;
            }
        }
    }

    // Random 2-flip attempts
    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    mt19937_64 rng(seed);
    uniform_int_distribution<int> dist(0, n - 1);

    for (int iter = 0; iter < 20000; ++iter) {
        double el = chrono::duration<double>(chrono::steady_clock::now() - start).count();
        if (el > timeLimitSec) break;
        int i = dist(rng), j = dist(rng);
        if (i == j) continue;
        long long newSum = curSum + (sel[i] ? -a[i] : a[i]) + (sel[j] ? -a[j] : a[j]);
        unsigned long long newErr = uabsll(newSum - T);
        if (newErr < curErr) {
            sel[i] ^= 1;
            sel[j] ^= 1;
            curSum = newSum;
            curErr = newErr;
            if (curErr == 0) break;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long T;
    if (!(cin >> n >> T)) return 0;
    vector<long long> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    if (n == 0) return 0;
    if (T == 0) {
        cout << string(n, '0') << "\n";
        return 0;
    }

    auto start = chrono::steady_clock::now();
    const double TOTAL_LIMIT = 1.95;
    const double DFS_LIMIT = 1.55;

    // If small enough, exact MITM on all items.
    if (n <= 44) {
        // Work in original order.
        Mask128 m;
        bool exact = exact_mitm_all(a, T, m);
        string ans(n, '0');
        for (int i = 0; i < n; ++i) if (getBit(m, i)) ans[i] = '1';
        // even if not exact (should be), still output best found by MITM
        cout << ans << "\n";
        return 0;
    }

    // Sort descending for DFS.
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int i, int j) {
        if (a[i] != a[j]) return a[i] > a[j];
        return i < j;
    });

    vector<long long> vals(n);
    for (int i = 0; i < n; ++i) vals[i] = a[order[i]];

    // Build modulo DP for pruning.
    ModDP mdp1(65536, n);
    ModDP mdp2(65521, n);
    mdp1.build(vals);
    mdp2.build(vals);

    // DFS try to find exact.
    DFSSolver solver;
    solver.init(vals, T, mdp1, mdp2, 30, DFS_LIMIT, start);
    bool found = false;
    if (T <= solver.suffixSum[0] && solver.mod_ok(0, T)) {
        found = solver.dfs(0, T);
    }

    vector<char> bestSel(n, 0);
    long long bestSum = 0;
    unsigned long long bestErr = ULLONG_MAX;

    auto update_best = [&](const vector<char> &sel) {
        long long s = sum_selected(a, sel);
        unsigned long long e = uabsll(s - T);
        if (e < bestErr) {
            bestErr = e;
            bestSum = s;
            bestSel = sel;
        }
    };

    if (found && !solver.timeout) {
        // Map back to original indices.
        vector<char> selOrig(n, 0);
        for (int i = 0; i < n; ++i) selOrig[order[i]] = solver.choose[i];
        string ans(n, '0');
        for (int i = 0; i < n; ++i) if (selOrig[i]) ans[i] = '1';
        cout << ans << "\n";
        return 0;
    }

    // Heuristic fallbacks.
    // Greedy improvement-based in sorted order.
    {
        vector<char> sel(n, 0);
        long long s = 0;
        for (int i = 0; i < n; ++i) {
            int idx = order[i];
            long long s2 = s + a[idx];
            if (uabsll(s2 - T) < uabsll(s - T)) {
                sel[idx] = 1;
                s = s2;
            }
        }
        update_best(sel);
    }

    // Beam searches with different permutations.
    int K = 120000;

    // Sorted order beam.
    {
        vector<int> perm = order;
        vector<char> sel = beam_closest(a, perm, T, K, start, TOTAL_LIMIT - 0.25);
        update_best(sel);
    }

    // Random order beams.
    {
        uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
        mt19937_64 rng(seed);
        for (int rep = 0; rep < 2; ++rep) {
            double el = chrono::duration<double>(chrono::steady_clock::now() - start).count();
            if (el > TOTAL_LIMIT - 0.35) break;
            vector<int> perm(n);
            iota(perm.begin(), perm.end(), 0);
            shuffle(perm.begin(), perm.end(), rng);
            vector<char> sel = beam_closest(a, perm, T, K, start, TOTAL_LIMIT - 0.15);
            update_best(sel);
            if (bestErr == 0) break;
        }
    }

    // Local improvement.
    {
        double el = chrono::duration<double>(chrono::steady_clock::now() - start).count();
        if (el < TOTAL_LIMIT - 0.02) {
            local_improve(a, T, bestSel, start, TOTAL_LIMIT - 0.01);
            bestErr = uabsll(sum_selected(a, bestSel) - T);
        }
    }

    string out(n, '0');
    for (int i = 0; i < n; ++i) if (bestSel[i]) out[i] = '1';
    cout << out << "\n";
    return 0;
}