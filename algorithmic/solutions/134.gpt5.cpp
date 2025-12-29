#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    unsigned long long n;
    if (!(cin >> n)) return 0;

    auto ask = [&](unsigned long long x, unsigned long long y) -> int {
        cout << x << " " << y << endl;
        cout.flush();
        int r;
        if (!(cin >> r)) exit(0);
        if (r == 0) exit(0);
        return r;
    };

    // Binary search for a using queries (mid, 1)
    unsigned long long L = 1, R = n;
    while (L < R) {
        unsigned long long mid = L + (R - L + 1) / 2;
        int res = ask(mid, 1);
        if (res == 3) {
            R = mid - 1;
        } else {
            L = mid;
        }
    }
    unsigned long long a = L;

    // Binary search for b using queries (1, mid)
    unsigned long long Ly = 1, Uy = n;
    while (Ly < Uy) {
        unsigned long long mid = Ly + (Uy - Ly + 1) / 2;
        int res = ask(1, mid);
        if (res == 3) {
            Uy = mid - 1;
        } else {
            Ly = mid;
        }
    }
    unsigned long long b = Ly;

    // Final confirmation query
    ask(a, b);

    return 0;
}