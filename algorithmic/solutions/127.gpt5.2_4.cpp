#include <bits/stdc++.h>
using namespace std;

static long long isqrtll(long long x) {
    if (x <= 0) return 0;
    long long r = (long long) sqrtl((long double)x);
    while ((r + 1) > 0 && (r + 1) * (r + 1) <= x) ++r;
    while (r * r > x) --r;
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) {
        return 0;
    }

    vector<int> qL(n, 0), qR(n, 0), qRank(n, 0);
    vector<char> qKnown(n, 0);

    int rmax = -1;
    bool rmaxKnown = false;
    int K = -1;

    vector<int> prefixMemo(n + 1, -1);
    auto finish = [&](int idx) {
        if (idx < 0) idx = 0;
        if (idx >= n) idx = n - 1;
        cout << "! " << idx << "\n" << flush;
        exit(0);
    };

    auto ask = [&](int idx) -> bool {
        if (idx < 0 || idx >= n) return false;
        if (qKnown[idx]) return true;
        cout << "? " << idx << "\n" << flush;
        int a0, a1;
        if (!(cin >> a0 >> a1)) return false;
        qKnown[idx] = 1;
        qL[idx] = a0;
        qR[idx] = a1;
        qRank[idx] = a0 + a1 + 1;

        if (a0 == 0 && a1 == 0) finish(idx);

        if (rmaxKnown && qRank[idx] == rmax && prefixMemo[idx] == -1) prefixMemo[idx] = a0;
        return true;
    };

    auto computeUB = [&](int nn) -> int {
        long long term = nn;
        int ub = 0;
        while (term > 1) {
            term = isqrtll(term - 1);
            if (term <= 0) break;
            ub += (int)term;
        }
        return ub;
    };

    // Deterministically find a cheapest element by querying UB+1 indices (or all if n smaller).
    int UB = computeUB(n);
    int m = min(n, UB + 1);

    int cheapestIdx = 0;
    for (int i = 0; i < m; i++) {
        if (!ask(i)) finish(0);
        if (qRank[i] > rmax) {
            rmax = qRank[i];
            cheapestIdx = i;
        }
    }

    // Now rmax is the global maximum rank => cheapest type.
    rmaxKnown = true;

    // Ensure cheapestIdx is indeed cheapest (it should be, but just in case).
    if (!ask(cheapestIdx)) finish(0);

    K = qL[cheapestIdx] + qR[cheapestIdx]; // number of non-cheapest elements
    prefixMemo[0] = 0;
    prefixMemo[n] = K;

    // Backfill memo for any already-queried cheapest positions.
    for (int i = 0; i < n; i++) {
        if (qKnown[i] && qRank[i] == rmax) prefixMemo[i] = qL[i];
    }

    auto getPrefix = [&](int pos) -> int {
        if (pos < 0) pos = 0;
        if (pos > n) pos = n;
        if (prefixMemo[pos] != -1) return prefixMemo[pos];
        if (pos == 0) return 0;
        if (pos == n) return K;

        // Try querying pos itself (pos < n).
        if (!ask(pos)) finish(0);
        if (qRank[pos] == rmax) {
            prefixMemo[pos] = qL[pos];
            return prefixMemo[pos];
        }

        int rightLimit = min(n - 1, pos + K);
        for (int j = pos + 1; j <= rightLimit; j++) {
            if (!ask(j)) finish(0);
            if (qRank[j] == rmax) {
                if (prefixMemo[j] == -1) prefixMemo[j] = qL[j];
                prefixMemo[pos] = qL[j] - (j - pos);
                return prefixMemo[pos];
            }
        }

        int leftLimit = max(0, pos - K);
        for (int j = pos - 1; j >= leftLimit; j--) {
            if (!ask(j)) finish(0);
            if (qRank[j] == rmax) {
                if (prefixMemo[j] == -1) prefixMemo[j] = qL[j];
                prefixMemo[pos] = qL[j] + (pos - j - 1);
                return prefixMemo[pos];
            }
        }

        // Should be unreachable if rmax is correct.
        prefixMemo[pos] = 0;
        return 0;
    };

    vector<int> nonCheapest;
    nonCheapest.reserve(max(0, K));

    function<void(int,int,int,int)> solve = [&](int l, int r, int prefL, int prefR) {
        if (prefL == prefR) return;
        if (r - l == 1) {
            nonCheapest.push_back(l);
            return;
        }
        int mid = (l + r) >> 1;
        int prefM = getPrefix(mid);
        solve(l, mid, prefL, prefM);
        solve(mid, r, prefM, prefR);
    };

    solve(0, n, 0, K);

    for (int idx : nonCheapest) {
        if (!ask(idx)) finish(0);
        if (qRank[idx] == 1) finish(idx);
    }

    finish(0);
    return 0;
}