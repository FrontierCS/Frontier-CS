#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

// Count overlapping occurrences of pattern t in text x
int countOccur(const string &t, const string &x) {
    if (t.empty()) return 0;
    int cnt = 0;
    size_t pos = 0;
    while ((pos = x.find(t, pos)) != string::npos) {
        ++cnt;
        ++pos;
    }
    return cnt;
}

int main(int argc, char *argv[]) {
    registerTestlibCmd(argc, argv);

    // Read input
    int n, q;
    n = inf.readInt();
    q = inf.readInt();

    vector<string> s(n + 1);
    for (int i = 1; i <= n; i++) {
        s[i] = inf.readToken();
    }

    struct Query { int l, r, k; };
    vector<Query> queries(q);
    for (int i = 0; i < q; i++) {
        queries[i].l = inf.readInt();
        queries[i].r = inf.readInt();
        queries[i].k = inf.readInt();
    }

    // Read participant permutation — do NOT call ouf.readEof() after;
    // solutions may output a trailing newline which testlib treats as non-EOF.
    vector<int> p(n + 1);
    for (int i = 1; i <= n; i++) {
        p[i] = ouf.readInt(1, n, "permutation element out of range");
    }

    // Validate permutation (check for duplicates)
    vector<int> seen(n + 1, 0);
    for (int i = 1; i <= n; i++) {
        if (seen[p[i]]) {
            quitf(_wa, "permutation has duplicate value %d at position %d", p[i], i);
        }
        seen[p[i]] = 1;
    }

    // Collect which k-values actually appear in queries to avoid O(n) per pair
    vector<bool> usedK(n + 1, false);
    for (int i = 0; i < q; i++) {
        usedK[queries[i].k] = true;
    }
    vector<int> usedKList;
    for (int k = 1; k <= n; k++) {
        if (usedK[k]) usedKList.push_back(k);
    }

    // computeCost: given a permutation perm (1-indexed positions 1..n),
    // compute total candy cost over all queries.
    // prefix[i][k] = sum of occur(s[k], s[perm[j]]+s[perm[j+1]]) for j=1..i
    // We only compute for k in usedKList.
    auto computeCost = [&](const vector<int> &perm) -> long long {
        // Map each used k to a compact index
        int nk = (int)usedKList.size();
        // prefix[i][ki]: cumulative cost for pairs 1..i, ki-th used pattern
        // i in [0..n-1], ki in [0..nk-1]
        // We use a flat array for speed: prefix[i * nk + ki]
        vector<long long> prefix((n) * nk, 0LL);

        for (int i = 1; i <= n - 1; i++) {
            string merged = s[perm[i]] + s[perm[i + 1]];
            for (int ki = 0; ki < nk; ki++) {
                int k = usedKList[ki];
                long long prev = (i >= 2) ? prefix[(i - 1) * nk + ki] : 0LL;
                prefix[i * nk + ki] = prev + countOccur(s[k], merged);
            }
        }

        // Build a map from k to ki index for fast lookup
        vector<int> kToIdx(n + 1, -1);
        for (int ki = 0; ki < nk; ki++) {
            kToIdx[usedKList[ki]] = ki;
        }

        long long total = 0;
        for (auto &qr : queries) {
            int l = qr.l, r = qr.r, k = qr.k;
            int ki = kToIdx[k];
            if (ki == -1) continue; // shouldn't happen
            // pairs from l to r-1
            // sum = prefix[(r-1)*nk + ki] - prefix[(l-1)*nk + ki]
            // but prefix[0..] = 0 for i=0 (no pairs), pair i uses index i in 1..n-1
            long long hi = (r - 1 >= 1) ? prefix[(r - 1) * nk + ki] : 0LL;
            long long lo = (l - 1 >= 1) ? prefix[(l - 1) * nk + ki] : 0LL;
            total += (hi - lo);
        }
        return total;
    };

    // Baseline: identity permutation
    vector<int> base(n + 1);
    for (int i = 1; i <= n; i++) base[i] = i;

    long long Y = computeCost(p);
    long long B = computeCost(base);

    // Score formula from problem:
    //   score = 1000 * min(2, (B+1)/(Y+1))
    // We report ratio in [0,1] for quitp:
    //   ratio = score / 2000 = min(2, (B+1)/(Y+1)) / 2
    double rawRatio = (double)(B + 1) / (double)(Y + 1);
    double clamped = min(2.0, rawRatio);
    double displayScore = 1000.0 * clamped;
    double scoreRatio = clamped / 2.0;
    if (scoreRatio < 0.0) scoreRatio = 0.0;
    if (scoreRatio > 1.0) scoreRatio = 1.0;

    quitp(scoreRatio, "Y=%lld B=%lld score=%.6f Ratio: %.9f", Y, B, displayScore, scoreRatio);

    return 0;
}