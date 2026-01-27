#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
using i128 = __int128_t;

static inline unsigned long long abs_u128_to_ull(i128 x) {
    if (x < 0) x = -x;
    return (unsigned long long)x;
}

static inline long long abs_ll(long long x) { return x < 0 ? -x : x; }

struct State {
    int64 sum;
    int parent;
    unsigned char bit;
};

struct Cand {
    int64 sum;
    int parent;
    unsigned char bit;
    unsigned long long dist;
};

static inline i128 to_i128(long long x) { return (i128)x; }

static long long subset_sum_from_sel(const vector<long long>& a, const vector<unsigned char>& sel) {
    i128 s = 0;
    for (size_t i = 0; i < a.size(); ++i) if (sel[i]) s += (i128)a[i];
    return (long long)s;
}

static void hill_climb_improve(const vector<long long>& a, long long T, vector<unsigned char>& sel) {
    int n = (int)a.size();
    long long curSum = subset_sum_from_sel(a, sel);
    long long diff = T - curSum; // want 0

    for (int iter = 0; iter < 200; ++iter) {
        long long bestAbs = abs_ll(diff);
        int bestI = -1, bestJ = -1;
        long long bestDelta = 0;

        // single flip
        for (int i = 0; i < n; ++i) {
            long long delta = sel[i] ? -a[i] : a[i];
            long long ndiff = diff - delta;
            long long nabs = abs_ll(ndiff);
            if (nabs < bestAbs) {
                bestAbs = nabs;
                bestI = i;
                bestJ = -1;
                bestDelta = delta;
                if (bestAbs == 0) break;
            }
        }
        if (bestAbs == 0) {
            if (bestI != -1) {
                sel[bestI] ^= 1;
                curSum += bestDelta;
                diff = T - curSum;
            }
            break;
        }

        // double flip
        for (int i = 0; i < n; ++i) {
            long long delta_i = sel[i] ? -a[i] : a[i];
            for (int j = i + 1; j < n; ++j) {
                long long delta_j = sel[j] ? -a[j] : a[j];
                long long delta = delta_i + delta_j;
                long long ndiff = diff - delta;
                long long nabs = abs_ll(ndiff);
                if (nabs < bestAbs) {
                    bestAbs = nabs;
                    bestI = i;
                    bestJ = j;
                    bestDelta = delta;
                    if (bestAbs == 0) break;
                }
            }
            if (bestAbs == 0) break;
        }

        if (bestI == -1) break;

        sel[bestI] ^= 1;
        if (bestJ != -1) sel[bestJ] ^= 1;
        curSum += bestDelta;
        diff = T - curSum;
        if (diff == 0) break;
    }
}

static void toggle_mitm_improve(mt19937_64& rng,
                               const vector<long long>& a,
                               long long T,
                               vector<unsigned char>& sel,
                               int trials,
                               int mChoose) {
    int n = (int)a.size();
    if (n == 0) return;
    mChoose = min(mChoose, n);
    if (mChoose <= 0) return;

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int i, int j) {
        if (a[i] != a[j]) return a[i] < a[j];
        return i < j;
    });

    long long curSum = subset_sum_from_sel(a, sel);
    long long bestErr = abs_ll(T - curSum);

    int Lpool = min(n, 60);

    for (int tr = 0; tr < trials; ++tr) {
        vector<int> cand;
        cand.reserve(mChoose);

        // Bias toward smaller values but keep randomness
        vector<int> pool(idx.begin(), idx.begin() + Lpool);
        shuffle(pool.begin(), pool.end(), rng);
        for (int i = 0; i < (int)pool.size() && (int)cand.size() < mChoose; ++i) cand.push_back(pool[i]);
        while ((int)cand.size() < mChoose) {
            int r = (int)(rng() % n);
            bool ok = true;
            for (int v : cand) if (v == r) { ok = false; break; }
            if (ok) cand.push_back(r);
        }

        vector<long long> c(mChoose);
        for (int i = 0; i < mChoose; ++i) {
            int id = cand[i];
            c[i] = sel[id] ? -a[id] : a[id];
        }

        int p = mChoose / 2;
        int q = mChoose - p;

        int sizeL = 1 << p;
        int sizeR = 1 << q;

        vector<long long> sumL(sizeL), sumR(sizeR);
        sumL[0] = 0;
        for (int i = 0; i < p; ++i) {
            int bit = 1 << i;
            for (int mask = 0; mask < bit; ++mask) sumL[mask | bit] = sumL[mask] + c[i];
        }
        sumR[0] = 0;
        for (int i = 0; i < q; ++i) {
            int bit = 1 << i;
            for (int mask = 0; mask < bit; ++mask) sumR[mask | bit] = sumR[mask] + c[p + i];
        }

        vector<pair<long long, uint32_t>> R;
        R.reserve(sizeR);
        for (uint32_t mask = 0; mask < (uint32_t)sizeR; ++mask) R.push_back({sumR[mask], mask});
        sort(R.begin(), R.end(), [](auto &x, auto &y) {
            if (x.first != y.first) return x.first < y.first;
            return x.second < y.second;
        });

        long long delta = T - curSum;
        long long bestLocalErr = bestErr;
        long long bestChange = 0;
        uint32_t bestMaskL = 0, bestMaskR = 0;

        for (uint32_t maskL = 0; maskL < (uint32_t)sizeL; ++maskL) {
            long long sl = sumL[maskL];
            long long need = delta - sl;
            auto it = lower_bound(R.begin(), R.end(), make_pair(need, (uint32_t)0),
                                  [](auto &x, auto &y) { return x.first < y.first; });
            for (int t = 0; t < 2; ++t) {
                if (it == R.end()) {
                    if (it == R.begin()) break;
                    --it;
                } else if (t == 1) {
                    if (it == R.begin()) break;
                    --it;
                }
                long long sr = it->first;
                long long change = sl + sr;
                long long newErr = abs_ll((T - (curSum + change)));
                if (newErr < bestLocalErr) {
                    bestLocalErr = newErr;
                    bestChange = change;
                    bestMaskL = maskL;
                    bestMaskR = it->second;
                    if (bestLocalErr == 0) break;
                }
            }
            if (bestLocalErr == 0) break;
        }

        if (bestLocalErr < bestErr) {
            // apply toggles
            for (int i = 0; i < p; ++i) if (bestMaskL & (1u << i)) sel[cand[i]] ^= 1;
            for (int i = 0; i < q; ++i) if (bestMaskR & (1u << i)) sel[cand[p + i]] ^= 1;
            curSum += bestChange;
            bestErr = bestLocalErr;
            if (bestErr == 0) break;
        }
    }
}

