#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> s(m);
    for (int i = 0; i < m; ++i) cin >> s[i];
    vector<int> charMap(256, -1);
    charMap['A'] = 0; charMap['C'] = 1; charMap['G'] = 2; charMap['T'] = 3;
    
    int M = 1 << m;
    vector<long long> c(M, 0); // counts of positions by Smask (patterns that specify that position)
    vector<unsigned long long> N(m, 0); // conflict adjacency masks
    
    // Build c[Smask] and conflict graph N
    for (int pos = 0; pos < n; ++pos) {
        unsigned long long Smask = 0;
        vector<pair<int,int>> specs; // (pattern idx, letter)
        specs.reserve(m);
        for (int i = 0; i < m; ++i) {
            int l = charMap[(unsigned char)s[i][pos]];
            if (l != -1) {
                Smask |= (1ULL << i);
                specs.emplace_back(i, l);
            }
        }
        c[(int)Smask]++;

        int k = (int)specs.size();
        for (int a = 0; a < k; ++a) {
            for (int b = a + 1; b < k; ++b) {
                if (specs[a].second != specs[b].second) {
                    int u = specs[a].first, v = specs[b].first;
                    N[u] |= (1ULL << v);
                    N[v] |= (1ULL << u);
                }
            }
        }
    }
    
    // SOS DP to compute H[mask] = sum_{S ⊆ mask} c[S]
    vector<long long> H = c;
    for (int b = 0; b < m; ++b) {
        for (int mask = 0; mask < M; ++mask) {
            if (mask & (1 << b)) {
                H[mask] += H[mask ^ (1 << b)];
            }
        }
    }
    
    // ok[mask]: mask is an independent set in conflict graph
    vector<char> ok(M, 0);
    ok[0] = 1;
    for (int mask = 1; mask < M; ++mask) {
        int lsb = mask & -mask;
        int i = __builtin_ctz(mask);
        int prev = mask ^ lsb;
        ok[mask] = ok[prev] && (( (unsigned long long)prev & N[i]) == 0ULL);
    }
    
    // Precompute powers of 1/4
    vector<long double> pow4inv(n + 1);
    pow4inv[0] = 1.0L;
    for (int i = 1; i <= n; ++i) pow4inv[i] = pow4inv[i - 1] * 0.25L;
    
    long double ans = 0.0L;
    for (int mask = 1; mask < M; ++mask) {
        if (!ok[mask]) continue;
        int comp = (~mask) & (M - 1);
        long long fixed = (long long)n - H[comp];
        int pc = __builtin_popcount((unsigned)mask);
        long double term = pow4inv[(int)fixed];
        if (pc & 1) ans += term;
        else ans -= term;
    }
    
    cout.setf(std::ios::fixed); 
    cout << setprecision(12) << (double)ans << "\n";
    return 0;
}