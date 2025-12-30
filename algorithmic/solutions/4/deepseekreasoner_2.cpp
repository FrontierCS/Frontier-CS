#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <climits>

using namespace std;

int n;
long long k;
vector<vector<bool>> visited;
vector<vector<long long>> value;
int query_count = 0;

long long query(int i, int j) {
    if (visited[i][j]) return value[i][j];
    cout << "QUERY " << i << " " << j << endl;
    cout.flush();
    long long v;
    cin >> v;
    visited[i][j] = true;
    value[i][j] = v;
    ++query_count;
    return v;
}

long long count_le(long long X) {
    long long total = 0;
    int col = n;
    for (int i = 1; i <= n; ++i) {
        while (col > 0) {
            long long v = query(i, col);
            if (v <= X) break;
            --col;
        }
        total += col;
    }
    return total;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> k;
    visited.assign(n + 1, vector<bool>(n + 1, false));
    value.assign(n + 1, vector<long long>(n + 1, 0));

    // get row minima and maxima
    long long min_val = LLONG_MAX, max_val = LLONG_MIN;
    for (int i = 1; i <= n; ++i) {
        long long first = query(i, 1);
        long long last = query(i, n);
        min_val = min(min_val, first);
        max_val = max(max_val, last);
    }

    long long low_val = min_val - 1;   // count(low_val) = 0
    long long high_val = max_val;      // count(high_val) = n*n
    long long cnt_low = 0;
    long long cnt_high = (long long)n * n;

    // interpolation search
    while (low_val + 1 < high_val) {
        double ratio = (double)(k - cnt_low) / (cnt_high - cnt_low);
        long long mid = low_val + (long long)(ratio * (high_val - low_val));
        if (mid <= low_val) mid = low_val + 1;
        if (mid >= high_val) mid = high_val - 1;
        long long cnt = count_le(mid);
        if (cnt >= k) {
            high_val = mid;
            cnt_high = cnt;
        } else {
            low_val = mid;
            cnt_low = cnt;
        }
    }

    cout << "DONE " << high_val << endl;
    cout.flush();

    return 0;
}