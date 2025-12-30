#include <iostream>
#include <vector>
#include <cstdlib>
using namespace std;

int query(int x, const vector<int>& indices) {
    cout << "? " << x << " " << indices.size();
    for (int idx : indices) cout << " " << idx;
    cout << endl;
    cout.flush();
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

int findOccurrence(int x, int m) {
    int l = 1, r = m;
    while (l < r) {
        int mid = (l + r) / 2;
        vector<int> S;
        S.reserve(mid - l + 1);
        for (int i = l; i <= mid; ++i) S.push_back(i);
        if (query(x, S) == 1) r = mid;
        else l = mid + 1;
    }
    return l;
}

void solve() {
    int n;
    cin >> n;
    if (n == -1) exit(0);
    int m = 2 * n - 1;
    for (int x = 1; x <= n; ++x) {
        int idx = findOccurrence(x, m);
        vector<int> S;
        S.reserve(m - 1);
        for (int i = 1; i <= m; ++i)
            if (i != idx) S.push_back(i);
        if (query(x, S) == 0) {
            cout << "! " << x << endl;
            cout.flush();
            return;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    cin >> t;
    while (t--) solve();
    return 0;
}