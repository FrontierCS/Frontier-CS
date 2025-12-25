#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    cin >> T;
    while (T--) {
        int n;
        cin >> n;
        int L = 1, R = n;
        while (L < R) {
            cout << "? " << L << " " << R << endl;
            int q;
            cin >> q;
            if (q == L) {
                L++;
                continue;
            }
            if (q == R) {
                R--;
                continue;
            }
            // Now L < q < R
            cout << "? " << L << " " << q << endl;
            int t;
            cin >> t;
            if (t == q) {
                R = q;
            } else {
                L = q + 1;
            }
        }
        cout << "! " << L << endl;
    }
    return 0;
}