#include <bits/stdc++.h>
using namespace std;

long long ask(long long x, long long y) {
    cout << x << " " << y << endl;
    cout.flush();
    long long r;
    if (!(cin >> r)) exit(0);
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    long long a = -1, b = -1;

    // Binary search for a using queries (mid, 1)
    long long L = 1, R = n;
    while (L < R) {
        long long mid = (L + R) / 2;
        long long r = ask(mid, 1);
        if (r == 0) return 0;
        if (r == 1) { // mid < a
            L = mid + 1;
        } else {      // mid >= a (r = 2 or 3)
            R = mid;
        }
    }
    a = L;

    // Binary search for b using queries (a, mid)
    long long LB = 1, RB = n;
    while (LB < RB) {
        long long mid = (LB + RB) / 2;
        long long r = ask(a, mid);
        if (r == 0) return 0;
        if (r == 2) {        // mid < b
            LB = mid + 1;
        } else if (r == 3) { // mid > b
            RB = mid - 1;
        } else {
            // r == 1 should be impossible here if interactor is consistent
            // but if it happens, we ignore and narrow conservatively
            // since x == a, x < a is false, so r != 1 in a correct interactor.
        }
    }
    b = LB;

    // Final confirmation query
    ask(a, b); // should receive 0 and then terminate
    return 0;
}