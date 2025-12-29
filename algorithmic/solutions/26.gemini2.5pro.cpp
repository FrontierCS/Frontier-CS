#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

const long long INF = 1e18;

struct FenwickTree {
    std::vector<int> bit;
    int size;

    FenwickTree(int n) : size(n + 1), bit(n + 1, 0) {}

    void update(int idx, int delta) {
        for (; idx < size; idx += idx & -idx) {
            bit[idx] += delta;
        }
    }

    int query(int idx) {
        int sum = 0;
        for (; idx > 0; idx -= idx & -idx) {
            sum += bit[idx];
        }
        return sum;
    }
};

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> v(n + 1);
    std::vector<int> pos(n + 1, 0);
    bool is_sorted = true;
    for (int i = 1; i <= n; ++i) {
        std::cin >> v[i];
        pos[v[i]] = i;
        if (v[i] != i) {
            is_sorted = false;
        }
    }

    if (n == 0) {
        std::cout << "1 0\n";
        return 0;
    }
    if (is_sorted) {
        std::cout << "1 0\n";
        return 0;
    }
    
    std::vector<long long> max_sum(n + 1, 0);
    std::vector<int> last_val(n + 1, 0);
    std::vector<std::vector<long long>> dp_sum(n + 1, std::vector<long long>(n + 1, 0));
    std::vector<std::vector<int>> pred_val(n + 1, std::vector<int>(n + 1, 0));

    for (int i = 1; i <= n; ++i) {
        int val = v[i];
        dp_sum[1][val] = val;
    }
    for(int val = 1; val <= n; ++val){
        if (dp_sum[1][val] > max_sum[1]) {
            max_sum[1] = dp_sum[1][val];
            last_val[1] = val;
        }
    }

    for (int l = 2; l <= n; ++l) {
        std::vector<long long> prefix_max_sum(n + 1, 0);
        std::vector<int> prefix_max_val(n + 1, 0);
        for (int val = 1; val <= n; ++val) {
            prefix_max_sum[val] = prefix_max_sum[val - 1];
            prefix_max_val[val] = prefix_max_val[val - 1];
            if (dp_sum[l-1][val] > prefix_max_sum[val]) {
                prefix_max_sum[val] = dp_sum[l-1][val];
                prefix_max_val[val] = val;
            }
        }
        
        for (int cur_v = 1; cur_v <= n; ++cur_v) {
            if (pos[cur_v] > 0) {
                if (prefix_max_sum[cur_v - 1] > 0) {
                    dp_sum[l][cur_v] = cur_v + prefix_max_sum[cur_v - 1];
                    pred_val[l][cur_v] = prefix_max_val[cur_v-1];
                    if (dp_sum[l][cur_v] > max_sum[l]) {
                        max_sum[l] = dp_sum[l][cur_v];
                        last_val[l] = cur_v;
                    }
                }
            }
        }
    }

    long long min_final_cost = -1;
    int best_len = 0;

    for (int l = 0; l <= n; ++l) {
        if (l > 0 && max_sum[l] == 0) continue;
        long long k = n - l;
        long long current_sum = (l == 0) ? 0 : max_sum[l];
        long long total_cost = (long long)n - l + (long long)n * l - current_sum - (long long)l * (l - 1) / 2;
        long long final_cost = (total_cost + 1) * (k + 1);

        if (min_final_cost == -1 || final_cost < min_final_cost) {
            min_final_cost = final_cost;
            best_len = l;
        }
    }
    
    std::vector<int> s_keep;
    std::vector<bool> to_keep(n + 1, false);
    if (best_len > 0) {
        int current_val = last_val[best_len];
        for (int l = best_len; l >= 1; --l) {
            s_keep.push_back(current_val);
            to_keep[current_val] = true;
            if (l > 1) {
                current_val = pred_val[l][current_val];
            }
        }
    }
    std::sort(s_keep.begin(), s_keep.end());

    std::vector<int> s_move;
    for (int i = 1; i <= n; ++i) {
        if (!to_keep[i]) {
            s_move.push_back(i);
        }
    }
    std::sort(s_move.rbegin(), s_move.rend());

    std::cout << min_final_cost << " " << s_move.size() << "\n";

    FenwickTree ft(n + 1);
    for(int i = 1; i <= n; ++i) {
        ft.update(i, 1);
    }
    
    std::vector<int> current_v = v;
    std::vector<int> current_pos = pos;

    for (int m : s_move) {
        int x_current = -1;
        for(int i=1; i<=current_v.size()-1; ++i){
             if(current_v[i] == m){
                 x_current = i;
                 break;
             }
        }

        long long y = 1;
        auto it = std::lower_bound(s_keep.begin(), s_keep.end(), m);
        y += (it - s_keep.begin());
        for (int moved_val : s_move) {
            if (moved_val > m && moved_val < m) { 
                // This logic is tricky. The simpler cost formula is better.
            }
        }
        
        // Cost calc from formula is simpler and more robust.
        int moved_count = 0;
        for(int moved_val : s_move) {
            if (moved_val > m) moved_count++;
        }
        y += moved_count;

        std::cout << x_current << " " << y << "\n";
        
        std::vector<int> next_v;
        next_v.push_back(0); // 1-indexed
        for(int i=1; i < current_v.size(); ++i){
            if(current_v[i] != m) next_v.push_back(current_v[i]);
        }
        next_v.insert(next_v.begin() + y, m);
        current_v = next_v;
    }

    return 0;
}