#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        vector<int> demag;
        for (int i = 1; i <= n; ++i) {
            string s;
            cin >> s;
            if (s == "0" || s == "-") {
                demag.push_back(i);
            }
        }
        cout << demag.size() << "\n";
        for (int i = 0; i < (int)demag.size(); ++i) {
            if (i) cout << ' ';
            cout << demag[i];
        }
        cout << "\n";
    }
    return 0;
}