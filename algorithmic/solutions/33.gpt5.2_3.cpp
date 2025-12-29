#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int q;
    cin >> q;

    vector<unsigned long long> M(61);
    for (int s = 0; s <= 60; s++) {
        if (s == 0) M[s] = 0;
        else M[s] = (1ULL << s) - 1ULL;
    }

    while (q--) {
        unsigned long long k;
        cin >> k;

        unsigned long long rem = k - 1; // need sum of (2^s - 1)
        vector<int> blocks;
        while (rem > 0) {
            int best = 1;
            for (int s = 60; s >= 1; s--) {
                if (M[s] <= rem) {
                    best = s;
                    break;
                }
            }
            blocks.push_back(best);
            rem -= M[best];
        }

        int n = 0;
        for (int s : blocks) n += s;

        cout << n << "\n";
        vector<int> perm;
        perm.reserve(n);

        int cur = n - 1;
        for (int s : blocks) {
            int start = cur - s + 1;
            for (int v = start; v <= cur; v++) perm.push_back(v);
            cur -= s;
        }

        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << perm[i];
        }
        cout << "\n";
    }

    return 0;
}