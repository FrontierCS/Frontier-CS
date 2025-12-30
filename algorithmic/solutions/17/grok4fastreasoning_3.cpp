#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);
    int T;
    cin >> T;
    for (int t = 0; t < T; t++) {
        int n;
        cin >> n;
        cout << "? 1 " << n << endl;
        int p;
        cin >> p;
        int leftL = 1, leftR = p - 1;
        int rightL = p + 1, rightR = n;
        int posn;
        if (leftR < leftL) {
            // right
            int L = rightL, R = rightR;
            while (L < R) {
                int mid = (L + R) / 2;
                cout << "? " << p << " " << mid << endl;
                int s;
                cin >> s;
                if (s == p) {
                    R = mid;
                } else {
                    L = mid + 1;
                }
            }
            posn = L;
        } else if (rightR < rightL) {
            // left
            int L = leftL, R = leftR;
            while (L < R) {
                int mid = (L + R) / 2;
                cout << "? " << (mid + 1) << " " << p << endl;
                int s;
                cin >> s;
                if (s == p) {
                    L = mid + 1;
                } else {
                    R = mid;
                }
            }
            posn = L;
        } else {
            // both possible, query side
            cout << "? 1 " << p << endl;
            int s;
            cin >> s;
            bool onleft = (s == p);
            if (onleft) {
                int L = leftL, R = leftR;
                while (L < R) {
                    int mid = (L + R) / 2;
                    cout << "? " << (mid + 1) << " " << p << endl;
                    int s2;
                    cin >> s2;
                    if (s2 == p) {
                        L = mid + 1;
                    } else {
                        R = mid;
                    }
                }
                posn = L;
            } else {
                int L = rightL, R = rightR;
                while (L < R) {
                    int mid = (L + R) / 2;
                    cout << "? " << p << " " << mid << endl;
                    int s2;
                    cin >> s2;
                    if (s2 == p) {
                        R = mid;
                    } else {
                        L = mid + 1;
                    }
                }
                posn = L;
            }
        }
        cout << "! " << posn << endl;
    }
    return 0;
}