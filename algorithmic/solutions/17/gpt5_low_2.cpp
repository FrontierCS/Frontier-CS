#include <bits/stdc++.h>
using namespace std;

int ask(int l, int r) {
    cout << "? " << l << " " << r << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;

        int s = ask(1, n);

        int pos = -1;

        // Determine side where n lies
        bool leftSide = false;
        if (s != 1) {
            int t = ask(1, s);
            if (t == s) leftSide = true;
        }
        // If s == 1, then n must be on the right side
        // If s != 1 and t != s, then on the right side

        if (leftSide) {
            int lo = 1, hi = s - 1;
            if (lo > hi) {
                // No space on the left, n must be on the right (shouldn't happen if leftSide is true)
                lo = s + 1; hi = n;
                while (lo < hi) {
                    int mid = (lo + hi) / 2;
                    int t = ask(s, mid);
                    if (t == s) hi = mid;
                    else lo = mid + 1;
                }
                pos = lo;
            } else {
                while (lo < hi) {
                    int mid = (lo + hi + 1) / 2;
                    int t = ask(mid, s);
                    if (t == s) lo = mid;
                    else hi = mid - 1;
                }
                pos = lo;
            }
        } else {
            int lo = s + 1, hi = n;
            if (lo > hi) {
                // No space on the right, n must be on the left
                lo = 1; hi = s - 1;
                while (lo < hi) {
                    int mid = (lo + hi + 1) / 2;
                    int t = ask(mid, s);
                    if (t == s) lo = mid;
                    else hi = mid - 1;
                }
                pos = lo;
            } else {
                while (lo < hi) {
                    int mid = (lo + hi) / 2;
                    int t = ask(s, mid);
                    if (t == s) hi = mid;
                    else lo = mid + 1;
                }
                pos = lo;
            }
        }

        cout << "! " << pos << endl;
        cout.flush();
        // Optionally read verdict per test if interactor provides
        // string verdict; if (!(cin >> verdict)) return 0;
    }

    return 0;
}