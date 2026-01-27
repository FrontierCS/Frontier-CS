#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) {
        cout << "! 0\n" << flush;
        return 0;
    }

    vector<pair<long long, long long>> res(n, {-1, -1});

    for (int i = 0; i < n; ++i) {
        cout << "? " << i << "\n" << flush;
        long long a0, a1;
        if (!(cin >> a0 >> a1)) {
            cout << "! 0\n" << flush;
            return 0;
        }
        res[i] = {a0, a1};
        if (a0 == 0 && a1 == 0) {
            cout << "! " << i << "\n" << flush;
            return 0;
        }
    }

    int best = 0;
    long long bestE = LLONG_MAX;
    for (int i = 0; i < n; ++i) {
        if (res[i].first != -1) {
            long long E = res[i].first + res[i].second;
            if (E < bestE) {
                bestE = E;
                best = i;
            }
        }
    }

    cout << "! " << best << "\n" << flush;
    return 0;
}