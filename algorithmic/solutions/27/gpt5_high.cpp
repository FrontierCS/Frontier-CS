#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;

    int lim = max(n, m);
    vector<int> primes;
    if (lim >= 2) {
        vector<bool> isP(lim + 1, true);
        isP[0] = isP[1] = false;
        for (int i = 2; i * 1LL * i <= lim; ++i) {
            if (isP[i]) {
                for (long long j = 1LL * i * i; j <= lim; j += i) isP[(int)j] = false;
            }
        }
        for (int i = 2; i <= lim; ++i) if (isP[i]) primes.push_back(i);
    }

    struct Plan {
        long long k = -1;
        int type = -1; // 0: plus-star, 1: orientation A (rows -> columns), 2: orientation B (columns -> rows)
        int p_or_q = -1;
    } best;

    // Candidate 0: union of row 1 and column 1
    best.k = (long long)n + m - 1;
    best.type = 0;

    // Candidate 1: Orientation A (rows heavy using columns structure)
    if (m >= 1) {
        for (int p : primes) {
            if (p > m) break;
            int S = min(m / p, p); // ensure S <= p
            if (S <= 0) continue;
            long long heavy = min((long long)n, 1LL * p * p);
            long long k = (long long)n + heavy * (S - 1);
            if (k > best.k) {
                best.k = k;
                best.type = 1;
                best.p_or_q = p;
            }
        }
    }

    // Candidate 2: Orientation B (columns heavy using rows structure)
    if (n >= 1) {
        for (int q : primes) {
            if (q > n) break;
            int T = min(n / q, q); // ensure T <= q
            if (T <= 0) continue;
            long long heavy = min((long long)m, 1LL * q * q);
            long long k = (long long)m + heavy * (T - 1);
            if (k > best.k) {
                best.k = k;
                best.type = 2;
                best.p_or_q = q;
            }
        }
    }

    vector<pair<int,int>> ans;
    ans.reserve((size_t)best.k);

    if (best.type == 0) {
        // union of row 1 and column 1
        for (int c = 1; c <= m; ++c) ans.emplace_back(1, c);
        for (int r = 2; r <= n; ++r) ans.emplace_back(r, 1);
    } else if (best.type == 1) {
        int p = best.p_or_q;
        int S = min(m / p, p);
        int heavy = (int)min((long long)n, 1LL * p * p);
        // heavy rows
        for (int i = 0; i < heavy; ++i) {
            int a = i / p;
            int b = i % p;
            for (int s = 0; s < S; ++s) {
                int x = (int)((1LL * a * s + b) % p);
                int col = s * p + x + 1;
                ans.emplace_back(i + 1, col);
            }
        }
        // light rows
        for (int i = heavy; i < n; ++i) {
            int b = i % p;
            int col = b + 1; // s=0 block
            ans.emplace_back(i + 1, col);
        }
    } else if (best.type == 2) {
        int q = best.p_or_q;
        int T = min(n / q, q);
        int heavy = (int)min((long long)m, 1LL * q * q);
        // heavy columns
        for (int j = 0; j < heavy; ++j) {
            int a = j / q;
            int b = j % q;
            for (int t = 0; t < T; ++t) {
                int y = (int)((1LL * a * t + b) % q);
                int row = t * q + y + 1;
                ans.emplace_back(row, j + 1);
            }
        }
        // light columns
        for (int j = heavy; j < m; ++j) {
            int b = (j - heavy) % q;
            int row = b + 1; // t=0 block
            ans.emplace_back(row, j + 1);
        }
    } else {
        // Fallback (should not happen): put everything in column 1
        for (int r = 1; r <= n; ++r) ans.emplace_back(r, 1);
    }

    cout << ans.size() << "\n";
    for (auto &pr : ans) {
        cout << pr.first << " " << pr.second << "\n";
    }
    return 0;
}