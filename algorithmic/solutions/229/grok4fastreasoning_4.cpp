#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    long long x;
    cin >> n >> x;
    vector<long long> t(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> t[i];
    }
    
    long long best_lis = 0;
    vector<tuple<int, int, long long>> best_ops;
    
    for (int num = 1; num <= 11 && num <= n; ++num) {
        vector<int> p(num + 1, 0);
        int sz = n / num;
        int rem = n % num;
        for (int i = 1; i <= num; ++i) {
            int leni = sz + (i <= rem ? 1 : 0);
            p[i] = p[i - 1] + leni;
        }
        
        vector<long long> seg_mins(num + 1, 0);
        vector<long long> seg_maxs(num + 1, 0);
        vector<int> seg_lis(num + 1, 0);
        
        long long this_sum = 0;
        for (int s = 1; s <= num; ++s) {
            int l = p[s - 1] + 1;
            int r = p[s];
            if (l > r) continue;
            
            long long minv = LLONG_MAX;
            long long maxv = LLONG_MIN;
            vector<long long> tails;
            for (int i = l; i <= r; ++i) {
                long long numv = t[i];
                minv = min(minv, numv);
                maxv = max(maxv, numv);
                
                auto it = lower_bound(tails.begin(), tails.end(), numv);
                if (it == tails.end()) {
                    tails.push_back(numv);
                } else {
                    *it = numv;
                }
            }
            seg_lis[s] = tails.size();
            seg_mins[s] = minv;
            seg_maxs[s] = maxv;
            this_sum += seg_lis[s];
        }
        
        long long needed = 0;
        bool can_do = true;
        for (int s = 1; s < num; ++s) {
            long long mj = seg_maxs[s];
            long long mn = seg_mins[s + 1];
            long long dd = max(0LL, mj - mn + 1);
            if (dd > 0) {
                if (x == 0) {
                    can_do = false;
                    break;
                } else {
                    long long cops = (dd + x - 1) / x;
                    needed += cops;
                    if (needed > 10) {
                        can_do = false;
                        break;
                    }
                }
            }
        }
        
        if (can_do && needed <= 10) {
            if (this_sum > best_lis) {
                best_lis = this_sum;
                best_ops.clear();
                for (int s = 1; s < num; ++s) {
                    long long mj = seg_maxs[s];
                    long long mn = seg_mins[s + 1];
                    long long dd = max(0LL, mj - mn + 1);
                    if (dd == 0) continue;
                    int start_suf = p[s] + 1;
                    long long remain = dd;
                    while (remain > 0) {
                        long long this_d = min(remain, x);
                        best_ops.emplace_back(start_suf, n, this_d);
                        remain -= this_d;
                    }
                }
            }
        }
    }
    
    // compute LIS for whole if better, but already included in num=1
    cout << best_lis << '\n';
    for (size_t i = 0; i < 10; ++i) {
        if (i < best_ops.size()) {
            auto [l, r, d] = best_ops[i];
            cout << l << " " << r << " " << d << '\n';
        } else {
            cout << "1 1 0\n";
        }
    }
    
    return 0;
}