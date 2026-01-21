#include <bits/stdc++.h>
using namespace std;

long long ask(long long u, long long d) {
    cout << "? " << u << ' ' << d << endl;
    cout.flush();
    long long x;
    if (!(cin >> x)) {
        exit(0);
    }
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long h;
    if (!(cin >> h)) return 0;
    long long n = (1LL << h) - 1;
    long long D = 2 * (h - 1);

    __int128 total_sum_queries = 0;
    for (long long u = 1; u <= n; ++u) {
        for (long long d = 1; d <= D; ++d) {
            long long res = ask(u, d);
            total_sum_queries += (__int128)res;
        }
    }

    __int128 denom = n - 1;
    __int128 total_sum = total_sum_queries / denom;
    long long answer = (long long)total_sum;

    cout << "! " << answer << endl;
    cout.flush();
    return 0;
}