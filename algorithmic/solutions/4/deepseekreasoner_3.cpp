#include <bits/stdc++.h>
using namespace std;
using ll = long long;

map<pair<int,int>, ll> cache;

ll query(int x, int y) {
    auto key = make_pair(x, y);
    if (cache.count(key)) return cache[key];
    cout << "QUERY " << x << " " << y << endl;
    ll val;
    cin >> val;
    cache[key] = val;
    return val;
}

ll count_le(ll x, int n) {
    int j = n;
    ll total = 0;
    for (int i = 1; i <= n; i++) {
        while (j > 0) {
            ll val = query(i, j);
            if (val > x) {
                j--;
            } else {
                break;
            }
        }
        total += j;
    }
    return total;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    cin >> n >> k;

    vector<ll> diag(n+1, 0);
    vector<bool> diag_queried(n+1, false);
    auto get_diag = [&](int i) {
        if (!diag_queried[i]) {
            diag[i] = query(i, i);
            diag_queried[i] = true;
        }
        return diag[i];
    };

    int lo = 1, hi = n;
    map<int, ll> count_at_index;

    while (lo < hi) {
        int mid = (lo + hi) / 2;
        ll x = get_diag(mid);
        ll c = count_le(x, n);
        count_at_index[mid] = c;
        if (c >= k) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }

    int i = lo;
    ll R_val = get_diag(i);
    ll count_R;
    if (count_at_index.count(i)) {
        count_R = count_at_index[i];
    } else {
        count_R = count_le(R_val, n);
        count_at_index[i] = count_R;
    }

    if (i == 1) {
        cout << "DONE " << R_val << endl;
        double score;
        cin >> score;
        return 0;
    }

    ll L_val = get_diag(i-1);
    ll count_L;
    if (count_at_index.count(i-1)) {
        count_L = count_at_index[i-1];
    } else {
        count_L = count_le(L_val, n);
        count_at_index[i-1] = count_L;
    }

    vector<ll> mid_vals;
    for (int col = 1; col < i; col++) {
        ll v = query(i, col);
        if (v > L_val && v < R_val) {
            mid_vals.push_back(v);
        }
    }
    for (int row = 1; row < i; row++) {
        ll v = query(row, i);
        if (v > L_val && v < R_val) {
            mid_vals.push_back(v);
        }
    }

    ll cnt_less = mid_vals.size();
    ll total_R = count_R - count_L - cnt_less;
    ll need = k - count_L;
    ll ans;

    if (need <= cnt_less) {
        sort(mid_vals.begin(), mid_vals.end());
        ans = mid_vals[need-1];
    } else {
        ans = R_val;
    }

    cout << "DONE " << ans << endl;
    double score;
    cin >> score;
    return 0;
}