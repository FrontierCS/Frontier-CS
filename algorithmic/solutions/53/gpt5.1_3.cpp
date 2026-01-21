#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) return 0;
        if (n == -1) return 0;

        // Choose arbitrary k = 1
        cout << 1 << "\n";
        cout.flush();

        // Construct an arbitrary derangement of size n
        vector<int> p(n + 1);
        if (n % 2 == 0) {
            for (int i = 1; i <= n; i += 2) {
                p[i] = i + 1;
                p[i + 1] = i;
            }
        } else {
            // First 3: 1->2, 2->3, 3->1
            p[1] = 2;
            p[2] = 3;
            p[3] = 1;
            for (int i = 4; i <= n; i += 2) {
                if (i + 1 <= n) {
                    p[i] = i + 1;
                    p[i + 1] = i;
                }
            }
        }

        cout << "! ";
        for (int i = 1; i <= n; ++i) {
            cout << p[i] << (i == n ? '\n' : ' ');
        }
        cout.flush();
    }
    return 0;
}