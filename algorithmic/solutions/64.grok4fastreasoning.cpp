#include <bits/stdc++.h>
using namespace std;

struct Item {
    long long val;
    int idx;
};

int main() {
    int n;
    long long T;
    cin >> n >> T;
    vector<long long> a(n);
    for (auto &x : a) cin >> x;
    vector<Item> items(n);
    for (int i = 0; i < n; i++) {
        items[i].val = a[i];
        items[i].idx = i;
    }
    sort(items.begin(), items.end(), [](const Item &x, const Item &y) {
        return x.val > y.val;
    });
    vector<long long> rem_sum(n + 1, 0);
    for (int i = n - 1; i >= 0; i--) {
        rem_sum[i] = rem_sum[i + 1] + items[i].val;
    }
    vector<char> best_selected(n, 0);
    long long best_error = abs(0LL - T);
    // greedy <= T
    vector<Item> gitems = items;
    long long gsum = 0;
    vector<char> gsel(n, 0);
    for (auto &p : gitems) {
        long long val = p.val;
        int id = p.idx;
        if (gsum + val <= T) {
            gsum += val;
            gsel[id] = 1;
        }
    }
    long long ge = abs(gsum - T);
    if (ge < best_error) {
        best_error = ge;
        best_selected = gsel;
    }
    // full
    long long tot = 0;
    for (auto x : a) tot += x;
    long long fe = abs(tot - T);
    if (fe < best_error) {
        best_error = fe;
        fill(best_selected.begin(), best_selected.end(), 1);
    }
    // current
    vector<char> current(n, 0);
    // dfs
    function<void(int, long long)> dfs = [&](int pos, long long cursum) {
        if (pos == n) {
            long long err = abs(cursum - T);
            if (err < best_error) {
                best_error = err;
                best_selected = current;
            }
            return;
        }
        // prune
        long long lo = cursum;
        long long hi = cursum + rem_sum[pos];
        long long min_err = 0;
        if (T < lo) min_err = lo - T;
        else if (T > hi) min_err = T - hi;
        if (min_err >= best_error) return;
        // not include
        dfs(pos + 1, cursum);
        // include
        int id = items[pos].idx;
        current[id] = 1;
        dfs(pos + 1, cursum + items[pos].val);
        current[id] = 0;
    };
    dfs(0, 0LL);
    // output
    for (int i = 0; i < n; i++) {
        cout << (int)best_selected[i];
    }
    cout << endl;
    return 0;
}