#include <bits/stdc++.h>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n, m;
    cin >> n >> m;
    vector<int> errs(n, 0);
    for (int t = 0; t < m; t++) {
        string s;
        cin >> s;
        int min_err = INT_MAX;
        for (int i = 0; i < n; i++) {
            min_err = min(min_err, errs[i]);
        }
        int count0 = 0, count1 = 0;
        for (int i = 0; i < n; i++) {
            if (errs[i] == min_err) {
                int p = s[i] - '0';
                if (p == 0) count0++;
                else count1++;
            }
        }
        int pred = (count1 > count0) ? 1 : 0;
        cout << pred << endl;
        int actual;
        cin >> actual;
        for (int i = 0; i < n; i++) {
            int p = s[i] - '0';
            if (p != actual) errs[i]++;
        }
    }
    return 0;
}