#include <iostream>
#include <vector>
#include <map>
#include <queue>
#include <functional>
#include <tuple>

using namespace std;

long long n;
long long k;

map<pair<int, int>, long long> memo;

long long do_query(int r, int c) {
    if (memo.count({r, c})) {
        return memo[{r, c}];
    }
    cout << "QUERY " << r << " " << c << endl;
    long long v;
    cin >> v;
    return memo[{r, c}] = v;
}

void done(long long ans) {
    cout << "DONE " << ans << endl;
}

void solve_dijkstra_min() {
    priority_queue<tuple<long long, int, int>, vector<tuple<long long, int, int>>, greater<tuple<long long, int, int>>> pq;
    vector<vector<bool>> visited(n + 1, vector<bool>(n + 1, false));

    long long val = do_query(1, 1);
    pq.emplace(val, 1, 1);
    visited[1][1] = true;

    long long result = -1;
    for (long long i = 0; i < k; ++i) {
        auto [v, r, c] = pq.top();
        pq.pop();
        result = v;

        if (r + 1 <= n && !visited[r + 1][c]) {
            long long next_val = do_query(r + 1, c);
            pq.emplace(next_val, r + 1, c);
            visited[r + 1][c] = true;
        }
        if (c + 1 <= n && !visited[r][c + 1]) {
            long long next_val = do_query(r, c + 1);
            pq.emplace(next_val, r, c + 1);
            visited[r][c + 1] = true;
        }
    }
    done(result);
}

void solve_dijkstra_max() {
    long long k_rev = n * n - k + 1;
    priority_queue<tuple<long long, int, int>> pq;
    vector<vector<bool>> visited(n + 1, vector<bool>(n + 1, false));

    long long val = do_query(n, n);
    pq.emplace(val, n, n);
    visited[n][n] = true;

    long long result = -1;
    for (long long i = 0; i < k_rev; ++i) {
        auto [v, r, c] = pq.top();
        pq.pop();
        result = v;

        if (r - 1 >= 1 && !visited[r - 1][c]) {
            long long next_val = do_query(r - 1, c);
            pq.emplace(next_val, r - 1, c);
            visited[r - 1][c] = true;
        }
        if (c - 1 >= 1 && !visited[r][c - 1]) {
            long long next_val = do_query(r, c - 1);
            pq.emplace(next_val, r, c - 1);
            visited[r][c - 1] = true;
        }
    }
    done(result);
}

long long count_le(long long val) {
    long long count = 0;
    int c = n;
    for (int r = 1; r <= n; ++r) {
        while (c >= 1 && do_query(r, c) > val) {
            c--;
        }
        count += c;
    }
    return count;
}

void solve_binary_search() {
    long long low = do_query(1, 1);
    long long high = do_query(n, n);
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

    long long dijkstra_k_threshold = 24500;
    if (k <= dijkstra_k_threshold) {
        solve_dijkstra_min();
    } else if (n * n - k + 1 <= dijkstra_k_threshold) {
        solve_dijkstra_max();
    } else {
        solve_binary_search();
    }

    return 0;
}