#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    cin >> t;
    while (t--) {
        // First query: single word of length 100000.
        cout << "? 1 100000" << endl;
        int resp;
        cin >> resp;
        if (resp == 1) {
            // W >= 100000, so W must be exactly 100000.
            cout << "! 100000" << endl;
            continue;
        }

        // Now W < 100000.
        // Second query: 100000 words of length 1.
        cout << "? 100000";
        for (int i = 0; i < 100000; ++i) {
            cout << " 1";
        }
        cout << endl;
        cin >> resp;

        // resp = ceil(100000 / W)
        // We need to find W such that ceil(100000 / W) = resp.
        // The correct W is the unique integer satisfying:
        //   100000 / resp <= W < 100000 / (resp - 1)   (if resp > 1)
        // For resp = 1, W >= 100000, but we already handled that.
        // Since resp >= 2, we compute bounds.
        int low = 100000 / resp;
        int high = (resp == 1) ? 100000 : (100000 / (resp - 1));
        // Because of integer division, adjust low upward.
        while (100000 / low > resp) ++low;
        while (100000 / low < resp) --low;
        // Now low is the smallest integer with ceil(100000/low) = resp.
        // Check neighbouring values to be safe.
        int W = low;
        if (100000 / W != resp - 1 && (100000 + W - 1) / W == resp) {
            // OK
        } else {
            ++W;
        }
        cout << "! " << W << endl;
    }
    return 0;
}