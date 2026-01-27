#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n;
    if (!(cin >> n)) return 0;
    // Vertices 0..n
    if (n == 0) {
        cout << 0 << "\n";
        return 0;
    }

    // Choose block size R ~ (2n)^(1/3), at least 1
    long long twoN = 2 * n;
    long long R = 1;
    while ((R+1)*(R+1)*(R+1) <= twoN) ++R;
    if (R < 1) R = 1;

    // Build boundary set S = {0, R, 2R, ..., floor(n/R)*R} plus n if not included
    vector<long long> S;
    for (long long x = 0; x <= n; x += R) S.push_back(x);
    if (S.back() != n) S.push_back(n);

    // Mark boundaries
    vector<char> isBoundary(n+1, 0);
    for (auto v : S) isBoundary[v] = 1;

    // To avoid duplicate u->v edges, track seen pairs
    struct PairHash {
        size_t operator()(const pair<long long,long long>& p) const noexcept {
            return (p.first * 1315423911u) ^ p.second;
        }
    };
    unordered_set<pair<long long,long long>, PairHash> seen;
    seen.reserve(200000);

    vector<array<long long,3>> ops;
    ops.reserve(200000);

    // 1) Add in-block edges for lengths 2..R (build sequentially via c = i+len-1)
    for (long long len = 2; len <= R; ++len) {
        for (long long i = 0; i + len <= n; ++i) {
            long long u = i;
            long long v = i + len;
            if (isBoundary[u] && isBoundary[v]) continue; // let boundary handling add these
            pair<long long,long long> key = {u, v};
            if (seen.find(key) != seen.end()) continue;
            long long c = v - 1; // u->(v-1) and (v-1)->v exist
            ops.push_back({u, c, v});
            seen.insert(key);
        }
    }

    // 2) Add adjacent boundary edges (between consecutive elements in S), skip if already direct (length 1)
    for (size_t t = 0; t + 1 < S.size(); ++t) {
        long long u = S[t], v = S[t+1];
        if (v - u <= 1) continue; // direct initial edge exists
        pair<long long,long long> key = {u, v};
        if (seen.find(key) != seen.end()) continue;
        long long c = v - 1; // u->(v-1) (<=R-1) and (v-1)->v exist
        ops.push_back({u, c, v});
        seen.insert(key);
    }

    // 3) Build longer boundary edges using DP over distance in S: use c = previous boundary (v' = S[t+dist-1])
    for (size_t dist = 2; dist < S.size(); ++dist) {
        for (size_t t = 0; t + dist < S.size(); ++t) {
            long long u = S[t];
            long long w = S[t + dist - 1];
            long long v = S[t + dist];
            pair<long long,long long> key = {u, v};
            if (seen.find(key) != seen.end()) continue;
            // u->w and w->v are ensured by previous steps
            long long c = w;
            ops.push_back({u, c, v});
            seen.insert(key);
        }
    }

    cout << ops.size() << "\n";
    for (auto &e : ops) {
        cout << e[0] << " " << e[1] << " " << e[2] << "\n";
    }
    return 0;
}