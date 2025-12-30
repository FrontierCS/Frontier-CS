#include <iostream>
#include <vector>
#include <algorithm>
#include <queue>
#include <tuple>

using namespace std;

// Function to perform a query
long long query(int r, int c) {
    cout << "QUERY " << r << " " << c << endl;
    long long v;
    cin >> v;
    return v;
}

// Function to submit the final answer
void done(long long ans) {
    cout << "DONE " << ans << endl;
}

long long n;
long long k;

// Heap-based solution for small k
void solve_heap_rev() {
    priority_queue<tuple<long long, int, int>, vector<tuple<long long, int, int>>, greater<tuple<long long, int, int>>> pq;
    for (int i = 1; i <= n; ++i) {
        pq.emplace(query(i, 1), i, 1);
    }
    for (int i = 0; i < k - 1; ++i) {
        auto [val, r, c] = pq.top();
        pq.pop();
        if (c < n) {
            pq.emplace(query(r, c + 1), r, c + 1);
        }
    }
    done(get<0>(pq.top()));
}

// Heap-based solution for large k
void solve_heap() {
    priority_queue<tuple<long long, int, int>> pq;
    for (int i = 1; i <= n; ++i) {
        pq.emplace(query(i, n), i, n);
    }

    long long k_rev = n * n - k + 1;
    for (int i = 0; i < k_rev - 1; ++i) {
        auto [val, r, c] = pq.top();
        pq.pop();
        if (c > 1) {
            pq.emplace(query(r, c - 1), r, c - 1);
        }
    }
    done(get<0>(pq.top()));
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> k;

    // Use heap method if k is small enough
    if (n + k - 1 <= 50000) {
        solve_heap_rev();
        return 0;
    }
    
    // Use heap method if k is large enough (k-th smallest is (n*n-k+1)-th largest)
    if (n + (n * n - k + 1) - 1 <= 50000) {
        solve_heap();
        return 0;
    }

    // General case: divide and conquer
    vector<int> L(n + 1, 1), R(n + 1, n);
    long long k_rem = k;

    while (true) {
        vector<pair<long long, int>> pivots;
        
        vector<int> active_rows;
        for (int i = 1; i <= n; ++i) {
            if (L[i] <= R[i]) {
                active_rows.push_back(i);
            }
        }

        if (active_rows.empty()) {
            break; 
        }

        for (int r : active_rows) {
            int mid_col = L[r] + (R[r] - L[r]) / 2;
            pivots.push_back({query(r, mid_col), r});
        }
        
        sort(pivots.begin(), pivots.end());
        long long pivot_val = pivots[pivots.size() / 2].first;

        vector<int> pos_le(n + 1);
        vector<int> pos_lt(n + 1);
        
        int j = n;
        for (int i = 1; i <= n; ++i) {
            if (L[i] > R[i]) {
                pos_le[i] = L[i] - 1;
                continue;
            }
            if (j > R[i]) j = R[i];
            while (j >= L[i] && query(i, j) > pivot_val) {
                j--;
            }
            pos_le[i] = j;
        }

        j = n;
        for (int i = 1; i <= n; ++i) {
            if (L[i] > R[i]) {
                pos_lt[i] = L[i] - 1;
                continue;
            }
            if (j > R[i]) j = R[i];
            while (j >= L[i] && query(i, j) >= pivot_val) {
                j--;
            }
            pos_lt[i] = j;
        }
        
        long long count_le = 0;
        long long count_lt = 0;
        for (int i = 1; i <= n; ++i) {
            if (pos_le[i] >= L[i]) {
                count_le += pos_le[i] - L[i] + 1;
            }
            if (pos_lt[i] >= L[i]) {
                count_lt += pos_lt[i] - L[i] + 1;
            }
        }

        if (k_rem <= count_lt) {
            for (int i = 1; i <= n; ++i) {
                R[i] = pos_lt[i];
            }
        } else if (k_rem > count_le) {
            k_rem -= count_le;
            for (int i = 1; i <= n; ++i) {
                L[i] = pos_le[i] + 1;
            }
        } else {
            done(pivot_val);
            return 0;
        }
    }

    return 0;
}