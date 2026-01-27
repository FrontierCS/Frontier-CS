#include <bits/stdc++.h>
using namespace std;

int ask(int i, int j) {
    cout << "? " << i << " " << j << endl;
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (r == -1) exit(0);
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;

        int p = -1, q = -1, a1 = 0, a2 = 0;
        for (int i = 1; i < n; ++i) {
            a1 = ask(i, i + 1);
            a2 = ask(i + 1, i);
            if (a1 != a2) {
                p = i;
                q = i + 1;
                break;
            }
        }

        if (p == -1) {
            // Shouldn't happen under valid constraints, but handle gracefully
            // Fallback: assume impostor is 1
            cout << "! " << 1 << endl;
            cout.flush();
            continue;
        }

        int k = 1;
        if (k == p || k == q) k = 2;
        if (k == p || k == q) k = 3;

        int b1 = ask(k, p);
        int b2 = ask(k, q);
        bool eq = (b1 == b2);

        int imp;
        if (eq) {
            // Pair is (K, I)
            if (a1 == 1 && a2 == 0) imp = q;
            else imp = p;
        } else {
            // Pair is (I, V)
            if (a1 == 1 && a2 == 0) imp = p;
            else imp = q;
        }

        cout << "! " << imp << endl;
        cout.flush();
    }

    return 0;
}