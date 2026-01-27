#include <bits/stdc++.h>
using namespace std;

int ask(int l, int r) {
    cout << "? " << l << " " << r << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

void answer(int x) {
    cout << "! " << x << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;

        int s = ask(1, n); // index of second maximum in [1, n]

        int pos;
        // Determine side where n lies
        bool leftSide;
        if (s == n) {
            leftSide = true;
        } else if (s == 1) {
            leftSide = false;
        } else {
            int t = ask(1, s);
            leftSide = (t == s);
        }

        if (leftSide) {
            int lo = 1, hi = s - 1;
            while (lo < hi) {
                int mid = (lo + hi + 1) / 2;
                int t = ask(mid, s);
                if (t == s) {
                    lo = mid;
                } else {
                    hi = mid - 1;
                }
            }
            pos = lo;
            if (s == 1) pos = 1; // edge, though leftSide won't be true when s==1
        } else {
            int lo = s + 1, hi = n;
            while (lo < hi) {
                int mid = (lo + hi) / 2;
                int t = ask(s, mid);
                if (t == s) {
                    hi = mid;
                } else {
                    lo = mid + 1;
                }
            }
            pos = lo;
            if (s == n) pos = n; // edge, though leftSide would be true when s==n
        }

        answer(pos);
    }

    return 0;
}