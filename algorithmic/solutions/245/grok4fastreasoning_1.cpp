#include <bits/stdc++.h>
using namespace std;

int main() {
    int t;
    cin >> t;
    for (int test = 0; test < t; test++) {
        int n;
        cin >> n;
        int impostor = -1;
        bool found = false;
        for (int i = 1; i <= n; i += 2) {
            if (i + 1 > n) break;
            // pair i and i+1
            cout << "? " << i << " " << (i + 1) << endl;
            cout.flush();
            int a;
            cin >> a;
            if (a == -1) return 0;
            cout << "? " << (i + 1) << " " << i << endl;
            cout.flush();
            int b;
            cin >> b;
            if (b == -1) return 0;
            if (a != b) {
                // found bad pair
                int left = i, right = i + 1;
                // pick k not left or right
                int k = 1;
                if (k == left || k == right) k = 2;
                if (k == left || k == right) k = 3;
                cout << "? " << left << " " << k << endl;
                cout.flush();
                int c;
                cin >> c;
                if (c == -1) return 0;
                cout << "? " << k << " " << left << endl;
                cout.flush();
                int d;
                cin >> d;
                if (d == -1) return 0;
                if (c != d) {
                    impostor = left;
                } else {
                    impostor = right;
                }
                found = true;
                break;
            }
        }
        if (!found) {
            impostor = n;
        }
        cout << "! " << impostor << endl;
        cout.flush();
    }
    return 0;
}