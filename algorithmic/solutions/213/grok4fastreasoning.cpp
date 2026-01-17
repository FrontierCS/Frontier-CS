#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
    }
    if (n == 1) {
        cout << 1 << " " << 0 << endl;
        return 0;
    }
    int x = (n <= 3 ? 2 : 4);
    vector<tuple<int, int, int>> operations;
    vector<int> original_a = a; // for potential verification, but not used
    int current_pos = 1;
    int r = x - 1;
    if (n <= 3) {
        // Place all
        while (current_pos <= n) {
            int t = -1;
            for (int j = current_pos; j <= n; ++j) {
                if (a[j] == current_pos) {
                    t = j;
                    break;
                }
            }
            int dd = t - current_pos;
            int num_big = dd / r;
            for (int b = 0; b < num_big; ++b) {
                int l = t - x + 1;
                int rr = t;
                // apply right shift
                int temp = a[t];
                for (int j = t; j > l; --j) {
                    a[j] = a[j - 1];
                }
                a[l] = temp;
                operations.emplace_back(l, rr, 1);
                t = l;
            }
            int remain = dd % r;
            int ll_start = current_pos;
            int rr_start = min(n, current_pos + x - 1);
            for (int ss = 0; ss < remain; ++ss) {
                int temp = a[ll_start];
                for (int j = ll_start; j < rr_start; ++j) {
                    a[j] = a[j + 1];
                }
                a[rr_start] = temp;
                operations.emplace_back(ll_start, rr_start, 0);
            }
            ++current_pos;
        }
    } else {
        // n >= 4, x=4, place up to n-3
        while (current_pos <= n - 3) {
            int t = -1;
            for (int j = current_pos; j <= n; ++j) {
                if (a[j] == current_pos) {
                    t = j;
                    break;
                }
            }
            int dd = t - current_pos;
            int num_big = dd / r;
            for (int b = 0; b < num_big; ++b) {
                int l = t - x + 1;
                int rr = t;
                // apply
                int temp = a[t];
                for (int j = t; j > l; --j) {
                    a[j] = a[j - 1];
                }
                a[l] = temp;
                operations.emplace_back(l, rr, 1);
                t = l;
            }
            int remain = dd % r;
            int ll_start = current_pos;
            int rr_start = current_pos + x - 1;
            for (int ss = 0; ss < remain; ++ss) {
                int temp = a[ll_start];
                for (int j = ll_start; j < rr_start; ++j) {
                    a[j] = a[j + 1];
                }
                a[rr_start] = temp;
                operations.emplace_back(ll_start, rr_start, 0);
            }
            ++current_pos;
        }
        // now special for last 3: positions n-2 to n
        int s = n - 2;
        int aff_start = max(1, s - 3);
        int aff_len = n - aff_start + 1;
        vector<int> initial(aff_len);
        for (int j = 0; j < aff_len; ++j) {
            initial[j] = a[aff_start + j];
        }
        vector<int> targ(aff_len);
        for (int j = 0; j < aff_len; ++j) {
            targ[j] = aff_start + j;
        }
        // BFS
        map<vector<int>, pair<vector<int>, pair<int, int>>> came_from;
        queue<vector<int>> q;
        q.push(initial);
        came_from[initial] = {{}, {-1, -1}};
        vector<int> goal_state;
        bool found = false;
        int max_l = n - x + 1;
        while (!q.empty() && !found) {
            vector<int> state = q.front();
            q.pop();
            if (state == targ) {
                found = true;
                goal_state = state;
                break;
            }
            for (int ll = aff_start; ll <= max_l; ++ll) {
                for (int d = 0; d < 2; ++d) {
                    vector<int> new_s = state;
                    int left_idx = ll - aff_start;
                    int right_idx = left_idx + x - 1;
                    if (d == 0) { // left
                        int firstv = new_s[left_idx];
                        for (int jj = left_idx; jj < right_idx; ++jj) {
                            new_s[jj] = new_s[jj + 1];
                        }
                        new_s[right_idx] = firstv;
                    } else { // right
                        int lastv = new_s[right_idx];
                        for (int jj = right_idx; jj > left_idx; --jj) {
                            new_s[jj] = new_s[jj - 1];
                        }
                        new_s[left_idx] = lastv;
                    }
                    if (came_from.find(new_s) == came_from.end()) {
                        came_from[new_s] = {state, {ll, d}};
                        q.push(new_s);
                    }
                }
            }
        }
        // reconstruct
        vector<tuple<int, int, int>> special_ops;
        if (found) {
            vector<int> cur = targ;
            while (cur != initial) {
                auto p = came_from[cur];
                vector<int> prevv = p.first;
                pair<int, int> op = p.second;
                int ll = op.first;
                int d = op.second;
                int rr = ll + x - 1;
                special_ops.emplace_back(ll, rr, d);
                cur = prevv;
            }
            reverse(special_ops.begin(), special_ops.end());
            // now apply to a to update
            for (auto& op : special_ops) {
                int ll, rr, d;
                tie(ll, rr, d) = op;
                if (d == 0) { // left
                    int temp = a[ll];
                    for (int j = ll; j < rr; ++j) {
                        a[j] = a[j + 1];
                    }
                    a[rr] = temp;
                } else { // right
                    int temp = a[rr];
                    for (int j = rr; j > ll; --j) {
                        a[j] = a[j - 1];
                    }
                    a[ll] = temp;
                }
                operations.push_back(op);
            }
        } else {
            // should not happen
            assert(false);
        }
    }
    // output
    int m = operations.size();
    cout << x << " " << m << endl;
    for (auto& op : operations) {
        int l, r, d;
        tie(l, r, d) = op;
        cout << l << " " << r << " " << d << endl;
    }
    return 0;
}