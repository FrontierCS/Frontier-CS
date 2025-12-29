#include <bits/stdc++.h>
using namespace std;

pair<int, int> query(int i) {
    cout << "? " << i << endl;
    fflush(stdout);
    int a0, a1;
    cin >> a0 >> a1;
    return {a0, a1};
}

int find_leftmost_good(int left, int right) {
    int loo = left, hii = right;
    while (loo < hii) {
        int mm = (loo + hii) / 2;
        auto [a0m, a1m] = query(mm);
        int sm = a0m + a1m;
        if (sm == 0) {
            cout << "! " << mm << endl;
            fflush(stdout);
            exit(0);
        }
        bool has = (sm <= 1) || (a0m >= 1);
        if (has) {
            hii = mm;
        } else {
            loo = mm + 1;
        }
    }
    auto [a0f, a1f] = query(loo);
    int sf = a0f + a1f;
    if (sf == 0) {
        cout << "! " << loo << endl;
        fflush(stdout);
        exit(0);
    }
    return loo;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    cin >> n;
    int lo = 0, hi = n - 1;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        auto [a0, a1] = query(mid);
        int s = a0 + a1;
        if (s == 0) {
            cout << "! " << mid << endl;
            fflush(stdout);
            exit(0);
        }
        if (s == 1) {
            if (a0 == 1) {
                hi = mid - 1;
            } else {
                lo = mid + 1;
            }
            continue;
        }
        // s >= 3, bad
        if (a0 == 0) {
            lo = mid + 1;
            continue;
        }
        if (a1 == 0) {
            hi = mid - 1;
            continue;
        }
        // ambiguous
        int l = find_leftmost_good(0, mid - 1);
        // now l queried, a0_l = 0, s=1
        bool more_in_left = false;
        int ss = l + 1, tt = mid - 1;
        if (ss <= tt) {
            auto [a0tt, a1tt] = query(tt);
            int sumtt = a0tt + a1tt;
            if (sumtt == 0) {
                cout << "! " << tt << endl;
                fflush(stdout);
                exit(0);
            }
            if (sumtt <= 1) {
                more_in_left = true;
            } else {
                if (a0tt > 1) {
                    more_in_left = true;
                }
            }
        }
        if (more_in_left) {
            hi = mid - 1;
        } else {
            lo = mid + 1;
        }
    }
    // lo == hi
    auto [a0f, a1f] = query(lo);
    int sf = a0f + a1f;
    if (sf != 0) {
        // arbitrary
        cout << "! 0" << endl;
    } else {
        cout << "! " << lo << endl;
    }
    fflush(stdout);
    return 0;
}