#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;

        vector<int> alive(n);
        iota(alive.begin(), alive.end(), 0);

        auto use_pen = [&](int i) -> int {
            cout << 0 << " " << i << endl;
            cout.flush();
            int x;
            if (!(cin >> x)) exit(0);
            return x;
        };

        while ((int)alive.size() > 2) {
            int a = alive[0];
            int b = alive[1];
            int c = alive[2];

            int xa = use_pen(a);
            if (xa == 0) {
                // a is empty, remove it
                alive.erase(alive.begin());
                continue;
            }

            int xb = use_pen(b);
            if (xb == 0) {
                // b is empty, remove it
                alive.erase(alive.begin() + 1);
                continue;
            }

            // both a and b had ink, consume 1 each and remove c
            alive.erase(alive.begin() + 2);
        }

        // select the remaining two pens
        cout << 1 << " " << alive[0] << " " << alive[1] << endl;
        cout.flush();
    }
    return 0;
}