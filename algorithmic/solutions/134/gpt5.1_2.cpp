#include <bits/stdc++.h>
using namespace std;
using int64 = long long;

int query(int64 x, int64 y) {
    cout << x << ' ' << y << '\n';
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (r == 0 || r == -1) exit(0);
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int64 n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        query(1, 1);
        return 0;
    }

    // Find a
    int64 L = 1, R = n;
    while (L < R) {
        int64 mid = L + (R - L) / 2;
        int r = query(mid, 1);
        if (r == 1) {
            L = mid + 1;
        } else {
            R = mid;
        }
    }
    int64 a = L;

    // Find b
    L = 1;
    R = n;
    while (L < R) {
        int64 mid = L + (R - L) / 2;
        int r = query(a, mid);
        if (r == 2) {
            L = mid + 1;
        } else {
            R = mid;
        }
    }

    // Final answer
    query(a, L);
    return 0;
}