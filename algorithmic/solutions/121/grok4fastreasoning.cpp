#include <bits/stdc++.h>
using namespace std;

long double mypow(long double base, int exp) {
    long double res = 1.0;
    for (int i = 0; i < exp; i++) {
        res *= base;
    }
    return res;
}

int main() {
    int n, m;
    cin >> n >> m;
    vector<string> pats(m);
    for (auto &s : pats) cin >> s;
    long double num = 0.0;
    int M = 1 << m;
    for (int mask = 1; mask < M; mask++) {
        int bits = __builtin_popcount(mask);
        long double sign = (bits % 2 == 1) ? 1.0 : -1.0;
        bool poss = true;
        int frees = 0;
        for (int pos = 0; pos < n && poss; pos++) {
            char forced = '\0';
            bool has_fixed = false;
            bool conflict = false;
            for (int j = 0; j < m; j++) {
                if (mask & (1 << j)) {
                    char c = pats[j][pos];
                    if (c != '?') {
                        if (has_fixed) {
                            if (c != forced) {
                                conflict = true;
                                break;
                            }
                        } else {
                            forced = c;
                            has_fixed = true;
                        }
                    }
                }
            }
            if (conflict) {
                poss = false;
            } else if (!has_fixed) {
                frees++;
            }
        }
        if (poss) {
            long double contrib = mypow(4.0, frees);
            num += sign * contrib;
        }
    }
    long double total = mypow(4.0, n);
    long double prob = num / total;
    cout << fixed << setprecision(10) << prob << endl;
    return 0;
}