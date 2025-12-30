#include <iostream>
#include <algorithm>
using namespace std;

int ask(int l, int r) {
    cout << "? " << l << " " << r << endl;
    int res;
    cin >> res;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        int n;
        cin >> n;
        int p2 = ask(1, n);
        int side; // 1: n > p2, -1: n < p2
        if (p2 == 1) {
            side = 1;
        } else if (p2 == n) {
            side = -1;
        } else {
            int res = ask(p2, n);
            if (res == p2) {
                side = 1;
            } else {
                side = -1;
            }
        }
        int ans;
        if (side == 1) {
            int L = p2 + 1, R = n;
            while (L < R) {
                int M = (L + R) / 2;
                int res = ask(p2, M);
                if (res == p2) {
                    R = M;
                } else {
                    L = M + 1;
                }
            }
            ans = L;
        } else {
            int L = 1, R = p2 - 1;
            while (L < R) {
                int M = (L + R + 1) / 2;
                int res = ask(M, p2);
                if (res == p2) {
                    L = M;
                } else {
                    R = M - 1;
                }
            }
            ans = L;
        }
        cout << "! " << ans << endl;
    }
    return 0;
}