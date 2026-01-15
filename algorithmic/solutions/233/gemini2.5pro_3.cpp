#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>

using namespace std;

int n;
long long m;
vector<vector<int>> grid;

long long count_le(int v) {
    if (v < 1) return 0;
    vector<vector<int>> len(n + 1, vector<int>(n + 1, 0));
    long long count = 0;

    for (int t = 2; t <= 2 * n; ++t) { // t = r + c, corresponds to time T = t - 1
        int max_len_t = 0;
        for (int r = 1; r <= n; ++r) {
            int c = t - r;
            if (c < 1 || c > n) continue;

            if (grid[r - 1][c - 1] <= v) {
                int prev_max_len = 0;
                if (r > 1) { // from (r-1, c)
                    prev_max_len = max(prev_max_len, len[r - 1][c]);
                }
                if (c > 1) { // from (r, c-1)
                    prev_max_len = max(prev_max_len, len[r][c - 1]);
                }
                len[r][c] = 1 + prev_max_len;
            }
            max_len_t = max(max_len_t, len[r][c]);
        }
        count += min(n, max_len_t);
    }
    return count;
}


void solve() {
    cin >> n >> m;
    grid.assign(n, vector<int>(n));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cin >> grid[i][j];
        }
    }

    int low = 1, high = n * n, V = n * n;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (count_le(mid) >= m) {
            V = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }
    
    vector<vector<int>> len(n + 1, vector<int>(n + 1, 0));
    vector<int> max_len_at_T(2 * n, 0);

    for (int t = 2; t <= 2 * n; ++t) { // t = r + c
        int max_len_t = 0;
        for (int r = 1; r <= n; ++r) {
            int c = t - r;
            if (c < 1 || c > n) continue;
            
            if (grid[r - 1][c - 1] <= V) {
                int prev_max_len = 0;
                if (r > 1) {
                    prev_max_len = max(prev_max_len, len[r - 1][c]);
                }
                if (c > 1) {
                    prev_max_len = max(prev_max_len, len[r][c - 1]);
                }
                len[r][c] = 1 + prev_max_len;
            }
            max_len_t = max(max_len_t, len[r][c]);
        }
        max_len_at_T[t - 1] = min(n, max_len_t);
    }

    vector<int> candidates;
    for (int T = 1; T <= 2 * n - 1; ++T) {
        for (int l = 1; l <= max_len_at_T[T]; ++l) {
            cout << "? " << l << " " << T << endl;
            int val;
            cin >> val;
            candidates.push_back(val);
        }
    }

    sort(candidates.begin(), candidates.end());

    cout << "! ";
    for (int i = 0; i < m; ++i) {
        cout << candidates[i] << (i == m - 1 ? "" : " ");
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}