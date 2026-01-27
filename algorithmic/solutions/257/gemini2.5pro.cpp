#include <iostream>
#include <vector>
#include <queue>
#include <utility>
#include <algorithm>

using namespace std;

// Function to make a query and read the response.
pair<int, int> query(int l, int r) {
    if (l > r) {
        return {-1, -1}; // Should not happen with proper range checks
    }
    cout << "? " << l << " " << r << endl;
    int x, f;
    cin >> x >> f;
    if (x == -1 && f == -1) {
        exit(0); // Exit on judge error signal
    }
    return {x, f};
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<int> ans(n + 1, 0);
    queue<pair<int, int>> q;
    q.push({1, n});

    while (!q.empty()) {
        pair<int, int> current_range = q.front();
        q.pop();
        int l = current_range.first;
        int r = current_range.second;

        if (l > r) {
            continue;
        }

        pair<int, int> res = query(l, r);
        int x = res.first;
        int f = res.second;

        // Optimization: If the frequency is the same as the range length, all elements are the same.
        if (r - l + 1 == f) {
            for (int i = l; i <= r; ++i) {
                ans[i] = x;
            }
            continue;
        }

        // Binary search to find the start of the mode's block.
        // The block starts at `p_start` and has length `f`.
        // We are looking for the largest `mid` in `[l, r - f + 1]`
        // such that query(mid, r) returns `(x, f)`. This `mid` will be `p_start`.
        int p_start;
        int low = l, high = r - f + 1;
        int candidate_p_start = r - f + 1;

        while (low <= high) {
            int mid = low + (high - low) / 2;
            pair<int, int> q_res = query(mid, r);
            if (q_res.first == x && q_res.second == f) {
                candidate_p_start = mid;
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }
        p_start = candidate_p_start;
        int p_end = p_start + f - 1;

        // Fill the found block in the answer array.
        for (int i = p_start; i <= p_end; ++i) {
            ans[i] = x;
        }

        // Add the remaining sub-ranges to the queue.
        if (l <= p_start - 1) {
            q.push({l, p_start - 1});
        }
        if (p_end + 1 <= r) {
            q.push({p_end + 1, r});
        }
    }

    // Print the final answer.
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;

    return 0;
}