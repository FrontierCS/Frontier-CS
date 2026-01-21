#include <bits/stdc++.h>
using namespace std;

using i64 = long long;
using u64 = unsigned long long;
using i128 = __int128_t;
using u128 = __uint128_t;

struct State {
    i64 sum;
    u64 lo, hi;
};

static inline u64 absDiff(i64 a, i64 b) {
    return (a >= b) ? (u64)(a - b) : (u64)(b - a);
}
static inline void setBit(u64 &lo, u64 &hi, int id) {
    if (id < 64) lo |= (1ULL << id);
    else hi |= (1ULL << (id - 64));
}
static inline void flipBit(u64 &lo, u64 &hi, int id) {
    if (id < 64) lo ^= (1ULL << id);
    else hi ^= (1ULL << (id - 64));
}
static inline bool getBit(u64 lo, u64 hi, int id) {
    if (id < 64) return (lo >> id) & 1ULL;
    return (hi >> (id - 64)) & 1ULL;
}

struct BestAns {
    u64 lo = 0, hi = 0;
    i64 sum = 0;
    u64 err = (u64)-1;
};

static BestAns greedyBest(int n, i64 T, const vector<i64>& a) {
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int i, int j){
        if (a[i] != a[j]) return a[i] > a[j];
        return i < j;
    });

    u64 lo = 0, hi = 0;
    i64 sum = 0;
    u64 err = absDiff(sum, T);
    for (int id : idx) {
        i64 sum2 = sum + a[id];
        u64 err2 = absDiff(sum2, T);
        if (err2 <= err) {
            setBit(lo, hi, id);
            sum = sum2;
            err = err2;
            if (err == 0) break;
        }
    }
    BestAns best;
    best.lo = lo; best.hi = hi; best.sum = sum; best.err = err;
    return best;
}

static void localImprove(int n, i64 T, const vector<i64>& a, BestAns& best) {
    i64 sum = best.sum;
    u64 lo = best.lo, hi = best.hi;
    u64 err = absDiff(sum, T);

    for (;;) {
        bool improved = false;
        u64 bestErr = err;
        int bestType = 0; // 1=flip, 2=swap
        int bi = -1, bj = -1;
        i64 bestSum = sum;

        // 1-flip
        for (int i = 0; i < n; i++) {
            bool in = getBit(lo, hi, i);
            i64 sum2 = in ? (sum - a[i]) : (sum + a[i]);
            u64 err2 = absDiff(sum2, T);
            if (err2 < bestErr) {
                bestErr = err2;
                bestType = 1;
                bi = i;
                bestSum = sum2;
                if (bestErr == 0) break;
            }
        }
        if (bestErr == 0) {
            flipBit(lo, hi, bi);
            sum = bestSum;
            err = bestErr;
            improved = true;
        } else {
            // 1-in 1-out swap
            vector<int> inIdx, outIdx;
            inIdx.reserve(n); outIdx.reserve(n);
            for (int i = 0; i < n; i++) {
                if (getBit(lo, hi, i)) inIdx.push_back(i);
                else outIdx.push_back(i);
            }
            for (int i : inIdx) {
                for (int j : outIdx) {
                    i64 sum2 = sum - a[i] + a[j];
                    u64 err2 = absDiff(sum2, T);
                    if (err2 < bestErr) {
                        bestErr = err2;
                        bestType = 2;
                        bi = i; bj = j;
                        bestSum = sum2;
                        if (bestErr == 0) break;
                    }
                }
                if (bestErr == 0) break;
            }

            if (bestType == 1) {
                flipBit(lo, hi, bi);
                sum = bestSum;
                err = bestErr;
                improved = true;
            } else if (bestType == 2) {
                flipBit(lo, hi, bi);
                flipBit(lo, hi, bj);
                sum = bestSum;
                err = bestErr;
                improved = true;
            }
        }

        if (!improved) break;
        if (err == 0) break;
    }

    best.lo = lo; best.hi = hi; best.sum = sum; best.err = err;
}

