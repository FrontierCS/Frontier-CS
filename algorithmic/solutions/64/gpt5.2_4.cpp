#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
using u64 = unsigned long long;

static inline u64 absDiffLL(int64 a, int64 b) {
    __int128 d = ( __int128)a - ( __int128)b;
    if (d < 0) d = -d;
    return (u64)d;
}

static inline void setBit(u64 &lo, u64 &hi, int i) {
    if (i < 64) lo |= (1ULL << i);
    else hi |= (1ULL << (i - 64));
}
static inline bool getBit(u64 lo, u64 hi, int i) {
    if (i < 64) return (lo >> i) & 1ULL;
    return (hi >> (i - 64)) & 1ULL;
}

struct Cand {
    int64 sum;
    u64 lo, hi;
    u64 err;
};

static inline bool cmpErr(const Cand& a, const Cand& b) {
    if (a.err != b.err) return a.err < b.err;
    return a.sum < b.sum;
}
static inline bool cmpSum(const Cand& a, const Cand& b) {
    if (a.sum != b.sum) return a.sum < b.sum;
    return a.err < b.err;
}

static void pruneDiverse(vector<Cand>& v, int K) {
    if ((int)v.size() <= K) return;

    // Keep some best by error
    sort(v.begin(), v.end(), cmpErr);
    int M = (int)(K * 3LL / 4LL);
    if (M < 1) M = 1;
    if (M > (int)v.size()) M = (int)v.size();

    vector<Cand> keep;
    keep.reserve((size_t)K + 32);
    for (int i = 0; i < M; i++) keep.push_back(v[i]);

    // Add diversity sampled by sum across range
    int D = K - M;
    if (D > 0) {
        sort(v.begin(), v.end(), cmpSum);
        if (D == 1) {
            keep.push_back(v[(int)v.size() / 2]);
        } else {
            int sz = (int)v.size();
            for (int t = 0; t < D; t++) {
                long long pos = (long long)t * (sz - 1) / (D - 1);
                keep.push_back(v[(int)pos]);
            }
        }
    }

    sort(keep.begin(), keep.end(), cmpErr);
    if ((int)keep.size() > K) keep.resize(K);
    v.swap(keep);
}

static Cand beamSolve(const vector<int>& order, const vector<int64>& a, int64 T, int K) {
    vector<Cand> states;
    states.reserve(K);
    states.push_back({0, 0, 0, absDiffLL(0, T)});

    for (int idx : order) {
        vector<Cand> next;
        next.reserve(states.size() * 2);
        int64 val = a[idx];

        for (const Cand& s : states) {
            next.push_back(s);
            Cand t = s;
            t.sum += val;
            setBit(t.lo, t.hi, idx);
            t.err = absDiffLL(t.sum, T);
            next.push_back(t);
        }

        pruneDiverse(next, K);
        states.swap(next);
    }

    Cand best = states[0];
    for (const auto& s : states) if (s.err < best.err) best = s;
    return best;
}

struct MiMResult {
    int64 subSum;
    u64 err;
    uint32_t m1, m2;
};

