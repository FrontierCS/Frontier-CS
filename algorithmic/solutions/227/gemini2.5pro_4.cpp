#include <iostream>
#include <vector>
#include <algorithm>
#include <functional>

const int INF = 1e9 + 7;
const int N_INF = -1e9 - 7;

struct LIS_Manager {
    const std::vector<int>& p_ref;
    std::vector<int> tails_indices;
    
    LIS_Manager(const std::vector<int>& p) : p_ref(p) {}

    bool can_extend(int val) const {
        if (tails_indices.empty()) return true;
        return val > p_ref[tails_indices.back()];
    }

    void extend(int idx) {
        tails_indices.push_back(idx);
    }
    
    std::pair<int, int> get_replace_info(int val) const {
        auto it = std::lower_bound(tails_indices.begin(), tails_indices.end(), val, [&](int idx, int v){
            return p_ref[idx] < v;
        });
        int len = std::distance(tails_indices.begin(), it) + 1;
        int tail_val = (it == tails_indices.end()) ? INF : p_ref[*it];
        return {len, tail_val};
    }

    void replace(int idx, int& pred_idx_out) {
        auto it = std::lower_bound(tails_indices.begin(), tails_indices.end(), p_ref[idx], [&](int i, int v){
            return p_ref[i] < v;
        });
        if (it == tails_indices.begin()) {
            pred_idx_out = 0;
        } else {
            pred_idx_out = *std::prev(it);
        }
        *it = idx;
    }
};

struct LDS_Manager {
    const std::vector<int>& p_ref;
    std::vector<int> tails_indices;
    
    LDS_Manager(const std::vector<int>& p) : p_ref(p) {}

    bool can_extend(int val) const {
        if (tails_indices.empty()) return true;
        return val < p_ref[tails_indices.back()];
    }

    void extend(int idx) {
        tails_indices.push_back(idx);
    }
    
    std::pair<int, int> get_replace_info(int val) const {
        auto it = std::lower_bound(tails_indices.begin(), tails_indices.end(), val, [&](int idx, int v){
            return p_ref[idx] > v;
        });
        int len = std::distance(tails_indices.begin(), it) + 1;
        int tail_val = (it == tails_indices.end()) ? N_INF : p_ref[*it];
        return {len, tail_val};
    }

    void replace(int idx, int& pred_idx_out) {
        auto it = std::lower_bound(tails_indices.begin(), tails_indices.end(), p_ref[idx], [&](int i, int v){
            return p_ref[i] > v;
        });
        if (it == tails_indices.begin()) {
            pred_idx_out = 0;
        } else {
            pred_idx_out = *std::prev(it);
        }
        *it = idx;
    }
};

void solve() {
    int n;
    std::cin >> n;
    std::vector<int> p_with_dummy(n + 1);
    for (int i = 0; i < n; ++i) {
        std::cin >> p_with_dummy[i + 1];
    }
    
    LIS_Manager manager_a(p_with_dummy);
    LDS_Manager manager_b(p_with_dummy);
    LIS_Manager manager_c(p_with_dummy);
    LDS_Manager manager_d(p_with_dummy);

    std::vector<int> group(n + 1, 0);

    for (int i = 1; i <= n; ++i) {
        int current_val = p_with_dummy[i];
        
        bool extended = false;
        if (manager_a.can_extend(current_val)) {
            manager_a.extend(i);
            group[i] = 1;
            extended = true;
        } else if (manager_b.can_extend(current_val)) {
            manager_b.extend(i);
            group[i] = 2;
            extended = true;
        } else if (manager_c.can_extend(current_val)) {
            manager_c.extend(i);
            group[i] = 3;
            extended = true;
        } else if (manager_d.can_extend(current_val)) {
            manager_d.extend(i);
            group[i] = 4;
            extended = true;
        }

        if (extended) continue;

        auto info_a = manager_a.get_replace_info(current_val);
        auto info_b = manager_b.get_replace_info(current_val);
        auto info_c = manager_c.get_replace_info(current_val);
        auto info_d = manager_d.get_replace_info(current_val);

        int max_len = std::max({info_a.first, info_b.first, info_c.first, info_d.first});
        
        int best_lis_choice = -1;
        int lis_tail_val = N_INF;
        if (info_a.first == max_len) {
            best_lis_choice = 1;
            lis_tail_val = info_a.second;
        }
        if (info_c.first == max_len) {
            if (best_lis_choice == -1 || info_c.second >= lis_tail_val) {
                best_lis_choice = 3;
            }
        }
        
        int best_lds_choice = -1;
        int lds_tail_val = INF;
        if (info_b.first == max_len) {
            best_lds_choice = 2;
            lds_tail_val = info_b.second;
        }
        if (info_d.first == max_len) {
            if (best_lds_choice == -1 || info_d.second <= lds_tail_val) {
                best_lds_choice = 4;
            }
        }

        std::vector<bool> final_candidates(5, false);
        if(best_lis_choice != -1) final_candidates[best_lis_choice] = true;
        if(best_lds_choice != -1) final_candidates[best_lds_choice] = true;
        
        int best_choice = 0;
        if (final_candidates[1]) best_choice = 1;
        else if (final_candidates[2]) best_choice = 2;
        else if (final_candidates[3]) best_choice = 3;
        else if (final_candidates[4]) best_choice = 4;
        
        group[i] = best_choice;
        int dummy_pred; // Not needed for this problem version
        if (best_choice == 1) manager_a.replace(i, dummy_pred);
        else if (best_choice == 2) manager_b.replace(i, dummy_pred);
        else if (best_choice == 3) manager_c.replace(i, dummy_pred);
        else if (best_choice == 4) manager_d.replace(i, dummy_pred);
    }

    std::vector<int> a, b, c, d;
    for (int i = 1; i <= n; ++i) {
        if (group[i] == 1) a.push_back(p_with_dummy[i]);
        else if (group[i] == 2) b.push_back(p_with_dummy[i]);
        else if (group[i] == 3) c.push_back(p_with_dummy[i]);
        else if (group[i] == 4) d.push_back(p_with_dummy[i]);
    }

    std::cout << a.size() << " " << b.size() << " " << c.size() << " " << d.size() << "\n";
    for (size_t i = 0; i < a.size(); ++i) std::cout << a[i] << (i == a.size() - 1 ? "" : " "); std::cout << "\n";
    for (size_t i = 0; i < b.size(); ++i) std::cout << b[i] << (i == b.size() - 1 ? "" : " "); std::cout << "\n";
    for (size_t i = 0; i < c.size(); ++i) std::cout << c[i] << (i == c.size() - 1 ? "" : " "); std::cout << "\n";
    for (size_t i = 0; i < d.size(); ++i) std::cout << d[i] << (i == d.size() - 1 ? "" : " "); std::cout << "\n";
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}