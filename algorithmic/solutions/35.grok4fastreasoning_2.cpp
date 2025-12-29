#include <bits/stdc++.h>
using namespace std;

int main() {
    int t;
    cin >> t;
    for (int test = 0; test < t; test++) {
        int nn;
        cin >> nn;
        if (nn == -1) return 0;
        int n = nn;
        int m = 2 * n - 1;
        bool found = false;
        for (int x = 1; x <= n && !found; x++) {
            // binary search to find the first position p with a_p = x
            int low = 1, high = m;
            while (low < high) {
                int md = (low + high) / 2;
                cout << "? " << x << " " << md;
                for (int j = 1; j <= md; j++) {
                    cout << " " << j;
                }
                cout << endl;
                cout.flush();
                int res;
                cin >> res;
                if (res == -1) return 0;
                if (res == 1) {
                    high = md;
                } else {
                    low = md + 1;
                }
            }
            int p = low;
            // now query all positions except p
            cout << "? " << x << " " << (m - 1);
            for (int j = 1; j <= m; j++) {
                if (j != p) {
                    cout << " " << j;
                }
            }
            cout << endl;
            cout.flush();
            int res2;
            cin >> res2;
            if (res2 == -1) return 0;
            if (res2 == 0) {
                // x appears only once
                cout << "! " << x << endl;
                cout.flush();
                found = true;
            }
        }
    }
    return 0;
}