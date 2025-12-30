#include <bits/stdc++.h>
using namespace std;
using int64 = long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int64 n;
    if (!(cin >> n)) return 0;

    auto ask = [&](int64 x, int64 y) -> int64 {
        cout << x << ' ' << y << endl;
        cout.flush();
        int64 r;
        if (!(cin >> r)) exit(0);
        if (r == 0) exit(0);
        return r;
    };

    if (n == 1) {
        ask(1, 1); // should get 0 and exit
        return 0;
    }

    // Find a
    int64 lo = 1, hi = n;
    while (lo < hi) {
        int64 mid = lo + (hi - lo) / 2;
        int64 res = ask(mid, 1);
        if (res == 1) {          // x < a
            lo = mid + 1;
        } else {                 // res == 2 or 3, assume x >= a
            hi = mid;
        }
    }
    int64 a = lo;

    // Find b
    lo = 1; hi = n;
    while (lo < hi) {
        int64 mid = lo + (hi - lo) / 2;
        int64 res = ask(a, mid);
        if (res == 2) {          // y < b
            lo = mid + 1;
        } else {                 // res == 3 (or 0, but 0 would exit)
            hi = mid;
        }
    }
    int64 b = lo;

    ask(a, b); // final confirmation (should get 0 and exit)

    return 0;
}