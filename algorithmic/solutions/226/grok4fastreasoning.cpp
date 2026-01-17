#include <bits/stdc++.h>
using namespace std;

int main() {
    long long n, x, y;
    cin >> n >> x >> y;
    if (x > y) swap(x, y);
    long long dd = __gcd(x, y);
    long long x1 = x / dd;
    long long y1 = y / dd;
    long long zz = x1 + y1;
    long long answer = 0;
    for (long long rr = 1; rr <= dd && rr <= n; rr++) {
        long long mmm = (n - rr) / dd + 1;
        if (mmm == 0) continue;
        vector<long long> we(zz, 0LL);
        for (long long ss = 0; ss < zz; ss++) {
            if (ss < mmm) {
                we[ss] = (mmm - 1 - ss) / zz + 1;
            }
        }
        vector<long long> pp(zz);
        for (long long kk = 0; kk < zz; kk++) {
            pp[kk] = (kk * x1 % zz + zz) % zz;
        }
        vector<long long> www(zz);
        for (long long kk = 0; kk < zz; kk++) {
            www[kk] = we[pp[kk]];
        }
        long long ress;
        if (zz == 1) {
            ress = www[0];
        } else {
            auto path_max = [&](int stt, int enn) -> long long {
                if (stt > enn) return 0LL;
                int lll = enn - stt + 1;
                vector<long long> notake(lll + 1, 0LL);
                vector<long long> ttake(lll + 1, LLONG_MIN / 2);
                notake[0] = 0;
                ttake[0] = LLONG_MIN / 2;
                for (int jj = 1; jj <= lll; jj++) {
                    long long vall = www[stt + jj - 1];
                    notake[jj] = max(notake[jj - 1], ttake[jj - 1]);
                    ttake[jj] = vall + notake[jj - 1];
                }
                return max(notake[lll], ttake[lll]);
            };
            long long cc1 = path_max(1, zz - 1);
            long long cc2 = www[0];
            if (zz >= 3) {
                cc2 += path_max(2, zz - 2);
            }
            ress = max(cc1, cc2);
        }
        answer += ress;
    }
    cout << answer << endl;
    return 0;
}