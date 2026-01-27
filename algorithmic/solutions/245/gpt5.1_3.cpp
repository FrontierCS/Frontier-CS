#include <bits/stdc++.h>
using namespace std;

int ask(int i, int j) {
    cout << "? " << i << ' ' << j << endl;
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;

        if (n <= 1) {
            cout << "! 1" << endl;
            cout.flush();
            continue;
        }

        int cntB = 0, idxB = 1;

        for (int i = 2; i <= n; ++i) {
            int a = ask(1, i);
            int b = ask(i, 1);
            int t = a ^ b; // s1 XOR si

            if (t == 1) {
                ++cntB;
                idxB = i;
            }
        }

        int impostor = (cntB == 1 ? idxB : 1);
        cout << "! " << impostor << endl;
        cout.flush();
    }

    return 0;
}