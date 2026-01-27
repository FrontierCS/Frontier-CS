#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int h;
    if (!(cin >> h)) return 0;
    long long n = (1LL << h) - 1;
    int D = 2 * (h - 1);

    vector<int> odd_ds;
    for (int d = 1; d <= D; d += 2) odd_ds.push_back(d);

    long long first_val = -1, second_val = -1;
    bool have_first = false, have_second = false;

    for (long long u = 1; u <= n; ++u) {
        long long O = 0;
        for (int d : odd_ds) {
            cout << "? " << u << " " << d << "\n" << flush;
            long long ans;
            if (!(cin >> ans)) return 0;
            if (ans < 0) return 0;
            O += ans;
        }
        if (!have_first) {
            first_val = O;
            have_first = true;
        } else if (O != first_val) {
            second_val = O;
            have_second = true;
            long long S = first_val + second_val;
            cout << "! " << S << "\n" << flush;
            return 0;
        }
    }

    // If all observed O are equal, then P0 == P1, so S = 2 * O
    long long S = 2 * first_val;
    cout << "! " << S << "\n" << flush;
    return 0;
}