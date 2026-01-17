#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

struct Run {
    int start, end;
    ll min_val, max_val;
    int length() const { return end - start + 1; }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n, x;
    cin >> n >> x;
    vector<int> t(n);
    for (int i=0; i<n; i++) cin >> t[i];

    if (x == 0) {
        vector<int> tails;
        for (int val : t) {
            auto it = lower_bound(tails.begin(), tails.end(), val);
            if (it == tails.end()) tails.push_back(val);
            else *it = val;
        }
        int lis_len = tails.size();
        cout << lis_len << "\n";
        for (int i=0; i<10; i++) cout << "1 1 0\n";
        return 0;
    }

    vector<Run> runs;
    int start = 0;
    for (int i=1; i<=n; i++) {
        if (i == n || t[i] <= t[i-1]) {
            ll min_val = t[start], max_val = t[start];
            for (int j=start+1; j<i; j++) {
                if (t[j] < min_val) min_val = t[j];
                if (t[j] > max_val) max_val = t[j];
            }
            runs.push_back({start+1, i, min_val, max_val});
            start = i;
        }
    }

    int m = runs.size();
    vector<ll> required(m-1, 0);
    vector<int> cost(m-1, 0);
    for (int i=0; i<m-1; i++) {
        ll D = runs[i].max_val - runs[i+1].min_val;
        if (D >= 0) {
            required[i] = D + 1;
            cost[i] = (required[i] + x - 1) / x;
            if (cost[i] > 10) cost[i] = 11;
        }
    }

    int left = 0, right = 0;
    int current_cost = 0, current_len = 0;
    int best_len = 0, best_l = 0, best_r = -1;
    while (right < m) {
        current_len += runs[right].length();
        if (right > 0) current_cost += cost[right-1];
        while (current_cost > 10) {
            current_len -= runs[left].length();
            if (left > 0) current_cost -= cost[left-1];
            left++;
        }
        if (current_len > best_len) {
            best_len = current_len;
            best_l = left;
            best_r = right;
        }
        right++;
    }

    int used_cost = 0;
    for (int i=best_l; i<best_r; i++) used_cost += cost[i];
    int remaining_ops = 10 - used_cost;

    int current_end = best_r;
    for (int i=best_r; i < m-1; i++) {
        if (cost[i] == 0) {
            current_end = i+1;
        } else if (remaining_ops >= cost[i]) {
            remaining_ops -= cost[i];
            current_end = i+1;
        } else {
            break;
        }
    }

    int current_start = best_l;
    for (int i=best_l-1; i>=0; i--) {
        if (runs[i].max_val < runs[current_start].min_val) {
            current_start = i;
        } else {
            break;
        }
    }

    int