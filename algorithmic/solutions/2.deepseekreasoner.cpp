#include <bits/stdc++.h>
using namespace std;

int ask(const vector<int>& q) {
    cout << 0;
    for (int x : q) cout << ' ' << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

void guess(const vector<int>& p) {
    cout << 1;
    for (int x : p) cout << ' ' << x;
    cout << endl;
    exit(0);
}

int main() {
    int n;
    cin >> n;

    if (n == 1) {
        guess({1});
    }

    vector<int> pos(n + 1, -1); // pos[value] = position (1-indexed)
    vector<int> unknown;
    for (int i = 1; i <= n; ++i) unknown.push_back(i);

    // Step 1: find positions of 1 and 2
    for (int i = 1; i <= n && (pos[1] == -1 || pos[2] == -1); ++i) {
        vector<int> q(n);
        for (int j = 1; j <= n; ++j) {
            if (j == i) q[j-1] = 1;
            else q[j-1] = 2;
        }
        int r = ask(q);
        if (r == 2) pos[1] = i;
        else if (r == 0) pos[2] = i;
    }

    // Remove found positions from unknown
    unknown.clear();
    for (int i = 1; i <= n; ++i) {
        if (i != pos[1] && i != pos[2]) unknown.push_back(i);
    }

    // Step 2: find positions for values 3..n using binary search
    for (int v = 3; v <= n; ++v) {
        int m = unknown.size();
        if (m == 1) {
            pos[v] = unknown[0];
            break;
        }
        int lo = 0, hi = m - 1;
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            vector<int> q(n);
            // set known positions
            for (int w = 1; w < v; ++w) {
                q[pos[w] - 1] = w;
            }
            // set first half of unknown to v
            for (int i = lo; i <= mid; ++i) {
                int idx = unknown[i];
                q[idx - 1] = v;
            }
            // set the rest of unknown to 1 (already placed, so no match)
            for (int i = mid + 1; i < m; ++i) {
                int idx = unknown[i];
                q[idx - 1] = 1;
            }
            int r = ask(q);
            if (r == v) { // pos[v] is in the first half
                hi = mid;
            } else { // r == v-1, pos[v] is in the second half
                lo = mid + 1;
            }
        }
        pos[v] = unknown[lo];
        unknown.erase(unknown.begin() + lo);
    }

    // Build the permutation from the positions
    vector<int> ans(n);
    for (int v = 1; v <= n; ++v) {
        ans[pos[v] - 1] = v;
    }
    guess(ans);

    return 0;
}