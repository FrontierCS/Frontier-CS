#include <bits/stdc++.h>
using namespace std;

struct Interactor {
    int n;
    long long qlimit = 50000;
    long long used = 0;

    vector<long long> val;
    vector<uint8_t> vis;

    Interactor(int n_) : n(n_) {
        size_t sz = size_t(n + 1) * size_t(n + 1);
        val.assign(sz, 0);
        vis.assign(sz, 0);
    }

    inline size_t idx(int x, int y) const {
        return size_t(x) * size_t(n + 1) + size_t(y);
    }

    long long get(int x, int y) {
        size_t id = idx(x, y);
        if (vis[id]) return val[id];
        if (used >= qlimit) {
            // Out of queries; terminate to avoid undefined behavior.
            // Best-effort: output something.
            cout << "DONE 0\n" << flush;
            exit(0);
        }
        cout << "QUERY " << x << ' ' << y << '\n' << flush;
        long long v;
        if (!(cin >> v)) exit(0);
        used++;
        vis[id] = 1;
        val[id] = v;
        return v;
    }

    long long count_leq(long long x, vector<int>* posOut = nullptr) {
        vector<int> local;
        vector<int>& pos = posOut ? *posOut : local;
        pos.assign(n + 1, 0);

        long long cnt = 0;
        int j = n;
        for (int i = 1; i <= n; i++) {
            while (j >= 1) {
                long long v = get(i, j);
                if (v <= x) break;
                --j;
            }
            pos[i] = j;
            cnt += j;
            if (j == 0) {
                for (int ii = i + 1; ii <= n; ii++) pos[ii] = 0;
                break;
            }
        }
        return cnt;
    }

    long long count_lt(long long x, vector<int>* posOut = nullptr) {
        vector<int> local;
        vector<int>& pos = posOut ? *posOut : local;
        pos.assign(n + 1, 0);

        long long cnt = 0;
        int j = n;
        for (int i = 1; i <= n; i++) {
            while (j >= 1) {
                long long v = get(i, j);
                if (v < x) break;
                --j;
            }
            pos[i] = j;
            cnt += j;
            if (j == 0) {
                for (int ii = i + 1; ii <= n; ii++) pos[ii] = 0;
                break;
            }
        }
        return cnt;
    }

    [[noreturn]] void done(long long ans) {
        cout << "DONE " << ans << '\n' << flush;
        // The interactor prints a score afterwards; read it if present.
        double score;
        if (cin >> score) {
            // ignore
        }
        exit(0);
    }
};

struct MinNode {
    long long v;
    int r, c, R;
    bool operator>(const MinNode& other) const { return v > other.v; }
};
struct MaxNode {
    long long v;
    int r, c, L;
    bool operator<(const MaxNode& other) const { return v < other.v; }
};

