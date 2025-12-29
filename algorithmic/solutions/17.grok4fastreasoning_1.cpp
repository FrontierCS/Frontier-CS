#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int T;
    cin >> T;
    for (int cas = 0; cas < T; ++cas) {
        int n;
        cin >> n;
        cout << "? 1 " << n << endl;
        int p;
        cin >> p;
        int low = 1, high = n;
        if (p == 1) {
            low = 2;
            high = n;
        } else if (p == n) {
            low = 1;
            high = n - 1;
        } else {
            cout << "? 1 " << p << endl;
            int t;
            cin >> t;
            if (t == p) {
                high = p - 1;
            } else {
                low = p + 1;
            }
        }
        while (low < high) {
            int mid = low + (high - low) / 2;
            int ql, qr;
            int tt;
            if (p < low) {
                ql = p;
                qr = mid;
                cout << "? " << ql << " " << qr << endl;
                cin >> tt;
                if (tt == p) {
                    high = mid;
                } else {
                    low = mid + 1;
                }
            } else {
                ql = mid + 1;
                qr = p;
                cout << "? " << ql << " " << qr << endl;
                cin >> tt;
                if (tt == p) {
                    low = mid + 1;
                } else {
                    high = mid;
                }
            }
        }
        cout << "! " << low << endl;
    }
    return 0;
}