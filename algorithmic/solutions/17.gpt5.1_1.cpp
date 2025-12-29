#include <bits/stdc++.h>
using namespace std;

int query(int l, int r) {
    cout << "? " << l << ' ' << r << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

void answer(int x) {
    cout << "! " << x << endl;
    cout.flush();
}

void solve_case(int n) {
    int s = query(1, n); // position of n-1 in the whole permutation

    bool leftSide;
    if (s == 1) {
        leftSide = false; // n must be to the right
    } else {
        int q = query(1, s);
        leftSide = (q == s); // if true, n is on the left of s; otherwise on the right
    }

    int pos_n;
    if (leftSide) {
        // n is in [1, s-1]
        int low = 1, high = s - 1;
        while (low < high) {
            int mid = (low + high + 1) / 2; // search for last position where query(mid, s) == s
            int q = query(mid, s);
            if (q == s) low = mid;
            else high = mid - 1;
        }
        pos_n = low;
    } else {
        // n is in [s+1, n]
        int low = s + 1, high = n;
        while (low < high) {
            int mid = (low + high) / 2; // search for first position where query(s, mid) == s
            int q = query(s, mid);
            if (q == s) high = mid;
            else low = mid + 1;
        }
        pos_n = low;
    }

    answer(pos_n);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;
        solve_case(n);
    }

    return 0;
}