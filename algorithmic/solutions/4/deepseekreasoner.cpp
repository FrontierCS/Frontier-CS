#include <bits/stdc++.h>
using namespace std;
using ll = long long;

int main() {
    int n, k;
    scanf("%d %d", &n, &k);
    
    vector<vector<ll>> cache(n+1, vector<ll>(n+1));
    vector<vector<bool>> known(n+1, vector<bool>(n+1, false));
    int query_count = 0;
    
    auto get_value = [&](int i, int j) -> ll {
        if (known[i][j]) return cache[i][j];
        printf("QUERY %d %d\n", i, j);
        fflush(stdout);
        ll val;
        scanf("%lld", &val);
        cache[i][j] = val;
        known[i][j] = true;
        query_count++;
        return val;
    };
    
    // Sample diagonal and anti-diagonal
    vector<ll> samples;
    for (int i = 1; i <= n; i++) {
        samples.push_back(get_value(i, i));
    }
    for (int i = 1; i <= n; i++) {
        int j = n + 1 - i;
        if (i != j) {
            samples.push_back(get_value(i, j));
        }
    }
    sort(samples.begin(), samples.end());
    ll min_val = samples[0];
    ll max_val = samples.back();
    
    // Count elements <= mid
    auto count_le = [&](ll mid) -> ll {
        int col = n;
        ll total = 0;
        for (int row = 1; row <= n; row++) {
            while (col >= 1) {
                ll v = get_value(row, col);
                if (v > mid) {
                    col--;
                } else {
                    break;
                }
            }
            total += col;
            if (col == 0) break; // remaining rows will also have 0
        }
        return total;
    };
    
    // Binary search on sampled values
    int idx_low = 0, idx_high = (int)samples.size() - 1;
    int target_idx = idx_high;
    while (idx_low < idx_high) {
        int mid_idx = (idx_low + idx_high) / 2;
        ll cnt = count_le(samples[mid_idx]);
        if (cnt >= k) {
            idx_high = mid_idx;
            target_idx = mid_idx;
        } else {
            idx_low = mid_idx + 1;
        }
    }
    
    ll ans;
    if (target_idx == 0) {
        ans = samples[0];
    } else {
        ll L = samples[target_idx-1];
        ll R = samples[target_idx];
        if (R == L) {
            ans = L;
        } else {
            ll low = L + 1, high = R;
            while (low < high) {
                ll mid = low + (high - low) / 2;
                ll cnt = count_le(mid);
                if (cnt >= k) {
                    high = mid;
                } else {
                    low = mid + 1;
                }
            }
            ans = low;
        }
    }
    
    printf("DONE %lld\n", ans);
    fflush(stdout);
    return 0;
}