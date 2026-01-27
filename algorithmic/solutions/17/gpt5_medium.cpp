#include <bits/stdc++.h>
using namespace std;

int ask(int l, int r) {
    if (l >= r) return -1;
    cout << "? " << l << " " << r << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

void answer(int x) {
    cout << "! " << x << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;

        int s = ask(1, n);
        if (s == -1) return 0;

        int pos = -1;

        bool leftSide = false;
        if (s == 1) {
            leftSide = false;
        } else if (s == n) {
            leftSide = true;
        } else {
            int q = ask(1, s);
            if (q == -1) return 0;
            leftSide = (q == s);
        }

        if (leftSide) {
            int l = 1, r = s - 1;
            while (l < r) {
                int mid = (l + r + 1) / 2;
                int q = ask(mid, s);
                if (q == -1) return 0;
                if (q == s) {
                    l = mid;
                } else {
                    r = mid - 1;
                }
            }
            pos = l;
        } else {
            int l = s + 1, r = n;
            while (l < r) {
                int mid = (l + r) / 2;
                int q = ask(s, mid);
                if (q == -1) return 0;
                if (q == s) {
                    r = mid;
                } else {
                    l = mid + 1;
                }
            }
            pos = l;
        }

        answer(pos);
    }

    return 0;
}