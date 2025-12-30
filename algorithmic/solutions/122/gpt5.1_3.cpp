#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    const int N1 = 100000;
    const int N2 = 99991; // arbitrary <= 1e5

    while (t--) {
        // First query: N1 ones
        cout << "? " << N1;
        for (int i = 0; i < N1; ++i) cout << " 1";
        cout << endl;
        cout.flush();

        int L1;
        if (!(cin >> L1)) return 0;
        if (L1 == -1) return 0;

        // Second query: N2 ones
        cout << "? " << N2;
        for (int i = 0; i < N2; ++i) cout << " 1";
        cout << endl;
        cout.flush();

        int L2;
        if (!(cin >> L2)) return 0;
        if (L2 == -1) return 0;

        int Wans = -1;
        for (int W = 1; W <= 100000; ++W) {
            int a = (N1 + W - 1) / W;
            int b = (N2 + W - 1) / W;
            if (a == L1 && b == L2) {
                Wans = W;
                break;
            }
        }
        if (Wans == -1) Wans = 1; // fallback (shouldn't normally happen)

        cout << "! " << Wans << endl;
        cout.flush();
    }

    return 0;
}