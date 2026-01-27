#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> s(m);
    for (int i = 0; i < m; ++i) cin >> s[i];

    int SZ = 1 << m;
    // cnt for single letters A,C,G,T (0..3)
    vector<uint32_t> cnt_a[4];
    for (int a = 0; a < 4; ++a) cnt_a[a].assign(SZ, 0);

    // cnt for unions of pairs (A,C),(A,G),(A,T),(C,G),(C,T),(G,T)
    vector<uint32_t> cnt_pair[6];
    for (int p = 0; p < 6; ++p) cnt_pair[p].assign(SZ, 0);

    auto letter_id = [](char c)->int{
        if (c=='A') return 0;
        if (c=='C') return 1;
        if (c=='G') return 2;
        if (c=='T') return 3;
        return -1;
    };

    // For each position, build masks for each letter and accumulate counts
    for (int j = 0; j < n; ++j) {
        uint32_t mask[4] = {0,0,0,0};
        for (int i = 0; i < m; ++i) {
            int id = letter_id(s[i][j]);
            if (id >= 0) mask[id] |= (1u << i);
        }
        for (int a = 0; a < 4; ++a) {
            cnt_a[a][mask[a]]++;
        }
        // pairs mapping indices
        // pairs order: (0,1)->0, (0,2)->1, (0,3)->2, (1,2)->3, (1,3)->4, (2,3)->5
        cnt_pair[0][ mask[0] | mask[1] ]++;
        cnt_pair[1][ mask[0] | mask[2] ]++;
        cnt_pair[2][ mask[0] | mask[3] ]++;
        cnt_pair[3][ mask[1] | mask[2] ]++;
        cnt_pair[4][ mask[1] | mask[3] ]++;
        cnt_pair[5][ mask[2] | mask[3] ]++;
    }

    // SOS DP: transform cnt arrays into H arrays where H[Z] = sum_{Y subset Z} cnt[Y]
    auto sos = [&](vector<uint32_t>& f){
        for (int i = 0; i < m; ++i) {
            for (int mask = 0; mask < SZ; ++mask) {
                if (mask & (1<<i)) {
                    f[mask] += f[mask ^ (1<<i)];
                }
            }
        }
    };
    for (int a = 0; a < 4; ++a) sos(cnt_a[a]);
    for (int p = 0; p < 6; ++p) sos(cnt_pair[p]);

    // Precompute powers of 1/4
    vector<double> pow4inv(n+1, 1.0);
    for (int k = 1; k <= n; ++k) pow4inv[k] = pow4inv[k-1] * 0.25;

    uint32_t full = SZ - 1;
    double ans = 0.0;

    for (int X = 1; X < SZ; ++X) {
        uint32_t comp = full ^ (uint32_t)X;
        uint32_t S[4];
        for (int a = 0; a < 4; ++a) {
            S[a] = cnt_a[a][comp]; // number of positions where (X & M_a[j]) == 0
        }
        // Check conflicts using pair counts
        bool conflict = false;
        // pairs indices mapping
        // (0,1)->0, (0,2)->1, (0,3)->2, (1,2)->3, (1,3)->4, (2,3)->5
        int pa = 0;
        for (int a = 0; a < 4 && !conflict; ++a) {
            for (int b = a+1; b < 4; ++b, ++pa) {
                uint32_t Sab = cnt_pair[pa][comp]; // positions where both empty for a and b
                uint32_t cab = (uint32_t)n - S[a] - S[b] + Sab; // positions where both hit -> conflict
                if (cab > 0) { conflict = true; break; }
            }
        }
        if (conflict) continue;
        // k = sum over letters of positions where hit (since no overlaps across letters)
        uint32_t k = 0;
        for (int a = 0; a < 4; ++a) {
            k += (uint32_t)n - S[a];
        }
        double contrib = pow4inv[k];
        if (__builtin_popcount((unsigned)X) & 1) ans += contrib;
        else ans -= contrib;
    }

    cout.setf(std::ios::fixed); 
    cout << setprecision(12) << ans << "\n";
    return 0;
}