#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <stack>

using namespace std;

// A cache for query results to avoid redundant queries, though its effectiveness might vary.
map<pair<int, int>, pair<int, int>> query_cache;

// Helper function to perform a query. It's 1-indexed as per the problem statement.
pair<int, int> do_query(int l, int r) {
    if (l > r) {
        return {-1, 0};
    }
    if (query_cache.count({l, r})) {
        return query_cache[{l, r}];
    }
    cout << "? " << l << " " << r << endl;
    int x, f;
    cin >> x >> f;
    if (x == -1 && f == -1) {
        // This case indicates an error, such as an invalid query.
        exit(0);
    }
    return query_cache[{l, r}] = {x, f};
}

// The final answer array, 1-indexed for convenience.
vector<int> ans;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    ans.resize(n + 1, 0);

    // Use a stack for an iterative divide-and-conquer process to avoid stack overflow.
    stack<pair<int, int>> ranges_to_solve;
    ranges_to_solve.push({1, n});

    while (!ranges_to_solve.empty()) {
        pair<int, int> range = ranges_to_solve.top();
        ranges_to_solve.pop();

        int l = range.first;
        int r = range.second;

        if (l > r) {
            continue;
        }

        pair<int, int> res = do_query(l, r);
        int x = res.first;
        int f = res.second;
        
        // Binary search to find the rightmost boundary 'end_pos' of the mode's block.
        // The search space for end_pos is [l + f - 1, r].
        // We are looking for the smallest `mid` in this range such that a query on `[l, mid]`
        // reveals that the block of `x`s is contained within it.
        int end_pos = r;
        int low = l + f - 1, high = r;
        
        while(low <= high) {
            int mid = low + (high - low) / 2;
            pair<int, int> q_res = do_query(l, mid);
            if (q_res.first == x && q_res.second >= f) {
                end_pos = mid;
                high = mid - 1;
            } else {
                low = mid + 1;
            }
        }
        
        int start_pos = end_pos - f + 1;

        // Fill the determined block in the answer array.
        for(int i = start_pos; i <= end_pos; ++i) {
            ans[i] = x;
        }
        
        // Push the remaining sub-ranges onto the stack to be solved.
        ranges_to_solve.push({l, start_pos - 1});
        ranges_to_solve.push({end_pos + 1, r});
    }

    // Output the final answer.
    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << ans[i] << (i == n ? "" : " ");
    }
    cout << endl;

    return 0;
}