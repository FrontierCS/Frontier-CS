#include <bits/stdc++.h>
using namespace std;

int ask(int l, int r) {
    cout << "? " << l << ' ' << r << '\n' << flush;
    int res;
    if (!(cin >> res)) {
        exit(0);
    }
    return res;
}

void answer(int pos) {
    cout << "! " << pos << '\n' << flush;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    while (T--) {
        int n;
        cin >> n;

        int s = ask(1, n); // position of n-1

        bool leftSide;
        if (s == 1) {
            leftSide = false; // n is to the right
        } else if (s == n) {
            leftSide = true;  // n is to the left
        } else {
            int res = ask(1, s);
            leftSide = (res == s);
        }

        int pos;
        if (leftSide) {
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
            pos = L;
        } else {
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
            pos = L;
        }

        answer(pos);
    }

    return 0;
}