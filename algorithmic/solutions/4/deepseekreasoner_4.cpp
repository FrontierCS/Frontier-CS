#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cassert>

using namespace std;

typedef long long ll;

int n;
ll k;
vector<vector<ll>> val;
vector<vector<bool>> vis;
int query_count = 0;

ll query(int x, int y) {
    if (!vis[x][y]) {
        cout << "QUERY " << x << " " << y << endl;
        cin >> val[x][y];
        vis[x][y] = true;
        ++query_count;
    }
    return val[x][y];
}

// Count number of elements <= v using staircase walk
ll count(ll v) {
    ll cnt = 0;
    int i = 1, j = n;
    while (i <= n && j >= 1) {
        ll cur = query(i, j);
        if (cur <= v) {
            cnt += j;
            ++i;
        } else {
            --j;
        }
    }
    return cnt;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> k;
    val.assign(n+1, vector<ll>(n+1, 0));
    vis.assign(n+1, vector<bool>(n+1, false));

    // Quick checks for corner cases
    if (k == 1) {
        ll ans = query(1, 1);
        cout << "DONE " << ans << endl;
        return 0;
    }
    if (k == (ll)n * n) {
        ll ans = query(n, n);
        cout << "DONE " << ans << endl;
        return 0;
    }

    // Sample a grid of points
    int step = max(1, n / 20);  // aim for about 20x20 = 400 samples
    vector<int> rows, cols;
    for (int i = 1; i <= n; i += step)
        rows.push_back(i);
    if (rows.back() != n)
        rows.push_back(n);
    for (int j = 1; j <= n; j += step)
        cols.push_back(j);
    if (cols.back() != n)
        cols.push_back(n);

    vector<ll> samples;
    for (int r : rows) {
        for (int c : cols) {
            samples.push_back(query(r, c));
        }
    }
    sort(samples.begin(), samples.end());
    samples.erase(unique(samples.begin(), samples.end()), samples.end());

    // Binary search on the sample values
    int left = 0, right = (int)samples.size() - 1;
    ll cnt_left = count(samples[left]);
    if (cnt_left >= k) {
        cout << "DONE " << samples[left] << endl;
        return 0;
    }
    while (left < right) {
        int mid = (left + right) / 2;
        ll cnt_mid = count(samples[mid]);
        if (cnt_mid >= k) {
            right = mid;
        } else {
            left = mid + 1;
        }
    }
    ll R = samples[left];
    ll cnt_R = count(R);  // already known if left==right from loop, but compute again to be safe
    ll L = (left > 0) ? samples[left-1] : (R - 1);
    ll cnt_L = (left > 0) ? count(L) : 0;

    // Now apply secant method to narrow the interval [L, R]
    ll x1 = L, y1 = cnt_L;
    ll x2 = R, y2 = cnt_R;
    const int MAX_SECANT = 5;
    for (int iter = 0; iter < MAX_SECANT; ++iter) {
        if (x2 - x1 <= 1)
            break;
        if (y2 == y1)
            break;
        // Use long double to avoid overflow in interpolation
        long double fraction = (long double)(k - y1) / (y2 - y1);
        long long delta = (long long)((long double)(x2 - x1) * fraction);
        ll x3 = x1 + delta;
        if (x3 <= x1) x3 = x1 + 1;
        if (x3 >= x2) x3 = x2 - 1;
        ll y3 = count(x3);
        if (y3 < k) {
            x1 = x3;
            y1 = y3;
        } else {
            x2 = x3;
            y2 = y3;
        }
    }

    // Final binary search on [x1+1, x2]
    ll lo = x1 + 1, hi = x2;
    while (lo < hi) {
        ll mid = (lo + hi) / 2;
        ll cnt = count(mid);
        if (cnt >= k) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    cout << "DONE " << lo << endl;

    return 0;
}