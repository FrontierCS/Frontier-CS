#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<string> s(m);
    for (int i = 0; i < m; i++) {
        cin >> s[i];
    }
    double total = 0.0;
    int M = 1 << m;
    for (int mask = 1; mask < M; mask++) {
        double p = 1.0;
        bool ok = true;
        for (int j = 0; j < n && ok; j++) {
            char req = 0;
            bool conf = false;
            for (int b = 0; b < m; b++) {
                if ((mask & (1 << b)) == 0) continue;
                char c = s[b][j];
                if (c == '?') continue;
                if (req == 0) {
                    req = c;
                } else if (c != req) {
                    conf = true;
                    break;
                }
            }
            if (conf) {
                ok = false;
                break;
            }
            if (req != 0) {
                p *= 0.25;
            }
        }
        if (ok) {
            int k = __builtin_popcount(mask);
            double sign = (k % 2 == 1) ? 1.0 : -1.0;
            total += sign * p;
        }
    }
    printf("%.10f\n", total);
    return 0;
}