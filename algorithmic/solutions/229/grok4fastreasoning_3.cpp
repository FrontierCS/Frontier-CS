#include <bits/stdc++.h>
using namespace std;

int lis_length(const vector<long long>& arr) {
    if (arr.empty()) return 0;
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
    cin.tie(0);
    long long n_, x_;
    cin >> n_ >> x_;
    int n = n_;
    long long x = x_;
    vector<long long> t(n);
    for (int i = 0; i < n; i++) cin >> t[i];
    int NUM_SEGS = min(11, n);
    int block_size = n / NUM_SEGS;
    int extra = n % NUM_SEGS;
    vector<int> lefts(NUM_SEGS), rights(NUM_SEGS);
    int pos = 0;
    for (int i = 0; i < NUM_SEGS; i++) {
        int sz = block_size + (i < extra ? 1 : 0);
        lefts[i] = pos + 1;
        rights[i] = pos + sz;
        pos += sz;
    }
    vector<long long> seg_min(NUM_SEGS, LLONG_MAX / 2);
    vector<long long> seg_max(NUM_SEGS, LLONG_MIN / 2);
    vector<int> lis_lens(NUM_SEGS, 0);
    for (int i = 0; i < NUM_SEGS; i++) {
        long long mn = LLONG_MAX / 2, mx = LLONG_MIN / 2;
        vector<long long> sub;
        for (int j = lefts[i] - 1; j < rights[i]; j++) {
            long long val = t[j];
            sub.push_back(val);
            mn = min(mn, val);
            mx = max(mx, val);
        }
        seg_min[i] = mn;
        seg_max[i] = mx;
        if (!sub.empty()) lis_lens[i] = lis_length(sub);
    }
    vector<bool> can_connect(NUM_SEGS - 1, false);
    vector<long long> delta(NUM_SEGS - 1, 0);
    for (int k = 0; k < NUM_SEGS - 1; k++) {
        long long req = seg_max[k] - seg_min[k + 1] + 1;
        if (req <= x) {
            can_connect[k] = true;
            delta[k] = max(req, 0LL);
        }
    }
    vector<vector<int>> supers;
    vector<int> curr_super;
    for (int i = 0; i < NUM_SEGS; i++) {
        curr_super.push_back(i);
        if (i == NUM_SEGS - 1 || !can_connect[i]) {
            supers.push_back(curr_super);
            curr_super.clear();
        }
    }
    vector<tuple<int, int, long long>> ops;
    for (const auto& su : supers) {
        int m = su.size();
        if (m <= 1) continue;
        for (int jj = 1; jj < m; jj++) {
            int conn_k = su[jj - 1];
            long long d = delta[conn_k];
            int l = lefts[su[jj]];
            int r = rights[su.back()];
            ops.emplace_back(l, r, d);
        }
    }
    while (ops.size() < 10) {
        ops.emplace_back(1, 1, 0LL);
    }
    vector<long long> new_t = t;
    for (auto [l, r, d] : ops) {
        for (int j = l - 1; j < r; j++) {
            new_t[j] += d;
        }
    }
    int len = lis_length(new_t);
    cout << len << '\n';
    for (auto [l, r, d] : ops) {
        cout << l << " " << r << " " << d << '\n';
    }
    return 0;
}