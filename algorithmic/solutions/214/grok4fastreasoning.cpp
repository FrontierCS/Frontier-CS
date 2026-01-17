#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> arr(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> arr[i];
    }
    vector<pair<int, int>> ops;
    for (int i = 1; i < n; i++) {
        int j = i;
        while (j <= n && arr[j] != i) j++;
        while (j > i) {
            if (j - i >= 3) {
                int l = j - 3;
                reverse(arr.begin() + l, arr.begin() + j + 1);
                ops.emplace_back(l, j);
                j = l;
            } else {
                int l = j - 1;
                reverse(arr.begin() + l, arr.begin() + j + 1);
                ops.emplace_back(l, j);
                j = l;
            }
        }
    }
    cout << 3 << endl;
    cout << ops.size() << endl;
    for (auto p : ops) {
        cout << p.first << " " << p.second << endl;
    }
    return 0;
}