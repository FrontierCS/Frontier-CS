#include <bits/stdc++.h>
using namespace std;

int ask(int l, int r) {
    if (l >= r) return -1;
    cout << "? " << l << " " << r << endl;
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;

        int s = ask(1, n); // position of n-1

        bool left;
        if (s != 1) {
            int t = ask(1, s);
            left = (t == s);
        } else {
            left = false;
        }

        int ans;
        if (left) {
            int L = 1, R = s - 1;
            while (L < R) {
                int mid = (L + R + 1) / 2;
                int t = ask(mid, s);
                if (t == s) L = mid;
                else R = mid - 1;
            }
            ans = L;
        } else {
            int L = s + 1, R = n;
            while (L < R) {
                int mid = (L + R) / 2;
                int t = ask(s, mid);
                if (t == s) R = mid;
                else L = mid + 1;
            }
            ans = L;
        }

        cout << "! " << ans << endl;
        cout.flush();
    }

    return 0;
}