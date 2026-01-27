#include <bits/stdc++.h>
using namespace std;

int query(int l, int r) {
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
        cin >> n;

        int s = query(1, n);

        int pos_n;
        if (s > 1 && query(1, s) == s) {
            // n is to the left of s
            int L = 1, R = s - 1;
            while (L < R) {
                int mid = (L + R + 1) / 2;
                if (query(mid, s) == s) {
                    L = mid;
                } else {
                    R = mid - 1;
                }
            }
            pos_n = L;
        } else {
            // n is to the right of s
            int L = s + 1, R = n;
            while (L < R) {
                int mid = (L + R) / 2;
                if (query(s, mid) == s) {
                    R = mid;
                } else {
                    L = mid + 1;
                }
            }
            pos_n = L;
        }

        cout << "! " << pos_n << endl;
        cout.flush();
    }

    return 0;
}