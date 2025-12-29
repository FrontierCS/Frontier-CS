#include <bits/stdc++.h>
using namespace std;

static int ask(int l, int r) {
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

        int s = ask(1, n); // position of the second largest (n-1) in [1..n]

        int ans = -1;

        if (s == 1) {
            int L = 2, R = n;
            while (L < R) {
                int mid = (L + R) / 2;
                int res = ask(s, mid);
                if (res == s) R = mid;
                else L = mid + 1;
            }
            ans = L;
        } else if (s == n) {
            int L = 1, R = n - 1;
            while (L < R) {
                int mid = (L + R + 1) / 2;
                int res = ask(mid, s);
                if (res == s) L = mid;
                else R = mid - 1;
            }
            ans = L;
        } else {
            int side = ask(1, s);
            if (side == s) {
                // maximum is in [1..s-1]
                int L = 1, R = s - 1;
                while (L < R) {
                    int mid = (L + R + 1) / 2;
                    int res = ask(mid, s);
                    if (res == s) L = mid;
                    else R = mid - 1;
                }
                ans = L;
            } else {
                // maximum is in [s+1..n]
                int L = s + 1, R = n;
                while (L < R) {
                    int mid = (L + R) / 2;
                    int res = ask(s, mid);
                    if (res == s) R = mid;
                    else L = mid + 1;
                }
                ans = L;
            }
        }

        cout << "! " << ans << endl;
        cout.flush();
    }
    return 0;
}