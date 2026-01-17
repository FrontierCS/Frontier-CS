#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> a(n+1);
    vector<int> pos(n+1);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    // choose x: for n >= 4 we can use length 4 and 2; otherwise only length 2.
    int x = (n >= 4) ? 3 : 1;

    vector<pair<int, int>> ops;

    // helper to reverse segment [l, r] and update positions
    auto rev = [&](int l, int r) {
        int i = l, j = r;
        while (i < j) {
            swap(a[i], a[j]);
            pos[a[i]] = i;
            pos[a[j]] = j;
            i++;
            j--;
        }
    };

    // process each number from 1 to n
    for (int val = 1; val <= n; val++) {
        while (pos[val] > val) {
            int p = pos[val];
            int dist = p - val;
            if (dist >= 3 && x >= 3) { // can use length 4 reversal
                int l = p - 3;
                int r = p;
                ops.emplace_back(l, r);
                rev(l, r);
            } else if (dist == 2) {
                // two adjacent swaps
                ops.emplace_back(p-1, p);
                rev(p-1, p);
                ops.emplace_back(p-2, p-1);
                rev(p-2, p-1);
            } else { // dist == 1
                ops.emplace_back(p-1, p);
                rev(p-1, p);
            }
        }
    }

    // output
    cout << x << "\n" << ops.size() << "\n";
    for (auto& op : ops) {
        cout << op.first << " " << op.second << "\n";
    }

    return 0;
}