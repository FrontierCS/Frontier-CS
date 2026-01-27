#include <bits/stdc++.h>
using namespace std;

int query(int a, int b) {
    cout << "? 1 1\n" << a << "\n" << b << endl;
    cout.flush();
    int F;
    if (!(cin >> F)) exit(0);
    return F;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;

        vector<int> isZero(n + 1, 0);
        int ref = -1;

        bool found = false;
        for (int i = 1; i <= n && !found; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                int F = query(i, j);
                if (F != 0) {
                    ref = i;
                    found = true;
                    break;
                }
            }
        }

        if (!found) {
            // According to the problem there are at least two non-'-' magnets,
            // so this should not happen. Still, to be safe:
            ref = 1;
        }

        for (int i = 1; i <= n; ++i) {
            if (i == ref) continue;
            int F = query(ref, i);
            if (F == 0) isZero[i] = 1;
        }

        vector<int> zeros;
        for (int i = 1; i <= n; ++i)
            if (isZero[i])
                zeros.push_back(i);

        cout << "! " << zeros.size();
        for (int x : zeros) cout << ' ' << x;
        cout << endl;
        cout.flush();
    }

    return 0;
}