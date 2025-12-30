#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;

struct Result {
    vector<int> exps;
    long long nsum;
    bool ok;
};

Result compute_for_M(ull k, int M) {
    Result res;
    res.ok = false;
    res.nsum = 0;
    if (M <= 0) return res;
    if ((ull)M > k - 1) return res;

    ull S = k - 1 + (ull)M;
    if (S & 1ULL) return res; // must be even since sum of even powers of two

    ull T = S >> 1; // S = 2 * T
    const int MAXB = 64;
    vector<long long> cnt(MAXB, 0);

    int cntTerms = 0;
    int pos = 0;
    while (T) {
        if (T & 1ULL) {
            if (pos + 1 >= MAXB) return res;
            cnt[pos + 1] += 1;
            cntTerms++;
        }
        T >>= 1;
        pos++;
    }

    if (cntTerms > M) return res;

    // Min-heap of t (>=2) values to split, pushing duplicates according to count
    priority_queue<int, vector<int>, greater<int>> pq;
    for (int t = 2; t < MAXB; ++t) {
        for (long long c = 0; c < cnt[t]; ++c) pq.push(t);
    }

    while (cntTerms < M) {
        if (pq.empty()) return res; // shouldn't happen if M <= k-1
        int t = pq.top(); pq.pop();
        cnt[t]--;
        cnt[t - 1] += 2;
        if (t - 1 >= 2) { pq.push(t - 1); pq.push(t - 1); }
        cntTerms++;
    }

    vector<int> exps;
    exps.reserve(M);
    long long nsum = 0;
    for (int t = 1; t < MAXB; ++t) {
        for (long long c = 0; c < cnt[t]; ++c) {
            exps.push_back(t);
            nsum += t;
        }
    }
    if ((int)exps.size() != M) return res;

    res.exps = move(exps);
    res.nsum = nsum;
    res.ok = true;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int q;
    if (!(cin >> q)) return 0;
    vector<ull> ks(q);
    for (int i = 0; i < q; ++i) cin >> ks[i];

    for (int qi = 0; qi < q; ++qi) {
        ull k = ks[qi];

        vector<int> bestExps;
        long long bestN = (1LL<<60);
        bool found = false;

        // Try M up to 60 first (sufficient for k up to 1e18)
        int Mmax1 = (int)min<ull>(60ULL, k - 1);
        for (int M = 1; M <= Mmax1; ++M) {
            Result r = compute_for_M(k, M);
            if (r.ok && r.nsum < bestN) {
                bestN = r.nsum;
                bestExps = r.exps;
                found = true;
            }
        }

        // Fallback: try a bit larger M if not found (very unlikely)
        if (!found) {
            int Mmax2 = (int)min<ull>(200ULL, k - 1);
            for (int M = 1; M <= Mmax2; ++M) {
                Result r = compute_for_M(k, M);
                if (r.ok && r.nsum < bestN) {
                    bestN = r.nsum;
                    bestExps = r.exps;
                    found = true;
                }
            }
        }

        // As a last resort (for very small k), handle trivial cases
        if (!found) {
            // For k >= 2, we can always take M = k-1 blocks of size 1:
            // total count = M*2 - (M-1) = M+1 = k
            int M = (int)(k - 1);
            bestExps.assign(M, 1);
            bestN = M;
            found = true;
        }

        long long n = 0;
        for (int t : bestExps) n += t;

        cout << n << "\n";
        vector<int> perm;
        perm.reserve((size_t)n);
        int cur = (int)n - 1;
        for (int t : bestExps) {
            int start = cur - t + 1;
            for (int j = 0; j < t; ++j) {
                perm.push_back(start + j);
            }
            cur -= t;
        }
        for (int i = 0; i < (int)perm.size(); ++i) {
            if (i) cout << ' ';
            cout << perm[i];
        }
        cout << "\n";
    }
    return 0;
}