static void refineMITMNeighborhood(int n, i64 T, const vector<i64>& a, BestAns& best, mt19937_64& rng) {
    if (best.err == 0) return;

    // Build candidate indices to toggle: mix of largest selected and largest unselected + random fill.
    vector<int> sel, unsel;
    sel.reserve(n); unsel.reserve(n);
    for (int i = 0; i < n; i++) {
        if (getBit(best.lo, best.hi, i)) sel.push_back(i);
        else unsel.push_back(i);
    }
    auto descByA = [&](int i, int j){
        if (a[i] != a[j]) return a[i] > a[j];
        return i < j;
    };
    sort(sel.begin(), sel.end(), descByA);
    sort(unsel.begin(), unsel.end(), descByA);

    vector<int> cand;
    cand.reserve(60);

    int takeSel = min<int>(20, (int)sel.size());
    int takeUnsel = min<int>(20, (int)unsel.size());
    for (int i = 0; i < takeSel; i++) cand.push_back(sel[i]);
    for (int i = 0; i < takeUnsel; i++) cand.push_back(unsel[i]);

    // Add random extra
    vector<int> allIdx(n);
    iota(allIdx.begin(), allIdx.end(), 0);
    shuffle(allIdx.begin(), allIdx.end(), rng);
    for (int id : allIdx) {
        cand.push_back(id);
        if ((int)cand.size() >= 60) break;
    }

    sort(cand.begin(), cand.end());
    cand.erase(unique(cand.begin(), cand.end()), cand.end());

    int p = min<int>(40, (int)cand.size());
    if (p <= 0) return;
    cand.resize(p);

    vector<i64> delta(p);
    for (int k = 0; k < p; k++) {
        int id = cand[k];
        bool in = getBit(best.lo, best.hi, id);
        delta[k] = in ? -a[id] : +a[id];
    }

    i64 residual = T - best.sum;

    int m1 = p / 2;
    int m2 = p - m1;

    int size1 = 1 << m1;
    vector<i64> sum1(size1);
    sum1[0] = 0;
    for (int mask = 1; mask < size1; mask++) {
        int lsb = mask & -mask;
        int b = __builtin_ctz(lsb);
        sum1[mask] = sum1[mask ^ lsb] + delta[b];
    }
    vector<pair<i64, uint32_t>> list1;
    list1.reserve(size1);
    for (int mask = 0; mask < size1; mask++) list1.emplace_back(sum1[mask], (uint32_t)mask);
    sort(list1.begin(), list1.end(), [](auto &x, auto &y){ return x.first < y.first; });

    int size2 = 1 << m2;
    vector<i64> sum2(size2);
    sum2[0] = 0;
    for (int mask = 1; mask < size2; mask++) {
        int lsb = mask & -mask;
        int b = __builtin_ctz(lsb);
        sum2[mask] = sum2[mask ^ lsb] + delta[m1 + b];
    }

    u64 bestErr = best.err;
    i64 bestSum = best.sum;
    uint32_t bestM1 = 0, bestM2 = 0;

    auto upd = [&](i64 dsum, uint32_t mm1, uint32_t mm2) {
        i64 newSum = best.sum + dsum;
        u64 e = absDiff(newSum, T);
        if (e < bestErr) {
            bestErr = e;
            bestSum = newSum;
            bestM1 = mm1;
            bestM2 = mm2;
        }
    };

    for (int mask = 0; mask < size2; mask++) {
        i64 s2 = sum2[mask];
        i64 target = residual - s2;
        auto it = lower_bound(list1.begin(), list1.end(), make_pair(target, 0u),
                              [](const auto& x, const auto& y){ return x.first < y.first; });
        if (it != list1.end()) upd(it->first + s2, it->second, (uint32_t)mask);
        if (it != list1.begin()) {
            --it;
            upd(it->first + s2, it->second, (uint32_t)mask);
        }
        if (bestErr == 0) break;
    }

    if (bestErr < best.err) {
        u64 lo = best.lo, hi = best.hi;
        for (int b = 0; b < m1; b++) if ((bestM1 >> b) & 1U) flipBit(lo, hi, cand[b]);
        for (int b = 0; b < m2; b++) if ((bestM2 >> b) & 1U) flipBit(lo, hi, cand[m1 + b]);
        best.lo = lo; best.hi = hi; best.sum = bestSum; best.err = bestErr;
    }
}

