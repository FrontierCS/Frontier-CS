#include <bits/stdc++.h>
using namespace std;

int ask(int l, int r) {
    cout << "? " << l << " " << r << endl;
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    return x;
}

int find_left(int L, int S) {
    int R = S - 1;
    if (L > R) return -1;
    while (L < R) {
        int mid = (L + R + 1) / 2; // upper mid
        int res = ask(mid, S);
        if (res == S) {
            L = mid;
        } else {
            R = mid - 1;
        }
    }
    return L;
}

int find_right(int S, int n) {
    int L = S + 1, R = n;
    if (L > R) return -1;
    while (L < R) {
        int mid = (L + R) / 2; // lower mid
        int res = ask(S, mid);
        if (res == S) {
            R = mid;
        } else {
            L = mid + 1;
        }
    }
    return L;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;

        int S = ask(1, n); // position of (n-1)
        int pos_n = -1;

        if (S == 1) {
            // maximum is on the right
            pos_n = find_right(S, n);
        } else if (S == n) {
            // maximum is on the left
            pos_n = find_left(1, S);
        } else {
            int res = ask(1, S);
            if (res == S) {
                // maximum is on the left side [1, S-1]
                pos_n = find_left(1, S);
            } else {
                // maximum is on the right side [S+1, n]
                pos_n = find_right(S, n);
            }
        }

        if (pos_n == -1) pos_n = 1; // fallback, should not happen

        cout << "! " << pos_n << endl;
        cout.flush();
    }

    return 0;
}