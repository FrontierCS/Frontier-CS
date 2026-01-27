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

        vector<int> from1(n + 1), to1(n + 1);

        // Queries: ? 1 j for j = 2..n
        for (int j = 2; j <= n; ++j) {
            cout << "? 1 " << j << "\n";
            cout.flush();
            int res;
            if (!(cin >> res)) return 0;
            if (res == -1) return 0;
            from1[j] = res;
        }

        // Queries: ? i 1 for i = 2..n
        for (int i = 2; i <= n; ++i) {
            cout << "? " << i << " 1\n";
            cout.flush();
            int res;
            if (!(cin >> res)) return 0;
            if (res == -1) return 0;
            to1[i] = res;
        }

        long long x00 = 0, x01 = 0, x10 = 0, x11 = 0;
        for (int i = 2; i <= n; ++i) {
            int a = to1[i];    // A[i][1]
            int b = from1[i];  // A[1][i]
            if (a == 0 && b == 0) ++x00;
            else if (a == 0 && b == 1) ++x01;
            else if (a == 1 && b == 0) ++x10;
            else ++x11; // a == 1 && b == 1
        }

        int KnightsMin = (3 * n) / 10 + 1;

        bool caseA = (x10 == 0 && x01 == 1 && (1 + x11 >= KnightsMin)); // 1 is Knight
        bool caseB = (x01 == 0 && x10 == 1 && (x00 >= KnightsMin));     // 1 is Knave
        bool caseC = (x00 == 0 && x11 == 0 && (x10 >= KnightsMin));     // 1 is Impostor

        int imp = -1;

        if (caseA) {
            // Impostor is unique i > 1 with pattern (0,1)
            for (int i = 2; i <= n; ++i) {
                if (to1[i] == 0 && from1[i] == 1) {
                    imp = i;
                    break;
                }
            }
        } else if (caseB) {
            // Impostor is unique i > 1 with pattern (1,0)
            for (int i = 2; i <= n; ++i) {
                if (to1[i] == 1 && from1[i] == 0) {
                    imp = i;
                    break;
                }
            }
        } else if (caseC) {
            // Player 1 is the Impostor
            imp = 1;
        } else {
            // Fallback (should not occur with a valid interactor)
            imp = 1;
        }

        cout << "! " << imp << "\n";
        cout.flush();
    }

    return 0;
}