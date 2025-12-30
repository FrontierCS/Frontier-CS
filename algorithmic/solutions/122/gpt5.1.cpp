#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    while (t--) {
        int low = 1, high = 100000;

        while (low < high) {
            int mid = (low + high + 1) / 2;
            cout << "? 1 " << mid << endl;
            cout.flush();

            int res;
            if (!(cin >> res)) return 0;
            if (res == -1) return 0;

            if (res == 0) {
                high = mid - 1;
            } else {
                low = mid;
            }
        }

        cout << "! " << low << endl;
        cout.flush();
    }

    return 0;
}