#include <bits/stdc++.h>
using namespace std;

int ask(int l, int r) {
    cout << "? " << l << " " << r << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 2) {
        int p = ask(1, 2);
        int ans = (p == 1 ? 2 : 1);
        cout << "! " << ans << endl;
        cout.flush();
        return 0;
    }

    int p = ask(1, n);  // position of second maximum in [1, n]
    int maxPos;

    if (p == 1) {
        // maximum is to the right of p
        int lo = 2, hi = n;
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            int res = ask(p, mid);
            if (res == p) hi = mid;
            else lo = mid + 1;
        }
        maxPos = lo;
    } else if (p == n) {
        // maximum is to the left of p
        int lo = 1, hi = n - 1;
        while (lo < hi) {
            int mid = (lo + hi + 1) / 2;
            int res = ask(mid, p);
            if (res == p) lo = mid;
            else hi = mid - 1;
        }
        maxPos = lo;
    } else {
        int resLeft = ask(1, p);
        if (resLeft == p) {
            // maximum is to the left of p
            int lo = 1, hi = p - 1;
            while (lo < hi) {
                int mid = (lo + hi + 1) / 2;
                int res = ask(mid, p);
                if (res == p) lo = mid;
                else hi = mid - 1;
            }
            maxPos = lo;
        } else {
            // maximum is to the right of p
            int lo = p + 1, hi = n;
            while (lo < hi) {
                int mid = (lo + hi) / 2;
                int res = ask(p, mid);
                if (res == p) hi = mid;
                else lo = mid + 1;
            }
            maxPos = lo;
        }
    }

    cout << "! " << maxPos << endl;
    cout.flush();
    return 0;
}