static inline int clampi(int x, int lo, int hi) {
    if (x < lo) return lo;
    if (x > hi) return hi;
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long k;
    if (!(cin >> n >> k)) return 0;

    Interactor it(n);
    long long N2 = 1LL * n * n;

    if (k <= 1) {
        long long ans = it.get(1, 1);
        it.done(ans);
    }
    if (k >= N2) {
        long long ans = it.get(n, n);
        it.done(ans);
    }

    auto merge_rows_smallest = [&](long long t) -> long long {
        priority_queue<MinNode, vector<MinNode>, greater<MinNode>> pq;
        pq = decltype(pq)();
        for (int i = 1; i <= n; i++) {
            long long v = it.get(i, 1);
            pq.push({v, i, 1, n});
        }
        long long ans = 0;
        for (long long step = 1; step <= t; step++) {
            auto cur = pq.top();
            pq.pop();
            ans = cur.v;
            if (step == t) break;
            if (cur.c < cur.R) {
                int nc = cur.c + 1;
                long long nv = it.get(cur.r, nc);
                pq.push({nv, cur.r, nc, cur.R});
            }
        }
        return ans;
    };

    auto merge_rows_largest = [&](long long t) -> long long {
        priority_queue<MaxNode> pq;
        for (int i = 1; i <= n; i++) {
            long long v = it.get(i, n);
            pq.push({v, i, n, 1});
        }
        long long ans = 0;
        for (long long step = 1; step <= t; step++) {
            auto cur = pq.top();
            pq.pop();
            ans = cur.v;
            if (step == t) break;
            if (cur.c > cur.L) {
                int nc = cur.c - 1;
                long long nv = it.get(cur.r, nc);
                pq.push({nv, cur.r, nc, cur.L});
            }
        }
        return ans;
    };

    // If k (or from the top) is small enough, do direct k-way merge on rows.
    long long tSmall = min(k, N2 - k + 1);
    if (tSmall + n <= 49000) {
        long long ans;
        if (k <= N2 - k + 1) ans = merge_rows_smallest(k);
        else ans = merge_rows_largest(N2 - k + 1);
        it.done(ans);
    }

    // Rank-narrowing + partial enumeration within (low, high] using row segments.
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Upper threshold: max of row ceil(k/n) is guaranteed >= k-th.
    int rBound = int((k + n - 1) / n);
    rBound = clampi(rBound, 1, n);
    long long highTh = it.get(rBound, n);

    vector<int> posHigh, posLow;
    long long cntHigh = it.count_leq(highTh, &posHigh);

    // If for some reason cntHigh < k (shouldn't happen), expand to full max.
    if (cntHigh < k) {
        highTh = it.get(n, n);
        cntHigh = it.count_leq(highTh, &posHigh);
    }

    posLow.assign(n + 1, 0);
    long long cntLow = 0;
    long long lowTh = LLONG_MIN; // informational only

    auto can_enumerate = [&](long long needSmall, long long needLarge, int nonemptyRows) -> bool {
        long long remaining = it.qlimit - it.used;
        long long need = min(needSmall, needLarge);
        return (long long)nonemptyRows + need + 10 <= remaining;
    };

    auto enumerate_answer = [&](long long needSmall, long long needLarge) -> long long {
        if (needSmall <= needLarge) {
            priority_queue<MinNode, vector<MinNode>, greater<MinNode>> pq;
            for (int i = 1; i <= n; i++) {
                int L = posLow[i] + 1;
                int R = posHigh[i];
                if (L <= R) {
                    long long v = it.get(i, L);
                    pq.push({v, i, L, R});
                }
            }
            long long ans = 0;
            for (long long step = 1; step <= needSmall; step++) {
                auto cur = pq.top();
                pq.pop();
                ans = cur.v;
                if (step == needSmall) break;
                if (cur.c < cur.R) {
                    int nc = cur.c + 1;
                    long long nv = it.get(cur.r, nc);
                    pq.push({nv, cur.r, nc, cur.R});
                }
            }
            return ans;
        } else {
            priority_queue<MaxNode> pq;
            for (int i = 1; i <= n; i++) {
                int L = posLow[i] + 1;
                int R = posHigh[i];
                if (L <= R) {
                    long long v = it.get(i, R);
                    pq.push({v, i, R, L});
                }
            }
            long long ans = 0;
            for (long long step = 1; step <= needLarge; step++) {
                auto cur = pq.top();
                pq.pop();
                ans = cur.v;
                if (step == needLarge) break;
                if (cur.c > cur.L) {
                    int nc = cur.c - 1;
                    long long nv = it.get(cur.r, nc);
                    pq.push({nv, cur.r, nc, cur.L});
                }
            }
            return ans;
        }
    };

    const int SAMPLES = 9;

    while (true) {
        if (cntHigh < k) {
            // Expand high to ensure correctness.
            long long mx = it.get(n, n);
            if (mx != highTh) {
                highTh = mx;
                cntHigh = it.count_leq(highTh, &posHigh);
            }
            if (cntHigh < k) {
                // Should never happen; fail-safe.
                break;
            }
        }

        long long candTotal = cntHigh - cntLow;
        if (candTotal <= 0) {
            // If interval collapsed, answer is <= highTh and > lowTh.
            // As a safe fallback, output highTh.
            it.done(highTh);
        }

        long long needSmall = k - cntLow;
        long long needLarge = cntHigh - k + 1;

        // Build prefix lengths and count non-empty rows.
        vector<long long> pref(n + 1, 0);
        int nonempty = 0;
        for (int i = 1; i <= n; i++) {
            int len = posHigh[i] - posLow[i];
            if (len > 0) nonempty++;
            pref[i] = pref[i - 1] + max(0, len);
        }
        candTotal = pref[n];
        if (candTotal <= 0) it.done(highTh);

        if (can_enumerate(needSmall, needLarge, nonempty)) {
            long long ans = enumerate_answer(needSmall, needLarge);
            it.done(ans);
        }

        long long remaining = it.qlimit - it.used;
        // If we can't afford another narrowing step and still enumerate, try again with enumeration anyway.
        if (remaining < (long long)2 * n + SAMPLES + 200) {
            // Best effort: attempt enumeration from whichever side is cheaper anyway.
            if ((long long)nonempty + min(needSmall, needLarge) + 10 <= remaining) {
                long long ans = enumerate_answer(needSmall, needLarge);
                it.done(ans);
            } else {
                // As a last resort, output highTh (likely incorrect, but prevents UB).
                it.done(highTh);
            }
        }

        // Sample pivot values from candidate segments (posLow+1 .. posHigh) uniformly by position.
        vector<long long> samp;
        samp.reserve(SAMPLES);
        uniform_int_distribution<long long> distPick(1, candTotal);

        for (int s = 0; s < SAMPLES; s++) {
            long long pick = distPick(rng);
            int row = int(lower_bound(pref.begin() + 1, pref.end(), pick) - pref.begin());
            int len = posHigh[row] - posLow[row];
            if (len <= 0) { s--; continue; }
            uniform_int_distribution<int> distCol(1, len);
            int col = posLow[row] + distCol(rng);
            samp.push_back(it.get(row, col));
        }

        sort(samp.begin(), samp.end());

        double q = double(needSmall) / double(candTotal);
        int idx = int(q * double(SAMPLES - 1));
        idx = clampi(idx, 0, SAMPLES - 1);
        long long pivot = samp[idx];

        vector<int> posPivot;
        long long cntPivot = it.count_leq(pivot, &posPivot);

        if (cntPivot >= k) {
            // Tighten high
            if (pivot == highTh && cntPivot == cntHigh) {
                // Can't shrink; handle duplicates by moving below pivot if needed.
                vector<int> posLess;
                long long cntLess = it.count_lt(pivot, &posLess);
                if (cntLess < k) {
                    it.done(pivot);
                }
                // Exclude pivot and above: new high threshold is < pivot.
                if (pivot == LLONG_MIN) {
                    it.done(pivot);
                }
                highTh = pivot - 1;
                posHigh.swap(posLess);
                cntHigh = cntLess;
            } else {
                highTh = pivot;
                posHigh.swap(posPivot);
                cntHigh = cntPivot;
            }
        } else {
            // Tighten low
            lowTh = pivot;
            posLow.swap(posPivot);
            cntLow = cntPivot;
        }
    }

    // Fallback: should not reach.
    it.done(0);
}