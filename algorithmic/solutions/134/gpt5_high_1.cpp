#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    long long x = 1, y = 1;
    const int MAX_QUERIES = 10000;
    for (int q = 0; q < MAX_QUERIES; ++q) {
        cout << x << ' ' << y << endl;
        int res;
        if (!(cin >> res)) return 0;
        if (res == 0) return 0;
        if (res == 1) {
            if (x < n) x++;
        } else if (res == 2) {
            if (y < n) y++;
        } else if (res == 3) {
            // Ideally shouldn't happen with our strategy,
            // but to be safe, try to adjust minimally.
            if (x > 1) x--;
            else if (y > 1) y--;
        }
    }
    return 0;
}