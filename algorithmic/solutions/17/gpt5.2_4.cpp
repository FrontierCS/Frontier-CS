#include <bits/stdc++.h>
using namespace std;

static inline int ask(int l, int r) {
    cout << "? " << l << " " << r << "\n" << flush;
    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        int n;
        cin >> n;

        int s = ask(1, n); // position of global second maximum (n-1)

        bool left;
        if (s == 1) left = false;
        else if (s == n) left = true;
        else {
            int t = ask(1, s);
            left = (t == s);
        }

        int pos;
        if (left) {
            int lo = 1, hi = s - 1;
            while (lo < hi) {
                int mid = (lo + hi + 1) / 2;
                int t = ask(mid, s);
                if (t == s) lo = mid;
                else hi = mid - 1;
            }
            pos = lo;
        } else {
            int lo = s + 1, hi = n;
            while (lo < hi) {
                int mid = (lo + hi) / 2;
                int t = ask(s, mid);
                if (t == s) hi = mid;
                else lo = mid + 1;
            }
            pos = lo;
        }

        cout << "! " << pos << "\n" << flush;
    }
    return 0;
}