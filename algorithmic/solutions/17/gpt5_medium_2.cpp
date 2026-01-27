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

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;

        int s = ask(1, n);

        bool left;
        if (s == 1) left = false;
        else if (s == n) left = true;
        else {
            int t = ask(1, s);
            left = (t == s);
        }

        int pos = -1;
        if (left) {
            int lo = 1, hi = s - 1, ans = 1;
            while (lo <= hi) {
                int mid = (lo + hi) / 2;
                int t = ask(mid, s);
                if (t == s) {
                    ans = mid;
                    lo = mid + 1;
                } else {
                    hi = mid - 1;
                }
            }
            pos = ans;
        } else {
            int lo = s + 1, hi = n, ans = n;
            while (lo <= hi) {
                int mid = (lo + hi) / 2;
                int t = ask(s, mid);
                if (t == s) {
                    ans = mid;
                    hi = mid - 1;
                } else {
                    lo = mid + 1;
                }
            }
            pos = ans;
        }

        cout << "! " << pos << endl;
        cout.flush();
    }
    return 0;
}