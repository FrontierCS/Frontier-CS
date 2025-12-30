#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long nn, kk;
    cin >> nn >> kk;
    int n = nn;
    long long k = kk;
    vector<vector<long long>> mat(n + 1, vector<long long>(n + 1, -1LL));
    auto get_val = [&](int x, int y) -> long long {
        if (mat[x][y] != -1LL) return mat[x][y];
        cout << "QUERY " << x << " " << y << endl;
        long long v;
        cin >> v;
        mat[x][y] = v;
        return v;
    };
    auto count_leq = [&](long long mid) -> long long {
        long long cnt = 0;
        int i = 1, j = n;
        while (i <= n && j >= 1) {
            long long val = get_val(i, j);
            if (val <= mid) {
                cnt += j;
                i++;
            } else {
                j--;
            }
        }
        return cnt;
    };
    long long lo = 0LL;
    long long hi = 1000000000000000001LL;
    while (lo < hi) {
        long long mid = lo + (hi - lo) / 2;
        if (count_leq(mid) >= k) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    cout << "DONE " << lo << endl;
    return 0;
}