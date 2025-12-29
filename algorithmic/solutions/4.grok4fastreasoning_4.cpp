#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    long long k;
    cin >> n >> k;
    vector<vector<long long>> queried(n + 1, vector<long long>(n + 1, LLONG_MIN));
    auto get = [&](int x, int y) -> long long {
        if (queried[x][y] != LLONG_MIN) return queried[x][y];
        cout << "QUERY " << x << " " << y << endl << flush;
        long long v;
        cin >> v;
        queried[x][y] = v;
        return v;
    };
    auto count_leq = [&](long long x) -> long long {
        long long cnt = 0;
        int r = 1, c = n;
        while (r <= n && c >= 1) {
            long long val = get(r, c);
            if (val <= x) {
                cnt += c;
                r++;
            } else {
                c--;
            }
        }
        return cnt;
    };
    long long low = get(1, 1);
    long long high = get(n, n);
    while (low < high) {
        long long mid = low + (high - low) / 2;
        long long cnt = count_leq(mid);
        if (cnt >= k) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    cout << "DONE " << low << endl << flush;
    return 0;
}