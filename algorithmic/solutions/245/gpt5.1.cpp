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

        vector<int> diff;
        diff.reserve(n);

        for (int i = 2; i <= n; ++i) {
            cout << "? 1 " << i << "\n" << flush;
            int a;
            if (!(cin >> a)) return 0;
            if (a == -1) return 0;

            cout << "? " << i << " 1\n" << flush;
            int b;
            if (!(cin >> b)) return 0;
            if (b == -1) return 0;

            if (a != b) diff.push_back(i);
        }

        int impostor;
        if ((int)diff.size() == 1) impostor = diff[0];
        else impostor = 1;

        cout << "! " << impostor << "\n" << flush;
    }

    return 0;
}