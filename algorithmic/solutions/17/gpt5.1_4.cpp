#include <bits/stdc++.h>
using namespace std;

int ask(int l, int r) {
    cout << "? " << l << ' ' << r << endl;
    cout.flush();
    int idx;
    if (!(cin >> idx)) exit(0);
    if (idx == -1) exit(0);
    return idx;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;

        int s = ask(1, n); // position of n-1

        int L, R;
        if (s == 1) {
            L = 2;
            R = n;
        } else if (s == n) {
            L = 1;
            R = n - 1;
        } else {
            int x = ask(1, s);
            if (x == s) {
                L = 1;
                R = s - 1;
            } else {
                L = s + 1;
                R = n;
            }
        }

        while (L < R) {
            int mid = (L + R) / 2;
            if (R < s) {
                // searching on the left side of s
                int x = ask(mid + 1, s);
                if (x == s) {
                    L = mid + 1;
                } else {
                    R = mid;
                }
            } else {
                // searching on the right side of s
                int x = ask(s, mid);
                if (x == s) {
                    R = mid;
                } else {
                    L = mid + 1;
                }
            }
        }

        cout << "! " << L << endl;
        cout.flush();
    }

    return 0;
}