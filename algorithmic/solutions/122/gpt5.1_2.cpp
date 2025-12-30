#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    const int MAXW = 100000;

    while (t--) {
        int lo = 1, hi = MAXW;
        while (lo < hi) {
            int mid = (lo + hi + 1) / 2;
            cout << "? 1 " << mid << "\n";
            cout.flush();

            int res;
            if (!(cin >> res)) return 0;
            if (res == -1) return 0;

            if (res == 0) {
                // W < mid
                hi = mid - 1;
            } else {
                // W >= mid
                lo = mid;
            }
        }

        int W = lo;
        cout << "! " << W << "\n";
        cout.flush();
    }

    return 0;
}