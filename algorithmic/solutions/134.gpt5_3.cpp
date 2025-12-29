#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    if (!(cin >> n)) return 0;

    auto ask = [&](long long x, long long y) -> long long {
        cout << x << " " << y << endl;
        cout.flush();
        long long r;
        if (!(cin >> r)) exit(0);
        if (r == 0) exit(0);
        return r;
    };

    // Find a via binary search using rule preference (1 over others)
    long long lo = 1, hi = n;
    while (lo < hi) {
        long long mid = (lo + hi) / 2;
        long long r = ask(mid, 1);
        if (r == 1) lo = mid + 1; // x < a
        else hi = mid; // x >= a
    }
    long long a = lo;

    // Find b via binary search holding x = a
    lo = 1; hi = n;
    while (lo < hi) {
        long long mid = (lo + hi) / 2;
        long long r = ask(a, mid);
        if (r == 2) lo = mid + 1; // y < b
        else hi = mid; // y >= b (3 or 0)
    }
    long long b = lo;

    // Final confirmation
    ask(a, b);
    return 0;
}