static MiMResult meetInMiddleClosest(const vector<int64>& vals, int64 target) {
    int m = (int)vals.size();
    int p = m / 2;
    int q = m - p;

    int L = 1 << p;
    int R = 1 << q;

    vector<int64> leftSum(L, 0);
    for (int mask = 1; mask < L; mask++) {
        int b = __builtin_ctz((unsigned)mask);
        leftSum[mask] = leftSum[mask ^ (1 << b)] + vals[b];
    }

    vector<pair<int64, uint32_t>> right;
    right.reserve(R);
    vector<int64> rightSum(R, 0);
    for (int mask = 1; mask < R; mask++) {
        int b = __builtin_ctz((unsigned)mask);
        rightSum[mask] = rightSum[mask ^ (1 << b)] + vals[p + b];
    }
    for (int mask = 0; mask < R; mask++) right.push_back({rightSum[mask], (uint32_t)mask});
    sort(right.begin(), right.end(), [](const auto& x, const auto& y) {
        if (x.first != y.first) return x.first < y.first;
        return x.second < y.second;
    });

    MiMResult best;
    best.err = absDiffLL(0, target);
    best.subSum = 0;
    best.m1 = 0;
    best.m2 = 0;

    for (int mask1 = 0; mask1 < L; mask1++) {
        int64 s1 = leftSum[mask1];
        int64 rem = target - s1;

        auto it = lower_bound(right.begin(), right.end(), rem,
                              [](const pair<int64, uint32_t>& pr, int64 v) { return pr.first < v; });

        auto relax = [&](const pair<int64, uint32_t>& pr) {
            int64 total = s1 + pr.first;
            u64 e = absDiffLL(total, target);
            if (e < best.err) {
                best.err = e;
                best.subSum = total;
                best.m1 = (uint32_t)mask1;
                best.m2 = pr.second;
            }
        };

        if (it != right.end()) relax(*it);
        if (it != right.begin()) relax(*prev(it));

        if (best.err == 0) break;
    }

    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    int64 T;
    if (!(cin >> n >> T)) return 0;
    vector<int64> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];

    // Immediate exact single-element match
    {
        for (int i = 0; i < n; i++) {
            if (a[i] == T) {
                string out(n, '0');
                out[i] = '1';
                cout << out << "\n";
                return 0;
            }
        }
    }

    auto start = chrono::steady_clock::now();
    auto elapsedSec = [&]() -> double {
        return chrono::duration<double>(chrono::steady_clock::now() - start).count();
    };
    const double TIME_LIMIT = 1.85;

    // If n small enough, solve exactly via MiM on all items
    if (n <= 40) {
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 0);
        vector<int64> vals(n);
        for (int i = 0; i < n; i++) vals[i] = a[i];
        MiMResult r = meetInMiddleClosest(vals, T);
        string out(n, '0');
        int p = n / 2;
        for (int i = 0; i < p; i++) if ((r.m1 >> i) & 1U) out[i] = '1';
        for (int i = 0; i < n - p; i++) if ((r.m2 >> i) & 1U) out[p + i] = '1';
        cout << out << "\n";
        return 0;
    }

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ (uint64_t)(uintptr_t)&rng);

    // Beam search attempts
    int K = 7000;
    if (n <= 60) K = 9000;
    if (n <= 50) K = 11000;

    vector<int> orderDesc(n);
    iota(orderDesc.begin(), orderDesc.end(), 0);
    sort(orderDesc.begin(), orderDesc.end(), [&](int i, int j) {
        if (a[i] != a[j]) return a[i] > a[j];
        return i < j;
    });

    Cand best = beamSolve(orderDesc, a, T, K);

    if (elapsedSec() < TIME_LIMIT * 0.55) {
        vector<int> orderRand(n);
        iota(orderRand.begin(), orderRand.end(), 0);
        shuffle(orderRand.begin(), orderRand.end(), rng);
        Cand cand2 = beamSolve(orderRand, a, T, K);
        if (cand2.err < best.err) best = cand2;
    }

    if (elapsedSec() < TIME_LIMIT * 0.75) {
        // Slightly perturbed descending order
        vector<int> orderPert = orderDesc;
        for (int i = 0; i + 1 < n; i++) {
            if ((rng() & 15ULL) == 0) swap(orderPert[i], orderPert[i + 1]);
        }
        Cand cand3 = beamSolve(orderPert, a, T, K);
        if (cand3.err < best.err) best = cand3;
    }

    // Decode to selection vector
    vector<uint8_t> sel(n, 0);
    int64 curSum = 0;
    for (int i = 0; i < n; i++) {
        sel[i] = getBit(best.lo, best.hi, i) ? 1 : 0;
        if (sel[i]) curSum += a[i];
    }
    u64 curErr = absDiffLL(curSum, T);

    // Large Neighborhood Search with MiM on random subsets
    vector<int> idxAll(n);
    iota(idxAll.begin(), idxAll.end(), 0);

    while (elapsedSec() < TIME_LIMIT && curErr != 0) {
        int mMin = min(n, 26);
        int mMax = min(n, 36);
        int m = mMin;
        if (mMax > mMin) m = mMin + (int)(rng() % (uint64_t)(mMax - mMin + 1));

        shuffle(idxAll.begin(), idxAll.end(), rng);
        vector<int> chosen(idxAll.begin(), idxAll.begin() + m);

        int64 removed = 0;
        for (int id : chosen) if (sel[id]) removed += a[id];
        int64 fixedSum = curSum - removed;
        int64 target2 = T - fixedSum; // subset sum among chosen aims for this

        vector<int64> vals(m);
        for (int i = 0; i < m; i++) vals[i] = a[chosen[i]];

        MiMResult r = meetInMiddleClosest(vals, target2);
        if (r.err < curErr) {
            int p = m / 2;
            for (int i = 0; i < p; i++) sel[chosen[i]] = ((r.m1 >> i) & 1U) ? 1 : 0;
            for (int i = 0; i < m - p; i++) sel[chosen[p + i]] = ((r.m2 >> i) & 1U) ? 1 : 0;

            curSum = fixedSum + r.subSum;
            curErr = r.err;
        }
    }

    // Final small local improvement: single-bit flip
    bool improved = true;
    while (improved && curErr != 0 && elapsedSec() < TIME_LIMIT) {
        improved = false;
        for (int i = 0; i < n; i++) {
            int64 newSum = curSum + (sel[i] ? -a[i] : a[i]);
            u64 newErr = absDiffLL(newSum, T);
            if (newErr < curErr) {
                sel[i] ^= 1;
                curSum = newSum;
                curErr = newErr;
                improved = true;
            }
        }
    }

    string out(n, '0');
    for (int i = 0; i < n; i++) if (sel[i]) out[i] = '1';
    cout << out << "\n";
    return 0;
}