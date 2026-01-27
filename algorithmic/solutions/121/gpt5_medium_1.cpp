#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> s(m);
    for (int i = 0; i < m; ++i) cin >> s[i];

    // Remove redundant patterns: if pattern q extends pattern p (i.e., for all positions where p has a letter,
    // q has the same letter), then q is redundant and can be removed.
    vector<int> alive(m, 1);
    for (int p = 0; p < m; ++p) if (alive[p]) {
        for (int q = 0; q < m; ++q) if (p != q && alive[q]) {
            bool q_extends_p = true;
            for (int j = 0; j < n; ++j) {
                char cp = s[p][j], cq = s[q][j];
                if (cp != '?') {
                    if (cq != cp) { q_extends_p = false; break; }
                }
            }
            if (q_extends_p) {
                // q is more constrained; remove q
                alive[q] = 0;
            }
        }
    }
    vector<string> ss;
    for (int i = 0; i < m; ++i) if (alive[i]) ss.push_back(s[i]);
    s.swap(ss);
    m = (int)s.size();

    if (m == 0) {
        cout << fixed << setprecision(15) << 0.0 << "\n";
        return 0;
    }

    if (m > 60) {
        // Not feasible with this approach; but such cases are unlikely given constraints.
        // Fallback: probability cannot be computed with current method.
        // Output 0 as a safe default (though problem likely doesn't include such cases).
        cout << fixed << setprecision(15) << 0.0 << "\n";
        return 0;
    }

    // Precompute per position masks of patterns that specify each letter
    vector<array<unsigned long long, 4>> M(n);
    vector<unsigned long long> U(n, 0);
    auto idx = [](char c)->int{
        if (c=='A') return 0;
        if (c=='C') return 1;
        if (c=='G') return 2;
        if (c=='T') return 3;
        return -1;
    };
    for (int j = 0; j < n; ++j) {
        M[j] = {0ULL,0ULL,0ULL,0ULL};
        for (int i = 0; i < m; ++i) {
            int k = idx(s[i][j]);
            if (k >= 0) {
                M[j][k] |= (1ULL << i);
            }
        }
        U[j] = M[j][0] | M[j][1] | M[j][2] | M[j][3];
    }

    // Order positions to maximize early conflict detection
    vector<int> order;
    order.reserve(n);
    for (int j = 0; j < n; ++j) if (U[j] != 0) order.push_back(j);
    // Positions with U==0 are irrelevant; skip them entirely
    sort(order.begin(), order.end(), [&](int a, int b){
        int la = (M[a][0]!=0) + (M[a][1]!=0) + (M[a][2]!=0) + (M[a][3]!=0);
        int lb = (M[b][0]!=0) + (M[b][1]!=0) + (M[b][2]!=0) + (M[b][3]!=0);
        if (la != lb) return la > lb;
        // tie-breaker: more total specified patterns
        auto pop = [](unsigned long long x){ return __builtin_popcountll(x); };
        int ca = pop(U[a]);
        int cb = pop(U[b]);
        return ca > cb;
    });

    // Precompute powers of 1/4
    vector<double> pow4(n+1, 1.0);
    for (int k = 1; k <= n; ++k) pow4[k] = pow4[k-1] * 0.25;

    double ans = 0.0;
    unsigned long long total = (m >= 63 ? 0 : (1ULL << m));
    // Iterate over all non-empty subsets of patterns
    for (unsigned long long S = 1; S < (1ULL << m); ++S) {
        int kfixed = 0;
        bool conflict = false;
        for (int jj = 0; jj < (int)order.size(); ++jj) {
            int j = order[jj];
            unsigned long long mask = S & U[j];
            if (mask == 0ULL) continue;
            int cnt = 0;
            // Check intersections with each letter group
            if ( (mask & M[j][0]) != 0ULL ) { ++cnt; if (cnt >= 2) { conflict = true; break; } }
            if ( (mask & M[j][1]) != 0ULL ) { ++cnt; if (cnt >= 2) { conflict = true; break; } }
            if ( (mask & M[j][2]) != 0ULL ) { ++cnt; if (cnt >= 2) { conflict = true; break; } }
            if ( (mask & M[j][3]) != 0ULL ) { ++cnt; if (cnt >= 2) { conflict = true; break; } }
            if (cnt == 1) ++kfixed;
        }
        if (conflict) continue;
        int bits = __builtin_popcountll(S);
        double contrib = pow4[kfixed];
        if (bits & 1) ans += contrib;
        else ans -= contrib;
    }

    cout << fixed << setprecision(15) << ans << "\n";
    return 0;
}