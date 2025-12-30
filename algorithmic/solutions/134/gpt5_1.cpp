#include <bits/stdc++.h>
using namespace std;

int ask(unsigned long long x, unsigned long long y) {
    cout << x << " " << y << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    if (res == 0) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    unsigned long long n;
    if (!(cin >> n)) return 0;

    // Find a
    unsigned long long lo = 1, hi = n;
    while (lo < hi) {
        unsigned long long mid = lo + (hi - lo) / 2;
        int res = ask(mid, n);
        if (res == 1) {
            lo = mid + 1;
        } else {
            hi = mid;
        }
    }
    unsigned long long a = lo;

    // Find b
    lo = 1; hi = n;
    while (lo < hi) {
        unsigned long long mid = lo + (hi - lo) / 2;
        int res = ask(a, mid);
        if (res == 2) {
            lo = mid + 1;
        } else {
            hi = mid;
        }
    }
    unsigned long long b = lo;

    // Final confirmation
    ask(a, b);

    return 0;
}