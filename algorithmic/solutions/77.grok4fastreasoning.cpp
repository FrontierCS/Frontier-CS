#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n, m;
    cin >> n >> m;
    vector<int> cor(n, 0);
    for (int w = 0; w < m; ++w) {
        string s;
        cin >> s;
        int maxc = 0;
        for (int i = 0; i < n; ++i) {
            maxc = max(maxc, cor[i]);
        }
        int cnt0 = 0, cnt1 = 0;
        for (int i = 0; i < n; ++i) {
            if (cor[i] == maxc) {
                if (s[i] == '0') ++cnt0;
                else ++cnt1;
            }
        }
        char pred;
        if (cnt0 > cnt1) pred = '0';
        else if (cnt1 > cnt0) pred = '1';
        else {
            int t0 = 0;
            for (char c : s) if (c == '0') ++t0;
            int t1 = n - t0;
            pred = (t1 > t0 ? '1' : '0');
        }
        cout << pred << endl;
        int outc;
        cin >> outc;
        char r = '0' + outc;
        for (int i = 0; i < n; ++i) {
            if (s[i] == r) ++cor[i];
        }
    }
}