static void beamDP(const vector<int>& order, int n, i64 T, const vector<i64>& a, size_t Kmax, BestAns& best) {
    if (best.err == 0) return;

    vector<i64> suf(n + 1, 0);
    for (int i = n - 1; i >= 0; i--) {
        suf[i] = suf[i + 1] + a[order[i]];
    }

    vector<State> cur;
    cur.reserve(Kmax + 8);
    cur.push_back({0, 0, 0});

    vector<State> tmp;
    tmp.reserve(2 * Kmax + 16);

    for (int step = 0; step < n; step++) {
        if (best.err == 0) break;

        int id = order[step];
        i64 val = a[id];
        i64 rem = suf[step + 1];

        tmp = cur;
        tmp.reserve(cur.size() * 2);

        // Generate added states
        for (const auto& s : cur) {
            State ns = s;
            ns.sum += val;
            setBit(ns.lo, ns.hi, id);

            u64 e = absDiff(ns.sum, T);
            if (e < best.err) {
                best.err = e;
                best.sum = ns.sum;
                best.lo = ns.lo;
                best.hi = ns.hi;
                if (best.err == 0) break;
            }
            tmp.push_back(ns);
        }
        if (best.err == 0) break;

        // Filter safe discards
        vector<State> filt;
        filt.reserve(tmp.size());
        for (const auto& s : tmp) {
            if (s.sum >= T) {
                u64 e = (u64)(s.sum - T);
                if (e > best.err) continue;
            } else {
                i128 maxReach = (i128)s.sum + (i128)rem;
                if (maxReach < (i128)T) {
                    u64 minErr = (u64)((i128)T - maxReach);
                    if (minErr > best.err) continue;
                }
            }
            filt.push_back(s);
        }
        tmp.swap(filt);

        if (tmp.empty()) {
            cur.clear();
            cur.push_back({0, 0, 0});
            continue;
        }

        // Prune by size
        if (tmp.size() > Kmax) {
            sort(tmp.begin(), tmp.end(), [](const State& x, const State& y){
                return x.sum < y.sum;
            });
            // Dedup by sum (safe: future depends only on sum with nonnegative remaining items)
            {
                size_t w = 1;
                for (size_t i = 1; i < tmp.size(); i++) {
                    if (tmp[i].sum != tmp[w - 1].sum) tmp[w++] = tmp[i];
                }
                tmp.resize(w);
            }

            // Split undershoot/overshoot
            size_t m = tmp.size();
            size_t pos = upper_bound(tmp.begin(), tmp.end(), T, [](i64 v, const State& s){
                return v < s.sum;
            }) - tmp.begin();

            vector<State> selected;
            selected.reserve(Kmax);

            // Keep a few best overshoots (smallest above T)
            size_t Okeep = 2000;
            if (pos < m) {
                size_t take = min(Okeep, m - pos);
                for (size_t i = pos; i < pos + take; i++) selected.push_back(tmp[i]);
            }

            // Keep many best undershoots near T
            size_t Knear = (size_t)((Kmax * 2) / 3);
            if (Knear > pos) Knear = pos;
            if (Knear > 0) {
                size_t start = pos - Knear;
                for (size_t i = start; i < pos; i++) selected.push_back(tmp[i]);
            }

            // Diversity buckets from undershoots
            if (selected.size() < Kmax && pos > 0) {
                size_t remainingSlots = Kmax - selected.size();
                size_t bcount = min<size_t>(remainingSlots, 15000);
                if (bcount > 0) {
                    vector<State> bucket(bcount);
                    vector<char> used(bcount, 0);
                    for (size_t i = 0; i < pos; i++) {
                        i64 ssum = tmp[i].sum;
                        size_t b;
                        if (T <= 0) b = 0;
                        else {
                            long double frac = (long double)ssum / ((long double)T + 1.0L);
                            if (frac < 0) frac = 0;
                            if (frac > 1) frac = 1;
                            b = (size_t)(frac * (long double)bcount);
                            if (b >= bcount) b = bcount - 1;
                        }
                        bucket[b] = tmp[i]; // overwrite => larger sum within bucket (since tmp ascending)
                        used[b] = 1;
                    }
                    for (size_t b = 0; b < bcount && selected.size() < Kmax; b++) {
                        if (used[b]) selected.push_back(bucket[b]);
                    }
                }
            }

            // Fill remaining with spaced undershoots if still short
            if (selected.size() < Kmax && pos > 0) {
                size_t need = Kmax - selected.size();
                size_t stride = max<size_t>(1, pos / need);
                for (size_t i = 0; i < pos && selected.size() < Kmax; i += stride) {
                    selected.push_back(tmp[i]);
                }
            }

            if (selected.empty()) selected.push_back({0, 0, 0});
            cur.swap(selected);
        } else {
            cur.swap(tmp);
        }
    }
}

