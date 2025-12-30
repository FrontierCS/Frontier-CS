#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int L = 1, R = n;
    int queriesUsed = 0;
    const int MAXQ = 53;

    if (n == 1) {
        cout << "! 1\n";
        cout.flush();
        return 0;
    }

    while (L < R && queriesUsed < MAXQ) {
        int m = (L + R) / 2;
        int k = m - L + 1;
        cout << "? " << k;
        for (int i = L; i <= m; ++i) cout << " " << i;
        cout << "\n";
        cout.flush();

        string ans;
        if (!(cin >> ans)) return 0;
        ++queriesUsed;

        if (ans == "YES") {
            R = m;
        } else {
            L = m + 1;
        }
    }

    cout << "! " << L << "\n";
    cout.flush();
    return 0;
}