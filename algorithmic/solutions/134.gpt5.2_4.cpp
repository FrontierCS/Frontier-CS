#include <bits/stdc++.h>
using namespace std;

static long long n;

static int query(long long x, long long y) {
    cout << x << ' ' << y << '\n';
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (r == 0) exit(0);
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << "1 1\n";
        cout.flush();
        int r;
        cin >> r;
        return 0;
    }

    long long lo = 1, hi = n;
    while (lo < hi) {
        long long mid = lo + (hi - lo) / 2;
        int r = query(mid, n);
        if (r == 1) lo = mid + 1;
        else hi = mid;
    }
    long long a = lo;

    lo = 1; hi = n;
    while (lo < hi) {
        long long mid = lo + (hi - lo) / 2;
        int r = query(a, mid);
        if (r == 2) lo = mid + 1;
        else hi = mid;
    }
    long long b = lo;

    cout << a << ' ' << b << '\n';
    cout.flush();
    int r;
    cin >> r;
    return 0;
}