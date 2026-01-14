#include <bits/stdc++.h>
using namespace std;

int n;

int query(int l, int r) {
    cout << "0 " << l << " " << r << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
}

bool lessThan(int i, int j) {
    int l = min(i, j);
    int r = max(i, j);
    int res = query(l, r);
    if (i == l) {
        // i is the left index
        return res == 0; // p_i < p_j when no inversion
    } else {
        // i is the right index
        return res == 1; // p_j > p_i means p_i < p_j
    }
}

int main() {
    cin >> n;
    vector<int> sorted; // indices in increasing order of p
    for (int i = 1; i <= n; i++) {
        int lo = 0, hi = sorted.size();
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            if (lessThan(sorted[mid], i)) {
                lo = mid + 1;
            } else {
                hi = mid;
            }
        }
        sorted.insert(sorted.begin() + lo, i);
    }
    vector<int> p(n + 1);
    for (int rank = 0; rank < n; rank++) {
        p[sorted[rank]] = rank + 1;
    }
    cout << "1";
    for (int i = 1; i <= n; i++) {
        cout << " " << p[i];
    }
    cout << endl;
    cout.flush();
    return 0;
}