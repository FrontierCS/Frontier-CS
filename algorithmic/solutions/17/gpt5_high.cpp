#include <bits/stdc++.h>
using namespace std;

int ask(int l, int r) {
    cout << "? " << l << " " << r << endl;
    cout.flush();
    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;

        int s = ask(1, n); // position of n-1 in the whole array

        int pos = -1;

        if (s != 1) {
            int ans = ask(1, s);
            if (ans == s) {
                // n is in [1, s-1], binary search for l maximizing Query(l, s) == s
                int low = 1, high = s - 1;
                while (low < high) {
                    int mid = (low + high + 1) >> 1;
                    int res = ask(mid, s);
                    if (res == s) low = mid;
                    else high = mid - 1;
                }
                pos = low;
            } else {
                // n is in [s+1, n], binary search for minimal r such that Query(s, r) == s
                int low = s + 1, high = n;
                while (low < high) {
                    int mid = (low + high) >> 1;
                    int res = ask(s, mid);
                    if (res == s) high = mid;
                    else low = mid + 1;
                }
                pos = low;
            }
        } else {
            // s == 1, n must be in [2, n]
            int low = s + 1, high = n;
            while (low < high) {
                int mid = (low + high) >> 1;
                int res = ask(s, mid);
                if (res == s) high = mid;
                else low = mid + 1;
            }
            pos = low;
        }

        cout << "! " << pos << endl;
        cout.flush();
    }

    return 0;
}