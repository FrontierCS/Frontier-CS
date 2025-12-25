#include <bits/stdc++.h>
using namespace std;

int query(const vector<int>& article) {
    cout << "? " << article.size();
    for (int x : article) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

void solve() {
    int L1, L2;
    {
        vector<int> a1(100000, 1);
        L1 = query(a1);
        if (L1 == 100000) {
            cout << "! 1" << endl;
            return;
        }
        if (L1 == 1) {
            cout << "! 100000" << endl;
            return;
        }
    }
    {
        vector<int> a2(100000, 2);
        L2 = query(a2);
    }

    // Brute force over possible W
    int W = -1;
    for (int candidate = 1; candidate <= 100000; ++candidate) {
        int l1 = (100000 + candidate - 1) / candidate;
        if (l1 != L1) continue;

        int l2;
        if (2 > candidate) {
            l2 = 0;
        } else {
            int k = candidate / 2;
            l2 = (100000 + k - 1) / k;
        }
        if (l2 != L2) continue;

        if (W == -1) {
            W = candidate;
        } else {
            // Multiple candidates found – choose the smallest
            // (should not happen for well‑chosen queries)
            W = min(W, candidate);
        }
    }
    cout << "! " << W << endl;
}

int main() {
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}