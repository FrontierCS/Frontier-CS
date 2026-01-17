#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }
    vector<pair<int, int>> ops;
    for (int i = 1; i <= n; i++) {
        int pos = i;
        for (int j = i; j <= n; j++) {
            if (a[j] == i) {
                pos = j;
                break;
            }
        }
        while (pos > i) {
            int delta = pos - i;
            if (delta >= 3) {
                int left = pos - 3;
                ops.emplace_back(left, pos);
                reverse(a.begin() + left, a.begin() + pos + 1);
                pos = left;
            } else {
                int left = pos - 1;
                ops.emplace_back(left, pos);
                reverse(a.begin() + left, a.begin() + pos + 1);
                pos = left;
            }
        }
    }
    cout << 3 << endl;
    cout << ops.size() << endl;
    for (auto [l, r] : ops) {
        cout << l << " " << r << endl;
    }
    return 0;
}