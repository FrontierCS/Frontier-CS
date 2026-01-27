#include <bits/stdc++.h>
using namespace std;

struct State {
    long long sum;
    uint64_t lo, hi;
};

inline bool getBit(uint64_t lo, uint64_t hi, int i) {
    if (i < 64) return (lo >> i) & 1ULL;
    return (hi >> (i - 64)) & 1ULL;
}

inline void toggleBit(uint64_t &lo, uint64_t &hi, int i) {
    if (i < 64) lo ^= (1ULL << i);
    else hi ^= (1ULL << (i - 64));
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long T;
    if (!(cin >> n >> T)) return 0;
    vector<long long> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    const long double DELTA = 1e-4L;

    vector<State> cur, added, merged, trimmed;
    cur.reserve(400000);
    added.reserve(400000);
    merged.reserve(800000);
    trimmed.reserve(400000);

    // Initial state: empty subset, sum = 0
    cur.push_back({0, 0ULL, 0ULL});

    for (int idx = 0; idx < n; ++idx) {
        long long ai = a[idx];

        added.clear();
        added.reserve(cur.size());

        // Generate states including a[idx]
        for (size_t i = 0; i < cur.size(); ++i) {
            long long s = cur[i].sum;
            if (s + ai <= T) {
                State t = cur[i];
                t.sum = s + ai;
                if (idx < 64) t.lo |= (1ULL << idx);
                else t.hi |= (1ULL << (idx - 64));
                added.push_back(t);
            }
        }

        // Merge cur and added (both sorted by sum)
        merged.clear();
        merged.reserve(cur.size() + added.size());
        size_t p = 0, q = 0;
        while (p < cur.size() && q < added.size()) {
            if (cur[p].sum <= added[q].sum) merged.push_back(cur[p++]);
            else merged.push_back(added[q++]);
        }
        while (p < cur.size()) merged.push_back(cur[p++]);
        while (q < added.size()) merged.push_back(added[q++]);

        // Trim the merged list
        trimmed.clear();
        if (!merged.empty()) {
            State last = merged[0];
            trimmed.push_back(last);
            for (size_t i = 1; i < merged.size(); ++i) {
                long long s = merged[i].sum;
                if ((long double)s > (long double)last.sum * (1.0L + DELTA)) {
                    last = merged[i];
                    trimmed.push_back(last);
                }
            }
        }

        cur.swap(trimmed);
    }

    // Best from DP: largest sum <= T (cur is sorted)
    State best = cur.back();
    long long curSum = best.sum;
    uint64_t curLo = best.lo, curHi = best.hi;

    // Local search: hill climbing with 1- and 2-bit flips
    long long curErr = llabs(T - curSum);
    bool improved = true;
    while (improved) {
        improved = false;

        // Single-bit improvements
        for (int i = 0; i < n; ++i) {
            bool sel = getBit(curLo, curHi, i);
            long long newSum = curSum + (sel ? -a[i] : a[i]);
            long long newErr = llabs(T - newSum);
            if (newErr < curErr) {
                toggleBit(curLo, curHi, i);
                curSum = newSum;
                curErr = newErr;
                improved = true;
            }
        }
        if (improved) continue;

        // Two-bit improvements
        int bestI = -1, bestJ = -1;
        long long bestSum = curSum;
        long long bestImprovement = 0;
        for (int i = 0; i < n; ++i) {
            bool selI = getBit(curLo, curHi, i);
            long long deltaI = selI ? -a[i] : a[i];
            for (int j = i + 1; j < n; ++j) {
                bool selJ = getBit(curLo, curHi, j);
                long long deltaJ = selJ ? -a[j] : a[j];
                long long newSum = curSum + deltaI + deltaJ;
                long long newErr = llabs(T - newSum);
                if (newErr < curErr) {
                    long long improvement = curErr - newErr;
                    if (improvement > bestImprovement) {
                        bestImprovement = improvement;
                        bestI = i;
                        bestJ = j;
                        bestSum = newSum;
                    }
                }
            }
        }
        if (bestI != -1) {
            toggleBit(curLo, curHi, bestI);
            toggleBit(curLo, curHi, bestJ);
            curSum = bestSum;
            curErr = llabs(T - curSum);
            improved = true;
        }
    }

    string ans;
    ans.reserve(n);
    for (int i = 0; i < n; ++i) {
        ans.push_back(getBit(curLo, curHi, i) ? '1' : '0');
    }
    cout << ans << '\n';

    return 0;
}