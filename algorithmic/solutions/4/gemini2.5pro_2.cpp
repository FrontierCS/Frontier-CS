#include <iostream>
#include <vector>
#include <queue>
#include <map>
#include <algorithm>

using namespace std;

long long n, k;
map<pair<int, int>, long long> cache;

long long query(int r, int c) {
    if (r < 1 || r > n || c < 1 || c > n) {
        // This case should not be reached with valid logic.
        // It's a safeguard against out-of-bounds access.
        return -1; 
    }
    if (cache.count({r, c})) {
        return cache[{r, c}];
    }
    cout << "QUERY " << r << " " << c << endl;
    long long val;
    cin >> val;
    return cache[{r, c}] = val;
}

void done(long long ans) {
    cout << "DONE " << ans << endl;
}

void solve_min_pq() {
    priority_queue<pair<long long, pair<int, int>>, vector<pair<long long, pair<int, int>>>, greater<pair<long long, pair<int, int>>>> pq;

    for (int i = 1; i <= n; ++i) {
        long long val = query(i, 1);
        pq.push({val, {i, 1}});
    }

    long long result = -1;
    for (int i = 0; i < k; ++i) {
        pair<long long, pair<int, int>> top = pq.top();
        pq.pop();
        result = top.first;
        int r = top.second.first;
        int c = top.second.second;

        if (c < n) {
            long long val = query(r, c + 1);
            pq.push({val, {r, c + 1}});
        }
    }
    done(result);
}

void solve_max_pq() {
    long long k_prime = n * n - k + 1;
    priority_queue<pair<long long, pair<int, int>>> pq;

    for (int i = 1; i <= n; ++i) {
        long long val = query(i, n);
        pq.push({val, {i, n}});
    }

    long long result = -1;
    for (int i = 0; i < k_prime; ++i) {
        pair<long long, pair<int, int>> top = pq.top();
        pq.pop();
        result = top.first;
        int r = top.second.first;
        int c = top.second.second;

        if (c > 1) {
            long long val = query(r, c - 1);
            pq.push({val, {r, c - 1}});
        }
    }
    done(result);
}

long long count_le(long long x) {
    long long count = 0;
    int r = 1, c = n;
    while (r <= n && c >= 1) {
        if (query(r, c) <= x) {
            count += c;
            r++;
        } else {
            c--;
        }
    }
    return count;
}

void solve_binary_search() {
    long long low = query(1, 1);
    long long high = query(n, n);
    long long ans = high;

    while (low <= high) {
        long long mid = low + (high - low) / 2;
        if (count_le(mid) >= k) {
            ans = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }
    done(ans);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> k;

    long long query_limit = 50000;
    
    if (n + k - 1 <= query_limit) {
        solve_min_pq();
    } 
    else if (n + (n * n - k + 1) - 1 <= query_limit) {
        solve_max_pq();
    }
    else {
        solve_binary_search();
    }

    return 0;
}