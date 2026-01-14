#include <iostream>
#include <vector>
#include <algorithm>
#include <functional>

void print_sequence(const std::vector<int>& s) {
    for (size_t i = 0; i < s.size(); ++i) {
        std::cout << s[i] << (i == s.size() - 1 ? "" : " ");
    }
    std::cout << "\n";
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;
    std::vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> p[i];
    }

    std::vector<int> tails_a, tails_c;
    std::vector<int> tails_b, tails_d;
    std::vector<int> group(n);

    for (int i = 0; i < n; ++i) {
        int val = p[i];
        
        int pos_a = std::lower_bound(tails_a.begin(), tails_a.end(), val) - tails_a.begin();
        int pos_b = std::lower_bound(tails_b.begin(), tails_b.end(), val, std::greater<int>()) - tails_b.begin();
        int pos_c = std::lower_bound(tails_c.begin(), tails_c.end(), val) - tails_c.begin();
        int pos_d = std::lower_bound(tails_d.begin(), tails_d.end(), val, std::greater<int>()) - tails_d.begin();

        int potentials[] = {pos_a, pos_b, pos_c, pos_d};
        int max_potential = -1;
        for (int pot : potentials) {
            if (pot > max_potential) {
                max_potential = pot;
            }
        }
        
        std::vector<int> candidates;
        for (int j = 0; j < 4; ++j) {
            if (potentials[j] == max_potential) {
                candidates.push_back(j);
            }
        }
        
        int best_group = -1;
        size_t min_size = n + 1;

        for (int cand_group : candidates) {
            size_t current_size;
            if (cand_group == 0) current_size = tails_a.size();
            else if (cand_group == 1) current_size = tails_b.size();
            else if (cand_group == 2) current_size = tails_c.size();
            else current_size = tails_d.size();
            
            if (current_size < min_size) {
                min_size = current_size;
                best_group = cand_group;
            }
        }
        
        group[i] = best_group;
        if (best_group == 0) {
            if (pos_a == tails_a.size()) tails_a.push_back(val); else tails_a[pos_a] = val;
        } else if (best_group == 1) {
            if (pos_b == tails_b.size()) tails_b.push_back(val); else tails_b[pos_b] = val;
        } else if (best_group == 2) {
            if (pos_c == tails_c.size()) tails_c.push_back(val); else tails_c[pos_c] = val;
        } else { // best_group == 3
            if (pos_d == tails_d.size()) tails_d.push_back(val); else tails_d[pos_d] = val;
        }
    }

    std::vector<int> sub_a_vals, sub_b_vals, sub_c_vals, sub_d_vals;
    for (int i = 0; i < n; ++i) {
        if (group[i] == 0) sub_a_vals.push_back(p[i]);
        else if (group[i] == 1) sub_b_vals.push_back(p[i]);
        else if (group[i] == 2) sub_c_vals.push_back(p[i]);
        else sub_d_vals.push_back(p[i]);
    }

    std::cout << sub_a_vals.size() << " " << sub_b_vals.size() << " " << sub_c_vals.size() << " " << sub_d_vals.size() << "\n";
    print_sequence(sub_a_vals);
    print_sequence(sub_b_vals);
    print_sequence(sub_c_vals);
    print_sequence(sub_d_vals);

    return 0;
}