static bool exact_mim(int n, long long T, const vector<long long>& a, vector<unsigned char>& outSel) {
    int n1 = n / 2;
    int n2 = n - n1;

    int size1 = 1 << n1;
    vector<pair<long long, uint32_t>> L;
    L.reserve(size1);

    vector<long long> sum1(size1);
    sum1[0] = 0;
    for (int i = 0; i < n1; ++i) {
        int bit = 1 << i;
        for (int mask = 0; mask < bit; ++mask) sum1[mask | bit] = sum1[mask] + a[i];
    }
    for (uint32_t mask = 0; mask < (uint32_t)size1; ++mask) L.push_back({sum1[mask], mask});
    sort(L.begin(), L.end(), [](auto &x, auto &y) {
        if (x.first != y.first) return x.first < y.first;
        return x.second < y.second;
    });

    int size2 = 1 << n2;
    vector<long long> sum2(size2);
    sum2[0] = 0;
    for (int i = 0; i < n2; ++i) {
        int bit = 1 << i;
        for (int mask = 0; mask < bit; ++mask) sum2[mask | bit] = sum2[mask] + a[n1 + i];
    }

    long long bestErr = (1LL<<62);
    uint32_t bestM1 = 0, bestM2 = 0;

    for (uint32_t m2 = 0; m2 < (uint32_t)size2; ++m2) {
        long long s2 = sum2[m2];
        long long need = T - s2;
        auto it = lower_bound(L.begin(), L.end(), make_pair(need, (uint32_t)0),
                              [](auto &x, auto &y){ return x.first < y.first; });
        for (int t = 0; t < 2; ++t) {
            if (it == L.end()) {
                if (it == L.begin()) break;
                --it;
            } else if (t == 1) {
                if (it == L.begin()) break;
                --it;
            }
            long long s1 = it->first;
            long long total = s1 + s2;
            long long err = abs_ll(total - T);
            if (err < bestErr) {
                bestErr = err;
                bestM1 = it->second;
                bestM2 = m2;
                if (bestErr == 0) break;
            }
        }
        if (bestErr == 0) break;
    }

    outSel.assign(n, 0);
    for (int i = 0; i < n1; ++i) if (bestM1 & (1u << i)) outSel[i] = 1;
    for (int i = 0; i < n2; ++i) if (bestM2 & (1u << i)) outSel[n1 + i] = 1;
    return bestErr == 0;
}

