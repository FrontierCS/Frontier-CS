#include <iostream>
#include <vector>
#include <string>
#include <functional>
#include <algorithm>

using namespace std;

// Wrapper for queries to handle potential judge errors.
pair<int, int> do_query(int l, int r) {
    if (l > r) {
        return {-1, -1};
    }
    cout << "? " << l << " " << r << endl;
    int x, f;
    cin >> x >> f;
    if (x == -1 && f == -1) {
        exit(0);
    }
    return {x, f};
}

vector<int> final_ans;

void solve(int l, int r) {
    if (l > r) {
        return;
    }

    pair<int, int> res = do_query(l, r);
    int x = res.first;
    int f = res.second;

    // We know a block of `f` elements with value `x` exists in `a[l...r]`.
    // Let this block be `a[p...p_end]`, where `p_end = p + f - 1`.
    // We can find `p_end` by binary searching for the smallest `m` such that `a[l...m]`
    // contains all `f` occurrences of `x`. A query on `? l m` will return mode `x`
    // with frequency `f` if and only if `p_end <= m`.
    
    int low = l + f - 1, high = r;
    int p_end = -1;

    while (low <= high) {
        int mid = low + (high - low) / 2;
        pair<int, int> q_res = do_query(l, mid);
        if (q_res.first == x && q_res.second == f) {
            p_end = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }
    
    int p = p_end - f + 1;
    for (int i = 0; i < f; ++i) {
        final_ans[p + i - 1] = x; // Convert 1-based index to 0-based
    }

    solve(l, p - 1);
    solve(p + f, r);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    final_ans.resize(n);
    
    solve(1, n);

    cout << "! ";
    for (int i = 0; i < n; ++i) {
        cout << final_ans[i] << (i == n - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}