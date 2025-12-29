#include <bits/stdc++.h>
using namespace std;

int ask(int l, int r) {
    cout << "? " << l << " " << r << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

int find_left(int s) {
    int low = 1, high = s - 1;
    while (low < high) {
        int mid = (low + high + 1) / 2;
        int res = ask(mid, s);
        if (res == s) {
            low = mid;
        } else {
            high = mid - 1;
        }
    }
    return low;
}

int find_right(int s, int n) {
    int low = s + 1, high = n;
    while (low < high) {
        int mid = (low + high) / 2;
        int res = ask(s, mid);
        if (res == s) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    return low;
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
        int ans = -1;

        if (s == 1) {
            ans = find_right(s, n);
        } else if (s == n) {
            ans = find_left(s);
        } else {
            int res = ask(1, s);
            if (res == s) {
                ans = find_left(s);
            } else {
                ans = find_right(s, n);
            }
        }

        cout << "! " << ans << endl;
        cout.flush();
    }
    return 0;
}