#include <bits/stdc++.h>
using namespace std;

int main() {
    long long n;
    cin >> n;
    long long best_v = 0;
    int best_k = 1;
    long long best_m = n;
    for (int kk = 1; kk <= 60; ++kk) {
        if ((1LL << (kk - 1)) > n) break;
        long long bk = (1LL << (kk - 1));
        long long mm = n / bk;
        long long sumb = (1LL << kk) - 1;
        if (mm == 0) continue;
        long long vv = (long long)kk * mm * sumb;
        if (vv > best_v) {
            best_v = vv;
            best_k = kk;
            best_m = mm;
        }
    }
    cout << best_k << endl;
    for (int i = 0; i < best_k; ++i) {
        cout << best_m * (1LL << i) << (i + 1 < best_k ? " " : "\n");
    }
    return 0;
}