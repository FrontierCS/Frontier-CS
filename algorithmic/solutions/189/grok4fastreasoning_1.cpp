#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    string S1, S2;
    getline(cin, S1);
    getline(cin, S2);
    size_t N = S1.size();
    size_t M = S2.size();
    long long best_sc = -1;
    int best_d = 0;
    const int MAX_S = 128;
    for (int dd = -MAX_S; dd <= MAX_S; ++dd) {
        int d = dd;
        int st = max(0, -d);
        int en = min(static_cast<int>(N) - 1, static_cast<int>(M) - 1 - d);
        if (st > en) continue;
        int ll = en - st + 1;
        int pp = 0;
        for (int ii = st; ii <= en; ++ii) {
            if (S1[ii] == S2[ii + d]) ++pp;
        }
        long long sc = static_cast<long long>(ll) + pp;
        if (sc > best_sc) {
            best_sc = sc;
            best_d = d;
        }
    }
    // also check d=0 explicitly if needed, but already included
    string T;
    int d = best_d;
    int st_i = max(0, -d);
    int en_i = min(static_cast<int>(N) - 1, static_cast<int>(M) - 1 - d);
    int L = (st_i <= en_i) ? en_i - st_i + 1 : 0;
    if (L == 0) {
        T = string(N, 'D') + string(M, 'I');
    } else {
        if (d >= 0) {
            T += string(d, 'I');
            T += string(L, 'M');
            T += string(N - L, 'D');
            int end_j = d + en_i;
            int rem_I = static_cast<int>(M) - end_j - 1;
            T += string(max(0, rem_I), 'I');
        } else {
            int num_init_D = -d;
            T += string(num_init_D, 'D');
            T += string(L, 'M');
            int total_consumed_i = num_init_D + L;
            T += string(N - total_consumed_i, 'D');
            T += string(M - L, 'I');
        }
    }
    cout << T << '\n';
    return 0;
}