static vector<unsigned char> beam_solve(const vector<long long>& a,
                                       long long T,
                                       const vector<int>& order,
                                       int K,
                                       long long& outErr) {
    int n = (int)a.size();
    vector<long long> suffix(n + 1, 0);
    for (int i = n - 1; i >= 0; --i) suffix[i] = suffix[i + 1] + a[order[i]];

    vector<vector<State>> layers;
    layers.resize(n + 1);
    layers[0].reserve(1);
    layers[0].push_back(State{0, -1, 0});

    vector<Cand> cand;
    cand.reserve((size_t)2 * K + 16);

    for (int i = 0; i < n; ++i) {
        const auto& prev = layers[i];
        int m = (int)prev.size();
        cand.clear();
        cand.reserve((size_t)2 * m);

        long long val = a[order[i]];
        i128 target2 = (i128)2 * (i128)T - (i128)suffix[i + 1];

        for (int j = 0; j < m; ++j) {
            int64 s = prev[j].sum;

            // exclude
            {
                i128 d = (i128)2 * (i128)s - target2;
                unsigned long long dist = abs_u128_to_ull(d);
                cand.push_back(Cand{s, j, 0, dist});
            }
            // include
            {
                int64 s2 = s + val;
                i128 d = (i128)2 * (i128)s2 - target2;
                unsigned long long dist = abs_u128_to_ull(d);
                cand.push_back(Cand{s2, j, 1, dist});
            }
        }

        int keep = min(K, (int)cand.size());
        if ((int)cand.size() > keep) {
            nth_element(cand.begin(), cand.begin() + keep, cand.end(), [](const Cand& x, const Cand& y) {
                if (x.dist != y.dist) return x.dist < y.dist;
                if (x.sum != y.sum) return x.sum < y.sum;
                return x.parent < y.parent;
            });
            cand.resize(keep);
        }

        layers[i + 1].clear();
        layers[i + 1].reserve(cand.size());
        for (const auto& c : cand) layers[i + 1].push_back(State{c.sum, c.parent, c.bit});
    }

    const auto& last = layers[n];
    int bestIdx = 0;
    long long bestErr = (1LL<<62);
    for (int i = 0; i < (int)last.size(); ++i) {
        long long err = abs_ll(last[i].sum - T);
        if (err < bestErr) {
            bestErr = err;
            bestIdx = i;
            if (bestErr == 0) break;
        }
    }

    vector<unsigned char> sel(n, 0);
    int cur = bestIdx;
    for (int i = n - 1; i >= 0; --i) {
        const State& st = layers[i + 1][cur];
        sel[order[i]] = st.bit;
        cur = st.parent;
    }

    outErr = bestErr;
    return sel;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long T;
    if (!(cin >> n >> T)) return 0;
    vector<long long> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    vector<unsigned char> bestSel(n, 0);
    long long bestErr = abs_ll(T);

    if (T == 0) {
        for (int i = 0; i < n; ++i) cout << '0';
        cout << "\n";
        return 0;
    }

    for (int i = 0; i < n; ++i) {
        if (a[i] == T) {
            for (int j = 0; j < n; ++j) cout << (j == i ? '1' : '0');
            cout << "\n";
            return 0;
        }
    }

    if (n <= 42) {
        vector<unsigned char> sel;
        exact_mim(n, T, a, sel);
        for (int i = 0; i < n; ++i) cout << (sel[i] ? '1' : '0');
        cout << "\n";
        return 0;
    }

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto start = chrono::steady_clock::now();
    auto time_left = [&]() -> double {
        auto now = chrono::steady_clock::now();
        return 1.80 - chrono::duration<double>(now - start).count();
    };

    int K = 50000;
    if (n <= 70) K = 70000;
    if (n <= 60) K = 90000;

    vector<int> order(n);
    iota(order.begin(), order.end(), 0);

    // Deterministic: descending and ascending
    {
        vector<int> desc = order;
        sort(desc.begin(), desc.end(), [&](int i, int j) {
            if (a[i] != a[j]) return a[i] > a[j];
            return i < j;
        });
        long long err;
        auto sel = beam_solve(a, T, desc, K, err);
        hill_climb_improve(a, T, sel);
        err = abs_ll(subset_sum_from_sel(a, sel) - T);
        if (err < bestErr) { bestErr = err; bestSel = sel; }
        if (bestErr == 0) {
            for (int i = 0; i < n; ++i) cout << (bestSel[i] ? '1' : '0');
            cout << "\n";
            return 0;
        }
    }
    if (time_left() > 0.2) {
        vector<int> asc = order;
        sort(asc.begin(), asc.end(), [&](int i, int j) {
            if (a[i] != a[j]) return a[i] < a[j];
            return i < j;
        });
        long long err;
        auto sel = beam_solve(a, T, asc, K, err);
        hill_climb_improve(a, T, sel);
        err = abs_ll(subset_sum_from_sel(a, sel) - T);
        if (err < bestErr) { bestErr = err; bestSel = sel; }
        if (bestErr == 0) {
            for (int i = 0; i < n; ++i) cout << (bestSel[i] ? '1' : '0');
            cout << "\n";
            return 0;
        }
    }

    int runs = 0;
    while (time_left() > 0.15 && runs < 12) {
        vector<int> rnd = order;
        shuffle(rnd.begin(), rnd.end(), rng);
        long long err;
        auto sel = beam_solve(a, T, rnd, K, err);
        hill_climb_improve(a, T, sel);
        err = abs_ll(subset_sum_from_sel(a, sel) - T);
        if (err < bestErr) { bestErr = err; bestSel = sel; }
        if (bestErr == 0) break;
        ++runs;
    }

    if (bestErr != 0 && time_left() > 0.10) {
        hill_climb_improve(a, T, bestSel);
        bestErr = abs_ll(subset_sum_from_sel(a, bestSel) - T);
    }

    if (bestErr != 0 && time_left() > 0.12) {
        int trials = 30;
        int mChoose = min(34, n);
        toggle_mitm_improve(rng, a, T, bestSel, trials, mChoose);
        bestErr = abs_ll(subset_sum_from_sel(a, bestSel) - T);
    }

    for (int i = 0; i < n; ++i) cout << (bestSel[i] ? '1' : '0');
    cout << "\n";
    return 0;
}