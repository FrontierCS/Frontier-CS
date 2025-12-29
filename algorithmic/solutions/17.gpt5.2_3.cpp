#include <bits/stdc++.h>
using namespace std;

static int query(int l, int r) {
    cout << "? " << l << " " << r << endl;
    cout.flush();
    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

static void answer(int pos) {
    cout << "! " << pos << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;

        int s = query(1, n); // position of (n-1)

        if (n == 2) {
            answer(s == 1 ? 2 : 1);
            continue;
        }

        bool right;
        if (s == 1) right = true;
        else if (s == n) right = false;
        else {
            int t = query(1, s);
            right = (t != s);
        }

        int posN;
        if (!right) { // max is on the left side: [1..s-1]
            int lo = 1, hi = s - 1;
            while (lo < hi) {
                int mid = (lo + hi + 1) / 2;
                int t = query(mid, s);
                if (t == s) lo = mid;
                else hi = mid - 1;
            }
            posN = lo;
        } else { // max is on the right side: [s+1..n]
            int lo = s + 1, hi = n;
            while (lo < hi) {
                int mid = (lo + hi) / 2;
                int t = query(s, mid);
                if (t == s) hi = mid;
                else lo = mid + 1;
            }
            posN = lo;
        }

        answer(posN);
    }
    return 0;
}