#include <iostream>
#include <vector>

using namespace std;

void solve() {
    int n;
    cin >> n;

    // Ask query for the full range to find the position of the second largest element
    cout << "? 1 " << n << endl;
    int s;
    cin >> s;

    if (s == 1) {
        // If the second largest is at position 1, then the largest must be > 1.
        // We binary search in the range (1, n].
        // We use 1 as a fixed left anchor.
        int l = 1, r = n;
        // Invariant: The maximum element is in the range (l, r]
        while (r - l > 1) {
            int mid = (l + r) / 2;
            cout << "? 1 " << mid << endl;
            int res;
            cin >> res;
            if (res == 1) {
                // If 1 is the second largest in [1, mid], the largest must be in [1, mid].
                // Since 1 is at index 1 and cannot be the largest (it's the global 2nd max),
                // the largest is in (1, mid].
                r = mid;
            } else {
                // If 1 is not the second largest in [1, mid], it must be the largest in [1, mid]
                // (because it is the global 2nd max, so only global max is larger).
                // Thus, the global max is not in [1, mid].
                l = mid;
            }
        }
        cout << "! " << r << endl;
    } else {
        // Determine whether the maximum is to the left or right of s.
        // We check the range [1, s].
        int res;
        if (s == n) {
            // Optimization: querying [1, n] would return n (since s=n).
            // This saves a query when s is at the boundary.
            res = s;
        } else {
            cout << "? 1 " << s << endl;
            cin >> res;
        }

        if (res == s) {
            // Case A: The maximum is in [1, s).
            // We use s as a fixed right anchor.
            int l = 1, r = s;
            // Invariant: The maximum element is in the range [l, r)
            while (r - l > 1) {
                int mid = (l + r) / 2;
                cout << "? " << mid << " " << s << endl;
                int ans;
                cin >> ans;
                if (ans == s) {
                    // If s is the second largest in [mid, s], max is in [mid, s).
                    l = mid;
                } else {
                    // If s is not the second largest, it must be the largest in [mid, s].
                    // Max is in [l, mid).
                    r = mid;
                }
            }
            cout << "! " << l << endl;
        } else {
            // Case B: The maximum is in (s, n].
            // We use s as a fixed left anchor.
            int l = s, r = n;
            // Invariant: The maximum element is in the range (l, r]
            while (r - l > 1) {
                int mid = (l + r) / 2;
                cout << "? " << s << " " << mid << endl;
                int ans;
                cin >> ans;
                if (ans == s) {
                    // If s is the second largest in [s, mid], max is in (s, mid].
                    r = mid;
                } else {
                    // If s is not the second largest, it must be the largest in [s, mid].
                    // Max is in (mid, r].
                    l = mid;
                }
            }
            cout << "! " << r << endl;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}