#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    auto ask = [&](long long x, long long y) -> int {
        cout << x << " " << y << endl;
        cout.flush();
        int r;
        if (!(cin >> r)) exit(0);
        if (r == 0) exit(0);
        return r;
    };

    // Step 1: find k = min(a, b) using binary search with queries (m, m)
    long long lo = 1, hi = n;
    while (lo < hi) {
        long long mid = lo + (hi - lo + 1) / 2;
        int res = ask(mid, mid);
        if (res == 3) {
            hi = mid - 1;
        } else {
            // res is 1 or 2 (or theoretically 0 which exits), so mid <= min(a,b)
            lo = mid;
        }
    }
    long long k = lo;
    if (k == n) {
        // both must be n
        cout << n << " " << n << endl;
        cout.flush();
        int r; 
        if (!(cin >> r)) return 0;
        return 0;
    }

    // Step 2: determine which equals k using (k+1, k)
    int r = ask(k + 1, k);
    if (r == 3) {
        // a = k, find b with binary search using (k, m)
        long long lo2 = k, hi2 = n;
        while (lo2 < hi2) {
            long long mid = lo2 + (hi2 - lo2 + 1) / 2;
            int res = ask(k, mid);
            if (res == 3) {
                hi2 = mid - 1;
            } else {
                lo2 = mid;
            }
        }
        cout << k << " " << lo2 << endl;
        cout.flush();
        int rr; 
        if (!(cin >> rr)) return 0;
        return 0;
    } else {
        // b = k (or exact found), find a with binary search using (m, k)
        long long lo2 = k, hi2 = n;
        while (lo2 < hi2) {
            long long mid = lo2 + (hi2 - lo2 + 1) / 2;
            int res = ask(mid, k);
            if (res == 3) {
                hi2 = mid - 1;
            } else {
                lo2 = mid;
            }
        }
        cout << lo2 << " " << k << endl;
        cout.flush();
        int rr; 
        if (!(cin >> rr)) return 0;
        return 0;
    }
}