#include <iostream>
#include <cmath>
using namespace std;

int ask(int l, int r) {
    cout << "? " << l << " " << r << endl;
    int res;
    cin >> res;
    return res;
}

void solve() {
    int n;
    cin >> n;
    
    // Step 1: find position of second largest overall (n-1)
    int s = ask(1, n);
    
    if (s > 1 && s < n) {
        // Determine which side contains n
        int a = ask(1, s);
        if (a == s) {
            // n is in [1, s-1]
            int L = 1, R = s - 1;
            while (L < R) {
                int mid = (L + R + 1) / 2;
                int res = ask(mid, s);
                if (res == s) {
                    L = mid;
                } else {
                    R = mid - 1;
                }
            }
            cout << "! " << L << endl;
        } else {
            // n is in [s+1, n]
            int L = s + 1, R = n;
            while (L < R) {
                int mid = (L + R) / 2;
                int res = ask(s, mid);
                if (res == s) {
                    R = mid;
                } else {
                    L = mid + 1;
                }
            }
            cout << "! " << L << endl;
        }
    } else if (s == 1) {
        // n is in [2, n]
        int L = 2, R = n;
        while (L < R) {
            int mid = (L + R) / 2;
            int res = ask(1, mid);
            if (res == 1) {
                R = mid;
            } else {
                L = mid + 1;
            }
        }
        cout << "! " << L << endl;
    } else { // s == n
        // n is in [1, n-1]
        int L = 1, R = n - 1;
        while (L < R) {
            int mid = (L + R + 1) / 2;
            int res = ask(mid, n);
            if (res == n) {
                L = mid;
            } else {
                R = mid - 1;
            }
        }
        cout << "! " << L << endl;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    cin >> T;
    while (T--) {
        solve();
    }
    
    return 0;
}