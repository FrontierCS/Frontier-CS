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
            int a, b;
            cout << "? " << i << " " << (i + 1) << endl;
            cin >> a;
            if (a == -1) return 0;
            cout << "? " << (i + 1) << " " << i << endl;
            cin >> b;
            if (b == -1) return 0;
            if (a == 1 && b == 0) {
                // asymmetric
                int c = 3;
                if (c == i || c == i + 1) c = 1;
                if (c == i || c == i + 1) c = n;
                int p, q;
                cout << "? " << c << " " << i << endl;
                cin >> p;
                if (p == -1) return 0;
                cout << "? " << c << " " << (i + 1) << endl;
                cin >> q;
                if (q == -1) return 0;
                if (p == q) {
                    impostor = i + 1;
                } else {
                    impostor = i;
                }
                found = true;
                break;
            }
        }
        if (!found) {
            impostor = n;
        }
        cout << "! " << impostor << endl;
    }
    return 0;
}