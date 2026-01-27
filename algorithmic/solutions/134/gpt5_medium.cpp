#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
using i128 = __int128_t;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    auto ask = [&](long long x, long long y) -> long long {
        cout << x << " " << y << "\n";
        cout.flush();
        long long r;
        if (!(cin >> r)) exit(0);
        if (r == 0) exit(0);
        return r;
    };

    // Binary search for a with y = n
    long long la = 1, ra = n;
    while (la < ra) {
        long long mid = la + (ra - la) / 2;
        long long r = ask(mid, n);
        if (r == 1) {
            // x < a
            la = mid + 1;
        } else if (r == 0) {
            return 0;
        } else {
            // Treat any other response as indicating x >= a (expected 3)
            ra = mid;
        }
    }
    long long a = la;

    // Binary search for b with x = a
    long long lb = 1, rb = n;
    while (lb < rb) {
        long long mid = lb + (rb - lb) / 2;
        long long r = ask(a, mid);
        if (r == 2) {
            // y < b
            lb = mid + 1;
        } else if (r == 0) {
            return 0;
        } else {
            // Treat any other response as indicating y >= b (expected 3)
            rb = mid;
        }
    }
    long long b = lb;

    // Final confirmation
    ask(a, b);
    return 0;
}