static BestAns exactMITM(int n, i64 T, const vector<i64>& a) {
    int n1 = n / 2;
    int n2 = n - n1;

    int size1 = 1 << n1;
    vector<pair<i64, uint32_t>> list1;
    list1.resize(size1);
    vector<i64> sum1(size1);
    sum1[0] = 0;
    for (int mask = 1; mask < size1; mask++) {
        int lsb = mask & -mask;
        int b = __builtin_ctz(lsb);
        sum1[mask] = sum1[mask ^ lsb] + a[b];
    }
    for (int mask = 0; mask < size1; mask++) list1[mask] = {sum1[mask], (uint32_t)mask};
    sort(list1.begin(), list1.end(), [](const auto& x, const auto& y){ return x.first < y.first; });

    int size2 = 1 << n2;
    vector<i64> sum2(size2);
    sum2[0] = 0;
    for (int mask = 1; mask < size2; mask++) {
        int lsb = mask & -mask;
        int b = __builtin_ctz(lsb);
        sum2[mask] = sum2[mask ^ lsb] + a[n1 + b];
    }

    BestAns best;
    best.err = absDiff(0, T);
    best.sum = 0;

    for (int m2 = 0; m2 < size2; m2++) {
        i64 s2 = sum2[m2];
        i64 target = T - s2;
        auto it = lower_bound(list1.begin(), list1.end(), make_pair(target, 0u),
                              [](const auto& x, const auto& y){ return x.first < y.first; });

        auto check = [&](const pair<i64, uint32_t>& p1) {
            i64 total = s2 + p1.first;
            u64 e = absDiff(total, T);
            if (e < best.err) {
                best.err = e;
                best.sum = total;
                u64 lo = 0, hi = 0;
                uint32_t m1 = p1.second;
                for (int b = 0; b < n1; b++) if ((m1 >> b) & 1U) setBit(lo, hi, b);
                for (int b = 0; b < n2; b++) if ((m2 >> b) & 1U) setBit(lo, hi, n1 + b);
                best.lo = lo;
                best.hi = hi;
            }
        };

        if (it != list1.end()) check(*it);
        if (it != list1.begin()) check(*prev(it));
        if (best.err == 0) break;
    }

    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    i64 T;
    if (!(cin >> n >> T)) return 0;
    vector<i64> a(n);
    for (int i = 0; i < n; i++) cin >> a[i];

    BestAns best;
    best.err = absDiff(0, T);
    best.sum = 0;
    best.lo = best.hi = 0;

    // Trivial if T==0
    if (T == 0) {
        string out(n, '0');
        cout << out << "\n";
        return 0;
    }

    // Exact for small n
    if (n <= 44) {
        best = exactMITM(n, T, a);
        string out;
        out.resize(n);
        for (int i = 0; i < n; i++) out[i] = getBit(best.lo, best.hi, i) ? '1' : '0';
        cout << out << "\n";
        return 0;
    }

    // Initial greedy
    best = greedyBest(n, T, a);
    localImprove(n, T, a, best);
    if (best.err == 0) {
        string out(n, '0');
        for (int i = 0; i < n; i++) if (getBit(best.lo, best.hi, i)) out[i] = '1';
        cout << out << "\n";
        return 0;
    }

    // Prepare orders
    vector<int> base(n);
    iota(base.begin(), base.end(), 0);

    vector<vector<int>> orders;

    {
        auto ord = base;
        sort(ord.begin(), ord.end(), [&](int i, int j){
            if (a[i] != a[j]) return a[i] > a[j];
            return i < j;
        });
        orders.push_back(ord);
    }
    {
        auto ord = base;
        sort(ord.begin(), ord.end(), [&](int i, int j){
            i64 ci = llabs(a[i] - T / 2);
            i64 cj = llabs(a[j] - T / 2);
            if (ci != cj) return ci > cj;
            if (a[i] != a[j]) return a[i] > a[j];
            return i < j;
        });
        orders.push_back(ord);
    }

    mt19937_64 rng((u64)chrono::high_resolution_clock::now().time_since_epoch().count());
    for (int r = 0; r < 4; r++) {
        auto ord = base;
        shuffle(ord.begin(), ord.end(), rng);
        orders.push_back(ord);
    }

    // Beam DP runs
    const size_t Kmax = 25000;
    for (auto &ord : orders) {
        if (best.err == 0) break;
        beamDP(ord, n, T, a, Kmax, best);
        localImprove(n, T, a, best);
    }

    // Neighborhood MITM refinements
    for (int t = 0; t < 3 && best.err != 0; t++) {
        refineMITMNeighborhood(n, T, a, best, rng);
        localImprove(n, T, a, best);
    }

    string out(n, '0');
    for (int i = 0; i < n; i++) if (getBit(best.lo, best.hi, i)) out[i] = '1';
    cout << out << "\n";
    return 0;
}