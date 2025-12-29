#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        int n;
        cin >> n;
        cout << "? 1 " << n << endl;
        int q;
        cin >> q;
        int L, R;
        if (q == 1) {
            L = 2;
            R = n;
        } else if (q == n) {
            L = 1;
            R = n - 1;
        } else {
            cout << "? 1 " << q << endl;
            int p;
            cin >> p;
            if (p == q) {
                L = 1;
                R = q - 1;
            } else {
                L = q + 1;
                R = n;
            }
        }
        while (L < R) {
            if (L > q) {
                // right side
                int mid = (L + R) / 2;
                cout << "? " << q << " " << mid << endl;
                int p;
                cin >> p;
                if (p == q) {
                    R = mid;
                } else {
                    L = mid + 1;
                }
            } else {
                // left side
                int mid = (L + R) / 2;
                cout << "? " << (mid + 1) << " " << q << endl;
                int p;
                cin >> p;
                if (p == q) {
                    L = mid + 1;
                } else {
                    R = mid;
                }
            }
        }
        cout << "! " << L << endl;
    }
    return 0;
}