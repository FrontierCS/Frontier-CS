#include <bits/stdc++.h>
using namespace std;

struct Cand {
    long long sum;
    uint64_t bits0;
    uint64_t bits1;
    long long diff;
};

static inline void setbit(Cand &c, int idx) {
    if (idx < 64) c.bits0 |= (1ULL << idx);
    else c.bits1 |= (1ULL << (idx - 64));
}
static inline bool getbit(const Cand &c, int idx) {
    if (idx < 64) return (c.bits0 >> idx) & 1ULL;
    else return (c.bits1 >> (idx - 64)) & 1ULL;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    long long T;
    if (!(cin >> n >> T)) return 0;
    vector<long long> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT_SEC = 1.80;

    // Initial candidate (empty set)
    auto bestCand = Cand{0LL, 0ULL, 0ULL, llabs(T - 0LL)};

    vector<int> order_orig(n);
    iota(order_orig.begin(), order_orig.end(), 0);

    vector<int> order_desc = order_orig;
    sort(order_desc.begin(), order_desc.end(), [&](int i, int j){ return a[i] > a[j]; });

    vector<int> order_asc = order_orig;
    sort(order_asc.begin(), order_asc.end(), [&](int i, int j){ return a[i] < a[j]; });

    // Prepare RNG
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    mt19937_64 rng(seed);

    auto beam_search = [&](const vector<int>& order, int W) -> Cand {
        vector<Cand> cur;
        cur.reserve(W);
        cur.push_back({0LL, 0ULL, 0ULL, llabs(T - 0LL)});
        for (int idx : order) {
            long long ai = a[idx];
            vector<Cand> tmp;
            tmp.reserve(min(W * 2, 40000));
            // Expand
            for (const auto &c : cur) {
                tmp.push_back(c); // keep
                Cand t = c; // take
                t.sum += ai;
                setbit(t, idx);
                t.diff = llabs(T - t.sum);
                tmp.push_back(t);
            }
            // Prune to width W
            if ((int)tmp.size() > W) {
                nth_element(tmp.begin(), tmp.begin() + W, tmp.end(),
                            [](const Cand &x, const Cand &y){
                                if (x.diff != y.diff) return x.diff < y.diff;
                                return x.sum < y.sum;
                            });
                tmp.resize(W);
            }
            cur.swap(tmp);
        }
        // pick best
        Cand best = cur[0];
        for (auto &c : cur) if (c.diff < best.diff) best = c;
        return best;
    };

    auto improve_local = [&](Cand cur) -> Cand {
        // Convert bits to vector<char> for convenience
        vector<char> bits(n, 0);
        for (int i = 0; i < n; ++i) bits[i] = getbit(cur, i) ? 1 : 0;
        long long sum = cur.sum;
        long long bestDiff = llabs(T - sum);
        bool improved = true;

        // 1-flip hill climbing
        while (improved) {
            improved = false;
            int bestIdx = -1;
            long long bestNewDiff = bestDiff;
            for (int i = 0; i < n; ++i) {
                long long delta = bits[i] ? -a[i] : a[i];
                long long newSum = sum + delta;
                long long newDiff = llabs(T - newSum);
                if (newDiff < bestNewDiff) {
                    bestNewDiff = newDiff;
                    bestIdx = i;
                }
            }
            if (bestIdx != -1) {
                long long delta = bits[bestIdx] ? -a[bestIdx] : a[bestIdx];
                bits[bestIdx] ^= 1;
                sum += delta;
                bestDiff = bestNewDiff;
                improved = true;
            }
        }

        // 2-flip improvement (a few iterations)
        for (int it = 0; it < 2; ++it) {
            long long curDiff = llabs(T - sum);
            long long bestNewDiff = curDiff;
            int bi = -1, bj = -1;
            for (int i = 0; i < n; ++i) {
                long long di = bits[i] ? -a[i] : a[i];
                for (int j = i + 1; j < n; ++j) {
                    long long dj = bits[j] ? -a[j] : a[j];
                    long long newSum = sum + di + dj;
                    long long newDiff = llabs(T - newSum);
                    if (newDiff < bestNewDiff) {
                        bestNewDiff = newDiff;
                        bi = i; bj = j;
                    }
                }
            }
            if (bi != -1) {
                bits[bi] ^= 1;
                bits[bj] ^= 1;
                sum += (bits[bi] ? a[bi] : -a[bi]); // This is incorrect; recompute properly:
                // Fix: recompute sum change accurately:
                // But simpler: recalc sum by adding both deltas computed earlier would require storing them.
                // Instead, recompute sum directly from scratch if needed. For performance, do direct deltas:
            }
            if (bi != -1) {
                // Apply deltas correctly
                long long di = bits[bi] ? a[bi] : -a[bi]; // after toggle, this is +a if now 1, else -a
                long long dj = bits[bj] ? a[bj] : -a[bj];
                // But this gives net change from before? We toggled bits already, so to compute change:
                // original change should be di' + dj' where di' = (new - old) = (bits^1? a : -a)
                // To avoid confusion, compute using previous sum and re-evaluate:
                // Instead, recompute sum succinctly:
                sum = 0;
                for (int k = 0; k < n; ++k) if (bits[k]) sum += a[k];
                bestDiff = llabs(T - sum);
            } else break;
        }

        // Build Cand
        Cand res;
        res.sum = sum;
        res.bits0 = 0ULL; res.bits1 = 0ULL;
        for (int i = 0; i < n; ++i) if (bits[i]) setbit(res, i);
        res.diff = llabs(T - res.sum);
        return res;
    };

    auto try_order = [&](const vector<int>& ord, int W) {
        Cand c = beam_search(ord, W);
        if (c.diff < bestCand.diff) bestCand = c;
        Cand imp = improve_local(c);
        if (imp.diff < bestCand.diff) bestCand = imp;
    };

    int W_large = min(10000, 2000 + 80 * n); // adaptive
    int W_small = max(3000, W_large / 2);

    try_order(order_desc, W_large);
    if (chrono::duration<double>(chrono::steady_clock::now() - start).count() < TIME_LIMIT_SEC * 0.5)
        try_order(order_asc, W_large);
    if (chrono::duration<double>(chrono::steady_clock::now() - start).count() < TIME_LIMIT_SEC * 0.75)
        try_order(order_orig, W_large);

    // Random restarts while time left
    vector<int> order_rand = order_orig;
    while (chrono::duration<double>(chrono::steady_clock::now() - start).count() < TIME_LIMIT_SEC) {
        shuffle(order_rand.begin(), order_rand.end(), rng);
        try_order(order_rand, W_small);
    }

    // Output result as binary string of length n
    string out(n, '0');
    for (int i = 0; i < n; ++i) {
        if (getbit(bestCand, i)) out[i] = '1';
    }
    cout << out << "\n";
    return 0;
}