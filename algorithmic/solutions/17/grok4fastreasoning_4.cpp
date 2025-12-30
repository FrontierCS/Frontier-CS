#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int T;
    cin >> T;
    for (int t = 0; t < T; t++) {
        int n;
        cin >> n;
        cout << "? 1 " << n << endl;
        int p;
        cin >> p;
        int low, high;
        if (p == 1) {
            low = 2;
            high = n;
        } else if (p == n) {
            low = 1;
            high = n - 1;
        } else {
            cout << "? 1 " << p << endl;
            int res;
            cin >> res;
            if (res == p) {
                low = 1;
                high = p - 1;
            } else {
                low = p + 1;
                high = n;
            }
        }
        int x;
        if (low == high) {
            x = low;
        } else {
            while (low < high) {
                int mid = low + (high - low) / 2;
                int ql, qr;
                int res;
                cout << "? ";
                if (high < p) { // left side
                    ql = mid + 1;
                    qr = p;
                    cout << ql << " " << qr << endl;
                    cin >> res;
                    if (res == p) {
                        low = mid + 1;
                    } else {
                        high = mid;
                    }
                } else { // right side
                    ql = p;
                    qr = mid;
                    cout << ql << " " << qr << endl;
                    cin >> res;
                    if (res == p) {
                        high = mid;
                    } else {
                        low = mid + 1;
                    }
                }
            }
            x = low;
        }
        cout << "! " << x << endl;
    }
    return 0;
}