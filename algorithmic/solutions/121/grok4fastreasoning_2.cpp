#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<string> strs(m);
    for (auto& str : strs) {
        cin >> str;
    }
    double prob = 0.0;
    int M = 1 << m;
    for (int mask = 1; mask < M; mask++) {
        int k = __builtin_popcount(mask);
        double sign = (k % 2 ? 1.0 : -1.0);
        double p = 1.0;
        bool ok = true;
        for (int j = 0; j < n && ok; j++) {
            char req = '\0';
            bool conf = false;
            for (int i = 0; i < m; i++) {
                if ((mask & (1 << i)) == 0) continue;
                char c = strs[i][j];
                if (c != '?') {
                    if (req == '\0') {
                        req = c;
                    } else if (req != c) {
                        conf = true;
                        break;
                    }
                }
            }
            if (conf) {
                ok = false;
                continue;
            }
            int choices = (req == '\0' ? 4 : 1);
            p *= (choices / 4.0);
        }
        if (ok) {
            prob += sign * p;
        }
    }
    cout << fixed << setprecision(15) << prob << endl;
    return 0;
}