#include <bits/stdc++.h>
using namespace std;

int get_lis(const vector<long long>& arr) {
    vector<long long> tails;
    for (auto num : arr) {
        auto it = lower_bound(tails.begin(), tails.end(), num);
        if (it == tails.end()) {
            tails.push_back(num);
        } else {
            *it = num;
        }
    }
    return tails.size();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    long long nn, xx;
    cin >> nn >> xx;
    int n = nn;
    vector<long long> t(n);
    for (int i = 0; i < n; i++) {
        cin >> t[i];
    }
    int m = min(11, n);
    int num_gaps = m - 1;
    vector<int> seg_len(m, n / m);
    int rem = n % m;
    for (int i = 0; i < rem; i++) {
        seg_len[i]++;
    }
    vector<int> start_pos(m + 1, 0);
    for (int i = 1; i <= m; i++) {
        start_pos[i] = start_pos[i - 1] + seg_len[i - 1];
    }
    vector<long long> minv(m, LLONG_MAX / 2);
    vector<long long> maxv(m, LLONG_MIN / 2);
    for (int i = 0; i < m; i++) {
        for (int j = start_pos[i]; j < start_pos[i + 1]; j++) {
            minv[i] = min(minv[i], t[j]);
            maxv[i] = max(maxv[i], t[j]);
        }
    }
    vector<tuple<int, int, long long>> ops;
    for (int g = 0; g < num_gaps; g++) {
        long long req = max(0LL, maxv[g] - minv[g + 1] + 1LL);
        long long dd = min(xx, req);
        int l = start_pos[g + 1] + 1;
        int r = n;
        ops.emplace_back(l, r, dd);
    }
    while ((int)ops.size() < 10) {
        ops.emplace_back(1, 1, 0LL);
    }
    vector<long long> modified = t;
    for (auto [l, r, d] : ops) {
        for (int ii = l - 1; ii < r; ii++) {
            modified[ii] += d;
        }
    }
    int len = get_lis(modified);
    cout << len << '\n';
    for (auto [l, r, d] : ops) {
        cout << l << ' ' << r << ' ' << (long long)d << '\n';
    }
    return 0;
}