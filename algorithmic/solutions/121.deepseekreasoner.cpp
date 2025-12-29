#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(0);
    cout << fixed << setprecision(15);
    
    int n, m;
    cin >> n >> m;
    vector<string> s(m);
    for (int i = 0; i < m; i++) {
        cin >> s[i];
    }
    
    vector<int> conflict_mask(m, 0);
    // Build conflict masks per position
    for (int j = 0; j < n; j++) {
        int mask[4] = {0};
        for (int i = 0; i < m; i++) {
            char c = s[i][j];
            if (c == 'A') mask[0] |= (1 << i);
            else if (c == 'C') mask[1] |= (1 << i);
            else if (c == 'G') mask[2] |= (1 << i);
            else if (c == 'T') mask[3] |= (1 << i);
        }
        int all_fixed = mask[0] | mask[1] | mask[2] | mask[3];
        for (int l = 0; l < 4; l++) {
            int other = all_fixed ^ mask[l];
            int msk = mask[l];
            while (msk) {
                int i = __builtin_ctz(msk);
                conflict_mask[i] |= other;
                msk &= msk - 1;
            }
        }
    }
    
    int total_masks = 1 << m;
    vector<bool> indep(total_masks, false);
    indep[0] = true;
    for (int mask = 1; mask < total_masks; mask++) {
        int lowbit = mask & -mask;
        int i = __builtin_ctz(lowbit);
        int rest = mask ^ lowbit;
        if (indep[rest] && ((rest & conflict_mask[i]) == 0)) {
            indep[mask] = true;
        }
    }
    
    // Compute mask_fixed for each position
    vector<int> pos_mask(n, 0);
    for (int j = 0; j < n; j++) {
        int mask = 0;
        for (int i = 0; i < m; i++) {
            if (s[i][j] != '?') {
                mask |= (1 << i);
            }
        }
        pos_mask[j] = mask;
    }
    
    vector<int> cnt(total_masks, 0);
    for (int j = 0; j < n; j++) {
        cnt[pos_mask[j]]++;
    }
    
    // SOS DP: F[mask] = sum over subsets of mask
    vector<int> F = cnt;
    for (int i = 0; i < m; i++) {
        for (int mask = 0; mask < total_masks; mask++) {
            if (mask & (1 << i)) {
                F[mask] += F[mask ^ (1 << i)];
            }
        }
    }
    
    // Precompute powers of 0.25
    vector<double> pow25(n + 1);
    pow25[0] = 1.0;
    for (int i = 1; i <= n; i++) {
        pow25[i] = pow25[i - 1] * 0.25;
    }
    
    double ans = 0.0;
    int all_bits = total_masks - 1;
    for (int mask = 1; mask < total_masks; mask++) {
        if (!indep[mask]) continue;
        int sz = __builtin_popcount(mask);
        int sign = (sz % 2 == 1) ? 1 : -1;
        int comp = all_bits ^ mask;
        int count = F[comp];
        int fixed_count = n - count;
        ans += sign * pow25[fixed_count];
    }
    
    cout << ans << "\n";
    return 0;
}