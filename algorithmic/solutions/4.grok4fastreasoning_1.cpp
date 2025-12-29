#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    long long k;
    cin >> n >> k;
    vector<vector<long long>> mat(n + 1, vector<long long>(n + 1, -1LL));

    auto get = [&](int i, int j) -> long long {
        if (mat[i][j] != -1LL) return mat[i][j];
        cout << "QUERY " << i << " " << j << endl;
        cout.flush();
        long long v;
        cin >> v;
        mat[i][j] = v;
        return v;
    };

    auto count_leq = [&](long long x) -> long long {
        long long cnt = 0;
        int i = 1, j = n;
        while (i <= n && j >= 1) {
            long long val = get(i, j);
            if (val > x) {
                j--;
            } else {
                cnt += j;
                i++;
            }
        }
        return cnt;
    };

    // Binary search for the row p
    int lo = 1, hi = n;
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        bool in_first_mid;
        if (mid == n) {
            in_first_mid = true;
        } else {
            long long xx = get(mid + 1, 1) - 1;
            long long s = count_leq(xx);
            in_first_mid = (s >= k);
        }
        if (in_first_mid) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    int p = lo;

    // Binary search for the column q in row p
    lo = 1, hi = n;
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        long long xx = get(p, mid);
        long long s = count_leq(xx);
        if (s >= k) {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    int q = lo;

    long long ans = get(p, q);

    cout << "DONE " << ans << endl;
    cout.flush();
    return 0;
}